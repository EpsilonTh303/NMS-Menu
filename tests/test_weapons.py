import copy
import unittest

from nmsmenu.live_fleet import engine
from nmsmenu import weapons


def store(amount=10):
    return {'Slots': [{'Id': '^LASER', 'Amount': amount, 'MaxAmount': 100, 'DamageFactor': 0.0,
                       'Index': {'X': 0, 'Y': 0}, 'Type': {'InventoryType': 'Technology'},
                       'FullyInstalled': True, 'AddedAutomatically': False}],
            'ValidSlotIndices': [{'X': 0, 'Y': 0}], 'BaseStatValues': [], 'SpecialSlots': [],
            'Width': 1, 'Height': 1, 'Class': {'InventoryClass': 'B'}, 'IsCool': False,
            'Name': '', 'Version': 1, 'NumSlotsFromTech': 0,
            'StackSizeGroup': {'InventoryStackSizeGroup': 'Default'}, 'UnknownInventory': 123}


def tool(seed):
    return {'Seed': [True, seed], 'Name': '', 'Store': store(),
            'Layout': {'Slots': 1, 'Seed': [True, '0x1'], 'Level': 1},
            'Resource': {'Filename': 'MODELS/COMMON/WEAPONS/MULTITOOL/MULTITOOL.SCENE.MBIN',
                         'Seed': [False, '0x0'], 'AltId': '', 'ProceduralTexture': {'Samplers': []}},
            'CustomisationData': {'DescriptorGroups': [], 'PaletteID': '^', 'Colours': [],
                                  'TextureOptions': [], 'BoneScales': [], 'Scale': 1.0},
            'IsLarge': False, 'PrimaryMode': 0, 'SecondaryMode': 0, 'UseLegacyColours': True,
            'UnknownTool': {'keep': True}}


class WeaponTests(unittest.TestCase):
    def setUp(self):
        self.fleet = engine()
        tools = [tool('0x1'), tool('0x2')] + [weapons.clear_slot(tool('0x3')) for _ in range(4)]
        self.p = {'Multitools': tools, 'WeaponInventory': store(42), 'WeaponLayout': copy.deepcopy(tools[1]['Layout']),
                  'CurrentWeapon': {'Filename': tools[1]['Resource']['Filename'], 'GenerationSeed': [True, '0x2']},
                  'UnrelatedProgress': {'mission': 999}}
        self.data = {'ActiveContext': 'Main', 'BaseContext': {'PlayerStateData': self.p}, 'UnknownRoot': 456}

    def plan(self, op, index=1, **extra):
        target = self.p['Multitools'][index]
        return {'save_slot': 1, 'actions': [{'op': op, 'selector': {'slot': index + 1,
            'seed': target['Seed'][1], 'filename': target['Resource']['Filename']}, **extra}]}

    def mutate(self, plan):
        return weapons.mutate(self.data, plan, {}, self.fleet)

    def test_add_preserves_owned_tools_and_clones_authoritative_active_inventory(self):
        original = copy.deepcopy(self.data)
        edited, report, exports = self.mutate(self.plan('tool_add', seed='0xCAFE', name='New'))
        p = self.fleet.player(edited)
        self.assertEqual(self.data, original)
        self.assertEqual(p['Multitools'][:2], self.p['Multitools'][:2])
        self.assertEqual(p['Multitools'][2]['Store'], self.p['WeaponInventory'])
        self.assertEqual(p['Multitools'][2]['UnknownTool'], {'keep': True})
        self.assertEqual(p['CurrentWeapon'], self.p['CurrentWeapon'])
        self.assertEqual(len(p['Multitools']), 6)
        self.assertEqual(exports, [])

    def test_remove_active_exports_full_current_technology_and_syncs_replacement(self):
        edited, report, exports = self.mutate(self.plan('tool_remove'))
        p = self.fleet.player(edited)
        self.assertFalse(p['Multitools'][1]['Seed'][0])
        self.assertEqual(exports[0]['tool']['Store']['Slots'][0]['Amount'], 42)
        self.assertEqual(p['CurrentWeapon']['GenerationSeed'], [True, '0x1'])
        self.assertEqual(p['WeaponInventory'], self.p['Multitools'][0]['Store'])
        self.assertEqual(p['Multitools'][0], self.p['Multitools'][0])
        self.assertEqual(p['UnrelatedProgress'], self.p['UnrelatedProgress'])

    def test_remove_inactive_preserves_active_inventory(self):
        edited, _, _ = self.mutate(self.plan('tool_remove', index=0))
        p = self.fleet.player(edited)
        self.assertEqual(p['WeaponInventory'], self.p['WeaponInventory'])
        self.assertEqual(p['CurrentWeapon'], self.p['CurrentWeapon'])

    def test_last_tool_cannot_be_removed(self):
        self.p['Multitools'][0] = weapons.clear_slot(self.p['Multitools'][0])
        with self.assertRaises(ValueError):
            self.mutate(self.plan('tool_remove'))

    def test_full_array_is_never_expanded_but_removal_works(self):
        for i in range(2, 6):
            self.p['Multitools'][i] = tool(hex(i + 1))
        with self.assertRaises(ValueError):
            self.mutate(self.plan('tool_add', seed='0xCAFE'))
        edited, _, _ = self.mutate(self.plan('tool_remove'))
        self.assertEqual(len(self.fleet.player(edited)['Multitools']), 6)

    def test_duplicate_or_invalid_seeds_and_long_name_rejected(self):
        for seed in ('0x1', '0x0', '-1', '0x10000000000000000', 'not-hex'):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                self.mutate(self.plan('tool_add', seed=seed))
        with self.assertRaises(ValueError):
            self.mutate(self.plan('tool_add', seed='0xCAFE', name='a' * 32))

    def test_stale_identity_and_unknown_operation_rejected(self):
        plan = self.plan('tool_remove')
        plan['actions'][0]['selector']['seed'] = '0xCAFE'
        with self.assertRaises(ValueError):
            self.mutate(plan)
        with self.assertRaises(ValueError):
            self.mutate(self.plan('station_damage'))

    def test_uncertain_active_identity_blocks_all_mutations(self):
        self.p['CurrentWeapon']['GenerationSeed'][1] = '0xFFFF'
        with self.assertRaises(ValueError):
            self.mutate(self.plan('tool_add', seed='0xCAFE'))


if __name__ == '__main__':
    unittest.main()
