import os
import subprocess
import sys

from .backend import FleetBackend, ROOT


class CatalogBackend(FleetBackend):
    def run(self, *args):
        result = subprocess.run([sys.executable, '-m', 'nmsmenu.catalog_cli', *map(str, args)],
            cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING='utf-8'), capture_output=True,
            encoding='utf-8', errors='replace', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result.stdout.strip()
