import json
import os
import subprocess
import sys
import uuid

from .backend import FleetBackend, ROOT, read_json


class WeaponBackend(FleetBackend):
    def run(self, *args):
        result = subprocess.run([sys.executable, '-m', 'nmsmenu.weapon_cli', *map(str, args)],
                                cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING='utf-8'),
                                capture_output=True, encoding='utf-8', errors='replace',
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()

    def prepare(self, plan):
        if not self.inspect():
            raise ValueError('Taze GOG kaydı bulunamadı.')
        self.runtime.mkdir(exist_ok=True, parents=True)
        path = self.runtime / ('weapon-' + uuid.uuid4().hex + '.json')
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
        result = json.loads(self.run('prepare', path))
        transaction = self.transaction(result['transaction'])
        manifest = read_json(transaction / 'manifest.json')
        if manifest['state'] != 'prepared' or manifest['plan'] != plan:
            raise ValueError('Silah işlem raporu planla eşleşmedi.')
        # The engine's legacy export filename is retained for commit compatibility;
        # add an explicitly named copy for the weapons UI and recovery.
        for stem in manifest['report']:
            export = read_json(transaction / (stem + '-removed-ships.json'))
            (transaction / (stem + '-removed-multitools.json')).write_text(
                json.dumps(export, ensure_ascii=False, indent=2), encoding='utf-8')
        return transaction, manifest, self.fingerprint(transaction)
