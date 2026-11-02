"""Offline freighter/frigate operations with explicit semantic allowlists.

Never allocates live game memory or rewrites bases.
Mission indices stay untouched: fleet removal requires an empty expedition list.
"""
import copy
import math
import re

MAX_FRIGATES = 30
NORMAL_FRIGATES = {'Combat', 'Exploration', 'Mining', 'Diplomacy', 'Support'}
FREIGHTER_INVENTORIES = ('FreighterInventory', 'FreighterInventory_TechOnly', 'FreighterInventory_Cargo')
FREIGHTER_MODELS = {
    'Normal': 'MODELS/COMMON/SPACECRAFT/INDUSTRIAL/FREIGHTER_PROC.SCENE.MBIN',
    'Capital': 'MODELS/COMMON/SPACECRAFT/INDUSTRIAL/CAPITALFREIGHTER_PROC.SCENE.MBIN',
    'Pirate': 'MODELS/COMMON/SPACECRAFT/INDUSTRIAL/PIRATEFREIGHTER.SCENE.MBIN',
}


def seed(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]{1,16}', value):
        raise ValueError('Geçersiz 64 bit tohum.')
    return f'0x{int(value, 16):016X}'


def name(value):
    if not isinstance(value, str) or not value.strip() or len(value.encode('utf-8')) > 31 or any(ord(c) < 32 for c in value):
        raise ValueError('Ad boş olamaz; UTF-8 olarak en fazla 31 bayt olmalı.')
    return value.strip()


def freighter_identity(p):
    resource = p.get('CurrentFreighter', {})
    if not resource.get('Filename'):
        return None
    if not isinstance(resource.get('Seed'), list) or len(resource['Seed']) != 2 or resource['Seed'][0] is not True:
        raise ValueError('Yük gemisi kimliği doğrulanamadı.')
    return {'filename': resource['Filename'], 'seed': seed(resource['Seed'][1])}


def frigate_identity(frigate, index):
    resource = frigate.get('ResourceSeed')
    if not isinstance(resource, list) or len(resource) != 2 or resource[0] is not True:
        raise ValueError('Fırkateyn tohumu doğrulanamadı.')
    return {'slot': index + 1, 'seed': seed(frigate['ResourceSeed'][1]),
            'type': frigate['FrigateClass']['FrigateClass']}


def expeditions(p):
    missions = p.get('FleetExpeditions')
    if not isinstance(missions, list):
        raise ValueError('Sefer listesi doğrulanamadı.')
    for mission in missions:
        if not isinstance(mission, dict) or not isinstance(mission.get('AllFrigateIndices'), list):
            raise ValueError('Sefer fırkateyn kimlikleri doğrulanamadı.')
        if any(type(i) is not int or not 0 <= i < len(p.get('FleetFrigates', [])) for i in mission['AllFrigateIndices']):
            raise ValueError('Sefer fırkateyn kimlikleri doğrulanamadı.')
    return missions


def snapshot(p):
    freighter = None
    identity = freighter_identity(p)
    if identity:
        inv = p['FreighterInventory']
        freighter = {**identity, 'name': p.get('PlayerFreighterName', ''),
                     'class': inv['Class']['InventoryClass'],
                     'cargo': len(inv['ValidSlotIndices']),
                     'tech': len(p['FreighterInventory_TechOnly']['ValidSlotIndices'])}
    missions = expeditions(p) if 'FleetExpeditions' in p else []
    frigates = []
    for index, frigate in enumerate(p.get('FleetFrigates', [])):
        busy = any(index in mission['AllFrigateIndices'] for mission in missions)
        frigates.append({**frigate_identity(frigate, index), 'name': frigate.get('CustomName', ''),
                         'class': frigate.get('InventoryClass', {}).get('InventoryClass', ''),
                         'damage': frigate.get('DamageTaken', 0), 'busy': busy,
                         'stats': list(frigate.get('Stats', [])[:4])})
    return {'freighter': freighter, 'frigates': frigates, 'missions': len(missions)}


def select_frigate(p, selector):
    if not isinstance(selector, dict) or set(selector) != {'slot', 'seed', 'type'} or type(selector['slot']) is not int:
        raise ValueError('Kesin fırkateyn yuvası, türü ve tohumu gerekli.')
    matches = [i for i, frigate in enumerate(p['FleetFrigates']) if frigate_identity(frigate, i) == selector]
    if len(matches) != 1:
        raise ValueError('Fırkateyn kimliği değişti; taze listeden yeniden seçin.')
    index = matches[0]
    if any(index in mission['AllFrigateIndices'] for mission in expeditions(p)):
        raise ValueError('Seferdeki veya rapor bekleyen fırkateyn düzenlenemez.')
    return index


