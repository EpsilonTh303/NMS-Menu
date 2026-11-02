"""UI-independent catalog queries and command construction for future frontends."""
import copy
import json
import os
import secrets
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path

from .backend import FLEET, ROOT, read_json
from .catalog_data import compatible, technologies, tool_models, ship_profiles, reference_entries

SAVE_SLOTS = range(1, 16)
MAX_CART = 256
MAX_RECENT = 50
SHIP_SELECTOR = frozenset({'slot', 'seed', 'type'})
TOOL_SELECTOR = frozenset({'slot', 'seed', 'filename'})
DEFAULT_SHIP_FAMILY = {
    'blue_squid': 'exotic', 'golden_vector': 'fighter', 'utopia_speeder': 'fighter',
    'starborn_runner': 'fighter', 'starborn_phoenix': 'fighter', 'boundary_herald': 'fighter',
    'iron_vulture': 'hauler',
}


class CatalogError(ValueError):
    """ValueError with a stable machine-readable `code`; frontends may translate by code.

    Subclasses ValueError so existing `except ValueError` callers keep working.
    """

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _inventory():
    # Imported lazily; presumably to avoid a circular import with .inventory.
    from . import inventory
    return inventory


def _random_seed():
    return f'0x{secrets.randbits(64) or 1:016X}'


def _fold(text):
    """Search normalisation that treats İ/I/ı/i alike and ignores diacritics (ş→s, ğ→g ...)."""
    text = text.replace('İ', 'i').replace('I', 'i').replace('ı', 'i')
    text = unicodedata.normalize('NFKD', text)
    return ''.join(ch for ch in text if not unicodedata.combining(ch)).casefold()


def _split_key(key):
    try:
        prefix, ident = key.split(':', 1)
    except (AttributeError, ValueError):
        raise CatalogError('unknown_entry', 'Bilinmeyen katalog girdisi.') from None
    return prefix, ident


@dataclass(frozen=True)
class CatalogItem:
    key: str
    kind: str
    title: str
    detail: str
    preferred: bool = False
    hidden: bool = False
    addable: bool = True
    family: str = ''


