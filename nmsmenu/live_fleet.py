"""Live inventory projections using FleetManager's existing mutation rules.

Only fixed-size data in existing allocations is writable. Ownership/resource
creation, deletion, model replacement and pointer writes are intentionally absent.
"""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import struct
import uuid

from .backend import FLEET, ROOT, read_json

INVENTORIES = {'Inventory': 0x7458, 'Inventory_Cargo': 0x8FC8, 'Inventory_TechOnly': 0xAB28}
STORE_SIZE = 0x248
TYPES = ('Substance', 'Technology', 'Product')
CLASSES = ('C', 'B', 'A', 'S')


def engine():
    spec = importlib.util.spec_from_file_location('menu_fleet_engine', FLEET / 'fleet.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unpack_inventory(header, items):
    """Decode the verified 179666 fixed store and element layouts."""
    masks = struct.unpack_from('<16Q', header)
    width, height, capacity = struct.unpack_from('<hhh', header, 0x80)
    allocated, count, pointer = struct.unpack_from('<IIQ', header, 0x88)
    # Rows outside current dimensions may contain stale bits from an older
    # layout. The engine serializes only the active width/height rectangle.
    valid = [{'X': x, 'Y': y} for y, mask in enumerate(masks[:max(height, 0)])
             for x in range(max(width, 0)) if mask & (1 << x)]
    if (any(mask > 0xFFFF for mask in masks) or not 0 <= width <= 16 or not 0 <= height <= 16
            or capacity != len(valid) or not 0 <= count <= allocated <= 4096
            or count > 256 or len(items) != count * 48):
        raise ValueError('Canlı envanter yerleşimi doğrulanamadı.')
    cls = struct.unpack_from('<I', header, 0x100)[0]
    if cls >= len(CLASSES):
        raise ValueError('Bilinmeyen gemi sınıfı.')
    slots, occupied = [], set()
    allowed = {(index['X'], index['Y']) for index in valid}
    for offset in range(0, len(items), 48):
        row = items[offset:offset + 48]
        ident = row[:16].split(b'\0')[0].decode('ascii')
        x, y, amount, damage, maximum, kind, added, installed = struct.unpack_from('<iiifiiBB', row, 16)
        if (not ident or kind not in range(3) or (x, y) not in allowed or (x, y) in occupied
                or amount < (-1 if kind == 1 else 0) or maximum < 0 or not math.isfinite(damage) or not 0 <= damage <= 100
                or added not in (0, 1) or installed not in (0, 1)):
            raise ValueError('Canlı eşya / teknoloji alanları doğrulanamadı.')
        occupied.add((x, y))
        slots.append({'Id': '^' + ident, 'Index': {'X': x, 'Y': y}, 'Amount': amount,
                      'DamageFactor': damage, 'MaxAmount': maximum, 'Type': {'InventoryType': TYPES[kind]},
                      'AddedAutomatically': bool(added), 'FullyInstalled': bool(installed)})
    return {'Width': width, 'Height': height, 'ValidSlotIndices': valid,
            'Slots': slots, 'Class': {'InventoryClass': CLASSES[cls]}}


def project_inventory(address, header, items, before, after, path):
    """Return an allowlisted byte diff; never resize a vector or alter identity."""
    patches = []

    def add(target, old, new, label):
        if old != new:
            patches.append({'address': target, 'before': old.hex(), 'after': new.hex(), 'path': label})

    allowed = {'Width', 'Height', 'ValidSlotIndices', 'Slots'}
    if any(before[key] != after[key] for key in before if key not in allowed):
        raise ValueError('Canlı işlem izinli envanter alanları dışına çıktı.')
    old_valid = {(s['X'], s['Y']) for s in before['ValidSlotIndices']}
    new_valid = {(s['X'], s['Y']) for s in after['ValidSlotIndices']}
    if not old_valid <= new_valid or any(not 0 <= x < 16 or not 0 <= y < 16 for x, y in new_valid):
        raise ValueError('Canlı işlem açık yuvaları kapatamaz veya sabit kapasiteyi aşamaz.')
    masks = list(struct.unpack_from('<16Q', header))
    for y in range(after['Height']):
        active = (1 << after['Width']) - 1
        masks[y] = (masks[y] & ~active) | sum(1 << x for x, y0 in new_valid if y0 == y)
    for y, mask in enumerate(masks):
        add(address + 8 * y, header[8 * y:8 * y + 8], struct.pack('<Q', mask), path + '/ValidSlotIndices')
    dims = struct.pack('<hhh', after['Width'], after['Height'], len(new_valid))
    # Split dimensions into aligned two-byte stores; no pointer or vector length changes.
    for off in (0, 2, 4):
        add(address + 0x80 + off, header[0x80 + off:0x82 + off], dims[off:off + 2], path + '/dimensions')
    if len(before['Slots']) != len(after['Slots']):
        raise ValueError('Canlı teknoloji ekleme veya silme henüz desteklenmiyor.')
    pointer = struct.unpack_from('<Q', header, 0x90)[0]
    for index, (left, right) in enumerate(zip(before['Slots'], after['Slots'])):
        if any(left[key] != right[key] for key in left if key not in ('Amount', 'DamageFactor', 'FullyInstalled')):
            raise ValueError('Canlı işlem eşya kimliği, konumu veya türünü değiştiremez.')
        if left != right and left['Type']['InventoryType'] != 'Technology':
            raise ValueError('Kargo öğeleri canlı onarım tarafından değiştirilemez.')
        base = pointer + index * 48
        raw = items[index * 48:index * 48 + 48]
        for offset, key, fmt in [(0x18, 'Amount', '<i'), (0x1C, 'DamageFactor', '<f'), (0x29, 'FullyInstalled', '<?')]:
            data = struct.pack(fmt, right[key])
            add(base + offset, raw[offset:offset + len(data)], data, f'{path}/Slots/{index}/{key}')
    return patches


class LiveFleet:
    def __init__(self, live, transactions=ROOT / 'runtime' / 'live-fleet'):
        self.live = live
        self.transactions = Path(transactions)
        self.fleet = engine()

    def require_paused(self):
        m = self.live.require_memory()
        from .live import ROOT_RVA
        flags = m.read(m.base + ROOT_RVA - 0x38 + 0xB8D5, 4)
        if flags[0] != 1 or flags[3] != 0:
            raise RuntimeError('Canlı filo için offline oyunda Esc duraklatma menüsünü açın. Oyunu kapatmanız gerekmez.')

    def capture(self):
        p, identity, _ = self.live.player()
        m = self.live.require_memory()
        ships, guards = [], []

        def guarded(address, count, kind='data'):
            raw = m.read(address, count)
            guards.append({'address': address, 'bytes': raw.hex(), 'kind': kind})
            return raw

        primary = struct.unpack('<I', guarded(p + 0x182A0, 4, 'structure'))[0]
        for index in range(12):
            resource = guarded(p + 0x17EE0 + index * 0x48, 0x48, 'structure')
            pointer, length = struct.unpack_from('<QI', resource, 0x10)
            if not length:
                continue
            if not pointer or not 1 <= length <= 512:
                raise ValueError('Gemi model dizesi doğrulanamadı.')
            filename = guarded(pointer, length).split(b'\0')[0].decode('ascii')
            if not filename.startswith('MODELS/COMMON/SPACECRAFT/') or not filename.endswith('.SCENE.MBIN'):
                raise ValueError('Gemi kaynağı beklenen biçimde değil.')
            seed = f'0x{struct.unpack_from("<Q", resource, 0x30)[0]:016X}'
            ship = {'slot': index + 1, 'seed': seed, 'filename': filename, 'inventories': {}}
            ship['type'] = self.fleet.kind({'Resource': {'Filename': filename}})
            for key, offset in INVENTORIES.items():
                address = p + offset + index * STORE_SIZE
                header = guarded(address, STORE_SIZE, 'structure')
                allocated, count, pointer = struct.unpack_from('<IIQ', header, 0x88)
                if not 0 <= count <= allocated <= 4096 or count > 256 or count and not pointer:
                    raise ValueError('Envanter vektörü doğrulanamadı.')
                items = guarded(pointer, count * 48) if count else b''
                decoded = unpack_inventory(header, items)
                special_cap, special_count, special_ptr = struct.unpack_from('<IIQ', header, 0xC0)
                if not 0 <= special_count <= special_cap <= 256 or special_count and not special_ptr:
                    raise ValueError('Özel yuva vektörü doğrulanamadı.')
                specials = guarded(special_ptr, special_count * 12) if special_count else b''
                coords = [dict(zip(('X', 'Y'), struct.unpack_from('<ii', specials, n * 12))) for n in range(special_count)]
                ship['inventories'][key] = {'address': address, 'header': header.hex(), 'items': items.hex(),
                                           'decoded': decoded, 'special_coords': coords}
            ships.append(ship)
        if not ships or primary + 1 not in {s['slot'] for s in ships}:
            raise ValueError('Aktif gemi sahipliği doğrulanamadı.')
        return {'identity': list(identity), 'primary': primary + 1, 'ships': ships, 'guards': guards}

    def inspect(self):
        capture = self.capture()
        return [{'slot': s['slot'], 'seed': s['seed'], 'type': s['type'], 'filename': s['filename'],
                 'active': s['slot'] == capture['primary'],
                 'cargo': len(s['inventories']['Inventory']['decoded']['ValidSlotIndices']),
                 'tech': len(s['inventories']['Inventory_TechOnly']['decoded']['ValidSlotIndices'])}
                for s in capture['ships']]

    def verify(self, capture, structure_only=False):
        if list(self.live.player()[1]) != capture['identity']:
            raise RuntimeError('Oyun / kayıt oturumu değişti. Yeni canlı plan hazırlayın.')
        m = self.live.require_memory()
        for guard in capture['guards']:
            if structure_only and guard.get('kind') != 'structure':
                continue
            expected = bytes.fromhex(guard['bytes'])
            if m.read(guard['address'], len(expected)) != expected:
                raise RuntimeError('Gemi veya envanter inceleme sonrası değişti. Yeni plan hazırlayın.')

    @staticmethod
    def advance(capture, patch, reverse=False):
        value = bytes.fromhex(patch['before' if reverse else 'after'])
        for guard in capture['guards']:
            raw = bytearray.fromhex(guard['bytes'])
            offset = patch['address'] - guard['address']
            if 0 <= offset and offset + len(value) <= len(raw):
                raw[offset:offset + len(value)] = value
                guard['bytes'] = raw.hex()

    def prepare(self, operation, selected=None):
        if operation not in ('repair_ship', 'max_slots'):
            raise ValueError('Canlı sahiplik / model değişimi henüz doğrulanmadı.')
        self.require_paused()
        capture = self.capture()
        slot = capture['identity'][2] + 1
        if operation == 'repair_ship':
            matches = [s for s in capture['ships'] if selected and all(
                str(s[key]).casefold() == str(selected[key]).casefold() for key in ('slot', 'seed', 'type'))]
            if len(matches) != 1:
                raise ValueError('Güncel listeden kesin gemi kimliği seçin.')
            action = {'op': operation, 'selector': {key: matches[0][key] for key in ('slot', 'seed', 'type')}}
        else:
            action = {'op': operation, 'scope': 'ships'}
        plan = {'save_slot': slot, 'actions': [action]}
        tx = self.transactions / uuid.uuid4().hex
        source, stage = tx / 'source', tx / 'staged'
        source.mkdir(parents=True)
        stage.mkdir()
        numbers = (slot * 2 - 1, slot * 2)
        files = [self.fleet.LIVE / ('save' + (str(n) if n != 1 else '') + '.hg') for n in numbers]
        files = [file for file in files if file.exists()]
        if not files:
            raise ValueError('Güncel GOG kaydı bulunamadı. Oyunda kaydedin.')
        file = max(files, key=lambda f: f.stat().st_mtime_ns)
        meta = file.with_name('mf_' + file.name)
        hashes = {f.name: self.fleet.digest(f) for f in (file, meta)}
        for f in (file, meta):
            shutil.copy2(f, source / f.name)
        for f in (file, meta):
            if self.fleet.digest(f) != hashes[f.name] or self.fleet.digest(source / f.name) != hashes[f.name]:
                raise RuntimeError('Otomatik kayıt güncelleniyor. Yeniden hazırlayın.')
        original = self.fleet.decode(source / file.name)
        p = self.fleet.player(original)
        saved_owned = {index + 1 for index, _ in self.fleet.owned(p)}
        if saved_owned != {ship['slot'] for ship in capture['ships']}:
            raise ValueError('Canlı filo henüz kayda geçmemiş. Oyunda kaydedip tekrar hazırlayın.')
        for ship in capture['ships']:
            target = p['ShipOwnership'][ship['slot'] - 1]
            if (target['Resource']['Filename'] != ship['filename'] or
                    int(target['Resource']['Seed'][1], 16) != int(ship['seed'], 16)):
                raise ValueError('Kayıt ve canlı gemi kimliği farklı. Oyunda kaydedip yeniden hazırlayın.')
            for key, data in ship['inventories'].items():
                if [s['Index'] for s in target[key]['SpecialSlots']] != data['special_coords']:
                    raise ValueError('Özel yuvalar kayıtla farklı. Oyunda kaydedip yeniden hazırlayın.')
                target[key].update(copy.deepcopy(data['decoded']))
        p['PrimaryShip'] = capture['primary'] - 1
        edited, report, exports = self.fleet.mutate(original, plan, self.fleet.load(FLEET / 'catalog.json'))
        if exports:
            raise ValueError('Canlı envanter işlemi gemi dışa aktaramaz / silemez.')
        # The runtime uses -1 for some non-consuming technologies. Preserve this
        # sentinel; it is not an empty rechargeable battery.
        for index, left in enumerate(p['ShipOwnership']):
            old = left['Inventory_TechOnly']['Slots']
            new = self.fleet.player(edited)['ShipOwnership'][index]['Inventory_TechOnly']['Slots']
            for before, after in zip(old, new):
                if before['Amount'] == -1 and before['Type']['InventoryType'] == 'Technology':
                    after['Amount'] = -1
        report['changed_paths'] = self.fleet.differences(original, edited)
        patches = []
        for ship in capture['ships']:
            index = ship['slot'] - 1
            for key, inv in ship['inventories'].items():
                path = f'/BaseContext/PlayerStateData/ShipOwnership/{index}/{key}'
                patches += project_inventory(inv['address'], bytes.fromhex(inv['header']), bytes.fromhex(inv['items']),
                    p['ShipOwnership'][index][key], self.fleet.player(edited)['ShipOwnership'][index][key], path)
        for f in source.iterdir():
            shutil.copy2(f, stage / f.name)
        number = 1 if file.stem == 'save' else int(file.stem[4:])
        self.fleet.encode(edited, stage, number - 1)
        if self.fleet.decode(stage / file.name) != edited:
            raise ValueError('Codec round-trip eşitliği sağlanmadı. Canlı belleğe yazılmadı.')
        self.verify(capture)
        self.require_paused()
        self.fleet.dump(tx / 'live-before.json', original)
        self.fleet.dump(tx / 'live-after.json', edited)
        manifest = {'state': 'prepared', 'plan': plan, 'report': report, 'capture': capture,
                    'patches': patches, 'source_hashes': hashes, 'codec_roundtrip': True}
        self.fleet.dump(tx / 'manifest.json', manifest)
        return tx, manifest, self.fingerprint(tx)

    def transaction(self, path):
        path = Path(path).resolve()
        if path.parent != self.transactions.resolve():
            raise ValueError('Geçersiz canlı filo işlem klasörü.')
        return path

    def fingerprint(self, path):
        return hashlib.sha256((self.transaction(path) / 'manifest.json').read_bytes()).hexdigest()

    def apply(self, path, fingerprint):
        path = self.transaction(path)
        if self.fingerprint(path) != fingerprint:
            raise ValueError('İncelenen canlı filo raporu değişti.')
        manifest = read_json(path / 'manifest.json')
        if manifest['state'] != 'prepared' or not manifest['codec_roundtrip']:
            raise ValueError('Canlı filo işlemi uygulanmaya hazır değil.')
        self.require_paused()
        self.verify(manifest['capture'])
        expected = copy.deepcopy(manifest['capture'])
        written = []
        try:
            for patch in manifest['patches']:
                self.require_paused()
                self.verify(expected)
                self.live.write_checked(patch['address'], bytes.fromhex(patch['before']),
                                        bytes.fromhex(patch['after']), patch['path'])
                written.append(patch)
                self.advance(expected, patch)
            manifest['state'] = 'applied'
            self.fleet.dump(path / 'manifest.json', manifest)
        except BaseException as error:
            conflicts = []
            for patch in reversed(written):
                before, after = bytes.fromhex(patch['before']), bytes.fromhex(patch['after'])
                try:
                    self.require_paused()
                    self.verify(expected, structure_only=True)
                    self.live.write_checked(patch['address'], after, before, 'rollback:' + patch['path'])
                    self.advance(expected, patch, reverse=True)
                except Exception:
                    conflicts.append(patch['path'])
            manifest.update(state='failed', rollback_conflicts=conflicts)
            self.fleet.dump(path / 'manifest.json', manifest)
            if conflicts:
                raise RuntimeError(f'Canlı işlem kısmen geri alınamadı; üzerine yazılmayan alanlar manifestte. İşlem: {path}') from error
            raise
        return f"Canlı filo işlemi uygulandı: {len(written)} alan.\nİşlem: {path}\nOyun kaydederse değişiklikler kalıcı olur."

    def undo(self, path):
        path = self.transaction(path)
        manifest = read_json(path / 'manifest.json')
        if manifest['state'] != 'applied':
            raise ValueError('Yalnız uygulanmış canlı filo işlemi geri alınabilir.')
        self.require_paused()
        expected = copy.deepcopy(manifest['capture'])
        for patch in manifest['patches']:
            self.advance(expected, patch)
        self.verify(expected)
        for patch in manifest['patches']:
            after = bytes.fromhex(patch['after'])
            if self.live.memory.read(patch['address'], len(after)) != after:
                raise RuntimeError('Gemi değişmiş; daha yeni ilerleme geri alınmadı.')
        undone = []
        try:
            for patch in reversed(manifest['patches']):
                self.require_paused()
                self.verify(expected)
                self.live.write_checked(patch['address'], bytes.fromhex(patch['after']),
                                        bytes.fromhex(patch['before']), 'undo:' + patch['path'])
                undone.append(patch)
                self.advance(expected, patch, reverse=True)
        except BaseException:
            for patch in reversed(undone):
                before = bytes.fromhex(patch['before'])
                try:
                    self.require_paused()
                    self.verify(expected, structure_only=True)
                    self.live.write_checked(patch['address'], before, bytes.fromhex(patch['after']),
                                            'undo-rollback:' + patch['path'])
                    self.advance(expected, patch)
                except Exception:
                    continue
            raise
        manifest['state'] = 'restored'
        self.fleet.dump(path / 'manifest.json', manifest)
        return 'Canlı filo işlemi geri alındı. Para, görevler ve diğer kayıt alanları değiştirilmedi.'
