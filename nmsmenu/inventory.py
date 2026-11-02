"""UI-free, identity-checked inventory operations. No disk or process writes."""
import copy
import hashlib
import json
from functools import lru_cache

from .backend import ROOT, read_json
from . import weapons


@lru_cache(maxsize=1)
def database():
    return read_json(ROOT / 'data' / 'items.json')


@lru_cache(maxsize=1)
def items():
    return {p['id']: p for p in database()['items']}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode('ascii')).hexdigest()


def resolve(player, spec, fleet):
    kind, section = spec['kind'], spec['section']
    if section not in ('cargo', 'tech'):
        raise ValueError('Bilinmeyen envanter bölümü.')
    if kind == 'exosuit':
        key = 'Inventory' if section == 'cargo' else 'Inventory_TechOnly'
        return player[key], fleet.PREFIX + key, None
    if kind == 'ship':
        i = fleet.select(player, spec['selector'])
        key = 'Inventory' if section == 'cargo' else 'Inventory_TechOnly'
        return player['ShipOwnership'][i][key], fleet.PREFIX + f'ShipOwnership/{i}/{key}', None
    if kind == 'multitool' and section == 'tech':
        i = weapons.select(player, spec['selector'])
        if i == weapons.active(player):
            return player['WeaponInventory'], fleet.PREFIX + 'WeaponInventory', i
        return player['Multitools'][i]['Store'], fleet.PREFIX + f'Multitools/{i}/Store', i
    raise ValueError('Desteklenmeyen envanter hedefi.')


def sync(player, tool_index):
    if tool_index is not None and tool_index == weapons.active(player):
        player['Multitools'][tool_index]['Store'] = copy.deepcopy(player['WeaponInventory'])


def validate(inv):
    valid = {(p['X'], p['Y']) for p in inv['ValidSlotIndices']}
    occupied = [(p['Index']['X'], p['Index']['Y']) for p in inv['Slots']]
    if len(occupied) != len(set(occupied)) or not set(occupied) <= valid:
        raise ValueError('Envanter koordinatları doğrulanamadı.')


def stack_limit(player, inv, entry):
    difficulty = player['DifficultyState']['Settings']['InventoryStackLimits']['InventoryStackLimitsDifficulty']
    group = inv['StackSizeGroup']['InventoryStackSizeGroup']
    try:
        rules = database()['stack_rules'][difficulty][entry['kind']]
        return min(rules['limit'], rules['groups'][group] * entry['stack_multiplier'])
    except KeyError:
        raise ValueError('Bu zorluk / envanter grubu için yığın sınırı doğrulanmadı.')


def selected(inv, identity):
    found = [item for item in inv['Slots'] if fingerprint(item) == identity]
    if len(found) != 1:
        raise ValueError('Seçilen eşya değişmiş; ortak listeyi yenileyip yeniden seçin.')
    return found[0]


def ordinary(item):
    return item['Type']['InventoryType'] in ('Product', 'Substance') and item['Id'].lstrip('^') in items()


def equivalent(a, b):
    return {k: v for k, v in a.items() if k not in ('Index', 'Amount', 'MaxAmount')} == {
        k: v for k, v in b.items() if k not in ('Index', 'Amount', 'MaxAmount')}


def amount(value):
    if type(value) is not int or not 1 <= value <= 10_000_000:
        raise ValueError('Miktar 1–10.000.000 arasında tam sayı olmalı.')
    return value


def add(player, inv, ident, quantity, fleet):
    entry = items().get(ident)
    if not entry:
        raise ValueError('Eşya normal envanter kataloğunda yok; görev ve özel kayıtlar kabul edilmez.')
    remaining = amount(quantity)
    limit = stack_limit(player, inv, entry)
    template = fleet.tech(ident, 1)
    template['Type']['InventoryType'] = entry['kind']
    for item in inv['Slots']:
        if equivalent(item, template) and 0 <= item['Amount'] <= min(limit, item['MaxAmount']):
            count = min(remaining, min(limit, item['MaxAmount']) - item['Amount'])
            item['Amount'] += count
            remaining -= count
    free = len(inv['ValidSlotIndices']) - len(inv['Slots'])
    if remaining > free * limit:
        raise ValueError('Yeterli boş yuva yok. Mevcut eşyalara dokunulmadı.')
    while remaining:
        count = min(remaining, limit)
        template.update(Amount=count, MaxAmount=limit)
        fleet.insert(inv, template)
        remaining -= count


