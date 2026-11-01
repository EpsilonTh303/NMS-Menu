import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest

from nmsmenu.live import LiveBackend, ROOT_RVA
from nmsmenu.live_fleet import LiveFleet, project_inventory, unpack_inventory
from test_live import FakeMemory


def inventory_fixture():
    header = bytearray(0x248)
    struct.pack_into('<Q', header, 0, 3)
    struct.pack_into('<Q', header, 8 * 5, 103)  # Stale row outside dimensions.
    struct.pack_into('<hhh', header, 0x80, 2, 1, 2)
    struct.pack_into('<IIQ', header, 0x88, 4, 1, 0x300000000)
    row = bytearray(48)
    row[:8] = b'LAUNCHER'
    struct.pack_into('<iiifiiBB', row, 16, 0, 0, 20, 0.5, 200, 1, 0, 1)
    return bytes(header), bytes(row)


class InventoryProjectionTests(unittest.TestCase):
    def test_ignores_stale_bits_and_preserves_them_in_noop_projection(self):
        header, items = inventory_fixture()
        before = unpack_inventory(header, items)
        self.assertEqual(before['ValidSlotIndices'], [{'X': 0, 'Y': 0}, {'X': 1, 'Y': 0}])
        self.assertEqual(project_inventory(0x1000, header, items, before, copy.deepcopy(before), '/inv'), [])

    def test_repairs_only_existing_scalar_technology_fields(self):
        header, items = inventory_fixture()
        before = unpack_inventory(header, items)
        after = copy.deepcopy(before)
        after['Slots'][0].update(Amount=200, DamageFactor=0.0)
        patches = project_inventory(0x1000, header, items, before, after, '/inv')
        self.assertEqual({patch['address'] for patch in patches}, {0x300000018, 0x30000001C})
        self.assertTrue(all(len(bytes.fromhex(patch['after'])) == 4 for patch in patches))

    def test_technology_sentinel_supported_but_negative_cargo_rejected(self):
        header, items = inventory_fixture()
        row = bytearray(items)
        struct.pack_into('<i', row, 0x18, -1)
        self.assertEqual(unpack_inventory(header, row)['Slots'][0]['Amount'], -1)
        struct.pack_into('<i', row, 0x24, 0)
        with self.assertRaises(ValueError):
            unpack_inventory(header, row)

    def test_never_shrinks_existing_valid_slots(self):
        header, items = inventory_fixture()
        before = unpack_inventory(header, items)
        after = copy.deepcopy(before)
        after['ValidSlotIndices'].pop()
        with self.assertRaises(ValueError):
            project_inventory(0x1000, header, items, before, after, '/inv')

    def test_rejects_pointer_requiring_item_creation_and_cargo_mutation(self):
        header, items = inventory_fixture()
        before = unpack_inventory(header, items)
        after = copy.deepcopy(before)
        after['Slots'].append(copy.deepcopy(after['Slots'][0]))
        with self.assertRaises(ValueError):
            project_inventory(0x1000, header, items, before, after, '/inv')
        before['Slots'][0]['Type']['InventoryType'] = 'Product'
        after = copy.deepcopy(before)
        after['Slots'][0]['Amount'] = 200
        with self.assertRaises(ValueError):
            project_inventory(0x1000, header, items, before, after, '/inv')


