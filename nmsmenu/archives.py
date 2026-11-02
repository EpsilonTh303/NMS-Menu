"""Native 18-slot archives. Ship removal delegates to FleetManager, preserving cargo."""
import copy

from . import weapons
from .catalog_data import tool_models


SHIP_CLASSES = {'fighter': 'Fighter', 'hauler': 'Dropship', 'explorer': 'Scientific', 'shuttle': 'Shuttle',
                'exotic': 'Royal', 'solar': 'Sail', 'sentinel': 'Robot', 'starborn': 'Fighter',
                'golden': 'Fighter', 'utopia': 'Fighter', 'boundary': 'Fighter'}


def tool_class(tool):
    path = tool['Resource']['Filename'].upper()
    for marker, name in [('SENTINELMULTITOOL', 'Robot'), ('ROYALMULTITOOL', 'Royal'),
                         ('STAFF', 'Staff'), ('ATLASMULTITOOL', 'Atlas'), ('SWARMMULTITOOL', 'Rifle'),
                         ('SWITCHMULTITOOL', 'Rifle'), ('RETROMULTITOOL', 'Pistol')]:
        if marker in path:
            return name
    for profile in tool_models().values():
        if profile.get('seed') and int(profile['seed'], 16) == int(tool['Seed'][1], 16) and profile['model'].upper() == path:
            return profile['family']
    return None


def select_archive(entries, selector, resource, fleet):
    matches = []
    for i, entry in enumerate(entries):
        obj = entry[resource]
        owned = obj['Seed'][0] if resource == 'MultitoolData' else fleet.kind(obj) != 'empty'
        seed = obj['Seed'][1] if resource == 'MultitoolData' else obj['Resource']['Seed'][1]
        if owned and selector.get('slot') == i + 1 and selector.get('seed', '').casefold() == seed.casefold() and selector.get('filename', '').casefold() == obj['Resource']['Filename'].casefold():
            matches.append(i)
    if len(matches) != 1 or set(selector) != {'slot', 'seed', 'filename'}:
        raise ValueError('Arşivdeki kesin yuva / model / tohum kimliği değişmiş.')
    return matches[0]