def mutate(original, action, fleet):
    data = copy.deepcopy(original)
    player = fleet.player(data)
    spec = action['inventory']
    inv, prefix, tool_index = resolve(player, spec, fleet)
    validate(inv)
    allowed = [prefix + '/Slots']
    op = action['op']
    if op == 'add_item':
        if spec['section'] != 'cargo':
            raise ValueError('Eşyalar yalnız kargo envanterine eklenir.')
        add(player, inv, action['id'], action['amount'], fleet)
    elif op == 'set_item_amount':
        item = selected(inv, action['item'])
        if spec['section'] != 'cargo' or not ordinary(item):
            raise ValueError('Yalnız katalogdaki kargo eşyasının miktarı değiştirilebilir.')
        count = amount(action['amount'])
        if count > min(item['MaxAmount'], stack_limit(player, inv, items()[item['Id'][1:]])):
            raise ValueError('Tek yığın sınırı aşıldı; yeni eşya ekleyerek birden çok yığın oluşturun.')
        item['Amount'] = count
    elif op in ('move_item', 'split_item'):
        item = selected(inv, action['item'])
        dest_spec = action['destination']
        dest, dest_prefix, dest_tool = resolve(player, dest_spec, fleet)
        validate(dest)
        pos = action['position']
        if set(pos) != {'X', 'Y'} or any(type(v) is not int for v in pos.values()) or pos not in dest['ValidSlotIndices']:
            raise ValueError('Hedef yuva açık değil.')
        if any(p['Index'] == pos for p in dest['Slots']):
            raise ValueError('Hedef yuva dolu; üzerine yazılmaz.')
        if prefix != dest_prefix and (spec['section'] != 'cargo' or dest_spec['section'] != 'cargo' or not ordinary(item)):
            raise ValueError('Hedefler arasında yalnız katalogdaki kargo eşyaları taşınır.')
        moved = copy.deepcopy(item)
        if op == 'split_item':
            if spec['section'] != 'cargo' or not ordinary(item):
                raise ValueError('Yalnız normal kargo yığını bölünebilir.')
            count = amount(action['amount'])
            if count >= item['Amount']:
                raise ValueError('Bölünen miktar mevcut yığından küçük olmalı.')
            moved['Amount'] = count
            item['Amount'] -= count
        else:
            inv['Slots'].remove(item)
        if prefix != dest_prefix:
            limit = stack_limit(player, dest, items()[moved['Id'][1:]])
            if moved['Amount'] > limit:
                raise ValueError('Hedef yığın sınırı aşıldı; önce yığını bölün.')
            moved['MaxAmount'] = limit
        moved['Index'] = copy.deepcopy(pos)
        dest['Slots'].append(moved)
        sync(player, dest_tool)
        allowed.append(dest_prefix + '/Slots')
        if dest_tool is not None:
            allowed.append(fleet.PREFIX + f'Multitools/{dest_tool}/Store')
        validate(dest)
    elif op == 'merge_stacks':
        if spec['section'] != 'cargo':
            raise ValueError('Teknoloji yuvaları birleştirilemez.')
        ordered = list(inv['Slots'])
        for index, first in enumerate(ordered):
            if not any(p is first for p in inv['Slots']) or not ordinary(first):
                continue
            limit = min(first['MaxAmount'], stack_limit(player, inv, items()[first['Id'][1:]]))
            for other in ordered[index + 1:]:
                if not any(p is other for p in inv['Slots']):
                    continue
                if first is other or not equivalent(first, other):
                    continue
                count = min(max(0, limit - first['Amount']), max(0, other['Amount']))
                first['Amount'] += count
                other['Amount'] -= count
                if other['Amount'] == 0:
                    inv['Slots'].remove(other)
    else:
        raise ValueError('Bilinmeyen envanter işlemi.')
    sync(player, tool_index)
    if tool_index is not None:
        allowed.append(fleet.PREFIX + f'Multitools/{tool_index}/Store')
    validate(inv)
    paths = fleet.differences(original, data)
    if not all(any(path == key or path.startswith(key + '/') for key in allowed) for path in paths):
        raise ValueError('Envanter işlemi izinli alanları aştı.')
    event = {k: copy.deepcopy(v) for k, v in action.items() if k != 'item'}
    return data, event, paths


def snapshot(player, fleet):
    result = []
    specs = [('Ekzosuit', {'kind': 'exosuit', 'section': 'cargo'}),
             ('Ekzosuit teknoloji', {'kind': 'exosuit', 'section': 'tech'})]
    for ship in fleet.fleet_summary(player):
        selector = {k: ship[k] for k in ('slot', 'seed', 'type')}
        for section in ('cargo', 'tech'):
            specs.append((f"Gemi {ship['slot']} • {ship['name']} • {section}", {'kind': 'ship', 'section': section, 'selector': selector}))
    for tool in weapons.summary(player):
        specs.append((f"Alet {tool['slot']} • {tool['name']}", {'kind': 'multitool', 'section': 'tech',
            'selector': {k: tool[k] for k in ('slot', 'seed', 'filename')}}))
    for label, spec in specs:
        inv, _, _ = resolve(player, spec, fleet)
        contents = []
        for item in inv['Slots']:
            entry = items().get(item['Id'].lstrip('^'), {})
            contents.append({'identity': fingerprint(item), 'id': item['Id'], 'title': entry.get('title', item['Id']),
                'kind': item['Type']['InventoryType'], 'amount': item['Amount'], 'max': item['MaxAmount'], 'position': item['Index']})
        result.append({'label': label, 'spec': spec, 'width': inv['Width'], 'height': inv['Height'],
            'valid': copy.deepcopy(inv['ValidSlotIndices']), 'special': copy.deepcopy(inv['SpecialSlots']), 'items': contents})
    return result