class LiveFleetTransactionTests(unittest.TestCase):
    def setUp(self):
        runtime = Path(__file__).resolve().parents[1] / 'runtime'
        runtime.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=runtime)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.live = LiveBackend(journal=self.root / 'audit.jsonl')
        self.memory = FakeMemory()
        self.live.memory = self.memory
        self.memory.store(self.memory.base + ROOT_RVA - 0x38 + 0xB8D5, b'\x01\x00\x00\x00')
        self.backend = LiveFleet(self.live, self.root / 'transactions')
        self.tx = self.backend.transactions / 'test-request'
        self.tx.mkdir(parents=True)
        self.address = 0x300001000
        self.memory.store(self.address, struct.pack('<I', 10))
        self.capture = {'identity': [123, 0x200000000, 0],
                        'guards': [{'address': self.address, 'bytes': struct.pack('<I', 10).hex()}]}
        self.manifest = {'state': 'prepared', 'codec_roundtrip': True, 'capture': self.capture,
                         'patches': [{'address': self.address, 'before': struct.pack('<I', 10).hex(),
                                      'after': struct.pack('<I', 20).hex(), 'path': '/tech/Amount'}]}
        self.save()

    def save(self):
        (self.tx / 'manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def test_apply_and_conditional_undo(self):
        self.backend.apply(self.tx, self.backend.fingerprint(self.tx))
        self.assertEqual(self.memory.read(self.address, 4), struct.pack('<I', 20))
        self.backend.undo(self.tx)
        self.assertEqual(self.memory.read(self.address, 4), struct.pack('<I', 10))
        self.assertEqual(json.loads((self.tx / 'manifest.json').read_text())['state'], 'restored')

    def test_any_inventory_change_blocks_apply(self):
        fingerprint = self.backend.fingerprint(self.tx)
        self.memory.store(self.address, struct.pack('<I', 11))
        with self.assertRaises(RuntimeError):
            self.backend.apply(self.tx, fingerprint)
        self.assertEqual(self.memory.writes, [])

    def test_running_simulation_or_multiplayer_blocks_apply(self):
        address = self.memory.base + ROOT_RVA - 0x38 + 0xB8D5
        for flags in (b'\x00\x00\x00\x00', b'\x01\x00\x00\x01'):
            self.memory.store(address, flags)
            with self.subTest(flags=flags), self.assertRaises(RuntimeError):
                self.backend.apply(self.tx, self.backend.fingerprint(self.tx))
        self.assertEqual(self.memory.writes, [])

    def test_changed_report_and_unchecked_codec_block_apply(self):
        fingerprint = self.backend.fingerprint(self.tx)
        self.manifest['codec_roundtrip'] = False
        self.save()
        with self.assertRaises(ValueError):
            self.backend.apply(self.tx, fingerprint)
        with self.assertRaises(ValueError):
            self.backend.apply(self.tx, self.backend.fingerprint(self.tx))
        self.assertEqual(self.memory.writes, [])

    def test_new_progress_blocks_undo(self):
        self.backend.apply(self.tx, self.backend.fingerprint(self.tx))
        self.memory.store(self.address, struct.pack('<I', 19))
        with self.assertRaises(RuntimeError):
            self.backend.undo(self.tx)
        self.assertEqual(len(self.memory.writes), 1)

    def test_write_failure_rolls_back_only_completed_changes(self):
        second = self.address + 4
        self.memory.store(second, struct.pack('<I', 30))
        self.manifest['capture']['guards'].append({'address': second, 'bytes': struct.pack('<I', 30).hex()})
        self.manifest['patches'].append({'address': second, 'before': struct.pack('<I', 30).hex(),
                                         'after': struct.pack('<I', 40).hex(), 'path': '/tech/other'})
        self.save()
        write = self.memory.write
        counter = 0

        def failing_write(address, data):
            nonlocal counter
            counter += 1
            if counter == 2:
                raise OSError('simulated write failure')
            write(address, data)
        self.memory.write = failing_write
        with self.assertRaises(OSError):
            self.backend.apply(self.tx, self.backend.fingerprint(self.tx))
        self.assertEqual(self.memory.read(self.address, 8), struct.pack('<II', 10, 30))

    def test_ownership_actions_never_reach_engine_or_memory(self):
        for action in ('add', 'remove', 'garage_import', 'auto_recharge'):
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.backend.prepare(action)
        self.assertEqual(self.memory.writes, [])


if __name__ == '__main__':
    unittest.main()