class CatalogService:
    def __init__(self, preferences_path=None):
        self.ships = {**read_json(FLEET / 'catalog.json'), **ship_profiles()}
        self.preferences = read_json(FLEET / 'preferences.json')
        self.garage = []
        self.preferences_path = Path(preferences_path or ROOT / 'runtime' / 'catalog-preferences.json')
        self.user = self._load_user()

    def _load_user(self):
        """Tolerates a missing, corrupt or older preferences file."""
        data = {}
        if self.preferences_path.exists():
            try:
                loaded = read_json(self.preferences_path)
                if isinstance(loaded, dict):
                    data = loaded
            except (OSError, ValueError):
                data = {}

        def keys(name):
            value = data.get(name)
            return [k for k in value if isinstance(k, str)] if isinstance(value, list) else []

        return {'favorites': keys('favorites'), 'recent': keys('recent')[:MAX_RECENT]}

    def items(self, query='', kind='', target='', ship_type=None, include_hidden=False, family='',
              favorites_only=False, recent_only=False):
        favorites = set(self.user['favorites'])
        recent = {key: rank for rank, key in enumerate(self.user['recent'])}
        tools, techs = tool_models(), technologies()
        items = []
        for key, profile in self.ships.items():
            group = profile.get('family', DEFAULT_SHIP_FAMILY.get(key, key))
            items.append(CatalogItem('ship:' + key, 'ship', profile['name'], key,
                key in self.preferences['liked_profiles'], key in self.preferences['disliked_profiles'], family=group))
        items += [CatalogItem('tool:' + key, 'multitool', p['title'],
            ' • '.join(filter(None, (p.get('family'), p.get('seed'), key))), family=p.get('family', ''))
            for key, p in tools.items()]
        items += [CatalogItem('tech:' + key, 'technology', p['title'], key + ' • ' + p['category'], family=p['category'])
                  for key, p in techs.items() if not target or compatible(p, target, ship_type)]
        items += [CatalogItem('garage:' + p['id'], 'garage', p['name'] or p['type'], p['type'] + ' • ' + p['seed'])
                  for p in self.garage]
        items += [CatalogItem('reference:' + p['id'], 'reference', p['title'],
            p['family'] + ' • ' + p['summary'], addable=False, family=p['family']) for p in reference_entries()]
        items += [CatalogItem('item:' + key, 'item', p['title'], key + ' • ' + p['aliases'], family=p['category'])
                  for key, p in _inventory().items().items()]
        items = [replace(item, preferred=True) if item.key in favorites else item for item in items]
        words = _fold(query).split()
        result = [item for item in items if (not kind or item.kind == kind) and (not family or item.family == family)
                  and (include_hidden or not item.hidden) and (not favorites_only or item.key in favorites)
                  and (not recent_only or item.key in recent)
                  and all(word in _fold(item.title + ' ' + item.detail + ' ' + item.key + ' ' + item.family)
                          for word in words)]
        if recent_only:  # most recently used first
            return sorted(result, key=lambda item: recent[item.key])
        return sorted(result, key=lambda item: (not item.preferred, item.kind, item.title.casefold()))

    @staticmethod
    def _require_selector(selector, keys, message):
        if not isinstance(selector, dict) or set(selector) != keys:
            raise CatalogError('bad_selector', message)

    def command(self, key, target='', selector=None, name='Yeni Alet', new_ship_seed=False,
                random_tool_seed=False, amount=1):
        prefix, ident = _split_key(key)
        if prefix == 'item':
            inventory = _inventory()
            if ident not in inventory.items() or target not in ('exosuit', 'ship'):
                raise CatalogError('bad_item_target', 'Eşya için ekzosuit veya gemi kargo hedefi seçin.')
            spec = {'kind': target, 'section': 'cargo'}
            if target == 'ship':
                self._require_selector(selector, SHIP_SELECTOR, 'Kesin hedef gemi kimliği gerekli.')
                spec['selector'] = dict(selector)
            return {'op': 'add_item', 'id': ident, 'amount': inventory.amount(amount), 'inventory': spec}
        if prefix == 'ship' and ident in self.ships:
            command = {'op': 'add', 'profile': ident}
            if new_ship_seed:
                command['seed'] = _random_seed()
            return command
        if prefix == 'tool':
            tools = tool_models()
            if ident in tools:
                self._require_selector(selector, TOOL_SELECTOR, 'Donanımı kaynak alınacak çok amaçlı aleti seçin.')
                seed = _random_seed() if random_tool_seed else tools[ident].get('seed', _random_seed())
                return {'op': 'tool_add', 'selector': dict(selector), 'profile': ident, 'seed': seed, 'name': name}
        if prefix == 'reference':
            raise CatalogError('reference_not_addable',
                               'Bu kayıt tür rehberidir. Ayrıntılarda destek durumu ve ekleme yolu açıklanır.')
        if prefix == 'tech':
            techs = technologies()
            if ident in techs:
                if target not in ('ship', 'multitool', 'exosuit'):
                    raise CatalogError('bad_tech_target', 'Teknolojinin kurulacağı hedefi seçin.')
                if target != 'exosuit':
                    self._require_selector(selector, SHIP_SELECTOR if target == 'ship' else TOOL_SELECTOR,
                                           'Kesin hedef kimliği gerekli.')
                if not compatible(techs[ident], target, (selector or {}).get('type')):
                    raise CatalogError('incompatible_target', 'Bu teknoloji seçilen hedef türüne uygun değil.')
                command = {'op': 'install_technology', 'id': ident, 'target': target}
                if target != 'exosuit':
                    command['selector'] = dict(selector)
                return command
        if prefix == 'garage' and any(p['id'] == ident for p in self.garage):
            return {'op': 'garage_import', 'id': ident}
        raise CatalogError('unknown_entry', 'Katalog girdisi artık mevcut değil.')

    def counts(self):
        return {'ships': len(self.ships), 'tools': len(tool_models()), 'technologies': len(technologies()),
                'garage': len(self.garage), 'reference': len(reference_entries()), 'items': len(_inventory().items())}

    def write_preferences(self):
        self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.preferences_path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.user, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, self.preferences_path)

    def toggle_favorite(self, key):
        self.detail(key)
        values = self.user['favorites']
        if key in values:
            values.remove(key)
        else:
            values.append(key)
        self.write_preferences()

    def remember(self, keys):
        keys = list(keys)
        for key in keys:  # validate everything first so a bad key leaves state untouched
            self.detail(key)
        recent = list(self.user['recent'])
        for key in keys:
            recent = [key] + [p for p in recent if p != key]
        self.user['recent'] = recent[:MAX_RECENT]
        self.write_preferences()

    def detail(self, key):
        """Serializable metadata for every frontend; never generates a random command."""
        prefix, ident = _split_key(key)
        try:
            if prefix == 'ship':
                value = self.ships[ident]
            elif prefix == 'tool':
                value = tool_models()[ident]
            elif prefix == 'tech':
                value = technologies()[ident]
            elif prefix == 'item':
                value = _inventory().items()[ident]
            elif prefix == 'reference':
                value = next(p for p in reference_entries() if p['id'] == ident)
            elif prefix == 'garage':
                value = next(p for p in self.garage if p['id'] == ident)
            else:
                raise KeyError(prefix)
        except (KeyError, StopIteration):
            raise CatalogError('unknown_entry', 'Bilinmeyen katalog girdisi.') from None
        return copy.deepcopy(value)

    @staticmethod
    def validate_slot(save_slot):
        if type(save_slot) is not int or save_slot not in SAVE_SLOTS:
            raise CatalogError('bad_slot', 'Oyun kayıt yuvası 1–15 olmalı.')

    @staticmethod
    def plan(save_slot, commands):
        CatalogService.validate_slot(save_slot)
        if not 1 <= len(commands) <= MAX_CART:
            raise CatalogError('bad_cart_size', f'Sepette 1–{MAX_CART} işlem bulunmalı.')
        return {'save_slot': save_slot, 'actions': copy.deepcopy(commands)}