def mutate(original, action, catalog, fleet, native_mutate):
    data = copy.deepcopy(original)
    p = fleet.player(data)
    ships, tools = p.get('ArchivedShipOwnership', []), p.get('ArchivedMultitools', [])
    if len(ships) != 18 or len(tools) != 18 or len(p['ShipOwnership']) != 12 or len(p['Multitools']) != 6:
        raise ValueError('Bu kaydın sabit arşiv / aktif dizi boyutları doğrulanmadı.')
    allowed, exports = [], []
    op = action['op']
    if op == 'archive_ship':
        from . import inventory
        index = fleet.select(p, action['selector'])
        ship = p['ShipOwnership'][index]
        kind = fleet.kind(ship)
        if kind not in SHIP_CLASSES:
            raise ValueError('Bu gemi ailesinin arşiv metadata eşlemesi doğrulanmadı.')
        if index == p['PrimaryShip'] and data['BaseContext']['SpawnStateData']['LastKnownPlayerState'] != 'InStation':
            raise ValueError('Aktif gemiyi arşivlemek için önce istasyonda kaydedin veya başka gemiyi aktif yapın.')
        target = next((i for i, a in enumerate(ships) if fleet.kind(a['Ownership']) == 'empty'), None)
        if target is None:
            raise ValueError('18 yerleşik gemi arşiv yuvası dolu; harici garajı kullanın.')
        payload = fleet.capture_ship(p, index)
        carried_before = len(p['Inventory']['Slots'])
        data, report, exports = native_mutate(data, {'actions': [{'op': 'remove', 'selector': action['selector'], 'preserve_cargo': True}]}, catalog)
        p = fleet.player(data)
        for item in p['Inventory']['Slots'][carried_before:]:
            ident = item['Id'].lstrip('^')
            if inventory.ordinary(item):
                limit = inventory.stack_limit(p, p['Inventory'], inventory.items()[ident])
            else:
                # Unknown cargo is preserved only within the verified base limit.
                cargo_kind = item['Type']['InventoryType']
                if cargo_kind not in ('Product', 'Substance'):
                    raise ValueError('Eski kargo bölümünde teknoloji var; önce oyun içinde taşıyın.')
                limit = inventory.stack_limit(p, p['Inventory'], {'kind': cargo_kind, 'stack_multiplier': 1})
            if not 0 <= item['Amount'] <= min(item['MaxAmount'], limit):
                raise ValueError('Gemi kargosu ekzosuit yığın sınırına sığmıyor; önce yığını bölün veya oyun içinde boşaltın.')
            item['MaxAmount'] = min(item['MaxAmount'], limit)
        a = p['ArchivedShipOwnership'][target]
        a['Ownership'] = copy.deepcopy(payload['ship'])
        # Cargo was transferred by the native engine, never silently discarded.
        for key in ('Inventory', 'Inventory_Cargo'):
            a['Ownership'][key]['Slots'] = []
        a.update(Customisation=copy.deepcopy(payload['customisation']), UsesLegacyColours=payload['legacy'], ArchivedName=ship['Name'])
        a['ArchivedClass']['ShipClass'] = SHIP_CLASSES[kind]
        a['ArchivedInventoryClass']['InventoryClass'] = ship['Inventory']['Class']['InventoryClass']
        for entry in exports:
            entry['garage'] = True
        allowed += report['changed_paths']
        allowed.append(fleet.PREFIX + f'ArchivedShipOwnership/{target}')
        event = {'op': op, 'source_slot': index + 1, 'archive_slot': target + 1,
                 'cargo_preserved': 'exosuit', 'full_ship_export': 'external garage before apply'}
    elif op == 'restore_archived_ship':
        index = select_archive(ships, action['selector'], 'Ownership', fleet)
        target = next((i for i, ship in enumerate(p['ShipOwnership']) if fleet.kind(ship) == 'empty'), None)
        if target is None:
            raise ValueError('12 aktif gemi yuvası dolu; önce bir gemiyi arşivleyin.')
        a = ships[index]
        if fleet.kind(a['Ownership']) not in SHIP_CLASSES:
            raise ValueError('Bu arşiv gemisi desteklenmiyor.')
        if any(s['Resource'] == a['Ownership']['Resource'] for _, s in fleet.owned(p)):
            raise ValueError('Aynı gemi zaten aktif filoda.')
        empty = fleet.blank_ship(p)
        p['ShipOwnership'][target] = copy.deepcopy(a['Ownership'])
        p['CharacterCustomisationData'][fleet.custom_index(target)] = copy.deepcopy(a['Customisation'])
        p['ShipUsesLegacyColours'][target] = a['UsesLegacyColours']
        a['Ownership'] = empty
        a['Customisation'] = fleet.fresh_custom(p, target)
        a.update(ArchivedName='', UsesLegacyColours=False)
        a['ArchivedClass']['ShipClass'] = 'Freighter'
        a['ArchivedInventoryClass']['InventoryClass'] = 'C'
        allowed += [fleet.PREFIX + f'ArchivedShipOwnership/{index}', fleet.PREFIX + f'ShipOwnership/{target}',
                    fleet.PREFIX + f'CharacterCustomisationData/{fleet.custom_index(target)}', fleet.PREFIX + f'ShipUsesLegacyColours/{target}']
        event = {'op': op, 'archive_slot': index + 1, 'active_slot': target + 1}
    elif op == 'archive_tool':
        index = weapons.select(p, action['selector'])
        target = next((i for i, a in enumerate(tools) if not a['MultitoolData']['Seed'][0]), None)
        if target is None:
            raise ValueError('18 alet arşiv yuvası dolu.')
        family = tool_class(p['Multitools'][index]) or action.get('weapon_class')
        if family not in ('Pistol', 'Rifle', 'Alien', 'Pristine', 'Royal', 'Robot', 'Staff', 'Atlas'):
            raise ValueError('Ortak model için doğru Pistol/Rifle/Alien/Pristine ailesini seçin.')
        data, report, exports = weapons.mutate(data, {'actions': [{'op': 'tool_remove', 'selector': action['selector']}]}, catalog, fleet)
        p = fleet.player(data)
        tool = exports[0]['tool']
        a = p['ArchivedMultitools'][target]
        a['MultitoolData'] = copy.deepcopy(tool)
        a['ArchivedName'] = tool['Name']
        a['ArchivedInventoryClass']['InventoryClass'] = tool['Store']['Class']['InventoryClass']
        a['WeaponClass']['WeaponStatClass'] = family
        allowed += report['changed_paths'] + [fleet.PREFIX + f'ArchivedMultitools/{target}']
        event = {'op': op, 'source_slot': index + 1, 'archive_slot': target + 1, 'weapon_class': family}
    elif op == 'restore_archived_tool':
        index = select_archive(tools, action['selector'], 'MultitoolData', fleet)
        target = next((i for i, tool in enumerate(p['Multitools']) if not tool['Seed'][0]), None)
        if target is None:
            raise ValueError('6 aktif alet yuvası dolu; önce birini arşivleyin.')
        a = tools[index]
        incoming = a['MultitoolData']
        if any(t['Seed'] == incoming['Seed'] and t['Resource']['Filename'] == incoming['Resource']['Filename'] for _, t in weapons.owned(p)):
            raise ValueError('Aynı alet zaten aktif koleksiyonda.')
        p['Multitools'][target] = copy.deepcopy(incoming)
        a['MultitoolData'] = weapons.clear_slot(incoming)
        a['ArchivedName'] = ''
        a['ArchivedInventoryClass']['InventoryClass'] = 'C'
        a['WeaponClass']['WeaponStatClass'] = 'Pistol'
        allowed += [fleet.PREFIX + f'ArchivedMultitools/{index}', fleet.PREFIX + f'Multitools/{target}']
        event = {'op': op, 'archive_slot': index + 1, 'active_slot': target + 1}
    else:
        raise ValueError('Bilinmeyen arşiv işlemi.')
    paths = fleet.differences(original, data)
    if not all(any(path == key or path.startswith(key.rstrip('/') + '/') for key in allowed) for path in paths):
        raise ValueError('Arşiv işlemi izinli alanları aştı.')
    return data, event, paths, exports


def snapshot(player, fleet):
    result = []
    for field, resource, kind in [('ArchivedShipOwnership', 'Ownership', 'ship'), ('ArchivedMultitools', 'MultitoolData', 'multitool')]:
        for i, archive in enumerate(player.get(field, [])):
            obj = archive[resource]
            if not (obj['Seed'][0] if kind == 'multitool' else fleet.kind(obj) != 'empty'):
                continue
            result.append({'kind': kind, 'name': archive['ArchivedName'] or '(prosedürel ad)',
                'class': archive['ArchivedInventoryClass']['InventoryClass'],
                'selector': {'slot': i + 1, 'seed': obj['Seed'][1] if kind == 'multitool' else obj['Resource']['Seed'][1],
                             'filename': obj['Resource']['Filename']}})
    return result
