"""File-based presentation translations. Original controller values stay intact.

Run `python -m nmsmenu.i18n check`, `sync`, or `add fr --name Français`.
An empty/missing entry falls back to Turkish; templates preserve runtime values.
"""
import argparse
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / 'locales'
SETTINGS = ROOT / 'runtime' / 'ui-settings.json'
TOKEN = re.compile(r'\{v\d+\}')


def read_catalog(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        raise ValueError('Language JSON must be an object')
    if not all(isinstance(k, str) and (isinstance(v, str) or k == '_meta' and isinstance(v, dict)) for k, v in data.items()):
        raise ValueError('Language entries must be strings')
    return data


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Translator:
    def __init__(self, directory=LOCALES, settings=SETTINGS):
        self.directory, self.settings = Path(directory), Path(settings)
        self.source = read_catalog(self.directory / 'tr.json')
        self.language = 'tr'
        self.catalog = self.source
        self.templates = []
        self.missing = set()
        try:
            code = json.loads(self.settings.read_text(encoding='utf-8')).get('language', 'tr')
        except (OSError, ValueError, AttributeError):
            code = 'tr'
        self.select(code, persist=False)

    def available(self):
        result = {}
        for path in sorted(self.directory.glob('*.json')):
            if not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]+)?', path.stem):
                continue
            try:
                data = read_catalog(path)
            except (OSError, ValueError):
                continue
            meta = data.get('_meta', {})
            name = meta.get('name', path.stem)
            result[path.stem] = name if isinstance(name, str) else path.stem
        return result

    def reload(self):
        self.source = read_catalog(self.directory / 'tr.json')
        self.select(self.language, persist=False)

    def select(self, language, persist=True):
        language = language if language in self.available() else 'tr'
        data = read_catalog(self.directory / f'{language}.json')
        if persist:
            try:
                settings = json.loads(self.settings.read_text(encoding='utf-8'))
                if not isinstance(settings, dict):
                    settings = {}
            except (OSError, ValueError):
                settings = {}
            atomic_json(self.settings, {**settings, 'language': language})
        self.language, self.catalog = language, data
        self.templates = []
        self.prefixes = []
        self.missing.clear()
        for source, fallback in self.source.items():
            if source == '_meta':
                continue
            translated = data.get(source) or fallback
            if sorted(TOKEN.findall(source)) != sorted(TOKEN.findall(translated)):
                translated = fallback
            if TOKEN.search(source):
                parts, names, cursor = [], [], 0
                for match in TOKEN.finditer(source):
                    parts.append(re.escape(source[cursor:match.start()]))
                    parts.append('(.*?)')
                    names.append(match.group())
                    cursor = match.end()
                parts.append(re.escape(source[cursor:]))
                self.templates.append((re.compile('^' + ''.join(parts) + '$', re.DOTALL), names, translated, source))
            elif source.endswith(': ') and len(source) > 4:
                self.prefixes.append((source, translated))
        self.templates.sort(key=lambda row: len(TOKEN.sub('', row[3])), reverse=True)
        self.prefixes.sort(key=lambda row: len(row[0]), reverse=True)
        self.text.cache_clear()

    @lru_cache(maxsize=4096)
    def text(self, value):
        value = str(value)
        if not value or self.language == 'tr':
            return self.source.get(value, value)
        translated = self.catalog.get(value)
        if translated and isinstance(translated, str):
            if sorted(TOKEN.findall(value)) == sorted(TOKEN.findall(translated)):
                return translated
        stripped = value.strip()
        if stripped != value and stripped in self.source:
            return value[:len(value)-len(value.lstrip())] + self.text(stripped) + value[len(value.rstrip()):]
        for pattern, names, translated, source in self.templates:
            match = pattern.fullmatch(value)
            if match:
                variables = dict(zip(names, match.groups()))
                return TOKEN.sub(lambda token: variables[token.group()], translated)
        for delimiter in ('\n', ' • ', ' | ', ' — '):
            if delimiter in value:
                return delimiter.join(self.text(part) for part in value.split(delimiter))
        for source, translated in self.prefixes:
            if value.startswith(source):
                return translated + self.text(value[len(source):])
        if value in self.source:
            self.missing.add(value)
        return value


def audit(directory=LOCALES):
    directory = Path(directory)
    source = read_catalog(directory / 'tr.json')
    errors = []
    for path in sorted(directory.glob('*.json')):
        try:
            catalog = read_catalog(path)
        except (OSError, ValueError) as exc:
            errors.append(f'{path.name}: {exc}')
            continue
        for key in source:
            if key == '_meta':
                continue
            value = catalog.get(key)
            if not value:
                errors.append(f'{path.name}: missing: {key}')
            elif sorted(TOKEN.findall(key)) != sorted(TOKEN.findall(value)):
                errors.append(f'{path.name}: placeholders: {key}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check')
    sub.add_parser('sync')
    add = sub.add_parser('add')
    add.add_argument('code')
    add.add_argument('--name', required=True)
    args = parser.parse_args()
    if args.command == 'check':
        errors = audit()
        print('\n'.join(errors) if errors else 'All language keys and placeholders are complete.')
        return bool(errors)
    if args.command == 'sync':
        import importlib.util
        spec = importlib.util.spec_from_file_location('extract_messages', ROOT / 'tools/extract_messages.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = read_catalog(LOCALES / 'tr.json')
        for key, value in module.extract().items():
            source.setdefault(key, value)
        atomic_json(LOCALES / 'tr.json', source)
        for path in LOCALES.glob('*.json'):
            if path.stem != 'tr':
                catalog = read_catalog(path)
                for key in source:
                    if key != '_meta':
                        catalog.setdefault(key, '')
                atomic_json(path, catalog)
        print('Source strings merged; empty translations are ready to fill.')
    else:
        if not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]+)?', args.code):
            parser.error('Use a language code such as fr or pt-BR.')
        path = LOCALES / f'{args.code}.json'
        if path.exists():
            parser.error('Language already exists; existing translations were preserved.')
        data = {'_meta': {'name': args.name}}
        data.update({key: '' for key in read_catalog(LOCALES / 'tr.json') if key != '_meta'})
        atomic_json(path, data)
        print(f'Created {path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