def expand_inventory(inv, count):
    """Open slots without silently closing existing coordinates or moving cargo."""
    width, height = inv['Width'], inv['Height']
    if type(width) is not int or type(height) is not int or not 1 <= width <= 16 or not 1 <= height <= 16:
        raise ValueError('Yük gemisi envanter boyutları doğrulanamadı.')
    valid = {(p['X'], p['Y']) for p in inv['ValidSlotIndices']}
    if len(valid) != len(inv['ValidSlotIndices']) or len(valid) > count:
        raise ValueError('Mevcut açık yuvalar azaltılamaz.')
    required = valid | {(s['Index']['X'], s['Index']['Y']) for s in inv['SpecialSlots']}
    if any(type(x) is not int or type(y) is not int or not 0 <= x < width or not 0 <= y < height for x, y in required):
        raise ValueError('Yük gemisi envanter koordinatları doğrulanamadı.')
    if any((item['Index']['X'], item['Index']['Y']) not in valid for item in inv['Slots']):
        raise ValueError('Yük gemisi envanter koordinatları doğrulanamadı.')
    if len(required) > count:
        raise ValueError('Mevcut açık yuvalar azaltılamaz.')
    width = max(width, 10)
    height = max(height, (count + width - 1) // width)
    for y in range(height):
        for x in range(width):
            if len(required) < count:
                required.add((x, y))
    inv.update(Width=width, Height=height, ValidSlotIndices=[{'X': x, 'Y': y} for x, y in sorted(required, key=lambda p: (p[1], p[0]))])


def mutate(original, action, fleet):
    data = copy.deepcopy(original)
    p = fleet.player(data)
    operation = action.get('op')
    allowed, exports = [], []
    if operation == 'freighter_create':
        if action.get('experimental') is not True:
            raise ValueError('Deneysel ekleme için açık onay gerekli.')
        if freighter_identity(p) is not None:
            raise ValueError('Mevcut yük gemisi değiştirilemez.')
        if expeditions(p):
            raise ValueError('Kaldırmadan önce tüm seferleri tamamlayıp raporlarını alın.')
        model = FREIGHTER_MODELS.get(action.get('model'))
        if not model:
            raise ValueError('Bilinmeyen yük gemisi modeli.')
        # Start only from the game's empty ownership template. No base, mission,
        # cargo, spawn transform or personal ship ownership is synthesized.
        for key in ('CurrentFreighter', 'CurrentFreighterNPC'):
            resource = p[key]
            if resource.get('Filename') or not isinstance(resource.get('Seed'), list) or len(resource['Seed']) != 2:
                raise ValueError('Boş yük gemisi şablonu doğrulanamadı.')
        if any(base.get('BaseType', {}).get('PersistentBaseTypes') == 'FreighterBase'
               for base in p['PersistentPlayerBases']):
            raise ValueError('Boş yük gemisi şablonu doğrulanamadı.')
        home = p['CurrentFreighterHomeSystemSeed']
        if not isinstance(home, list) or len(home) != 2 or home[0] is not False:
            raise ValueError('Boş yük gemisi şablonu doğrulanamadı.')
        for key in FREIGHTER_INVENTORIES:
            inventory = p[key]
            if inventory['Slots'] or inventory['Class']['InventoryClass'] not in ('C', 'B', 'A', 'S'):
                raise ValueError('Boş yük gemisi şablonu doğrulanamadı.')
            if not isinstance(inventory['ValidSlotIndices'], list):
                raise ValueError('Boş yük gemisi şablonu doğrulanamadı.')
        p['CurrentFreighter']['Filename'] = model
        p['CurrentFreighter']['Seed'] = [True, seed(action.get('seed'))]
        p['CurrentFreighterHomeSystemSeed'] = [True, seed(action.get('home_seed'))]
        p['CurrentFreighterNPC']['Filename'] = 'MODELS/COMMON/PLAYER/PLAYERCHARACTER/NPCKORVAX.SCENE.MBIN'
        p['CurrentFreighterNPC']['Seed'] = [True, seed(action.get('crew_seed'))]
        p['PlayerFreighterName'] = name(action.get('name'))
        allowed.extend(('CurrentFreighter/Filename', 'CurrentFreighter/Seed',
                        'CurrentFreighterHomeSystemSeed', 'CurrentFreighterNPC/Filename',
                        'CurrentFreighterNPC/Seed', 'PlayerFreighterName'))
    elif operation in ('freighter_edit', 'freighter_expand', 'freighter_repair'):
        identity = freighter_identity(p)
        if identity is None or identity != action.get('selector'):
            raise ValueError('Sahip olunan yük gemisi gerekli; kimliğini taze listeden seçin.')
        if operation == 'freighter_edit':
            fields = action.get('fields', {})
            if not fields or set(fields) - {'name', 'class'}:
                raise ValueError('Bilinmeyen yük gemisi alanı.')
            if 'name' in fields:
                p['PlayerFreighterName'] = name(fields['name'])
                allowed.append('PlayerFreighterName')
            if 'class' in fields:
                if fields['class'] not in ('C', 'B', 'A', 'S'):
                    raise ValueError('Geçersiz yük gemisi sınıfı.')
                for key in FREIGHTER_INVENTORIES:
                    if key in p:
                        p[key]['Class']['InventoryClass'] = fields['class']
                        allowed.append(key + '/Class/InventoryClass')
        elif operation == 'freighter_expand':
            if p['FreighterInventory']['Class']['InventoryClass'] != 'S':
                raise ValueError('120/60 yuva için önce yük gemisini S sınıfına yükseltin.')
            for key, count in [('FreighterInventory', 120), ('FreighterInventory_TechOnly', 60)]:
                if len(p[key]['ValidSlotIndices']) > count:
                    raise ValueError('Mevcut açık yuvalar azaltılamaz.')
                expand_inventory(p[key], count)
                allowed.extend(key + '/' + field for field in ('Width', 'Height', 'ValidSlotIndices'))
        else:
            key = 'FreighterInventory_TechOnly'
            for item in p[key]['Slots']:
                if item['Type']['InventoryType'] != 'Technology':
                    raise ValueError('Yük gemisi teknoloji envanteri doğrulanamadı.')
                damage = item['DamageFactor']
                if not isinstance(damage, (int, float)) or not math.isfinite(damage):
                    raise ValueError('Geçersiz teknoloji hasarı.')
                item['DamageFactor'] = 0.0
                if item['Amount'] >= 0 and item['MaxAmount'] > 0:
                    item['Amount'] = item['MaxAmount']
            allowed.extend(key + f'/Slots/{i}/' + field for i in range(len(p[key]['Slots'])) for field in ('DamageFactor', 'Amount'))
    elif operation in ('frigate_edit', 'frigate_repair', 'frigate_clone', 'frigate_remove'):
        frigates = p.get('FleetFrigates')
        if not isinstance(frigates, list) or len(frigates) > MAX_FRIGATES:
            raise ValueError('Fırkateyn listesi veya 30 gemilik sınır doğrulanamadı.')
        index = select_frigate(p, action.get('selector'))
        frigate = frigates[index]
        prefix = f'FleetFrigates/{index}/'
        if operation == 'frigate_repair':
            for key in ('DamageTaken', 'RepairsMade'):
                if type(frigate.get(key)) is not int or frigate[key] < 0:
                    raise ValueError('Fırkateyn hasar alanları doğrulanamadı.')
                frigate[key] = 0
                allowed.append(prefix + key)
        elif operation == 'frigate_edit':
            fields = action.get('fields', {})
            if not fields or set(fields) - {'name', 'stats'}:
                raise ValueError('Bilinmeyen fırkateyn alanı.')
            if 'name' in fields:
                frigate['CustomName'] = name(fields['name'])
                allowed.append(prefix + 'CustomName')
            if 'stats' in fields:
                stats = fields['stats']
                if not isinstance(stats, list) or len(stats) != 4 or any(type(value) is not int or not 0 <= value <= 100 for value in stats):
                    raise ValueError('Dört beceri değeri 0–100 arasında tam sayı olmalı.')
                if len(frigate['Stats']) != 11:
                    raise ValueError('Fırkateyn beceri dizisi doğrulanamadı.')
                frigate['Stats'][:4] = stats
                allowed.extend(prefix + 'Stats/' + str(i) for i in range(4))
        elif operation == 'frigate_clone':
            if len(frigates) >= MAX_FRIGATES:
                raise ValueError('30 fırkateyn sınırı dolu.')
            if frigate_identity(frigate, index)['type'] not in NORMAL_FRIGATES:
                raise ValueError('Yalnız normal fırkateyn türleri kopyalanabilir.')
            new_seed = seed(action.get('seed'))
            if any(seed(f['ResourceSeed'][1]) == new_seed for f in frigates):
                raise ValueError('Bu fırkateyn tohumu zaten filoda.')
            clone = copy.deepcopy(frigate)
            clone['ResourceSeed'] = [True, new_seed]
            clone['CustomName'] = name(action.get('name'))
            # Never copy transient damage to a newly created fleet entry.
            clone['DamageTaken'] = clone['RepairsMade'] = 0
            frigates.append(clone)
            allowed.append('FleetFrigates')  # list length change; existing entries checked below
            if frigates[:-1] != fleet.player(original)['FleetFrigates']:
                raise ValueError('Mevcut fırkateynler değişti.')
        else:
            if expeditions(p):
                raise ValueError('Kaldırmadan önce tüm seferleri tamamlayıp raporlarını alın.')
            exports.append({'kind': 'frigate', 'selector': copy.deepcopy(action['selector']), 'frigate': copy.deepcopy(frigate)})
            del frigates[index]
            allowed.append('FleetFrigates')
    else:
        raise ValueError('Bilinmeyen yük gemisi / fırkateyn işlemi.')
    prefixes = [fleet.PREFIX + path for path in allowed]
    paths = fleet.differences(original, data)
    if any(not any(path == prefix or path.startswith(prefix + '/') for prefix in prefixes) for path in paths):
        raise ValueError('İşlem yük gemisi / fırkateyn sınırını aştı.')
    event = {'op': operation, 'selector': action.get('selector'), 'fields': action.get('fields', {})}
    if operation == 'freighter_create':
        event.update(experimental=True, identity=freighter_identity(p), name=p['PlayerFreighterName'],
                     home_seed=p['CurrentFreighterHomeSystemSeed'][1], crew_seed=p['CurrentFreighterNPC']['Seed'][1])
    return data, event, paths, exports
