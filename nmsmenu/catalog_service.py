"""UI-independent catalog queries and command construction for future frontends."""
from dataclasses import dataclass
import secrets

from .backend import FLEET, read_json
from .catalog_data import compatible, technologies, tool_models, ship_profiles, reference_entries


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
    def __init__(self):
        self.ships = {**read_json(FLEET / 'catalog.json'), **ship_profiles()}
        self.preferences = read_json(FLEET / 'preferences.json')
        self.garage = []

    def items(self, query='', kind='', target='', ship_type=None, include_hidden=False, family=''):
        items = []
        for key, profile in self.ships.items():
            group = profile.get('family', {'blue_squid': 'exotic', 'golden_vector': 'fighter',
                'utopia_speeder': 'fighter', 'starborn_runner': 'fighter', 'starborn_phoenix': 'fighter',
                'boundary_herald': 'fighter', 'iron_vulture': 'hauler'}.get(key, key))
            items.append(CatalogItem('ship:' + key, 'ship', profile['name'], key,
                key in self.preferences['liked_profiles'], key in self.preferences['disliked_profiles'], family=group))
        items += [CatalogItem('tool:' + key, 'multitool', p['title'],
            ' • '.join(filter(None, (p.get('family'), p.get('seed'), key))), family=p.get('family', '')) for key, p in tool_models().items()]
        items += [CatalogItem('tech:' + key, 'technology', p['title'], key + ' • ' + p['category'], family=p['category'])
                  for key, p in technologies().items() if not target or compatible(p, target, ship_type)]
        items += [CatalogItem('garage:' + p['id'], 'garage', p['name'] or p['type'], p['type'] + ' • ' + p['seed']) for p in self.garage]
        items += [CatalogItem('reference:' + p['id'], 'reference', p['title'],
            p['family'] + ' • ' + p['summary'], addable=False, family=p['family']) for p in reference_entries()]
        words = query.casefold().split()
        result = [item for item in items if (not kind or item.kind == kind) and (not family or item.family == family)
                  and (include_hidden or not item.hidden)
                  and all(word in (item.title + ' ' + item.detail + ' ' + item.key + ' ' + item.family).casefold() for word in words)]
        return sorted(result, key=lambda item: (not item.preferred, item.kind, item.title.casefold()))

    def command(self, key, target='', selector=None, name='Yeni Alet', new_ship_seed=False, random_tool_seed=False):
        prefix, ident = key.split(':', 1)
        if prefix == 'ship' and ident in self.ships:
            command = {'op': 'add', 'profile': ident}
            if new_ship_seed:
                command['seed'] = f'0x{secrets.randbits(64) or 1:016X}'
            return command
        if prefix == 'tool' and ident in tool_models():
            if not selector or set(selector) != {'slot', 'seed', 'filename'}:
                raise ValueError('Donanımı kaynak alınacak çok amaçlı aleti seçin.')
            return {'op': 'tool_add', 'selector': dict(selector), 'profile': ident,
                    'seed': (f'0x{secrets.randbits(64) or 1:016X}' if random_tool_seed else
                             tool_models()[ident].get('seed', f'0x{secrets.randbits(64) or 1:016X}')), 'name': name}
        if prefix == 'reference':
            raise ValueError('Bu kayıt tür rehberidir. Ayrıntılarda destek durumu ve ekleme yolu açıklanır.')
        if prefix == 'tech' and ident in technologies():
            if target not in ('ship', 'multitool', 'exosuit'):
                raise ValueError('Teknolojinin kurulacağı hedefi seçin.')
            if target != 'exosuit' and not selector:
                raise ValueError('Kesin hedef kimliği gerekli.')
            if not compatible(technologies()[ident], target, (selector or {}).get('type')):
                raise ValueError('Bu teknoloji seçilen hedef türüne uygun değil.')
            command = {'op': 'install_technology', 'id': ident, 'target': target}
            if target != 'exosuit':
                command['selector'] = dict(selector)
            return command
        if prefix == 'garage' and any(p['id'] == ident for p in self.garage):
            return {'op': 'garage_import', 'id': ident}
        raise ValueError('Katalog girdisi artık mevcut değil.')

    def counts(self):
        return {'ships': len(self.ships), 'tools': len(tool_models()), 'technologies': len(technologies()),
                'garage': len(self.garage), 'reference': len(reference_entries())}

    def detail(self, key):
        """Serializable metadata for every frontend; never generates a random command."""
        import copy
        prefix, ident = key.split(':', 1)
        if prefix == 'ship':
            value = self.ships[ident]
        elif prefix == 'tool':
            value = tool_models()[ident]
        elif prefix == 'tech':
            value = technologies()[ident]
        elif prefix == 'reference':
            value = next(p for p in reference_entries() if p['id'] == ident)
        elif prefix == 'garage':
            value = next(p for p in self.garage if p['id'] == ident)
        else:
            raise ValueError('Bilinmeyen katalog girdisi.')
        return copy.deepcopy(value)

    @staticmethod
    def plan(save_slot, commands):
        if type(save_slot) is not int or not 1 <= save_slot <= 15:
            raise ValueError('Oyun kayıt yuvası 1–15 olmalı.')
        if not 1 <= len(commands) <= 256:
            raise ValueError('Sepette 1–256 işlem bulunmalı.')
        import copy
        return {'save_slot': save_slot, 'actions': copy.deepcopy(commands)}


class CatalogCart:
    def __init__(self):
        self.save_slot = None
        self._commands = []
        self.revision = 0

    @property
    def commands(self):
        import copy
        return copy.deepcopy(self._commands)

    def add(self, save_slot, command):
        import copy
        if self._commands and self.save_slot != save_slot:
            raise ValueError('Aynı sepet farklı oyun kayıt yuvalarını karıştıramaz. Önce sepeti temizleyin.')
        CatalogService.plan(save_slot, [command])
        if command['op'] == 'install_technology' and command in self._commands:
            return False
        self.save_slot = save_slot
        self._commands.append(copy.deepcopy(command))
        self.revision += 1
        return True

    def remove(self, index):
        del self._commands[index]
        self.revision += 1
        if not self._commands:
            self.save_slot = None

    def clear(self):
        self._commands.clear()
        self.revision += 1
        self.save_slot = None

    def plan(self):
        if not self._commands:
            raise ValueError('Sepet boş.')
        return CatalogService.plan(self.save_slot, self._commands)
