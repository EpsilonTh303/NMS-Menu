"""Opt-in, file-based native ship reward requests. Never writes game memory."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import time
import uuid

from .backend import ROOT
from .live import BUILD_HASH, EXE

BRIDGE = ROOT / 'runtime' / 'native-ship-bridge'
SIGNATURE = '48 89 5C 24 ? 48 89 6C 24 ? 48 89 74 24 ? 57 41 56 41 57 48 83 EC ? 48 8B 3D ? ? ? ? 48 8B F1'
REWARD_RVA = 0xF03D60


def rewards():
    return json.loads((ROOT / 'data/native-ship-rewards.json').read_text(encoding='utf-8'))['rewards']


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def verify_binary(path=EXE):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != BUILD_HASH:
        raise ValueError('Native bridge requires the pinned GOG 179666 executable.')
    pe = struct.unpack_from('<I', raw, 0x3C)[0]
    count = struct.unpack_from('<H', raw, pe + 6)[0]
    optional = struct.unpack_from('<H', raw, pe + 20)[0]
    rx = re.compile(b''.join(b'.' if token == '?' else re.escape(bytes.fromhex(token))
                            for token in SIGNATURE.split()), re.DOTALL)
    matches = []
    for index in range(count):
        offset = pe + 24 + optional + index * 40
        rva, size, start = struct.unpack_from('<III', raw, offset + 12)
        flags = struct.unpack_from('<I', raw, offset + 36)[0]
        if flags & 0x20000000:
            matches += [rva + hit.start() for hit in rx.finditer(raw[start:start + size])]
    if matches != [REWARD_RVA]:
        raise ValueError('Native reward signature must match exactly once at the verified RVA.')


def validate_request(request, state, nonce, now=None):
    now = time.time() if now is None else now
    if not isinstance(request, dict):
        raise ValueError('Invalid request ID.')
    if request.get('experimental') is not True or request.get('nonce') != nonce:
        raise ValueError('Experimental acknowledgement and current bridge session required.')
    if not isinstance(request.get('expires'), (int, float)) or not now <= request['expires'] <= now + 121:
        raise ValueError('Native request expired or has an invalid lifetime.')
    if not state.get('loaded') or not state.get('offline') or request.get('identity') != state.get('identity'):
        raise ValueError('Loaded offline player session changed.')
    if not re.fullmatch('[a-f0-9]{32}', request.get('id', '')):
        raise ValueError('Invalid request ID.')
    profile = rewards().get(request.get('reward'))
    if profile is None:
        raise ValueError('Only curated single-ship native rewards are accepted.')
    ships = state.get('ships', [])
    if not 1 <= len(ships) < 12 or ships != request.get('ships'):
        raise ValueError('Ship ownership changed or all 12 native slots are full.')
    if any(ship['filename'].upper() == profile['model'].upper() and
           int(ship['seed'], 16) == int(profile['seed'], 16) for ship in ships):
        raise ValueError('This native reward ship is already owned.')
    return profile


def capture(live):
    """Read existing verified ownership fields; no inventory allocation or writes."""
    p, identity, _ = live.player()
    m = live.require_memory()
    from .live import ROOT_RVA
    flags = m.read(m.base + ROOT_RVA - 0x38 + 0xB8D5, 4)
    ships = []
    for index in range(12):
        resource = m.read(p + 0x17EE0 + index * 0x48, 0x48)
        pointer, length = struct.unpack_from('<QI', resource, 0x10)
        if not length:
            continue
        if not pointer or not 1 <= length <= 512:
            raise ValueError('Unverified native ship resource.')
        filename = m.read(pointer, length).split(b'\0')[0].decode('ascii')
        if not filename.startswith('MODELS/COMMON/SPACECRAFT/') or not filename.endswith('.SCENE.MBIN'):
            raise ValueError('Unverified native ship model.')
        ships.append({'slot': index + 1, 'filename': filename,
                      'seed': f'0x{struct.unpack_from("<Q", resource, 0x30)[0]:016X}'})
    if list(live.player()[1]) != list(identity):
        raise ValueError('Native player session changed during read.')
    return {'loaded': True, 'offline': flags[3] == 0, 'identity': list(identity), 'ships': ships}


class RuntimeShipClient:
    def __init__(self, directory=BRIDGE):
        self.directory = Path(directory)

    def status(self):
        try:
            data = json.loads((self.directory / 'status.json').read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                return {}
            if data.get('build_hash') != BUILD_HASH or not 0 <= time.time() - data['timestamp'] < 4:
                return {}
            return data
        except (OSError, ValueError, KeyError, TypeError):
            return {}

    def enqueue(self, reward, experimental, live):
        status = self.status()
        current = capture(live)
        request = {'id': uuid.uuid4().hex, 'reward': reward, 'experimental': experimental,
                   'nonce': status.get('nonce'), 'identity': current['identity'],
                   'ships': current['ships'], 'expires': time.time() + 120}
        if not status.get('accepting') or not status.get('nonce') or status.get('identity') != current['identity']:
            raise ValueError('Runtime bridge is unavailable for this player session.')
        validate_request(request, current, status['nonce'])
        self.directory.mkdir(parents=True, exist_ok=True)
        lock = self.directory / 'enqueue.lock'
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.close(fd)
            if (self.directory / 'request.json').exists():
                raise ValueError('A native request is already pending.')
            # Save copies are a rollback path only; no active save is replaced.
            from .live_fleet import engine
            fleet = engine()
            before = {p.name: fleet.digest(p) for p in fleet.LIVE.glob('*.hg')}
            backup = self.directory / 'backups' / request['id']
            copied = fleet.snapshot(fleet.LIVE, backup)
            if not before or before != copied or before != {p.name: fleet.digest(p) for p in fleet.LIVE.glob('*.hg')}:
                raise ValueError('Save files changed during native request backup; retry with a fresh request.')
            atomic_json(backup / 'manifest.json', {'request': request, 'hashes': copied,
                        'scope': 'Full saves at request time; newer progress is not included.'})
            atomic_json(self.directory / 'request.json', request)
        finally:
            lock.unlink(missing_ok=True)
        return request['id']

    def cancel(self):
        pending = self.directory / 'request.json'
        if pending.exists():
            pending.rename(self.directory / ('cancelled-' + uuid.uuid4().hex + '.json'))


def restore_backup(ident):
    """Explicit full-save restore, through the existing backed-up fleet engine."""
    if not re.fullmatch('[a-f0-9]{32}', ident):
        raise ValueError('Invalid native backup ID.')
    from .live_fleet import engine
    import shutil
    fleet = engine()
    fleet.stopped()
    backup = BRIDGE / 'backups' / ident
    manifest = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
    hashes = manifest['hashes']
    if not hashes or any(Path(name).name != name or not name.endswith('.hg') for name in hashes):
        raise ValueError('Invalid backup file list.')
    fleet.unchanged(backup, hashes)
    transaction = ROOT / 'transactions' / ('native-restore-' + uuid.uuid4().hex)
    before = transaction / 'before'
    before.mkdir(parents=True)
    for name in hashes:
        shutil.copy2(backup / name, before / name)
    fleet.unchanged(before, hashes)
    fleet.dump(transaction / 'manifest.json', {'source': str(fleet.LIVE), 'state': 'applied',
        'before_hashes': hashes, 'after_hashes': hashes, 'report': {}, 'native_backup': ident})
    fleet.commit(transaction, restore=True)  # preserves newer saves in before-restore/rollback


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('preflight')
    restore = sub.add_parser('restore-backup')
    restore.add_argument('id')
    args = parser.parse_args()
    if args.command == 'preflight':
        verify_binary()
        print('Pinned build hash and native reward signature match. Gameplay remains unverified.')
    else:
        restore_backup(args.id)
