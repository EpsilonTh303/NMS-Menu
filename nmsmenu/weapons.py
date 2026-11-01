"""Transactional multitool ownership mutations; save editing requires stopped NMS."""
import copy

PREFIX = '/BaseContext/PlayerStateData/'


def owned(player):
    return [(i, tool) for i, tool in enumerate(player['Multitools']) if tool['Seed'][0]]


def select(player, selector):
    if not selector or set(selector) != {'slot', 'seed', 'filename'}:
        raise ValueError('Kesin alet yuvası, tohum ve model kimliği gerekli.')
    matches = [i for i, tool in owned(player) if i + 1 == selector['slot']
               and int(tool['Seed'][1], 16) == int(selector['seed'], 16)
               and tool['Resource']['Filename'].casefold() == selector['filename'].casefold()]
    if len(matches) != 1:
        raise ValueError('Alet kimliği güncel kayıtta tek bir aletle eşleşmedi.')
    return matches[0]


def active(player):
    matches = [i for i, tool in owned(player)
               if int(tool['Seed'][1], 16) == int(player['CurrentWeapon']['GenerationSeed'][1], 16)
               and tool['Resource']['Filename'].casefold() == player['CurrentWeapon']['Filename'].casefold()]
    if len(matches) != 1:
        raise ValueError('Aktif çok amaçlı alet kimliği doğrulanamadı.')
    return matches[0]


def summary(player):
    primary = active(player)
    return [{'slot': i + 1, 'name': tool['Name'] or '(prosedürel ad)', 'seed': tool['Seed'][1],
             'filename': tool['Resource']['Filename'], 'class': tool['Store']['Class']['InventoryClass'],
             'slots': len((player['WeaponInventory'] if i == primary else tool['Store'])['ValidSlotIndices']),
             'active': i == primary} for i, tool in owned(player)]


def clear_slot(tool):
    """Reset known ownership fields while retaining unknown schema fields."""
    tool = copy.deepcopy(tool)
    tool.update(Name='', Seed=[False, '0x0'], IsLarge=False, PrimaryMode=0, SecondaryMode=0, UseLegacyColours=True)
    tool['Resource'].update(Filename='', Seed=[False, '0x0'], AltId='')
    tool['Resource']['ProceduralTexture']['Samplers'] = []
    tool['Store'].update(Slots=[], ValidSlotIndices=[], BaseStatValues=[], SpecialSlots=[], Width=0, Height=0,
                         IsCool=False, Name='', Version=0, NumSlotsFromTech=0)
    tool['Store']['Class']['InventoryClass'] = 'C'
    tool['CustomisationData'].update(DescriptorGroups=[], PaletteID='^', Colours=[], TextureOptions=[], BoneScales=[], Scale=1.0)
    return tool


def mutate(original, plan, unused_catalog, fleet):
    if len(plan.get('actions', [])) != 1:
        raise ValueError('Her silah isteği için tek eylemli yeni plan hazırlayın.')
    data = copy.deepcopy(original)
    p = fleet.player(data)
    tools = p['Multitools']
    if len(tools) != 6:
        raise ValueError('Bu kayıt sürümünün çok amaçlı alet dizisi doğrulanmadı.')
    current = active(p)
    action = plan['actions'][0]
    op = action['op']
    index = select(p, action['selector'])
    allowed, exports = [], []
    if op == 'tool_add':
        empty = next((i for i, tool in enumerate(tools) if not tool['Seed'][0]), None)
        if empty is None:
            raise ValueError('Altı aktif alet yuvası dolu. Sabit dizi genişletilmedi.')
        seed = action.get('seed', '')
        try:
            number = int(seed, 16)
        except (ValueError, TypeError):
            raise ValueError('Geçerli hexadecimal tohum gerekli.')
        if not 0 < number < 2 ** 64 or any(int(t['Seed'][1], 16) == number for _, t in owned(p)):
            raise ValueError('Tohum benzersiz, sıfırdan büyük uint64 olmalı.')
        name = action.get('name', 'Yeni Alet')
        if not isinstance(name, str) or len(name.encode('utf-8')) > 31:
            raise ValueError('Alet adı UTF-8 olarak en fazla 31 byte olmalı.')
        tool = copy.deepcopy(tools[index])
        if index == current:
            tool['Store'] = copy.deepcopy(p['WeaponInventory'])
            tool['Layout'] = copy.deepcopy(p['WeaponLayout'])
        tool['Seed'] = [True, f'0x{number:016X}']
        tool['Name'] = name
        tools[empty] = tool
        allowed.append(PREFIX + f'Multitools/{empty}')
        event = {'op': op, 'source_slot': index + 1, 'new_slot': empty + 1, 'name': name,
                 'seed': tool['Seed'][1], 'note': 'Kaynak aletin modeli, sınıfı ve donanımı kopyalandı; görünüm tohumu yeni.'}
    elif op == 'tool_remove':
        if len(owned(p)) <= 1:
            raise ValueError('Son çok amaçlı alet silinemez.')
        exported = copy.deepcopy(tools[index])
        if index == current:
            exported['Store'] = copy.deepcopy(p['WeaponInventory'])
            exported['Layout'] = copy.deepcopy(p['WeaponLayout'])
        exports.append({'kind': 'multitool', 'slot': index + 1, 'tool': exported})
        tools[index] = clear_slot(tools[index])
        allowed.append(PREFIX + f'Multitools/{index}')
        event = {'op': op, 'removed_slot': index + 1, 'full_tool_exported': True}
        if index == current:
            replacement, tool = owned(p)[0]
            p['WeaponInventory'] = copy.deepcopy(tool['Store'])
            p['WeaponLayout'] = copy.deepcopy(tool['Layout'])
            p['CurrentWeapon']['Filename'] = tool['Resource']['Filename']
            p['CurrentWeapon']['GenerationSeed'] = copy.deepcopy(tool['Seed'])
            allowed += [PREFIX + key for key in ('WeaponInventory', 'WeaponLayout', 'CurrentWeapon')]
            event['new_active_slot'] = replacement + 1
    else:
        raise ValueError('Desteklenmeyen silah işlemi.')
    diffs = fleet.differences(original, data)
    if not all(any(path == prefix or path.startswith(prefix + '/') for prefix in allowed) for path in diffs):
        raise ValueError('Silah işlemi izinli alanları aştı.')
    if len(tools) != len(fleet.player(original)['Multitools']):
        raise ValueError('Sabit alet dizisi değişti.')
    active(p)
    for _, tool in owned(p):
        inv = tool['Store']
        valid = {(s['X'], s['Y']) for s in inv['ValidSlotIndices']}
        occupied = [(s['Index']['X'], s['Index']['Y']) for s in inv['Slots']]
        if len(occupied) != len(set(occupied)) or not set(occupied) <= valid:
            raise ValueError('Alet envanter koordinatları geçersiz.')
    return data, {'events': [event], 'changed_paths': diffs, 'multitools': summary(p)}, exports
