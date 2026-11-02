"""Install the pinned official Windows codec without executing it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen
import uuid

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def install(directory=ROOT / 'codec', check=False):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    filename = manifest['filename']
    if Path(filename).name != filename:
        raise ValueError('Codec filename must stay inside its directory.')
    target = directory / filename
    if target.is_file() and digest(target) == manifest['sha256']:
        return target
    if check:
        raise ValueError('Codec missing or checksum mismatch. Run setup.cmd.')
    if not manifest['url'].startswith('https://github.com/zencq/libNOM.io/releases/download/'):
        raise ValueError('Unexpected codec source.')
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / (filename + '.' + uuid.uuid4().hex + '.part')
    try:
        request = Request(manifest['url'], headers={'User-Agent': 'NMS-Menu/0.9'})
        with urlopen(request, timeout=60) as response, temporary.open('xb') as stream:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > manifest['size']:
                    raise ValueError('Codec download exceeded expected size.')
                stream.write(chunk)
        if total != manifest['size'] or digest(temporary) != manifest['sha256']:
            raise ValueError('Codec checksum/size mismatch; existing file was preserved.')
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify only; never download')
    args = parser.parse_args()
    try:
        print('Codec verified: ' + str(install(check=args.check)))
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