class CatalogCart:
    def __init__(self):
        self.save_slot = None
        self._commands = []
        self.revision = 0

    @property
    def commands(self):
        return copy.deepcopy(self._commands)

    def add(self, save_slot, command):
        if self._commands and self.save_slot != save_slot:
            raise CatalogError('mixed_slots',
                               'Aynı sepet farklı oyun kayıt yuvalarını karıştıramaz. Önce sepeti temizleyin.')
        CatalogService.validate_slot(save_slot)
        if not isinstance(command, dict) or 'op' not in command:
            raise CatalogError('bad_command', 'Geçersiz işlem.')
        if command['op'] == 'install_technology' and command in self._commands:
            return False
        if len(self._commands) >= MAX_CART:
            raise CatalogError('bad_cart_size', f'Tek sepet en fazla {MAX_CART} işlem alabilir.')
        self.save_slot = save_slot
        self._commands.append(copy.deepcopy(command))
        self.revision += 1
        return True

    def remove(self, index):
        del self._commands[index]
        self.revision += 1
        if not self._commands:
            self.save_slot = None

    def set_item_amount(self, index, value):
        """Edit a queued item's amount and invalidate any prepared review."""
        if type(index) is not int or not 0 <= index < len(self._commands):
            raise CatalogError('bad_selection', 'Bekleyen işlem seçin.')
        command = self._commands[index]
        if command.get('op') != 'add_item':
            raise CatalogError('bad_item_target', 'Adet yalnız eşya ve malzemeler için kullanılır.')
        amount = _inventory().amount(value)
        if command['amount'] != amount:
            self._commands[index] = {**copy.deepcopy(command), 'amount': amount}
            self.revision += 1

    def clear(self):
        self._commands.clear()
        self.revision += 1
        self.save_slot = None

    def plan(self):
        if not self._commands:
            raise CatalogError('empty_cart', 'Sepet boş.')
        return CatalogService.plan(self.save_slot, self._commands)
