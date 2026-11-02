"""Keep Python/native failures visible in CMD and in runtime/menu.log."""
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    log = root / 'runtime' / 'menu.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.reconfigure(encoding='utf-8', errors='replace')
    if log.exists() and log.stat().st_size > 2_000_000:
        log.replace(log.with_suffix('.log.1'))
    print(f'Hata ve panel kısayolu günlüğü: {log}', flush=True)
    with log.open('a', encoding='utf-8', buffering=1) as output:
        output.write(f'\n--- Menü açılışı {datetime.now().isoformat(timespec="seconds")} ---\n')
        with subprocess.Popen([sys.executable, '-u', '-X', 'faulthandler', str(root / 'main.py'), *sys.argv[1:]],
                              cwd=root, env=dict(os.environ, PYTHONIOENCODING='utf-8'),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, encoding='utf-8', errors='replace') as child:
            for line in child.stdout:
                output.write(line)
                print(line, end='', flush=True)
            code = child.wait()
        output.write(f'Menü çıkış kodu: {code}\n')
    if code:
        print(f'Menü hata ile kapandı ({code}). Ayrıntılar: {log}', flush=True)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
