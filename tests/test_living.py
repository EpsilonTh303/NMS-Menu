import copy
import unittest
from nmsmenu.live_fleet import engine
from nmsmenu.catalog_service import CatalogService
from nmsmenu.catalog_data import technologies, compatible
from test_inventory import fixture


class LivingShipTests(unittest.TestCase):
    def setUp(self):
        self.fleet = engine()
        self.catalog = self.fleet.load(self.fleet.ROOT / 'catalog.json')
        self.data = fixture()

    def add(self):
        return self.fleet.mutate(self.data, {'actions': [{'op': 'add', 'profile': 'living_ship'}]}, self.catalog)[0]

    def test_add_uses_empty_slot_preserves_cargo_and_originals(self):
        before = copy.deepcopy(self.data)
        result = self.add()
        p = self.fleet.player(result)
        self.assertEqual(self.data, before)
        self.assertEqual(len(p['ShipOwnership']), 12)
        self.assertEqual(p['PrimaryShip'], 0)
        self.assertEqual(p['ShipOwnership'][:2], self.fleet.player(before)['ShipOwnership'][:2])
        self.assertEqual(p['ShipOwnership'][3:], self.fleet.player(before)['ShipOwnership'][3:])
        ship = p['ShipOwnership'][2]
        self.assertEqual(self.fleet.kind(ship), 'alien')
        self.assertTrue(self.fleet.fleet_summary(p)[2]['auto_recharge'])
        self.assertEqual(len(ship['Inventory']['ValidSlotIndices']), 35)
        self.assertTrue(all(compatible(technologies()[item['Id'][1:]], 'ship', 'alien') for item in ship['Inventory_TechOnly']['Slots']))
        self.assertEqual(CatalogService().command('ship:living_ship')['profile'], 'living_ship')

    def test_reject_conventional_or_missing_organic_core_and_wrong_class(self):
        profile = self.catalog['living_ship']
        for change in ('conventional', 'missing', 'class'):
            with self.subTest(change=change):
                saved = copy.deepcopy(profile)
                if change == 'conventional':
                    profile['technology']['UT_LAUNCHCHARGE'] = 100
                elif change == 'missing':
                    del profile['technology']['LAUNCHER_SPEC']
                else:
                    profile['class'] = 'C'
                with self.assertRaises(ValueError):
                    self.add()
                profile.clear()
                profile.update(saved)

    def test_capacity_and_organic_charger_are_idempotent(self):
        data = self.add()
        actions = [{'op': 'max_slots', 'scope': 'ships'}, {'op': 'auto_recharge', 'scope': 'ships'}]
        result = self.fleet.mutate(data, {'actions': actions}, self.catalog)[0]
        again = self.fleet.mutate(result, {'actions': actions}, self.catalog)[0]
        self.assertEqual(result, again)
        ship = self.fleet.player(result)['ShipOwnership'][2]
        self.assertEqual(len(ship['Inventory']['ValidSlotIndices']), 120)
        self.assertEqual(len(ship['Inventory_TechOnly']['ValidSlotIndices']), 60)
        ids = [item['Id'] for item in ship['Inventory_TechOnly']['Slots']]
        self.assertEqual(ids.count('^CHARGER_ALIEN'), 1)
        self.assertNotIn('^UT_LAUNCHCHARGE', ids)

    def test_full_fleet_and_duplicate_cannot_replace_existing_ships(self):
        data = self.add()
        with self.assertRaises(ValueError):
            self.fleet.mutate(data, {'actions': [{'op': 'add', 'profile': 'living_ship'}]}, self.catalog)
        self.fleet.player(self.data)['ShipOwnership'] = [copy.deepcopy(self.fleet.player(self.data)['ShipOwnership'][0]) for _ in range(12)]
        with self.assertRaises(ValueError):
            self.add()

    def test_residual_items_in_an_empty_template_are_not_discarded_or_inherited(self):
        p = self.fleet.player(self.data)
        p['ShipOwnership'][2]['Inventory_TechOnly']['Slots'] = [self.fleet.tech('LAUNCHER')]
        before = copy.deepcopy(self.data)
        with self.assertRaises(ValueError):
            self.add()
        self.assertEqual(self.data, before)
