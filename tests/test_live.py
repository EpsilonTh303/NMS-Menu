import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch

from nmsmenu.live import LiveBackend, PLAYER_GLOBALS, PLAYER_OFFSET, ROOT_RVA, SETTINGS


class FakeMemory:
    base = 0x140000000
    pid = 123

    def __init__(self):
        self.bytes = {}
        self.running = True
        self.writes = []
        self.store(self.base + 0x597739, bytes.fromhex('48 8B 0D 68 62 8F 06'))
        self.store(self.base + ROOT_RVA, struct.pack('<QII', 0x200000000, 0, 1))
        self.player = 0x200000000 + PLAYER_OFFSET
        self.store(self.player + 0x890, struct.pack('<6I', 100, 60, 500, 12345, 262, 150))
        self.store(self.player + 0x182A0, struct.pack('<I', 2))
        for field in SETTINGS.values():
            self.store(self.base + PLAYER_GLOBALS + field.offset, struct.pack('<f', 1.0))

    def store(self, address, data):
        self.bytes.update({address + i: b for i, b in enumerate(data)})

    def read(self, address, size):
        return bytes(self.bytes.get(address + i, 0) for i in range(size))

    def write(self, address, data):
        self.writes.append((address, data))
        self.store(address, data)

    def alive(self):
        return self.running

    def close(self):
        self.running = False


class LiveTests(unittest.TestCase):
    def setUp(self):
        runtime = Path(__file__).resolve().parents[1] / 'runtime'
        runtime.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=runtime)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.exe = self.base / 'NMS.exe'
        self.exe.write_bytes(b'synthetic-test-build')
        self.hash_patch = patch('nmsmenu.live.BUILD_HASH', hashlib.sha256(self.exe.read_bytes()).hexdigest())
        self.hash_patch.start()
        self.addCleanup(self.hash_patch.stop)
        self.memory = FakeMemory()
        self.factory = Mock(return_value=self.memory)
        self.live = LiveBackend(self.exe, self.base / 'audit.jsonl', self.factory)

    def test_attach_is_read_only_and_loaded_values_match(self):
        state = self.live.connect()
        self.assertTrue(state['loaded'])
        self.assertEqual(state['currencies']['Units'], 12345)
        self.assertEqual(self.memory.writes, [])

    def test_unknown_build_never_opens_process(self):
        self.exe.write_bytes(b'unknown-build')
        with self.assertRaises(RuntimeError):
            self.live.connect()
        self.factory.assert_not_called()

    def test_loaded_code_mismatch_never_writes(self):
        self.memory.store(self.memory.base + 0x597739, b'changed')
        with self.assertRaises(RuntimeError):
            self.live.connect()
        self.assertEqual(self.memory.writes, [])

    def test_main_menu_locks_currency(self):
        self.memory.store(self.memory.player + 0x890, bytes(24))
        self.assertFalse(self.live.connect()['loaded'])
        with self.assertRaises(RuntimeError):
            self.live.set_currency('Units', 100)
        self.assertEqual(self.memory.writes, [])

    def test_setting_is_restored_on_disconnect(self):
        self.live.connect()
        address = self.memory.base + PLAYER_GLOBALS + SETTINGS['walk'].offset
        before = self.memory.read(address, 4)
        self.live.set_setting('walk', 7)
        self.live.disconnect()
        self.assertEqual(self.memory.read(address, 4), before)

    def test_restore_never_overwrites_other_tool(self):
        self.live.connect()
        self.live.set_setting('walk', 7)
        address = self.memory.base + PLAYER_GLOBALS + SETTINGS['walk'].offset
        self.memory.store(address, struct.pack('<f', 9))
        with self.assertRaises(RuntimeError):
            self.live.restore_settings()
        self.assertEqual(struct.unpack('<f', self.memory.read(address, 4))[0], 9)

    def test_nan_and_out_of_range_never_write(self):
        self.live.connect()
        for value in (float('nan'), float('inf'), -1, 500):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.live.set_setting('walk', value)
        for value in (-1, 2_000_000_001, True, 1.2):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.live.set_currency('Units', value)
        self.assertEqual(self.memory.writes, [])

    def test_currency_undo_refuses_new_game_progress(self):
        self.live.connect()
        self.live.set_currency('Units', 100000)
        self.memory.store(self.memory.player + 0x89C, struct.pack('<I', 100001))
        with self.assertRaises(RuntimeError):
            self.live.undo_currency()
        self.assertEqual(len(self.memory.writes), 1)

    def test_currency_undo_refuses_other_save_slot(self):
        self.live.connect()
        self.live.set_currency('Units', 100000)
        self.memory.store(self.memory.base + ROOT_RVA + 8, struct.pack('<I', 1))
        with self.assertRaises(RuntimeError):
            self.live.undo_currency()
        self.assertEqual(len(self.memory.writes), 1)

    def test_currency_undo_restores_only_selected_currency(self):
        self.live.connect()
        before = self.memory.read(self.memory.player + 0x890, 24)
        self.live.set_currency('Nanit', 20000)
        self.live.undo_currency()
        self.assertEqual(self.memory.read(self.memory.player + 0x890, 24), before)

    def test_failed_audit_blocks_memory_write(self):
        self.live.connect()
        self.live.log = Mock(side_effect=OSError('disk full'))
        with self.assertRaises(OSError):
            self.live.set_setting('walk', 7)
        self.assertEqual(self.memory.writes, [])

    def test_failed_post_write_journal_rolls_back_own_value(self):
        self.live.connect()
        address = self.memory.base + PLAYER_GLOBALS + SETTINGS['walk'].offset
        before = self.memory.read(address, 4)
        self.live.log = Mock(side_effect=[None, OSError('disk full')])
        with self.assertRaises(OSError):
            self.live.set_setting('walk', 7)
        self.assertEqual(self.memory.read(address, 4), before)

    def test_closed_process_blocks_writes(self):
        self.live.connect()
        self.memory.running = False
        with self.assertRaises(RuntimeError):
            self.live.set_setting('walk', 7)
        self.assertEqual(self.memory.writes, [])
        self.live.forget_closed_session()
        self.assertIsNone(self.live.memory)


if __name__ == '__main__':
    unittest.main()
