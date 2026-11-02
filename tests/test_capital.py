import copy
import unittest

from nmsmenu import capital, inventory
from nmsmenu.catalog_mutations import mutate as basket_mutate
from nmsmenu.live_fleet import engine
from test_inventory import fixture, inv


def frigate(value='0x1', kind='Exploration'):
    return {'ResourceSeed': [True, value], 'HomeSystemSeed': [True, '0x44'],
            'ForcedTraitsSeed': [False, '0x0'], 'CustomName': '',
            'FrigateClass': {'FrigateClass': kind}, 'InventoryClass': {'InventoryClass': 'C'},
            'Stats': [3, 10, 2, 1, 5, 10, 4, 0, 1, 2, 0], 'TraitIDs': ['^EXPLORE_PRI', '^', '^', '^', '^'],
            'DamageTaken': 2, 'RepairsMade': 1, 'TotalNumberOfExpeditions': 8,
            'TimeOfLastIncomeCollection': 1789000000, 'UnknownFutureField': {'keep': [1, 2]}}


def source():
    data = fixture()
    p = data['BaseContext']['PlayerStateData']
    p.update(CurrentFreighter={'Filename': 'MODELS/COMMON/SPACECRAFT/INDUSTRIAL/FREIGHTER_PROC.SCENE.MBIN',
                               'Seed': [True, '0xAB'], 'Unknown': 42},
             PlayerFreighterName='Capital', FreighterInventory=inv(20, 'Freighter'),
             FreighterInventory_TechOnly=inv(20, 'Default'), FreighterInventory_Cargo=inv(0, 'FreighterCargo'),
             FleetFrigates=[frigate(), frigate('0x2', 'Combat')], FleetExpeditions=[],
             PersistentPlayerBases=[{'BaseType': {'PersistentBaseTypes': 'FreighterBase'}, 'Objects': [{'unknown': 7}]}])
    return data


