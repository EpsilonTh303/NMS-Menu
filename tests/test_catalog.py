import copy
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from nmsmenu.catalog_data import compatible, technologies, tool_models
from nmsmenu.catalog_service import CatalogCart, CatalogService
from nmsmenu.catalog_mutations import install, mutate
from nmsmenu.live_fleet import engine
from nmsmenu import weapons
from test_weapons import store, tool


class CatalogServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = CatalogService()

    def test_pending_item_amount_edit_preserves_target_and_revises_review(self):
        cart = CatalogCart()
        command = {'op': 'add_item', 'id': 'FUEL1', 'amount': 5,
                   'inventory': {'kind': 'ship', 'section': 'cargo',
                                 'selector': {'slot': 2, 'seed': '0x123', 'type': 'fighter'}}}
        cart.add(1, command)
        revision = cart.revision
        cart.set_item_amount(0, 12345)
        self.assertEqual(cart.commands[0], {**command, 'amount': 12345})
        self.assertGreater(cart.revision, revision)
        for invalid in (0, -1, 10_000_001, '12'):
            with self.assertRaises(ValueError):
                cart.set_item_amount(0, invalid)
        cart.add(1, {'op': 'add', 'profile': 'utopia_speeder'})
        with self.assertRaises(ValueError):
            cart.set_item_amount(1, 4)
        self.assertEqual(cart.commands[0]['amount'], 12345)

    def test_catalog_has_unique_nonprocedural_ids_and_no_maintenance(self):
        entries = technologies()
        self.assertGreater(len(entries), 100)
        self.assertTrue(all('#' not in key and not key.startswith('DUMMY_') for key in entries))
        self.assertTrue(all(e['category'] != 'Maintenance' for e in entries.values()))

    def test_preferences_and_search_are_applied(self):
        result = self.service.items(kind='ship')
        self.assertEqual(result[0].key, 'ship:utopia_speeder')
        self.assertNotIn('ship:blue_squid', [item.key for item in result])
        self.assertIn('ship:blue_squid', [i.key for i in self.service.items(kind='ship', include_hidden=True)])
        self.assertTrue(any(i.key == 'tech:BOLT' for i in self.service.items(query='bolt', kind='technology')))

    def test_target_compatibility_filters_robot_and_solar_technology(self):
        self.assertFalse(compatible(technologies()['SOLAR_SAIL'], 'ship', 'fighter'))
        self.assertTrue(compatible(technologies()['SOLAR_SAIL'], 'ship', 'solar'))
        self.assertTrue(compatible(technologies()['BOLT'], 'multitool'))
        self.assertFalse(compatible(technologies()['BOLT'], 'exosuit'))
        self.assertFalse(compatible(technologies()['LAUNCHER_SPEC'], 'ship', 'fighter'))

    def test_command_rejects_invalid_target_and_model(self):
        with self.assertRaises(ValueError):
            self.service.command('tech:BOLT', target='exosuit')
        with self.assertRaises(ValueError):
            self.service.command('tool:royal')
        with self.assertRaises(ValueError):
            self.service.command('ship:unknown')

    def test_ship_variants_are_explicit_and_do_not_modify_profile(self):
        normal = self.service.command('ship:utopia_speeder')
        variant = self.service.command('ship:utopia_speeder', new_ship_seed=True)
        self.assertNotIn('seed', normal)
        self.assertTrue(0 < int(variant['seed'], 16) < 2 ** 64)

    def test_reward_presets_use_explicit_local_seed_and_random_override(self):
        key, profile = next((k, v) for k, v in tool_models().items() if v.get('seed'))
        selector = {'slot': 1, 'seed': '0x1', 'filename': 'source'}
        command = self.service.command('tool:' + key, selector=selector)
        self.assertEqual(command['seed'], profile['seed'])
        random = self.service.command('tool:' + key, selector=selector, random_tool_seed=True)
        self.assertTrue(0 < int(random['seed'], 16) < 2 ** 64)

    def test_reference_entries_are_searchable_but_cannot_be_added(self):
        result = self.service.items('corvette', kind='reference')
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0].addable)
        with self.assertRaises(ValueError):
            self.service.command(result[0].key)

    def test_family_filter_and_detail_are_ui_independent(self):
        result = self.service.items(kind='ship', family='explorer')
        self.assertGreater(len(result), 5)
        self.assertTrue(all(item.family == 'explorer' for item in result))
        detail = self.service.detail(result[0].key)
        detail['technology']['BROKEN_TEST'] = 1
        self.assertNotIn('BROKEN_TEST', self.service.detail(result[0].key)['technology'])

    def test_catalog_separates_model_and_seed_variants(self):
        self.assertEqual(self.service.counts()['ships'], 81)
        self.assertEqual(self.service.counts()['tools'], 49)
        self.assertEqual(len({p['model'] for p in tool_models().values()}), 12)
        for key, profile in self.service.ships.items():
            self.assertTrue(0 <= int(profile['seed'], 16) < 2 ** 64, key)
            self.assertLessEqual(profile.get('tech_slots', 20), 60)
            self.assertTrue(set(profile['technology']) <= technologies().keys(), key)

    def test_codec_stdin_preserves_unicode_across_windows_code_pages(self):
        import json
        from pathlib import Path
        fleet = engine()
        payload = {'Name': 'Nakliye • Türkçe ıİşŞğĞüÜöÖçÇ'}
        with patch.object(fleet.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as run:
            fleet.encode(payload, Path('.'), 0)
        raw = run.call_args.kwargs['input']
        self.assertTrue(raw.isascii())
        for encoding in ('ascii', 'cp437', 'cp1252', 'utf-8'):
            self.assertEqual(json.loads(raw.decode(encoding)), payload)

    def test_cart_copies_commands_deduplicates_tech_and_rejects_cross_save(self):
        cart = CatalogCart()
        command = self.service.command('tech:JET1', 'exosuit')
        cart.add(1, command)
        self.assertFalse(cart.add(1, command))
        command['id'] = 'changed'
        self.assertEqual(cart.plan()['actions'][0]['id'], 'JET1')
        snapshot = cart.commands
        snapshot[0]['id'] = 'external-change'
        self.assertEqual(cart.commands[0]['id'], 'JET1')
        with self.assertRaises(ValueError):
            cart.add(2, command)
        cart.clear()
        with self.assertRaises(ValueError):
            cart.plan()


class CatalogMutationTests(unittest.TestCase):
    def setUp(self):
        self.fleet = engine()
        inv = store(10)
        inv['ValidSlotIndices'] = [{'X': i, 'Y': 0} for i in range(5)]
        inv['Width'] = 5
        t = tool('0x1')
        t['Store'] = copy.deepcopy(inv)
        ship = {'Name': 'Test', 'Resource': {'Filename': 'MODELS/COMMON/SPACECRAFT/FIGHTERS/FIGHTER_PROC.SCENE.MBIN',
                                           'Seed': [True, '0xA']}, 'Inventory': copy.deepcopy(inv),
                'Inventory_Cargo': copy.deepcopy(inv), 'Inventory_TechOnly': copy.deepcopy(inv)}
        self.p = {'PrimaryShip': 0, 'ShipOwnership': [ship], 'Inventory_TechOnly': copy.deepcopy(inv),
                  'Multitools': [t] + [weapons.clear_slot(tool('0x2')) for _ in range(5)],
                  'WeaponInventory': copy.deepcopy(inv), 'WeaponLayout': t['Layout'],
                  'CurrentWeapon': {'Filename': t['Resource']['Filename'], 'GenerationSeed': [True, '0x1']},
                  'UnknownProgress': 999}
        self.data = {'ActiveContext': 'Main', 'BaseContext': {'PlayerStateData': self.p}}
        self.selector = {'slot': 1, 'seed': '0x1', 'filename': t['Resource']['Filename']}

    def action(self, ident='BOLT'):
        return {'op': 'install_technology', 'id': ident, 'target': 'multitool', 'selector': self.selector}

    def test_installs_in_free_slot_preserves_existing_and_syncs_active_copy(self):
        original = copy.deepcopy(self.data)
        data, event, paths = install(self.data, self.action(), self.fleet)
        p = self.fleet.player(data)
        self.assertEqual(self.data, original)
        self.assertEqual(p['WeaponInventory']['Slots'][0], self.p['WeaponInventory']['Slots'][0])
        self.assertEqual(p['WeaponInventory']['Slots'][1]['Id'], '^BOLT')
        self.assertEqual(p['WeaponInventory']['Slots'][1]['Amount'], 200)
        self.assertEqual(p['Multitools'][0]['Store'], p['WeaponInventory'])
        self.assertEqual(p['UnknownProgress'], 999)

    def test_repeat_install_is_noop(self):
        data, _, _ = install(self.data, self.action(), self.fleet)
        result, event, paths = install(data, self.action(), self.fleet)
        self.assertEqual(result, data)
        self.assertTrue(event['already_installed'])
        self.assertEqual(paths, [])

    def test_no_free_slot_does_not_relocate_or_overwrite(self):
        self.p['WeaponInventory']['ValidSlotIndices'] = [{'X': 0, 'Y': 0}]
        before = copy.deepcopy(self.data)
        with self.assertRaises(ValueError):
            install(self.data, self.action(), self.fleet)
        self.assertEqual(self.data, before)

    def test_unknown_procedural_and_wrong_target_are_rejected(self):
        for ident in ('UP_UNKNOWN#123', 'PROTECT'):
            with self.subTest(ident=ident), self.assertRaises(ValueError):
                install(self.data, self.action(ident), self.fleet)

    def test_failed_basket_cannot_partially_change_input(self):
        before = copy.deepcopy(self.data)
        with self.assertRaises(ValueError):
            mutate(self.data, {'actions': [self.action(), self.action('PROTECT')]}, {}, self.fleet, self.fleet.mutate)
        self.assertEqual(self.data, before)

    def test_tool_profile_changes_only_new_slot_and_keeps_source(self):
        action = {'op': 'tool_add', 'selector': self.selector, 'seed': '0xCAFE', 'profile': 'royal'}
        data, report, exports = weapons.mutate(self.data, {'actions': [action]}, {}, self.fleet)
        p = self.fleet.player(data)
        self.assertEqual(p['Multitools'][0], self.p['Multitools'][0])
        self.assertEqual(p['Multitools'][1]['Resource']['Filename'], tool_models()['royal']['model'])
        self.assertEqual(p['Multitools'][1]['Store'], self.p['WeaponInventory'])
        self.assertEqual(len(p['Multitools']), 6)

    def test_basket_report_contains_all_technology_events(self):
        data, report, exports = mutate(self.data, {'actions': [self.action('BOLT'), self.action('SHOTGUN')]}, {}, self.fleet, self.fleet.mutate)
        self.assertEqual(len(report['events']), 2)
        self.assertEqual(len(self.fleet.player(data)['WeaponInventory']['Slots']), 3)


if __name__ == '__main__':
    unittest.main()
