"""Local, transactional fleet editor. No network, no game injection.

prepare creates a reviewed workspace transaction; apply requires unchanged source
hashes and a stopped game. All save slots are edited independently. Unknown JSON
fields are retained and the codec is checked by decoding each staged save again.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parent
GARAGE = ROOT / 'garage'
TOOL = ROOT / 'codec' / 'libNOM.io.cli.exe'
LIVE = Path(os.environ.get('APPDATA', '')) / 'HelloGames' / 'NMS' / 'DefaultUser'
PREFIX = '/BaseContext/PlayerStateData/'

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def stopped():
    # Run on the user's Windows session for prepare/apply/restore.
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
        "$ErrorActionPreference='Stop'; if (Get-Process -Name NMS -ErrorAction SilentlyContinue) { exit 42 }"],
        capture_output=True, creationflags=0x08000000)
    if result.returncode:
        raise RuntimeError('Oyunu tamamen kapatin. Kayitlara dokunulmadi.')

def decode(path):
    result = subprocess.run([str(TOOL), 'Read', '-Input', str(Path(path).resolve()),
        '-JsonHumanReadable', 'true'], capture_output=True, check=True)
    return json.loads(result.stdout.decode('utf-8-sig'))

def encode(data, output, index):
    result = subprocess.run([str(TOOL), 'Write', '-Output', str(output.resolve()),
        '-Format', 'Gog', '-Index', str(index)],
        # The Windows codec may read redirected stdin using its OEM code page.
        # ASCII JSON escapes preserve Unicode regardless of Console.InputEncoding.
        input=json.dumps(data, ensure_ascii=True, separators=(',', ':')).encode('ascii'),
        capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace') +
                           result.stdout.decode('utf-8', errors='replace'))

def player(data):
    if data.get('ActiveContext') != 'Main':
        raise ValueError('Only the verified Main save context is supported.')
    return data['BaseContext']['PlayerStateData']

def kind(ship):
    path = ship['Resource']['Filename'].upper()
    for marker, name in [('SAILSHIP/', 'solar'), ('SENTINELSHIP/', 'sentinel'),
                         ('FIGHTERS/WRACER.', 'starborn'), ('FIGHTERS/WRACERSE.', 'starborn'),
                         ('FIGHTERS/SPOOKSHIP.', 'boundary'),
                         ('FIGHTERS/FIGHTERCLASSICGOLD.', 'golden'), ('FIGHTERS/VRSPEEDER.', 'utopia'),
                         ('S-CLASS/S-CLASS_PROC.', 'exotic'),
                         ('DROPSHIPS/', 'hauler'), ('FIGHTERS/', 'fighter'),
                         ('SCIENTIFIC/', 'explorer'), ('SHUTTLE/', 'shuttle')]:
        if marker in path:
            return name
    return 'other' if path else 'empty'

def owned(p):
    return [(i, ship) for i, ship in enumerate(p['ShipOwnership']) if kind(ship) != 'empty']

def custom_index(index):
    return index + 3 if index < 6 else index + 11

def select(p, selector):
    if not selector or any(k not in ('slot', 'seed', 'name', 'type') for k in selector):
        raise ValueError('Use an exact name, seed, type or 1-based slot selector.')
    matches = []
    for i, ship in owned(p):
        values = {'slot': i + 1, 'seed': ship['Resource']['Seed'][1],
                  'name': ship['Name'], 'type': kind(ship)}
        if all(str(values[k]).casefold() == str(v).casefold() for k, v in selector.items()):
            matches.append(i)
    if len(matches) != 1:
        raise ValueError(f'Selector must match exactly one owned ship: {selector}; found {len(matches)}')
    return matches[0]

def resize(inv, count):
    width, height = 10, (count + 9) // 10
    valid = [{'X': n % width, 'Y': n // width} for n in range(count)]
    indices = {(x['X'], x['Y']) for x in valid}
    occupied = set()
    for item in inv['Slots']:
        pos = (item['Index']['X'], item['Index']['Y'])
        if pos not in indices or pos in occupied:
            raise ValueError('Existing items do not fit the target grid; refusing to relocate them silently.')
        occupied.add(pos)
    for special in inv.get('SpecialSlots', []):
        if (special['Index']['X'], special['Index']['Y']) not in indices:
            raise ValueError('Existing supercharged slot would be lost.')
    inv['Width'], inv['Height'] = width, height
    inv['ValidSlotIndices'] = valid

def insert(inv, item, preferred=None):
    occupied = {(s['Index']['X'], s['Index']['Y']) for s in inv['Slots']}
    if preferred is not None and preferred in inv['ValidSlotIndices'] and (preferred['X'], preferred['Y']) not in occupied:
        item = copy.deepcopy(item)
        item['Index'] = copy.deepcopy(preferred)
        inv['Slots'].append(item)
        return
    for index in inv['ValidSlotIndices']:
        if (index['X'], index['Y']) not in occupied:
            item = copy.deepcopy(item)
            item['Index'] = copy.deepcopy(index)
            inv['Slots'].append(item)
            return
    raise ValueError('No free inventory slot; no live files were changed.')

def tech(ident, amount=100):
    return {'Type': {'InventoryType': 'Technology'}, 'Id': '^' + ident,
            'Amount': amount, 'MaxAmount': amount, 'DamageFactor': 0.0,
            'FullyInstalled': True, 'AddedAutomatically': False, 'Index': {'X': 0, 'Y': 0}}

def fresh_custom(p, index):
    old = p['CharacterCustomisationData'][custom_index(index)]
    value = copy.deepcopy(old)
    value['SelectedPreset'] = '^'
    value['CustomData'].update({'DescriptorGroups': [], 'PaletteID': '^', 'Colours': [],
                               'TextureOptions': [], 'BoneScales': [], 'Scale': 1.0})
    return value

def blank_ship(p):
    template = next((s for s in p['ShipOwnership'] if kind(s) == 'empty'), None)
    if template is None:
        # Archiving must also work with all 12 active slots occupied. The game's
        # empty archive Ownership uses the same schema; never grow either array.
        template = next((a['Ownership'] for a in p.get('ArchivedShipOwnership', [])
                         if kind(a['Ownership']) == 'empty'), None)
        if template is not None and template.keys() != p['ShipOwnership'][0].keys():
            raise ValueError('Empty archive ship schema differs from active ownership.')
    if template is None:
        raise ValueError('No empty template available; a full fleet cannot be edited by this method.')
    return copy.deepcopy(template)

def fleet_summary(p):
    return [{'slot': i + 1, 'name': s['Name'] or '(procedural name)', 'type': kind(s),
             'seed': s['Resource']['Seed'][1], 'class': s['Inventory']['Class']['InventoryClass'],
             'cargo_slots': len(s['Inventory']['ValidSlotIndices']),
             'tech_slots': len(s['Inventory_TechOnly']['ValidSlotIndices']),
             'auto_recharge': any(x['Id'] == '^UT_LAUNCHCHARGE' for x in s['Inventory_TechOnly']['Slots'])}
            for i, s in owned(p)]

def capture_ship(p, index):
    if kind(p['ShipOwnership'][index]) == 'empty':
        raise ValueError('Cannot export an empty ship slot')
    return {'ship': copy.deepcopy(p['ShipOwnership'][index]),
            'legacy': p['ShipUsesLegacyColours'][index],
            'customisation': copy.deepcopy(p['CharacterCustomisationData'][custom_index(index)])}

def garage_hash(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()

def save_garage(payload, version):
    # Content addressed: cargo and technology changes create independent versions.
    ident = garage_hash(payload)
    GARAGE.mkdir(exist_ok=True)
    target = GARAGE / (ident + '.json')
    if target.exists():
        existing = load(target)
        if existing['payload'] != payload or existing['save_version'] != version:
            raise ValueError('Garage content collision or incompatible save version')
        return ident
    temp = GARAGE / (ident + '.tmp')
    dump(temp, {'format': 1, 'id': ident, 'save_version': version,
                'saved_at': dt.datetime.now().astimezone().isoformat(), 'payload': payload})
    os.replace(temp, target)
    return ident

def read_garage(ident, version):
    if len(ident) != 64 or any(c not in '0123456789abcdef' for c in ident):
        raise ValueError('Garage ID must be the full SHA256 ID from garage-list')
    entry = load(GARAGE / (ident + '.json'))
    if entry['format'] != 1 or entry['save_version'] != version:
        raise ValueError('Garage entry format/save version is incompatible')
    if garage_hash(entry['payload']) != ident or entry['id'] != ident:
        raise ValueError('Garage payload checksum failed')
    return copy.deepcopy(entry['payload'])

def garage_snapshot(source, save_slot):
    stopped()
    names = ['save' if n == 1 else 'save' + str(n) for n in (2 * save_slot - 1, 2 * save_slot)]
    files = [source / (name + '.hg') for name in names if (source / (name + '.hg')).exists()]
    if not files:
        raise ValueError('No save pair found')
    latest = max(files, key=lambda path: path.stat().st_mtime_ns)
    data = decode(latest)
    p = player(data)
    entries = [{'id': save_garage(capture_ship(p, i), data['Version']), 'slot': i + 1,
                'name': ship['Name'], 'type': kind(ship)} for i, ship in owned(p)]
    print(json.dumps({'source': str(latest), 'saved': entries}, ensure_ascii=False))

def mutate(original, plan, catalog):
    data = copy.deepcopy(original)
    p = player(data)
    events, exports, allowed = [], [], []
    for action in plan['actions']:
        op = action['op']
        if op == 'max_slots':
            scope = action['scope']
            if scope == 'exosuit':
                for field, count in [('Inventory', 120), ('Inventory_TechOnly', 60)]:
                    resize(p[field], count)
                    allowed.extend(PREFIX + field + '/' + key for key in ('Width', 'Height', 'ValidSlotIndices'))
            elif scope == 'ships':
                for i, ship in owned(p):
                    cargo_max = {'fighter': 100, 'solar': 110, 'explorer': 105,
                                 'shuttle': 110, 'hauler': 120, 'sentinel': 120, 'exotic': 105,
                                 'starborn': 105, 'golden': 100, 'utopia': 100, 'boundary': 100}.get(kind(ship))
                    if cargo_max is None:
                        raise ValueError('Unsupported ship slot cap; add its verified cap to the tool first.')
                    for field, count in [('Inventory', cargo_max), ('Inventory_TechOnly', 60)]:
                        resize(ship[field], count)
                        allowed.extend(PREFIX + f'ShipOwnership/{i}/{field}/' + key
                                       for key in ('Width', 'Height', 'ValidSlotIndices'))
            else:
                raise ValueError('Unknown max_slots scope')
            events.append({'op': op, 'scope': scope})
        elif op == 'remove':
            i = select(p, action['selector'])
            if len(owned(p)) < 2:
                raise ValueError('Cannot remove the final owned ship.')
            ship = p['ShipOwnership'][i]
            exports.append({'ship': copy.deepcopy(ship), 'slot': i + 1,
                            'legacy': p['ShipUsesLegacyColours'][i],
                            'customisation': copy.deepcopy(p['CharacterCustomisationData'][custom_index(i)])})
            items = ship['Inventory']['Slots'] + ship['Inventory_Cargo']['Slots']
            if items and not action.get('preserve_cargo', True):
                raise ValueError('Cargo deletion is not supported; preserve it or empty the ship first.')
            for item in items:
                insert(p['Inventory'], item)
            allowed.append(PREFIX + 'Inventory/Slots')
            empty = blank_ship(p)
            p['ShipOwnership'][i] = empty
            p['ShipUsesLegacyColours'][i] = True
            p['CharacterCustomisationData'][custom_index(i)] = fresh_custom(p, i)
            allowed.extend([PREFIX + f'ShipOwnership/{i}/', PREFIX + f'ShipUsesLegacyColours/{i}',
                            PREFIX + f'CharacterCustomisationData/{custom_index(i)}/'])
            if p['PrimaryShip'] == i:
                p['PrimaryShip'] = owned(p)[0][0]
                allowed.append(PREFIX + 'PrimaryShip')
            events.append({'op': op, 'slot': i + 1, 'type': kind(ship), 'seed': ship['Resource']['Seed'][1],
                           'cargo_items_preserved': len(items)})
        elif op == 'add':
            profile = copy.deepcopy(catalog[action['profile']])
            for key in ('name', 'seed', 'class'):
                if key in action:
                    profile[key] = action[key]
            if any(s['Resource']['Filename'] == profile['model'] and
                   s['Resource']['Seed'][1].casefold() == profile['seed'].casefold() for _, s in owned(p)):
                raise ValueError('This ship seed/model is already owned; refusing an accidental duplicate.')
            seed = int(profile['seed'], 16)
            if not 0 <= seed <= 0xffffffffffffffff or profile['class'] not in ('C', 'B', 'A', 'S'):
                raise ValueError('Invalid ship seed or class')
            i = next((index for index, s in enumerate(p['ShipOwnership']) if kind(s) == 'empty'), None)
            if i is None:
                raise ValueError('All 12 active ship slots are full. Use garage_import with an explicit replace selector.')
            ship = blank_ship(p)
            ship['Name'] = profile['name']
            ship['Resource'].update({'Filename': profile['model'], 'Seed': [True, profile['seed']]})
            stats = [{'BaseStatID': '^' + key, 'Value': value} for key, value in profile['stats'].items()]
            for field in ('Inventory', 'Inventory_Cargo', 'Inventory_TechOnly'):
                ship[field]['Class']['InventoryClass'] = profile['class']
                ship[field]['BaseStatValues'] = copy.deepcopy(stats)
            ship['Inventory']['StackSizeGroup']['InventoryStackSizeGroup'] = 'Ship'
            resize(ship['Inventory'], profile.get('cargo_slots', 30))
            resize(ship['Inventory_TechOnly'], profile.get('tech_slots', 20))
            for ident, amount in profile['technology'].items():
                insert(ship['Inventory_TechOnly'], tech(ident, amount))
            ship['Inventory_TechOnly']['SpecialSlots'] = [
                {'Type': {'InventorySpecialSlotType': 'TechBonus'}, 'Index': {'X': x, 'Y': 1}}
                for x in (1, 2, 3, 4)] if profile['class'] == 'S' else []
            p['ShipOwnership'][i] = ship
            p['ShipUsesLegacyColours'][i] = False
            p['CharacterCustomisationData'][custom_index(i)] = fresh_custom(p, i)
            if 'customisation_file' in profile:
                appearance_path = (ROOT / profile['customisation_file']).resolve()
                if not appearance_path.is_relative_to((ROOT / 'ship-references').resolve()):
                    raise ValueError('Custom ship appearance must come from local ship-references.')
                appearance = load(appearance_path)
                target = p['CharacterCustomisationData'][custom_index(i)]
                if appearance.keys() != target.keys() or appearance['CustomData'].keys() != target['CustomData'].keys():
                    raise ValueError('Custom ship appearance schema differs from this game save.')
                p['CharacterCustomisationData'][custom_index(i)] = copy.deepcopy(appearance)
            allowed.extend([PREFIX + f'ShipOwnership/{i}/', PREFIX + f'ShipUsesLegacyColours/{i}',
                            PREFIX + f'CharacterCustomisationData/{custom_index(i)}/'])
            events.append({'op': op, 'slot': i + 1, 'name': ship['Name'], 'profile': action['profile']})
        elif op == 'auto_recharge':
            indices = [i for i, _ in owned(p)] if action.get('scope') == 'ships' else [select(p, action['selector'])]
            for i in indices:
                ship = p['ShipOwnership'][i]
                if kind(ship) not in ('fighter', 'hauler', 'solar', 'sentinel', 'explorer', 'shuttle', 'exotic', 'starborn', 'golden', 'utopia', 'boundary'):
                    raise ValueError('Auto-charger is not verified for this ship type.')
                inventory = ship['Inventory_TechOnly']
                if not any(s['Id'] == '^UT_LAUNCHCHARGE' for s in inventory['Slots']):
                    insert(inventory, tech('UT_LAUNCHCHARGE'))
                    allowed.append(PREFIX + f'ShipOwnership/{i}/Inventory_TechOnly/Slots')
            events.append({'op': op, 'slots': [i + 1 for i in indices]})
        elif op == 'garage_import':
            incoming = read_garage(action['id'], original['Version'])
            ship = incoming['ship']
            if kind(ship) in ('empty', 'other'):
                raise ValueError('This garage ship type is not supported for import.')
            if any(s['Resource'] == ship['Resource'] for _, s in owned(p)):
                raise ValueError('This garage ship model/seed is already active.')
            if 'replace' in action:
                i = select(p, action['replace'])
                if p['PrimaryShip'] == i and data['BaseContext']['SpawnStateData']['LastKnownPlayerState'] != 'InStation':
                    raise ValueError('An active ship may only be swapped while saved inside a station.')
                # The outgoing full ship is written to the disk garage BEFORE live
                # save replacement in commit(), keeping its cargo and technology.
                exports.append(dict(capture_ship(p, i), slot=i + 1, garage=True))
            else:
                i = next((j for j, s in enumerate(p['ShipOwnership']) if kind(s) == 'empty'), None)
                if i is None:
                    raise ValueError('Fleet full: choose a replace selector for a lossless garage swap.')
            p['ShipOwnership'][i] = copy.deepcopy(ship)
            p['ShipUsesLegacyColours'][i] = incoming['legacy']
            p['CharacterCustomisationData'][custom_index(i)] = copy.deepcopy(incoming['customisation'])
            allowed.extend([PREFIX + f'ShipOwnership/{i}/', PREFIX + f'ShipUsesLegacyColours/{i}',
                            PREFIX + f'CharacterCustomisationData/{custom_index(i)}/'])
            events.append({'op': op, 'slot': i + 1, 'id': action['id'], 'name': ship['Name']})
        elif op == 'equip':
            i = select(p, action['selector'])
            ship = p['ShipOwnership'][i]
            profile = load(ROOT / 'loadouts.json')[action['profile']]
            if kind(ship) not in profile['ship_types']:
                raise ValueError('Loadout is not verified for this ship type.')
            inventory = ship['Inventory_TechOnly']
            added = []
            for spec in profile['items']:
                ident = spec['id']
                if any(s['Id'] == '^' + ident for s in inventory['Slots']):
                    continue
                insert(inventory, tech(ident, spec.get('amount', 100)), spec.get('position'))
                added.append(ident)
            for family, limit in profile.get('procedural_family_limits', {}).items():
                count = sum(s['Id'].startswith('^' + family) for s in inventory['Slots'])
                if count > limit:
                    raise ValueError(f'Loadout would overload {family}: {count} modules, limit {limit}')
            allowed.append(PREFIX + f'ShipOwnership/{i}/Inventory_TechOnly/Slots')
            events.append({'op': op, 'slot': i + 1, 'profile': action['profile'], 'added': added})
        elif op == 'repair_ship':
            i = select(p, action['selector'])
            ship = p['ShipOwnership'][i]
            inventory = ship['Inventory_TechOnly']
            for item in inventory['Slots']:
                if item['Type']['InventoryType'] == 'Technology':
                    item['DamageFactor'] = 0.0
                    item['FullyInstalled'] = True
                    if item['MaxAmount'] > 0:
                        item['Amount'] = item['MaxAmount']
            inserted = []
            if action.get('compatibility_core'):
                if kind(ship) != 'sentinel':
                    raise ValueError('Compatibility core fix is restricted to Sentinel ships.')
                # Reversible workaround for an uninitialised imported Sentinel being
                # rejected by the summon critical-tech gate despite intact robot tech.
                # Keep robot tech intact; standard ship technology is also supported
                # on Interceptors. This is a workaround, not a proved engine diagnosis.
                for ident, amount in [('LAUNCHER', 200), ('SHIPJUMP1', 200)]:
                    if not any(s['Id'] == '^' + ident for s in inventory['Slots']):
                        insert(inventory, tech(ident, amount))
                        inserted.append(ident)
            allowed.append(PREFIX + f'ShipOwnership/{i}/Inventory_TechOnly/Slots')
            if action.get('activate'):
                if data['BaseContext']['SpawnStateData']['LastKnownPlayerState'] != 'InStation':
                    raise ValueError('Safe activation workaround requires a saved position inside a station.')
                p['PrimaryShip'] = i
                allowed.append(PREFIX + 'PrimaryShip')
            events.append({'op': op, 'slot': i + 1, 'inserted_compatibility_core': inserted,
                           'activate_in_station': action.get('activate', False)})
        else:
            raise ValueError('Unsupported operation: ' + op)
    diffs = differences(original, data)
    if not all(any(path == prefix or path.startswith(prefix if prefix.endswith('/') else prefix + '/')
                   for prefix in allowed) for path in diffs):
        raise ValueError('Mutation escaped the operation-specific allowlist.')
    assert len(p['ShipOwnership']) == len(player(original)['ShipOwnership'])
    assert p['ShipOwnership'][p['PrimaryShip']]['Resource']['Filename']
    validate(p)
    return data, {'events': events, 'changed_paths': diffs, 'fleet': fleet_summary(p)}, exports

def differences(a, b, path=''):
    if type(a) != type(b):
        return [path]
    if isinstance(a, dict):
        if a.keys() != b.keys():
            raise ValueError('JSON schema keys changed at ' + path)
        return [x for key in a for x in differences(a[key], b[key], path + '/' + key)]
    if isinstance(a, list):
        if len(a) != len(b):
            return [path]
        return [x for i, (left, right) in enumerate(zip(a, b))
                for x in differences(left, right, path + '/' + str(i))]
    return [] if a == b else [path]

def validate(p):
    inventories = [p['Inventory'], p['Inventory_TechOnly']]
    inventories += [s[key] for _, s in owned(p)
                    for key in ('Inventory', 'Inventory_Cargo', 'Inventory_TechOnly')]
    for inv in inventories:
        valid = {(x['X'], x['Y']) for x in inv['ValidSlotIndices']}
        if len(valid) != len(inv['ValidSlotIndices']):
            raise ValueError('Duplicate valid inventory slots')
        used = set()
        for item in inv['Slots']:
            pos = (item['Index']['X'], item['Index']['Y'])
            if pos not in valid or pos in used:
                raise ValueError('Invalid or duplicate occupied inventory slot')
            used.add(pos)

def snapshot(source, destination):
    destination.mkdir(parents=True)
    for file in source.glob('*.hg'):
        shutil.copy2(file, destination / file.name)
    return {file.name: digest(file) for file in destination.glob('*.hg')}

def prepare(source, plan_path):
    stopped()
    source = source.resolve()
    plan = load(plan_path)
    stamp = dt.datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
    transaction = ROOT / 'transactions' / stamp
    backup, stage = transaction / 'before', transaction / 'staged'
    before = snapshot(source, backup)
    stage.mkdir()
    manifest = {'source': str(source), 'created': dt.datetime.now().astimezone().isoformat(),
                'state': 'preparing', 'plan': plan, 'before_hashes': before,
                'codec_sha256': digest(TOOL), 'after_hashes': {}, 'report': {}}
    dump(transaction / 'manifest.json', manifest)
    found = False
    slot = plan.get('save_slot', 1)
    if not isinstance(slot, int) or not 1 <= slot <= 15:
        raise ValueError('save_slot must be between 1 and 15')
    for number in (2 * slot - 1, 2 * slot):
        stem = 'save' if number == 1 else 'save' + str(number)
        original_file = backup / (stem + '.hg')
        if not original_file.exists():
            continue
        found = True
        meta = 'mf_' + stem + '.hg'
        if not (backup / meta).exists():
            raise ValueError('Missing metadata pair: ' + meta)
        original = decode(original_file)
        edited, report, exports = mutate(original, plan, load(ROOT / 'catalog.json'))
        report['save_version'] = original['Version']
        shutil.copy2(original_file, stage / original_file.name)
        shutil.copy2(backup / meta, stage / meta)
        encode(edited, stage, number - 1)
        if decode(stage / original_file.name) != edited:
            raise ValueError('Codec round-trip failed; live files were not touched.')
        for name in (original_file.name, meta):
            shutil.copystat(backup / name, stage / name)
            manifest['after_hashes'][name] = digest(stage / name)
        manifest['report'][stem] = report
        dump(transaction / (stem + '-removed-ships.json'), exports)
    if not found:
        raise ValueError('No saves found')
    manifest['state'] = 'prepared'
    dump(transaction / 'manifest.json', manifest)
    print(json.dumps({'transaction': str(transaction), 'report': manifest['report']}, ensure_ascii=False))

def unchanged(source, hashes):
    for name, expected in hashes.items():
        if not (source / name).is_file() or digest(source / name) != expected:
            raise ValueError('Source changed since backup: ' + name)

def commit(transaction, restore=False):
    stopped()
    transaction = transaction.resolve()
    manifest = load(transaction / 'manifest.json')
    source = Path(manifest['source'])
    if source.resolve() != LIVE.resolve():
        raise ValueError('Only the established GOG DefaultUser save location may be written.')
    if restore:
        if manifest['state'] != 'applied':
            raise ValueError('Only an applied transaction can be restored.')
        snapshot(source, transaction / ('before-restore-' + uuid.uuid4().hex[:8]))
        # A full restore is explicit; the latest progress is retained in that backup.
        from_dir, target_hashes = transaction / 'before', manifest['before_hashes']
        names = list(manifest['after_hashes'])
    else:
        if manifest['state'] != 'prepared':
            raise ValueError('Transaction is not prepared, or has already been applied.')
        unchanged(source, manifest['before_hashes'])
        from_dir, target_hashes = transaction / 'staged', manifest['after_hashes']
        names = list(target_hashes)
    unchanged(from_dir, {name: target_hashes[name] for name in names})
    if not restore:
        for stem, report in manifest['report'].items():
            for entry in load(transaction / (stem + '-removed-ships.json')):
                if entry.get('garage'):
                    save_garage({key: entry[key] for key in ('ship', 'legacy', 'customisation')}, report['save_version'])
    rollback_dir = transaction / ('rollback-' + uuid.uuid4().hex[:8])
    snapshot(source, rollback_dir)
    try:
        for name in names:
            temp = source / (name + '.fleet-tmp')
            shutil.copy2(from_dir / name, temp)
            os.replace(temp, source / name)
        unchanged(source, {name: target_hashes[name] for name in names})
        for name, expected in manifest['before_hashes'].items():
            if name not in names and digest(source / name) != expected and not restore:
                raise ValueError('An unrelated save file changed: ' + name)
    except BaseException:
        for name in names:
            shutil.copy2(rollback_dir / name, source / name)
        raise
    manifest['state'] = 'restored' if restore else 'applied'
    manifest['completed'] = dt.datetime.now().astimezone().isoformat()
    dump(transaction / 'manifest.json', manifest)
    if not restore:
        dump(ROOT / 'last-applied.json', {'transaction': str(transaction), 'completed': manifest['completed']})
    print(manifest['state'].upper() + ': ' + str(transaction))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect')
    inspect.add_argument('--source', type=Path, default=LIVE)
    prep = sub.add_parser('prepare')
    prep.add_argument('plan', type=Path)
    prep.add_argument('--source', type=Path, default=LIVE)
    for command in ('apply', 'restore'):
        sub.add_parser(command).add_argument('transaction', type=Path)
    sub.add_parser('restore-last')
    garage = sub.add_parser('garage-snapshot')
    garage.add_argument('--source', type=Path, default=LIVE)
    garage.add_argument('--save-slot', type=int, choices=range(1, 16), default=1)
    sub.add_parser('garage-list')
    args = parser.parse_args()
    if args.command == 'inspect':
        for file in sorted(args.source.glob('save*.hg')):
            p = player(decode(file))
            print(json.dumps({'file': file.name, 'primary_slot': p['PrimaryShip'] + 1,
                              'exosuit_cargo': len(p['Inventory']['ValidSlotIndices']),
                              'exosuit_tech': len(p['Inventory_TechOnly']['ValidSlotIndices']),
                              'fleet': fleet_summary(p)}, ensure_ascii=False))
    elif args.command == 'garage-snapshot':
        garage_snapshot(args.source, args.save_slot)
    elif args.command == 'garage-list':
        for file in sorted(GARAGE.glob('*.json')):
            entry = load(file)
            payload = read_garage(file.stem, entry['save_version'])
            ship = payload['ship']
            print(json.dumps({'id': file.stem, 'name': ship['Name'], 'type': kind(ship),
                              'seed': ship['Resource']['Seed'][1], 'saved_at': entry['saved_at']}, ensure_ascii=False))
    elif args.command == 'prepare':
        prepare(args.source, args.plan)
    elif args.command == 'restore-last':
        transaction = Path(load(ROOT / 'last-applied.json')['transaction']).resolve()
        if not transaction.is_relative_to((ROOT / 'transactions').resolve()):
            raise ValueError('Unexpected transaction path')
        commit(transaction, True)
    else:
        commit(args.transaction, args.command == 'restore')

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        sys.exit(1)
