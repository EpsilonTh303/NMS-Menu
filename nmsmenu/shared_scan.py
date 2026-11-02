"""One shared live session and one cached decode per changed disk save."""
import copy
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
import logging

from .backend import ROOT
from .live_fleet import engine
from . import weapons


def stamp():
    return datetime.now(timezone.utc).isoformat()


class DiskScanner:
    def __init__(self, fleet=None, runtime=ROOT / 'runtime'):
        self.fleet = fleet or engine()
        self.runtime = Path(runtime)
        self.cache = {}

    def signature(self):
        paths = list(self.fleet.LIVE.glob('*.hg'))
        if hasattr(self.fleet, 'ROOT'):
            paths += list((self.fleet.ROOT / 'transactions').glob('*/manifest.json'))
            paths += list(self.fleet.GARAGE.glob('*.json'))
        return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in sorted(paths))

    def storage(self):
        garage, history, errors = [], [], []
        if not hasattr(self.fleet, 'ROOT'):
            return garage, history, errors
        for path in sorted((self.fleet.ROOT / 'transactions').glob('*/manifest.json'), reverse=True):
            try:
                history.append((path.parent, self.fleet.load(path)['state']))
            except Exception as exc:
                errors.append(f'{path.parent.name}: {exc}')
        for path in sorted(self.fleet.GARAGE.glob('*.json')):
            try:
                entry = self.fleet.load(path)
                ship = self.fleet.read_garage(path.stem, entry['save_version'])['ship']
                garage.append({'id': path.stem, 'name': ship['Name'], 'type': self.fleet.kind(ship),
                               'seed': ship['Resource']['Seed'][1], 'saved_at': entry['saved_at']})
            except Exception as exc:
                errors.append(f'Garaj {path.stem}: {exc}')
        return garage, history, errors

    def scan(self, force=False):
        self.runtime.mkdir(parents=True, exist_ok=True)
        result, errors = [], []
        files = sorted(self.fleet.LIVE.glob('save*.hg'))
        for file in files:
            try:
                meta = file.with_name('mf_' + file.name)
                pair = [file, meta] if meta.exists() else [file]
                signature = tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in pair)
                cached = self.cache.get(file.name)
                if not force and cached and cached[0] == signature:
                    result.append(copy.deepcopy(cached[1]))
                    continue
                with tempfile.TemporaryDirectory(prefix='shared-scan-', dir=self.runtime) as temp:
                    hashes = {p.name: self.fleet.digest(p) for p in pair}
                    for p in pair:
                        shutil.copy2(p, Path(temp) / p.name)
                    if any(self.fleet.digest(p) != hashes[p.name] or
                           self.fleet.digest(Path(temp) / p.name) != hashes[p.name] for p in pair):
                        raise RuntimeError('Kayıt kopyalanırken değişti; sonraki taramada yeniden okunacak.')
                    data = self.fleet.decode(Path(temp) / file.name)
                p = self.fleet.player(data)
                entry = {'file': file.name, 'mtime_ns': signature[0][1], 'read_at': stamp(),
                         'primary_slot': p['PrimaryShip'] + 1,
                         'exosuit_cargo': len(p['Inventory']['ValidSlotIndices']),
                         'exosuit_tech': len(p['Inventory_TechOnly']['ValidSlotIndices']),
                         'fleet': self.fleet.fleet_summary(p)}
                try:
                    entry['multitools'] = weapons.summary(p)
                except Exception as exc:
                    entry.update(multitools=[], weapons_error=str(exc))
                try:
                    from . import capital
                    entry['capital'] = capital.snapshot(p)
                except Exception as exc:
                    entry.update(capital={'freighter': None, 'frigates': [], 'missions': 0}, capital_error=str(exc))
                try:
                    from . import inventory, archives
                    entry['inventories'] = inventory.snapshot(p, self.fleet)
                    entry['archives'] = archives.snapshot(p, self.fleet)
                except Exception as exc:
                    entry.update(inventories=[], archives=[], inventory_error=str(exc))
                self.cache[file.name] = (signature, entry)
                result.append(copy.deepcopy(entry))
            except Exception as exc:
                logging.getLogger(__name__).exception('Disk kaydı okunamadı: %s', file.name)
                errors.append(f'{file.name}: {exc}')
        live_names = {p.name for p in files}
        self.cache = {name: value for name, value in self.cache.items() if name in live_names}
        garage, history, storage_errors = self.storage()
        return {'saves': result, 'garage': garage, 'history': history,
                'errors': errors + storage_errors, 'read_at': stamp()}


class SharedScan:
    def __init__(self, live, fleet, disk=None):
        self.live, self.fleet = live, fleet
        self.disk = disk or DiskScanner()
        self.last_error = ''

    def fast(self):
        result = {'read_at': stamp(), 'live': None, 'fleet': [], 'error': ''}
        try:
            if self.live.memory and not self.live.memory.alive():
                self.live.forget_closed_session()
            state = self.live.snapshot() if self.live.memory else self.live.connect()
            result['live'] = state
            if state['loaded']:
                result['fleet'] = self.fleet.inspect()
        except Exception as exc:
            result['error'] = str(exc)
            if result['error'] != self.last_error:
                logging.getLogger(__name__).warning('Canlı bağlantı: %s', exc, exc_info=True)
        self.last_error = result['error']
        return result