class CapitalTests(unittest.TestCase):
    def setUp(self):
        self.fleet = engine()
        self.data = source()
        self.p = self.fleet.player(self.data)
        self.ship_selector = capital.freighter_identity(self.p)
        self.selector = capital.frigate_identity(self.p['FleetFrigates'][0], 0)

    def apply(self, operation, **fields):
        selector = self.ship_selector if operation.startswith('freighter') else self.selector
        return capital.mutate(self.data, {'op': operation, 'selector': selector, **fields}, self.fleet)

    def test_snapshot_uses_seed_and_slot_even_when_name_blank(self):
        view = capital.snapshot(self.p)
        self.assertEqual(view['frigates'][0]['name'], '')
        self.assertEqual(view['frigates'][0]['seed'], '0x0000000000000001')
        self.assertEqual(view['freighter']['cargo'], 20)

    def test_unowned_freighter_has_no_write_target(self):
        self.p['CurrentFreighter']['Filename'] = ''
        self.assertIsNone(capital.snapshot(self.p)['freighter'])
        with self.assertRaises(ValueError):
            self.apply('freighter_edit', fields={'name': 'No grant'})

    def test_freighter_class_sync_preserves_cargo_and_bases(self):
        before = copy.deepcopy(self.data)
        result, _, paths, _ = self.apply('freighter_edit', fields={'class': 'S', 'name': 'Flagship'})
        p = self.fleet.player(result)
        for key in capital.FREIGHTER_INVENTORIES:
            self.assertEqual(p[key]['Class']['InventoryClass'], 'S')
            self.assertEqual(p[key]['Slots'], self.p[key]['Slots'])
        self.assertEqual(p['PersistentPlayerBases'], self.p['PersistentPlayerBases'])
        self.assertEqual(self.data, before)
        self.assertTrue(all('Freighter' in path for path in paths))

    def test_freighter_slots_require_s_class_and_preserve_special_slots(self):
        with self.assertRaisesRegex(ValueError, 'S sınıfı'):
            self.apply('freighter_expand')
        for key in capital.FREIGHTER_INVENTORIES:
            self.p[key]['Class']['InventoryClass'] = 'S'
        self.p['FreighterInventory_TechOnly']['SpecialSlots'] = [{'Index': {'X': 5, 'Y': 1}, 'Type': {'InventorySpecialSlotType': 'TechBonus'}}]
        result, _, _, _ = self.apply('freighter_expand')
        p = self.fleet.player(result)
        self.assertEqual(len(p['FreighterInventory']['ValidSlotIndices']), 120)
        self.assertEqual(len(p['FreighterInventory_TechOnly']['ValidSlotIndices']), 60)
        self.assertEqual(p['FreighterInventory_TechOnly']['SpecialSlots'], self.p['FreighterInventory_TechOnly']['SpecialSlots'])
        self.assertEqual(p['FreighterInventory_Cargo'], self.p['FreighterInventory_Cargo'])

    def test_freighter_repair_only_changes_charge_and_damage(self):
        tech = self.fleet.tech('F_HYPERDRIVE', 10)
        tech['MaxAmount'], tech['DamageFactor'] = 200, 75.0
        self.p['FreighterInventory_TechOnly']['Slots'] = [tech]
        result, _, paths, _ = self.apply('freighter_repair')
        repaired = self.fleet.player(result)['FreighterInventory_TechOnly']['Slots'][0]
        self.assertEqual(repaired['Amount'], 200)
        self.assertEqual(repaired['DamageFactor'], 0.0)
        self.assertTrue(all(path.endswith(('/Amount', '/DamageFactor')) for path in paths))

    def test_wide_freighter_grid_keeps_every_existing_coordinate(self):
        cargo = self.p['FreighterInventory']
        cargo.update(Width=15, Height=10)
        cargo['ValidSlotIndices'].append({'X': 14, 'Y': 9})
        original = copy.deepcopy(cargo)
        capital.expand_inventory(cargo, 120)
        self.assertTrue({(p['X'], p['Y']) for p in original['ValidSlotIndices']} <= {(p['X'], p['Y']) for p in cargo['ValidSlotIndices']})
        self.assertEqual(cargo['Width'], 15)
        self.assertEqual(cargo['Height'], 10)

    def test_frigate_repair_preserves_history_traits_and_unknown_fields(self):
        result, _, paths, _ = self.apply('frigate_repair')
        repaired = self.fleet.player(result)['FleetFrigates'][0]
        expected = {**self.p['FleetFrigates'][0], 'DamageTaken': 0, 'RepairsMade': 0}
        self.assertEqual(repaired, expected)
        self.assertEqual(len(paths), 2)

    def test_stats_edit_keeps_other_seven_stats_and_grade(self):
        result, _, _, _ = self.apply('frigate_edit', fields={'stats': [20, 30, 40, 50]})
        f = self.fleet.player(result)['FleetFrigates'][0]
        self.assertEqual(f['Stats'][4:], self.p['FleetFrigates'][0]['Stats'][4:])
        self.assertEqual(f['TraitIDs'], self.p['FleetFrigates'][0]['TraitIDs'])
        self.assertEqual(f['InventoryClass'], self.p['FleetFrigates'][0]['InventoryClass'])

    def test_active_or_pending_mission_blocks_all_target_operations(self):
        self.p['FleetExpeditions'] = [{'AllFrigateIndices': [0], 'NextEventToTrigger': 100, 'EventNumber': 100}]
        for op in ('frigate_repair', 'frigate_edit', 'frigate_remove', 'frigate_clone'):
            with self.subTest(op=op), self.assertRaisesRegex(ValueError, 'Seferdeki'):
                self.apply(op)

    def test_other_mission_indices_stay_identical_on_append(self):
        self.p['FleetExpeditions'] = [{'AllFrigateIndices': [1], 'Future': {'keep': True}}]
        result, _, _, _ = self.apply('frigate_clone', name='New ship', seed='0x999')
        p = self.fleet.player(result)
        self.assertEqual(p['FleetFrigates'][:-1], self.p['FleetFrigates'])
        self.assertEqual(p['FleetExpeditions'], self.p['FleetExpeditions'])
        self.assertEqual(p['FleetFrigates'][-1]['ResourceSeed'], [True, '0x0000000000000999'])

    def test_remove_exports_full_frigate_and_blocks_any_expedition(self):
        result, _, _, exports = self.apply('frigate_remove')
        self.assertEqual(exports[0]['frigate'], self.p['FleetFrigates'][0])
        self.assertEqual(self.fleet.player(result)['FleetFrigates'], self.p['FleetFrigates'][1:])
        self.p['FleetExpeditions'] = [{'AllFrigateIndices': [1]}]
        with self.assertRaisesRegex(ValueError, 'tüm seferleri'):
            self.apply('frigate_remove')

    def test_clone_enforces_native_limit_unique_seed_and_normal_type(self):
        with self.assertRaisesRegex(ValueError, 'zaten'):
            self.apply('frigate_clone', seed='0x2', name='Duplicate')
        self.p['FleetFrigates'] = [frigate(hex(i+1)) for i in range(30)]
        with self.assertRaisesRegex(ValueError, '30'):
            self.apply('frigate_clone', seed='0x999', name='Too many')
        self.p['FleetFrigates'] = [frigate(kind='Normandy')]
        self.selector = capital.frigate_identity(self.p['FleetFrigates'][0], 0)
        with self.assertRaisesRegex(ValueError, 'normal'):
            self.apply('frigate_clone', seed='0x999', name='Unique reward')

    def test_wrong_identity_and_unknown_mission_schema_fail_closed(self):
        self.selector['seed'] = '0x000000000000FFFF'
        with self.assertRaisesRegex(ValueError, 'kimliği'):
            self.apply('frigate_repair')
        self.selector = capital.frigate_identity(self.p['FleetFrigates'][0], 0)
        self.p['FleetExpeditions'] = [{'UnknownMissionSchema': []}]
        with self.assertRaisesRegex(ValueError, 'Sefer'):
            self.apply('frigate_repair')

    def test_inventory_view_resolves_freighter_by_identity(self):
        nodes = inventory.snapshot(self.p, self.fleet)
        specs = [node['spec'] for node in nodes if node['spec']['kind'] == 'freighter']
        self.assertEqual(len(specs), 2)
        resolved, path, tool = inventory.resolve(self.p, specs[0], self.fleet)
        self.assertIs(resolved, self.p['FreighterInventory'])
        specs[0]['selector']['seed'] = '0xBAD'
        with self.assertRaisesRegex(ValueError, 'kimliği'):
            inventory.resolve(self.p, specs[0], self.fleet)

    def test_catalog_basket_routes_capital_through_existing_engine(self):
        result, report, _ = basket_mutate(self.data, {'actions': [{'op': 'frigate_repair', 'selector': self.selector}]}, {}, self.fleet, self.fleet.mutate)
        self.assertEqual(self.fleet.player(result)['FleetFrigates'][0]['DamageTaken'], 0)
        self.assertEqual(report['events'][0]['op'], 'frigate_repair')

    def test_malformed_fields_cannot_expand_schema_or_stats(self):
        for fields in ({'stats': [True, 0, 0, 0]}, {'stats': [101, 0, 0, 0]}, {'unknown': 1}, {'name': 'a'*32}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.apply('frigate_edit', fields=fields)
