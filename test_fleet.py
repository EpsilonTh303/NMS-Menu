import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fleet


class FleetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (fleet.ROOT / 'inspection' / 'save2.json').is_file():
            raise unittest.SkipTest('Historical regression fixtures are local save snapshots, not distributed.')
        cls.original = fleet.load(fleet.ROOT / 'inspection' / 'save2.json')
        cls.catalog = fleet.load(fleet.ROOT / 'catalog.json')

    def test_requested_transaction_preserves_progress_and_items(self):
        original = copy.deepcopy(self.original)
        result, report, exports = fleet.mutate(original,
            fleet.load(fleet.ROOT / 'current-request.json'), self.catalog)
        p, old = fleet.player(result), fleet.player(original)
        self.assertEqual(original, self.original)
        self.assertEqual(p['PrimaryShip'], old['PrimaryShip'])
        self.assertEqual(len(fleet.owned(p)), 3)
        self.assertEqual([fleet.kind(s) for _, s in fleet.owned(p)], ['fighter', 'sentinel', 'solar'])
        self.assertEqual(len(p['Inventory']['ValidSlotIndices']), 120)
        self.assertEqual(len(p['Inventory_TechOnly']['ValidSlotIndices']), 60)
        self.assertEqual([len(s['Inventory']['ValidSlotIndices']) for _, s in fleet.owned(p)], [100, 120, 110])
        sentinel_tech = {item['Id'] for item in p['ShipOwnership'][1]['Inventory_TechOnly']['Slots']}
        self.assertTrue({'^LAUNCHER_ROBO', '^SHIPJUMP_ROBO', '^LAUNCHER', '^SHIPJUMP1'} <= sentinel_tech)
        for _, ship in fleet.owned(p):
            self.assertEqual(len(ship['Inventory_TechOnly']['ValidSlotIndices']), 60)
            self.assertEqual(sum(x['Id'] == '^UT_LAUNCHCHARGE' for x in ship['Inventory_TechOnly']['Slots']), 1)
        expected = old['Inventory']['Slots'] + old['ShipOwnership'][1]['Inventory']['Slots']
        def content(items):
            return [dict((key, value) for key, value in x.items() if key != 'Index') for x in items]
        self.assertEqual(content(p['Inventory']['Slots']), content(expected))
        self.assertEqual(exports[0]['ship'], old['ShipOwnership'][1])
        for i in (0, 2):
            self.assertEqual(p['ShipOwnership'][i]['Resource'], old['ShipOwnership'][i]['Resource'])
            self.assertEqual(p['ShipOwnership'][i]['Inventory']['Slots'], old['ShipOwnership'][i]['Inventory']['Slots'])
        # Unrelated progression must remain byte-for-byte equivalent as JSON.
        for key in original:
            if key != 'BaseContext':
                self.assertEqual(original[key], result[key])
        allowed_keys = {'ShipOwnership', 'ShipUsesLegacyColours', 'CharacterCustomisationData',
                        'Inventory', 'Inventory_TechOnly'}
        for key in old:
            if key not in allowed_keys:
                self.assertEqual(old[key], p[key], key)

    def test_missing_or_ambiguous_ship_is_rejected(self):
        p = fleet.player(self.original)
        for selector in ({'name': 'Parallax'}, {}, {'type': 'empty'}):
            with self.assertRaises(ValueError):
                fleet.select(p, selector)

    def test_duplicate_addition_is_rejected(self):
        with self.assertRaises(ValueError):
            fleet.mutate(self.original, {'actions': [{'op': 'add', 'profile': 'solar'}]}, self.catalog)

    def test_primary_removal_selects_an_owned_ship(self):
        result, _, _ = fleet.mutate(self.original, {'actions': [
            {'op': 'remove', 'selector': {'name': 'Gece Yelkencisi'}}]}, self.catalog)
        self.assertEqual(fleet.player(result)['PrimaryShip'], 0)

    def test_stale_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=fleet.ROOT) as temp:
            self.assertTrue(Path(temp).resolve().is_relative_to(fleet.ROOT.resolve()))
            path = Path(temp) / 'save.hg'
            path.write_bytes(b'before')
            hashes = {'save.hg': fleet.digest(path)}
            fleet.unchanged(Path(temp), hashes)
            path.write_bytes(b'after')
            with self.assertRaises(ValueError):
                fleet.unchanged(Path(temp), hashes)

    def test_sentinel_compatibility_repair_preserves_station_and_other_ships(self):
        original = fleet.load(fleet.ROOT / 'diagnosis-sentinel' / 'after-exit.json')
        result, report, _ = fleet.mutate(original,
            fleet.load(fleet.ROOT / 'repair-sentinel.json'), self.catalog)
        p, old = fleet.player(result), fleet.player(original)
        self.assertEqual(p['PrimaryShip'], 1)
        self.assertEqual(result['BaseContext']['SpawnStateData'], original['BaseContext']['SpawnStateData'])
        self.assertEqual(p['ShipOwnership'][0], old['ShipOwnership'][0])
        self.assertEqual(p['ShipOwnership'][2:], old['ShipOwnership'][2:])
        self.assertEqual(p['Inventory'], old['Inventory'])
        items = {x['Id']: x for x in p['ShipOwnership'][1]['Inventory_TechOnly']['Slots']}
        for ident in ('^LAUNCHER_ROBO', '^SHIPJUMP_ROBO', '^LAUNCHER', '^SHIPJUMP1'):
            self.assertIn(ident, items)
            self.assertTrue(items[ident]['FullyInstalled'])
            self.assertEqual(items[ident]['DamageFactor'], 0.0)
            self.assertGreater(items[ident]['Amount'], 0)
        # Applying the targeted repair twice must never duplicate installed modules.
        again, _, _ = fleet.mutate(result, fleet.load(fleet.ROOT / 'repair-sentinel.json'), self.catalog)
        self.assertEqual(result, again)

    def test_combat_loadout_and_exotic_keep_working_engines_and_progress(self):
        original = fleet.load(fleet.ROOT / 'inspection-loadout' / 'save.json')
        result, report, _ = fleet.mutate(original,
            fleet.load(fleet.ROOT / 'sentinel-loadout-and-exotic.json'), self.catalog)
        old, p = fleet.player(original), fleet.player(result)
        self.assertEqual(p['PrimaryShip'], old['PrimaryShip'])
        self.assertEqual(p['Inventory'], old['Inventory'])
        self.assertEqual(result['BaseContext']['SpawnStateData'], original['BaseContext']['SpawnStateData'])
        self.assertEqual(p['ShipOwnership'][0], old['ShipOwnership'][0])
        self.assertEqual(p['ShipOwnership'][2], old['ShipOwnership'][2])
        old_items = old['ShipOwnership'][1]['Inventory_TechOnly']['Slots']
        items = p['ShipOwnership'][1]['Inventory_TechOnly']['Slots']
        self.assertEqual(items[:len(old_items)], old_items)
        ids = [item['Id'] for item in items]
        self.assertEqual(sum(x.startswith('^UP_SMINI') for x in ids), 3)
        self.assertEqual(sum(x.startswith('^UP_S_SHL') for x in ids), 3)
        for ident in ('^SHIPMINIGUN', '^UT_SHIPMINI', '^UT_SHIPSHIELD', '^SHIPSCAN_ECON', '^SHIPSCAN_COMBAT'):
            self.assertIn(ident, ids)
        exotic = p['ShipOwnership'][3]
        self.assertEqual(fleet.kind(exotic), 'exotic')
        self.assertEqual(exotic['Name'], 'Altin Inci')
        self.assertEqual(len(exotic['Inventory']['ValidSlotIndices']), 105)
        self.assertEqual(len(exotic['Inventory_TechOnly']['ValidSlotIndices']), 60)
        equip_only = {'actions': [fleet.load(fleet.ROOT / 'sentinel-loadout-and-exotic.json')['actions'][0]]}
        again, _, _ = fleet.mutate(result, equip_only, self.catalog)
        self.assertEqual(result, again)

    def test_loadout_rejects_a_fourth_procedural_upgrade(self):
        original = fleet.load(fleet.ROOT / 'inspection-loadout' / 'save.json')
        p = fleet.player(original)
        fleet.insert(p['ShipOwnership'][1]['Inventory_TechOnly'], fleet.tech('UP_SMINI4#45678'))
        equip_only = {'actions': [fleet.load(fleet.ROOT / 'sentinel-loadout-and-exotic.json')['actions'][0]]}
        with self.assertRaisesRegex(ValueError, 'overload'):
            fleet.mutate(original, equip_only, self.catalog)

    def test_four_new_models_preserve_existing_four_and_fixed_capacity(self):
        original = fleet.load(fleet.ROOT / 'inspection-collection' / 'save2.json')
        result, _, _ = fleet.mutate(original, fleet.load(fleet.ROOT / 'collection-expansion.json'), self.catalog)
        old, p = fleet.player(original), fleet.player(result)
        self.assertEqual(p['ShipOwnership'][:4], old['ShipOwnership'][:4])
        self.assertEqual(p['PrimaryShip'], old['PrimaryShip'])
        self.assertEqual(p['Inventory'], old['Inventory'])
        self.assertEqual(len(p['ShipOwnership']), 12)
        self.assertEqual(len(fleet.owned(p)), 8)
        self.assertEqual([fleet.kind(s) for _, s in fleet.owned(p)][4:], ['starborn', 'golden', 'utopia', 'exotic'])
        for _, ship in fleet.owned(p)[4:]:
            self.assertEqual(ship['Inventory']['Class']['InventoryClass'], 'S')
            self.assertEqual(len(ship['Inventory_TechOnly']['ValidSlotIndices']), 60)
            self.assertIn('^UT_LAUNCHCHARGE', {item['Id'] for item in ship['Inventory_TechOnly']['Slots']})

    def full_fleet(self):
        original = fleet.load(fleet.ROOT / 'inspection-collection' / 'save2.json')
        p = fleet.player(original)
        for i in range(4, 12):
            ship = copy.deepcopy(p['ShipOwnership'][0])
            ship['Name'] = 'Test Fleet ' + str(i)
            ship['Resource']['Seed'] = [True, hex(1000 + i)]
            p['ShipOwnership'][i] = ship
        return original

    def test_full_fleet_refuses_a_thirteenth_active_ship(self):
        with self.assertRaisesRegex(ValueError, '12 active'):
            fleet.mutate(self.full_fleet(), {'actions': [{'op': 'add', 'profile': 'golden_vector'}]}, self.catalog)

    def test_full_fleet_garage_swap_is_lossless(self):
        original = self.full_fleet()
        p = fleet.player(original)
        incoming = fleet.capture_ship(p, 3)
        incoming['ship']['Name'] = 'Garage Test'
        incoming['ship']['Resource']['Seed'] = [True, '0xFEDCBA9876543210']
        fleet.insert(incoming['ship']['Inventory'], p['Inventory']['Slots'][0])
        outgoing = fleet.capture_ship(p, 0)
        with tempfile.TemporaryDirectory(dir=fleet.ROOT) as temp:
            self.assertTrue(Path(temp).resolve().is_relative_to(fleet.ROOT.resolve()))
            with patch.object(fleet, 'GARAGE', Path(temp)):
                ident = fleet.save_garage(incoming, original['Version'])
                self.assertEqual(fleet.read_garage(ident, original['Version']), incoming)
                plan = {'actions': [{'op': 'garage_import', 'id': ident, 'replace': {'slot': 1}}]}
                result, _, exports = fleet.mutate(original, plan, self.catalog)
                q = fleet.player(result)
                self.assertEqual(len(q['ShipOwnership']), 12)
                self.assertEqual(len(fleet.owned(q)), 12)
                self.assertEqual(q['ShipOwnership'][0], incoming['ship'])
                self.assertEqual(q['ShipOwnership'][1:], p['ShipOwnership'][1:])
                self.assertEqual({k: exports[0][k] for k in outgoing}, outgoing)
                self.assertTrue(exports[0]['garage'])
                # No existing cargo or installed technology is dropped in the swap.
                self.assertEqual(q['Inventory'], p['Inventory'])
                self.assertEqual(q['PrimaryShip'], p['PrimaryShip'])

    def test_garage_rejects_tampering_and_version_mismatch(self):
        original = fleet.load(fleet.ROOT / 'inspection-collection' / 'save2.json')
        payload = fleet.capture_ship(fleet.player(original), 3)
        with tempfile.TemporaryDirectory(dir=fleet.ROOT) as temp:
            self.assertTrue(Path(temp).resolve().is_relative_to(fleet.ROOT.resolve()))
            with patch.object(fleet, 'GARAGE', Path(temp)):
                ident = fleet.save_garage(payload, original['Version'])
                with self.assertRaisesRegex(ValueError, 'incompatible'):
                    fleet.read_garage(ident, original['Version'] + 1)
                path = Path(temp) / (ident + '.json')
                bad = fleet.load(path)
                bad['payload']['ship']['Name'] = 'Changed outside manager'
                fleet.dump(path, bad)
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    fleet.read_garage(ident, original['Version'])

    def test_aesthetic_refresh_preserves_utopia_and_squid_cargo(self):
        original = fleet.load(fleet.ROOT / 'inspection-aesthetic' / 'save2.json')
        result, report, exports = fleet.mutate(original,
            fleet.load(fleet.ROOT / 'aesthetic-refresh.json'), self.catalog)
        old, p = fleet.player(original), fleet.player(result)
        self.assertEqual(p['PrimaryShip'], old['PrimaryShip'])
        self.assertEqual(p['ShipOwnership'][:7], old['ShipOwnership'][:7])
        self.assertEqual(p['ShipOwnership'][6]['Name'], 'Utopia Izcisi')
        self.assertEqual(len(fleet.owned(p)), 10)
        self.assertEqual(len(p['ShipOwnership']), 12)
        self.assertFalse(any(s['Name'] == 'Mavi Kalamar' for _, s in fleet.owned(p)))
        self.assertEqual([s['Name'] for _, s in fleet.owned(p)][7:],
                         ['Iron Vulture', 'Boundary Herald', 'Starborn Phoenix'])
        self.assertEqual(exports[0]['ship'], old['ShipOwnership'][7])
        def content(items):
            return [{k: v for k, v in item.items() if k != 'Index'} for item in items]
        self.assertEqual(content(p['Inventory']['Slots']), content(old['Inventory']['Slots'] +
            old['ShipOwnership'][7]['Inventory']['Slots'] + old['ShipOwnership'][7]['Inventory_Cargo']['Slots']))
        iron_appearance = p['CharacterCustomisationData'][fleet.custom_index(7)]
        self.assertEqual(iron_appearance, fleet.load(fleet.ROOT / 'ship-references' / 'iron-vulture-ccd.json'))
        self.assertEqual(iron_appearance['CustomData']['DescriptorGroups'],
                         ['^DROPS_COCKS13', '^DROPS_ENGIS13', '^DROPS_WINGS13'])
        self.assertEqual(result['BaseContext']['SpawnStateData'], original['BaseContext']['SpawnStateData'])
        for _, ship in fleet.owned(p)[7:]:
            self.assertEqual(ship['Inventory']['Class']['InventoryClass'], 'S')
            self.assertEqual(len(ship['Inventory_TechOnly']['ValidSlotIndices']), 60)
            self.assertIn('^UT_LAUNCHCHARGE', {item['Id'] for item in ship['Inventory_TechOnly']['Slots']})


if __name__ == '__main__':
    unittest.main()
