import copy
import tempfile
from pathlib import Path
import unittest

from nmsmenu import inventory, archives, weapons, loadouts, knowledge
from nmsmenu.catalog_service import CatalogService
from nmsmenu.catalog_mutations import mutate
from nmsmenu.live_fleet import engine
from nmsmenu.backend import ROOT
from test_weapons import store, tool


def inv(count=10, group='Personal'):
    value = store()
    value['Slots'] = []
    value['ValidSlotIndices'] = [{'X': i % 10, 'Y': i // 10} for i in range(count)]
    value.update(Width=10, Height=(count + 9) // 10)
    value['StackSizeGroup']['InventoryStackSizeGroup'] = group
    return value


def custom():
    return {'SelectedPreset': '^', 'CustomData': {'DescriptorGroups': [], 'PaletteID': '^',
        'Colours': [], 'TextureOptions': [], 'BoneScales': [], 'Scale': 1.0, 'Unknown': 77}}


def ship(seed=None):
    return {'Name': 'Ship' if seed else '', 'Resource': {'Filename': 'MODELS/COMMON/SPACECRAFT/FIGHTERS/FIGHTER_PROC.SCENE.MBIN' if seed else '',
        'Seed': [bool(seed), seed or '0x0'], 'AltId': '', 'ProceduralTexture': {'Samplers': []}},
        'Inventory': inv(10, 'Ship'), 'Inventory_Cargo': inv(0, 'ShipCargo'), 'Inventory_TechOnly': inv(20, 'Ship'), 'UnknownShip': 123}


def fixture():
    tools = [tool('0x1'), tool('0x2')] + [weapons.clear_slot(tool('0x3')) for _ in range(4)]
    for t in tools[:2]:
        t['Store'] = inv(20)
    p = {'PrimaryShip': 0, 'ShipOwnership': [ship('0xA'), ship('0xB')] + [ship() for _ in range(10)],
        'ShipUsesLegacyColours': [False] * 12, 'CharacterCustomisationData': [custom() for _ in range(30)],
        'Inventory': inv(), 'Inventory_TechOnly': inv(20), 'Multitools': tools,
        'WeaponInventory': copy.deepcopy(tools[0]['Store']), 'WeaponLayout': tools[0]['Layout'],
        'CurrentWeapon': {'Filename': tools[0]['Resource']['Filename'], 'GenerationSeed': tools[0]['Seed']},
        'DifficultyState': {'Settings': {'InventoryStackLimits': {'InventoryStackLimitsDifficulty': 'High'}}},
        'ArchivedShipOwnership': [{'Ownership': ship(), 'Customisation': custom(), 'UsesLegacyColours': False,
            'ArchivedName': '', 'ArchivedClass': {'ShipClass': 'Freighter'}, 'ArchivedInventoryClass': {'InventoryClass': 'C'}, 'UnknownArchive': 888} for _ in range(18)],
        'ArchivedMultitools': [{'MultitoolData': weapons.clear_slot(tool('0x3')), 'ArchivedName': '',
            'ArchivedInventoryClass': {'InventoryClass': 'C'}, 'WeaponClass': {'WeaponStatClass': 'Pistol'}, 'UnknownArchive': 999} for _ in range(18)],
        'UnrelatedProgress': {'currency': 123456, 'missions': ['keep']}}
    p.update(KnownTech=[], KnownProducts=[])
    return {'ActiveContext': 'Main', 'Version': 1234, 'BaseContext': {'PlayerStateData': p, 'SpawnStateData': {'LastKnownPlayerState': 'InStation'}}}


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.fleet, self.data = engine(), fixture()
        self.p = self.fleet.player(self.data)
        self.spec = {'kind': 'exosuit', 'section': 'cargo'}

    def apply(self, action, data=None):
        return inventory.mutate(data or self.data, {'inventory': self.spec, **action}, self.fleet)[0]

    def add(self, ident='FUEL1', amount=50, data=None):
        return self.apply({'op': 'add_item', 'id': ident, 'amount': amount}, data)

    def test_limits_follow_difficulty_container_and_product_multiplier(self):
        carbon, casing = inventory.items()['FUEL1'], inventory.items()['CASING']
        self.assertEqual(inventory.stack_limit(self.p, self.p['Inventory'], carbon), 9999)
        self.assertEqual(inventory.stack_limit(self.p, self.p['Inventory'], casing), 20)
        self.p['DifficultyState']['Settings']['InventoryStackLimits']['InventoryStackLimitsDifficulty'] = 'Low'
        self.assertEqual(inventory.stack_limit(self.p, self.p['Inventory'], carbon), 300)
        self.assertEqual(inventory.stack_limit(self.p, self.p['Inventory'], casing), 6)

    def test_add_fills_compatible_stacks_and_allocates_without_losing_unknown_fields(self):
        data = self.add('CASING', 45)
        slots = self.fleet.player(data)['Inventory']['Slots']
        self.assertEqual([s['Amount'] for s in slots], [20, 20, 5])
        data = self.add('CASING', 10, data)
        self.assertEqual([s['Amount'] for s in self.fleet.player(data)['Inventory']['Slots']], [20, 20, 15])
        self.assertEqual(self.p['Inventory']['Slots'], [])
        self.assertEqual(self.fleet.player(data)['UnrelatedProgress'], self.p['UnrelatedProgress'])

    def test_no_space_and_invalid_items_leave_source_unchanged(self):
        self.p['Inventory']['ValidSlotIndices'] = []
        before = copy.deepcopy(self.data)
        with self.assertRaises(ValueError):
            self.add()
        self.assertEqual(self.data, before)
        for ident in ('NOT_REAL', 'MISSION_TEST', 'BUILD_REFINER1'):
            with self.subTest(ident=ident), self.assertRaises(ValueError):
                self.add(ident)

    def test_stale_identity_is_rejected(self):
        data = self.add()
        item = self.fleet.player(data)['Inventory']['Slots'][0]
        identity = inventory.fingerprint(item)
        item['Amount'] += 1
        with self.assertRaises(ValueError):
            self.apply({'op': 'set_item_amount', 'item': identity, 'amount': 20}, data)

    def test_split_merge_conserve_quantity_and_unknown_stack_metadata(self):
        data = self.add(amount=99)
        item = self.fleet.player(data)['Inventory']['Slots'][0]
        item['UnknownStack'] = {'keep': 5}
        data = self.apply({'op': 'split_item', 'item': inventory.fingerprint(item), 'amount': 25,
            'destination': self.spec, 'position': {'X': 1, 'Y': 0}}, data)
        slots = self.fleet.player(data)['Inventory']['Slots']
        self.assertEqual([s['Amount'] for s in slots], [74, 25])
        self.assertTrue(all(s['UnknownStack'] == {'keep': 5} for s in slots))
        data = self.apply({'op': 'merge_stacks'}, data)
        slots = self.fleet.player(data)['Inventory']['Slots']
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]['Amount'], 99)
        self.assertEqual(slots[0]['UnknownStack'], {'keep': 5})

    def test_move_to_ship_conserves_item_and_applies_destination_limit(self):
        data = self.add('CASING', 12)
        item = self.fleet.player(data)['Inventory']['Slots'][0]
        dest = {'kind': 'ship', 'section': 'cargo', 'selector': {'slot': 2, 'seed': '0xB', 'type': 'fighter'}}
        data = self.apply({'op': 'move_item', 'item': inventory.fingerprint(item), 'destination': dest, 'position': {'X': 2, 'Y': 0}}, data)
        p = self.fleet.player(data)
        self.assertEqual(p['Inventory']['Slots'], [])
        self.assertEqual(p['ShipOwnership'][1]['Inventory']['Slots'][0]['Amount'], 12)
        self.assertEqual(p['ShipOwnership'][1]['Inventory']['Slots'][0]['MaxAmount'], 20)

    def test_occupied_locked_and_cross_section_destinations_are_rejected(self):
        data = self.add()
        item = self.fleet.player(data)['Inventory']['Slots'][0]
        for dest, pos in [(self.spec, {'X': 0, 'Y': 0}), (self.spec, {'X': 9, 'Y': 9}),
                          ({'kind': 'exosuit', 'section': 'tech'}, {'X': 1, 'Y': 0})]:
            with self.subTest(dest=dest, pos=pos), self.assertRaises(ValueError):
                self.apply({'op': 'move_item', 'item': inventory.fingerprint(item), 'destination': dest, 'position': pos}, data)

    def test_active_tool_reposition_syncs_store_and_keeps_supercharged_slots(self):
        spec = {'kind': 'multitool', 'section': 'tech', 'selector': {'slot': 1, 'seed': '0x1', 'filename': self.p['CurrentWeapon']['Filename']}}
        item = self.fleet.tech('BOLT', 100)
        self.p['WeaponInventory']['Slots'] = [item]
        bonus = {'Type': {'InventorySpecialSlotType': 'TechBonus'}, 'Index': {'X': 2, 'Y': 0}}
        self.p['WeaponInventory']['SpecialSlots'] = [bonus]
        data = self.apply({'op': 'move_item', 'inventory': spec, 'item': inventory.fingerprint(item), 'destination': spec, 'position': {'X': 1, 'Y': 0}})
        p = self.fleet.player(data)
        self.assertEqual(p['WeaponInventory'], p['Multitools'][0]['Store'])
        self.assertEqual(p['WeaponInventory']['SpecialSlots'], [bonus])

    def test_quantity_validation_rejects_bool_zero_negative_and_overflow(self):
        for amount in (True, 0, -1, 10_000_001, 1.5):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.add(amount=amount)

    def test_merge_does_not_drain_earlier_full_stacks_or_combine_different_metadata(self):
        data = self.add('CASING', 25)
        before = copy.deepcopy(self.fleet.player(data)['Inventory']['Slots'])
        data = self.apply({'op': 'merge_stacks'}, data)
        self.assertEqual(self.fleet.player(data)['Inventory']['Slots'], before)
        before[0]['UnknownTag'] = 1
        self.fleet.player(data)['Inventory']['Slots'] = before
        data = self.apply({'op': 'merge_stacks'}, data)
        self.assertEqual(len(self.fleet.player(data)['Inventory']['Slots']), 2)

    def test_technology_inventory_cannot_receive_cargo(self):
        with self.assertRaises(ValueError):
            self.apply({'op': 'add_item', 'id': 'FUEL1', 'amount': 1, 'inventory': {'kind': 'exosuit', 'section': 'tech'}})


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.fleet, self.data = engine(), fixture()
        self.p = self.fleet.player(self.data)
        self.selector = {'slot': 2, 'seed': '0xB', 'type': 'fighter'}

    def apply(self, action, data=None):
        return archives.mutate(data or self.data, action, {}, self.fleet, self.fleet.mutate)

    def test_ship_archive_preserves_cargo_in_suit_tech_in_archive_and_full_export(self):
        item = self.fleet.tech('CASING', 5)
        item['Type']['InventoryType'] = 'Product'
        self.p['ShipOwnership'][1]['Inventory']['Slots'] = [item]
        self.p['ShipOwnership'][1]['Inventory_TechOnly']['Slots'] = [self.fleet.tech('SHIPGUN1')]
        original = copy.deepcopy(self.p['ShipOwnership'][1])
        data, event, paths, exports = self.apply({'op': 'archive_ship', 'selector': self.selector})
        p = self.fleet.player(data)
        self.assertEqual(p['Inventory']['Slots'], [item])
        self.assertEqual(p['ArchivedShipOwnership'][0]['Ownership']['Inventory']['Slots'], [])
        self.assertEqual(p['ArchivedShipOwnership'][0]['Ownership']['Inventory_TechOnly'], original['Inventory_TechOnly'])
        self.assertEqual(p['ArchivedShipOwnership'][0]['UnknownArchive'], 888)
        self.assertEqual(exports[0]['ship'], original)
        self.assertTrue(exports[0]['garage'])
        self.assertEqual(len(p['ShipOwnership']), 12)
        self.assertEqual(len(p['ArchivedShipOwnership']), 18)

    def test_full_twelve_ship_array_can_archive_using_empty_archive_template(self):
        self.p['ShipOwnership'] = [ship(hex(i + 10)) for i in range(12)]
        data, *_ = self.apply({'op': 'archive_ship', 'selector': {'slot': 2, 'seed': hex(11), 'type': 'fighter'}})
        p = self.fleet.player(data)
        self.assertEqual(len(self.fleet.owned(p)), 11)
        self.assertEqual(len(p['ShipOwnership']), 12)

    def test_ship_restore_preserves_identity_customisation_and_native_cap(self):
        original = copy.deepcopy(self.p['ShipOwnership'][1])
        data, *_ = self.apply({'op': 'archive_ship', 'selector': self.selector})
        archived = archives.snapshot(self.fleet.player(data), self.fleet)[0]
        data, *_ = self.apply({'op': 'restore_archived_ship', 'selector': archived['selector']}, data)
        p = self.fleet.player(data)
        self.assertEqual(p['ShipOwnership'][1], original)
        self.assertEqual(p['ArchivedShipOwnership'][0]['Ownership']['Resource']['Filename'], '')
        self.assertEqual(p['UnrelatedProgress'], self.p['UnrelatedProgress'])

    def test_cargo_does_not_disappear_when_suit_is_full(self):
        self.p['ShipOwnership'][1]['Inventory']['Slots'] = [self.fleet.tech('CASING')]
        self.p['Inventory']['ValidSlotIndices'] = []
        before = copy.deepcopy(self.data)
        with self.assertRaises(ValueError):
            self.apply({'op': 'archive_ship', 'selector': self.selector})
        self.assertEqual(self.data, before)

    def test_active_ship_cannot_archive_outside_station(self):
        self.data['BaseContext']['SpawnStateData']['LastKnownPlayerState'] = 'OnFoot'
        with self.assertRaises(ValueError):
            self.apply({'op': 'archive_ship', 'selector': {'slot': 1, 'seed': '0xA', 'type': 'fighter'}})

    def test_ship_cargo_respects_lower_suit_stack_limit_without_losing_original_export(self):
        self.p['DifficultyState']['Settings']['InventoryStackLimits']['InventoryStackLimitsDifficulty'] = 'Normal'
        item = self.fleet.tech('FUEL1', 1000)
        item['Type']['InventoryType'] = 'Substance'
        item['Amount'] = 100
        self.p['ShipOwnership'][1]['Inventory']['Slots'] = [item]
        data, _, _, exports = self.apply({'op': 'archive_ship', 'selector': self.selector})
        self.assertEqual(self.fleet.player(data)['Inventory']['Slots'][0]['Amount'], 100)
        self.assertEqual(self.fleet.player(data)['Inventory']['Slots'][0]['MaxAmount'], 500)
        self.assertEqual(exports[0]['ship']['Inventory']['Slots'][0]['MaxAmount'], 1000)
        item['Amount'] = 600
        with self.assertRaises(ValueError):
            self.apply({'op': 'archive_ship', 'selector': self.selector})

    def test_unknown_single_stack_cargo_is_preserved_without_changing_ship_class(self):
        item = self.fleet.tech('BUILD_REFINER1', 1)
        item['Type']['InventoryType'] = 'Product'
        self.p['ShipOwnership'][1]['Inventory']['Slots'] = [item]
        data, *_ = self.apply({'op': 'archive_ship', 'selector': self.selector})
        p = self.fleet.player(data)
        self.assertEqual(p['Inventory']['Slots'], [item])
        self.assertEqual(p['ArchivedShipOwnership'][0]['ArchivedClass']['ShipClass'], 'Fighter')

    def test_active_tool_archive_and_restore_preserve_authoritative_equipment(self):
        selector = {'slot': 1, 'seed': '0x1', 'filename': self.p['CurrentWeapon']['Filename']}
        self.p['WeaponInventory']['Slots'] = [self.fleet.tech('BOLT', 175)]
        data, _, _, exports = self.apply({'op': 'archive_tool', 'selector': selector, 'weapon_class': 'Rifle'})
        p = self.fleet.player(data)
        self.assertEqual(p['ArchivedMultitools'][0]['MultitoolData']['Store'], self.p['WeaponInventory'])
        self.assertEqual(weapons.active(p), 1)
        self.assertEqual(p['ArchivedMultitools'][0]['UnknownArchive'], 999)
        archived = next(p for p in archives.snapshot(p, self.fleet) if p['kind'] == 'multitool')
        data, *_ = self.apply({'op': 'restore_archived_tool', 'selector': archived['selector']}, data)
        p = self.fleet.player(data)
        self.assertEqual(p['Multitools'][0], exports[0]['tool'])
        self.assertFalse(p['ArchivedMultitools'][0]['MultitoolData']['Seed'][0])
        self.assertEqual(len(p['Multitools']), 6)

    def test_unknown_common_model_needs_explicit_family_and_last_tool_is_protected(self):
        selector = {'slot': 1, 'seed': '0x1', 'filename': self.p['CurrentWeapon']['Filename']}
        with self.assertRaises(ValueError):
            self.apply({'op': 'archive_tool', 'selector': selector})
        self.p['Multitools'][1] = weapons.clear_slot(self.p['Multitools'][1])
        with self.assertRaises(ValueError):
            self.apply({'op': 'archive_tool', 'selector': selector, 'weapon_class': 'Pistol'})

    def test_wrong_archive_identity_cannot_restore_another_ship(self):
        data, *_ = self.apply({'op': 'archive_ship', 'selector': self.selector})
        selector = archives.snapshot(self.fleet.player(data), self.fleet)[0]['selector']
        selector['seed'] = '0xFFFF'
        with self.assertRaises(ValueError):
            self.apply({'op': 'restore_archived_ship', 'selector': selector}, data)


class ServiceTests(unittest.TestCase):
    def test_learning_is_idempotent_and_does_not_set_mission_or_reward_flags(self):
        fleet, original = engine(), fixture()
        action = {'op': 'learn_recipe', 'kind': 'product', 'id': 'CASING'}
        data, event, paths = knowledge.mutate(original, action, fleet)
        self.assertEqual(paths, [fleet.PREFIX + 'KnownProducts'])
        self.assertEqual(fleet.player(data)['UnrelatedProgress'], fleet.player(original)['UnrelatedProgress'])
        result, event, paths = knowledge.mutate(data, action, fleet)
        self.assertEqual(result, data)
        self.assertTrue(event['already_known'])
        self.assertEqual(paths, [])
        with self.assertRaises(ValueError):
            knowledge.mutate(original, {'op': 'learn_recipe', 'kind': 'product', 'id': 'FUEL1'}, fleet)

    def test_personal_profiles_and_favorites_persist_without_changing_game_data(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as temp:
            path = Path(temp)
            store = loadouts.LoadoutStore(path / 'sets.json')
            key = store.save('Keşif', 'multitool', ['SCAN1', 'SCAN1', 'SCANBINOC1'])
            self.assertEqual(store.all()[key]['ids'], ['SCAN1', 'SCANBINOC1'])
            service = CatalogService(path / 'favorites.json')
            service.toggle_favorite('item:FUEL1')
            service.remember(['item:FUEL1'])
            other = CatalogService(path / 'favorites.json')
            self.assertEqual([i.key for i in other.items(favorites_only=True)], ['item:FUEL1'])
            self.assertEqual([i.key for i in other.items(recent_only=True)], ['item:FUEL1'])

    def test_loadout_rejects_wrong_target_and_unknown_procedural_modules(self):
        with self.assertRaises(ValueError):
            loadouts.commands(loadouts.BUILTINS['tool_combat'], {'kind': 'exosuit', 'section': 'tech'})
        with tempfile.TemporaryDirectory(dir=ROOT / 'runtime') as temp, self.assertRaises(ValueError):
            loadouts.LoadoutStore(Path(temp) / 'sets.json').save('Bad', 'multitool', ['UP_FAKE#123'])

    def test_every_builtin_profile_has_compatible_fixed_technology(self):
        for key, profile in loadouts.BUILTINS.items():
            spec = {'kind': profile['target'], 'section': 'tech'}
            if profile['target'] == 'ship':
                spec['selector'] = {'slot': 1, 'type': 'fighter', 'seed': '0x1'}
            elif profile['target'] == 'multitool':
                spec['selector'] = {'slot': 1, 'filename': 'tool', 'seed': '0x1'}
            with self.subTest(key=key):
                self.assertEqual(len(loadouts.commands(profile, spec)), len(profile['ids']))

    def test_failed_mixed_cart_does_not_partially_modify_source(self):
        fleet, original = engine(), fixture()
        before = copy.deepcopy(original)
        actions = [{'op': 'add_item', 'inventory': {'kind': 'exosuit', 'section': 'cargo'}, 'id': 'CASING', 'amount': 3},
                   {'op': 'archive_ship', 'selector': {'slot': 8, 'seed': '0xFFFF', 'type': 'fighter'}}]
        with self.assertRaises(ValueError):
            mutate(original, {'actions': actions}, {}, fleet, fleet.mutate)
        self.assertEqual(original, before)


if __name__ == '__main__':
    unittest.main()
