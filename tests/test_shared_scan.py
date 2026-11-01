import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from nmsmenu.shared_scan import DiskScanner, SharedScan
from test_weapons import tool, store


class SharedDiskTests(unittest.TestCase):
    def setUp(self):
        runtime = Path(__file__).resolve().parents[1] / 'runtime'
        runtime.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=runtime)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.live = self.root / 'DefaultUser'
        self.live.mkdir()
        self.file = self.live / 'save.hg'
        self.meta = self.live / 'mf_save.hg'
        self.file.write_bytes(b'synthetic save')
        self.meta.write_bytes(b'synthetic metadata')
        t = tool('0x1')
        self.player = {'PrimaryShip': 0, 'Inventory': {'ValidSlotIndices': []},
                       'Inventory_TechOnly': {'ValidSlotIndices': []}, 'Multitools': [t],
                       'WeaponInventory': store(), 'WeaponLayout': t['Layout'],
                       'CurrentWeapon': {'Filename': t['Resource']['Filename'], 'GenerationSeed': t['Seed']}}
        self.fleet = SimpleNamespace(LIVE=self.live,
            digest=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(),
            decode=Mock(side_effect=lambda _: copy.deepcopy(self.player)), player=lambda p: p,
            fleet_summary=lambda p: [{'slot': 1, 'seed': '0x1'}])
        self.scanner = DiskScanner(self.fleet, self.root / 'runtime')

    def test_one_decode_supplies_both_fleet_and_weapons(self):
        result = self.scanner.scan()
        self.assertEqual(len(result['saves'][0]['fleet']), 1)
        self.assertEqual(len(result['saves'][0]['multitools']), 1)
        self.assertEqual(self.fleet.decode.call_count, 1)
        self.assertEqual(result['errors'], [])

    def test_unchanged_saves_are_not_decoded_again(self):
        self.scanner.scan()
        self.scanner.scan()
        self.assertEqual(self.fleet.decode.call_count, 1)

    def test_changed_metadata_or_save_triggers_one_new_decode(self):
        self.scanner.scan()
        self.meta.write_bytes(b'changed metadata content')
        self.scanner.scan()
        self.assertEqual(self.fleet.decode.call_count, 2)
        self.file.write_bytes(b'new save progress')
        self.scanner.scan()
        self.assertEqual(self.fleet.decode.call_count, 3)

    def test_user_refresh_can_force_a_fresh_decode(self):
        self.scanner.scan()
        self.scanner.scan(force=True)
        self.assertEqual(self.fleet.decode.call_count, 2)

    def test_ui_cannot_mutate_cached_data(self):
        result = self.scanner.scan()
        result['saves'][0]['fleet'][0]['seed'] = 'changed-in-ui'
        self.assertEqual(self.scanner.scan()['saves'][0]['fleet'][0]['seed'], '0x1')

    def test_decode_reads_copy_instead_of_live_file(self):
        self.scanner.scan()
        path = self.fleet.decode.call_args.args[0]
        self.assertNotEqual(path, self.file)
        self.assertEqual(self.file.read_bytes(), b'synthetic save')

    def test_bad_weapon_context_does_not_hide_valid_fleet(self):
        self.player['CurrentWeapon']['GenerationSeed'] = [True, '0xFFFF']
        result = self.scanner.scan()
        self.assertEqual(len(result['saves'][0]['fleet']), 1)
        self.assertIn('weapons_error', result['saves'][0])

    def test_decode_failure_is_returned_as_status(self):
        self.fleet.decode.side_effect = RuntimeError('codec failure')
        result = self.scanner.scan()
        self.assertEqual(result['saves'], [])
        self.assertIn('codec failure', result['errors'][0])

    def test_history_change_updates_shared_lists_without_decoding_save_again(self):
        self.fleet.ROOT = self.root
        self.fleet.GARAGE = self.root / 'garage'
        self.fleet.GARAGE.mkdir()
        self.fleet.load = lambda p: json.loads(p.read_text())
        self.scanner.scan()
        before = self.scanner.signature()
        tx = self.root / 'transactions' / 'new-tx'
        tx.mkdir(parents=True)
        (tx / 'manifest.json').write_text('{"state":"prepared"}')
        self.assertNotEqual(before, self.scanner.signature())
        result = self.scanner.scan()
        self.assertEqual(result['history'], [(tx, 'prepared')])
        self.assertEqual(self.fleet.decode.call_count, 1)

    def test_garage_is_included_in_same_shared_result(self):
        self.fleet.ROOT = self.root
        self.fleet.GARAGE = self.root / 'garage'
        self.fleet.GARAGE.mkdir()
        self.fleet.load = lambda p: json.loads(p.read_text())
        self.fleet.read_garage = Mock(return_value={'ship': {'Name': 'Test', 'Resource': {'Seed': [True, '0x1']}}})
        self.fleet.kind = lambda p: 'fighter'
        (self.fleet.GARAGE / ('a' * 64 + '.json')).write_text('{"save_version":1,"saved_at":"test"}')
        result = self.scanner.scan()
        self.assertEqual(result['garage'][0]['id'], 'a' * 64)
        self.assertEqual(len(result['saves']), 1)
        self.assertEqual(self.fleet.decode.call_count, 1)


class SharedLiveTests(unittest.TestCase):
    def setUp(self):
        self.memory = SimpleNamespace(alive=Mock(return_value=True))
        self.live = SimpleNamespace(memory=None, connect=Mock(), snapshot=Mock(),
                                    forget_closed_session=Mock(), write=Mock())
        state = {'loaded': True, 'pid': 123}

        def connect():
            self.live.memory = self.memory
            return state
        self.live.connect.side_effect = connect
        self.live.snapshot.return_value = state
        self.fleet = SimpleNamespace(inspect=Mock(return_value=[{'slot': 1}]))
        self.shared = SharedScan(self.live, self.fleet, disk=Mock())

    def test_reuses_one_connection_for_all_fast_refreshes(self):
        self.shared.fast()
        self.shared.fast()
        self.live.connect.assert_called_once()
        self.live.snapshot.assert_called_once()
        self.assertEqual(self.fleet.inspect.call_count, 2)
        self.live.write.assert_not_called()

    def test_main_menu_does_not_scan_unloaded_fleet(self):
        self.live.memory = self.memory
        self.live.snapshot.return_value = {'loaded': False}
        result = self.shared.fast()
        self.assertEqual(result['fleet'], [])
        self.fleet.inspect.assert_not_called()

    def test_missing_game_is_quiet_status_and_retryable(self):
        self.live.connect.side_effect = RuntimeError('game closed')
        self.assertEqual(self.shared.fast()['error'], 'game closed')
        self.assertEqual(self.shared.fast()['error'], 'game closed')
        self.live.write.assert_not_called()
