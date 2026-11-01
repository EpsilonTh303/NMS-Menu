"""Adapter to the existing transactional engine. No save mutation code here."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
FLEET = ROOT.parent / 'FleetManager'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


class FleetBackend:
    def __init__(self, fleet=FLEET, runtime=ROOT / 'runtime'):
        self.fleet = fleet
        self.runtime = runtime

    def run(self, *args):
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        result = subprocess.run(
            [sys.executable, str(self.fleet / 'fleet.py'), *map(str, args)],
            cwd=self.fleet.parent, env=env, capture_output=True, encoding='utf-8',
            errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or 'İşlem başarısız.')
        return result.stdout.strip()

    def inspect(self):
        output = self.run('inspect')
        return [json.loads(line) for line in output.splitlines() if line.strip()]

    def catalog(self):
        return read_json(self.fleet / 'catalog.json')

    def loadouts(self):
        return read_json(self.fleet / 'loadouts.json')

    def garage(self):
        output = self.run('garage-list')
        return [json.loads(line) for line in output.splitlines() if line.strip()]

    def snapshot(self, slot):
        return self.run('garage-snapshot', '--save-slot', slot)

    def transaction(self, path):
        path = Path(path).resolve()
        base = (self.fleet / 'transactions').resolve()
        if path.parent != base or not (path / 'manifest.json').is_file():
            raise ValueError('Geçersiz işlem klasörü.')
        return path

    def prepare(self, plan):
        # Fresh inspection per request; prepare itself checks stopped game,
        # source snapshot, schema allowlist and codec round-trip equality.
        fresh = self.inspect()
        if not fresh:
            raise ValueError('DefaultUser altında kayıt bulunamadı.')
        self.runtime.mkdir(parents=True, exist_ok=True)
        path = self.runtime / (uuid.uuid4().hex + '.json')
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
        result = json.loads(self.run('prepare', path))
        transaction = self.transaction(result['transaction'])
        manifest = read_json(transaction / 'manifest.json')
        if manifest['state'] != 'prepared' or manifest['plan'] != plan:
            raise ValueError('Hazırlanan işlem planla eşleşmedi.')
        return transaction, manifest, self.fingerprint(transaction)

    def fingerprint(self, path):
        return hashlib.sha256((self.transaction(path) / 'manifest.json').read_bytes()).hexdigest()

    def apply(self, path, reviewed_hash):
        path = self.transaction(path)
        if self.fingerprint(path) != reviewed_hash:
            raise ValueError('İnceleme sonrası rapor değişti. Yeni plan hazırlayın.')
        return self.run('apply', path)

    def history(self):
        result = []
        for path in sorted((self.fleet / 'transactions').glob('*/manifest.json'), reverse=True):
            manifest = read_json(path)
            result.append((path.parent, manifest['state']))
        return result

    def restore(self, path):
        return self.run('restore', self.transaction(path))
