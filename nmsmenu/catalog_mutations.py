"""Catalog transaction adapter. Each operation owns its semantic write allowlist."""
import copy

from . import weapons
from .catalog_data import compatible, technologies


def install(original, action, fleet):
    ident = action['id']
    if ident not in technologies():
        raise ValueError('Bu teknoloji yerel sürüm kataloğunda yok.')
    entry = technologies()[ident]
    data = copy.deepcopy(original)
    p = fleet.player(data)
    target = action['target']
    ship_type, index = None, None
    if target == 'exosuit':
        inv = p['Inventory_TechOnly']
        prefix = fleet.PREFIX + 'Inventory_TechOnly/Slots'
    elif target == 'ship':
        index = fleet.select(p, action['selector'])
        ship = p['ShipOwnership'][index]
        ship_type = 'alien' if 'BIOSHIP' in ship['Resource']['Filename'].upper() else fleet.kind(ship)
        inv = ship['Inventory_TechOnly']
        prefix = fleet.PREFIX + f'ShipOwnership/{index}/Inventory_TechOnly/Slots'
    elif target == 'multitool':
        index = weapons.select(p, action['selector'])
        inv = copy.deepcopy(p['WeaponInventory'] if index == weapons.active(p) else p['Multitools'][index]['Store'])
        prefix = fleet.PREFIX + f'Multitools/{index}/Store'
    else:
        raise ValueError('Bilinmeyen teknoloji hedefi.')
    if not compatible(entry, target, ship_type):
        raise ValueError(f'{ident} bu hedefe uygun değil.')
    allowed = [prefix]
    exists = any(item['Id'] == '^' + ident for item in inv['Slots'])
    if not exists:
        amount = entry['charge'] if (entry['chargeable'] or entry['uses_ammo']) and entry['charge'] > 0 else 100
        fleet.insert(inv, fleet.tech(ident, amount))
    if target == 'multitool':
        p['Multitools'][index]['Store'] = copy.deepcopy(inv)
        if index == weapons.active(p):
            p['WeaponInventory'] = copy.deepcopy(inv)
            allowed.append(fleet.PREFIX + 'WeaponInventory')
    paths = fleet.differences(original, data)
    if not all(any(path == prefix or path.startswith(prefix + '/') for prefix in allowed) for path in paths):
        raise ValueError('Teknoloji işlemi izinli envanter alanlarını aştı.')
    return data, {'op': 'install_technology', 'id': ident, 'target': target,
                  'slot': index + 1 if index is not None else None, 'already_installed': exists}, paths


def mutate(original, plan, catalog, fleet, native_mutate):
    if not 1 <= len(plan.get('actions', [])) <= 256:
        raise ValueError('Geçersiz katalog sepeti.')
    data = copy.deepcopy(original)
    events, allowed, exports = [], [], []
    for action in plan['actions']:
        if action['op'] == 'learn_recipe':
            from . import knowledge
            data, event, paths = knowledge.mutate(data, action, fleet)
            events.append(event)
        elif action['op'] in ('add_item', 'set_item_amount', 'move_item', 'split_item', 'merge_stacks'):
            from . import inventory
            data, event, paths = inventory.mutate(data, action, fleet)
            events.append(event)
        elif action['op'] in ('archive_ship', 'restore_archived_ship', 'archive_tool', 'restore_archived_tool'):
            from . import archives
            data, event, paths, exported = archives.mutate(data, action, catalog, fleet, native_mutate)
            events.append(event)
            exports += exported
        elif action['op'] == 'install_technology':
            data, event, paths = install(data, action, fleet)
            events.append(event)
        elif action['op'] == 'tool_add':
            data, report, exported = weapons.mutate(data, {'actions': [action]}, catalog, fleet)
            events.extend(report['events'])
            paths = report['changed_paths']
            exports += exported
        elif action['op'] in ('add', 'garage_import'):
            from .catalog_data import ship_profiles
            data, report, exported = native_mutate(data, {'actions': [action]}, {**catalog, **ship_profiles()})
            events.extend(report['events'])
            paths = report['changed_paths']
            exports += exported
        else:
            raise ValueError('Bilinmeyen katalog / envanter / arşiv işlemi.')
        allowed += paths
    paths = fleet.differences(original, data)
    if not all(any(path == prefix or path.startswith(prefix + '/') for prefix in allowed) for path in paths):
        raise ValueError('Katalog sepeti işlem sınırını aştı.')
    p = fleet.player(data)
    return data, {'events': events, 'changed_paths': paths, 'fleet': fleet.fleet_summary(p),
                  'multitools': weapons.summary(p)}, exports
