import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from nmsmenu.backend import FleetBackend
from nmsmenu.modules import build_plan


class PlanTests(unittest.TestCase):
    def test_procedural_name_is_never_used_as_identity_and_cargo_preserved(self):
        ship = {'slot': 3, 'name': '(procedural name)', 'seed': '0xCAFE', 'type': 'solar'}
        action = build_plan('remove', 1, ship)['actions'][0]
        self.assertEqual(action['selector'], {'slot': 3, 'seed': '0xCAFE', 'type': 'solar'})
        self.assertTrue(action['preserve_cargo'])

    def test_destructive_selection_requires_identity(self):
        for op in ('remove', 'repair_ship', 'equip', 'garage_replace'):
            with self.subTest(op=op), self.assertRaises(ValueError):
                build_plan(op, 1, garage_id='a' * 64)

    def test_planned_features_cannot_execute(self):
        for op in ('money', 'godmode', 'teleport', 'unknown'):
            with self.subTest(op=op), self.assertRaises(ValueError):
                build_plan(op, 1)

    def test_slot_and_garage_validation(self):
        for slot in (0, 16, True, '1'):
            with self.subTest(slot=slot), self.assertRaises(ValueError):
                build_plan('exosuit_slots', slot)
        for ident in ('../outside', 'g' * 64, ''):
            with self.subTest(ident=ident), self.assertRaises(ValueError):
                build_plan('garage_import', 1, garage_id=ident)

    def test_replacement_preserves_exact_outgoing_identity(self):
        ship = {'slot': 2, 'seed': '0xB', 'type': 'utopia'}
        plan = build_plan('garage_replace', 2, ship, garage_id='a' * 64)
        self.assertEqual(plan, {'save_slot': 2, 'actions': [
            {'op': 'garage_import', 'id': 'a' * 64, 'replace': ship}]})


class TransactionTests(unittest.TestCase):
    def setUp(self):
        runtime = Path(__file__).resolve().parents[1] / 'runtime'
        runtime.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=runtime)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.fleet = self.base / 'FleetManager'
        self.transaction = self.fleet / 'transactions' / 'new-request'
        self.transaction.mkdir(parents=True)
        self.manifest = self.transaction / 'manifest.json'
        self.manifest.write_text('{"state":"prepared"}', encoding='utf-8')
        self.backend = FleetBackend(self.fleet, self.base / 'runtime')
        self.backend.run = Mock(return_value='APPLIED')

    def test_changed_review_blocks_apply_before_subprocess(self):
        reviewed = self.backend.fingerprint(self.transaction)
        self.manifest.write_text('{"state":"changed"}', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.backend.apply(self.transaction, reviewed)
        self.backend.run.assert_not_called()

    def test_matching_review_delegates_to_guarded_engine(self):
        self.backend.apply(self.transaction, self.backend.fingerprint(self.transaction))
        self.backend.run.assert_called_once_with('apply', self.transaction.resolve())

    def test_external_transaction_path_rejected(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'manifest.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.backend.restore(outside)
        self.backend.run.assert_not_called()

    def test_every_prepare_inspects_fresh_and_creates_unique_plan(self):
        plan = build_plan('exosuit_slots', 1)
        self.manifest.write_text(json.dumps({'state': 'prepared', 'plan': plan}), encoding='utf-8')
        self.backend.inspect = Mock(return_value=[{'file': 'save.hg'}])
        self.backend.run.return_value = json.dumps({'transaction': str(self.transaction)})
        self.backend.prepare(plan)
        self.backend.prepare(plan)
        self.assertEqual(self.backend.inspect.call_count, 2)
        paths = [call.args[1] for call in self.backend.run.call_args_list]
        self.assertNotEqual(paths[0], paths[1])
        self.assertEqual(json.loads(paths[0].read_text(encoding='utf-8')), plan)


if __name__ == '__main__':
    unittest.main()
