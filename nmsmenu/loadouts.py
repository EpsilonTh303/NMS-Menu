"""Named sets of fixed technologies; installation remains in catalog transactions."""
import copy
import json
import os
from pathlib import Path
import uuid

from .backend import ROOT
from .catalog_data import technologies, compatible


BUILTINS = {
    'suit_exploration': {'title': 'Ekzosuit • Keşif', 'target': 'exosuit', 'ids': ['UT_JET', 'UT_JUMP', 'UT_MIDAIR', 'UT_WATERJET', 'UT_WATERENERGY', 'POWERGLOVE']},
    'tool_mining': {'title': 'Alet • Madencilik ve tarama', 'target': 'multitool', 'ids': ['LASER', 'STRONGLASER', 'UT_MINER', 'SCAN1', 'SCANBINOC1', 'UT_SCAN', 'UT_SURVEY']},
    'tool_combat': {'title': 'Alet • Neutron Cannon', 'target': 'multitool', 'ids': ['CANNON', 'UT_CANNON', 'STUN_GREN', 'UT_STUNDMG']},
    'ship_exploration': {'title': 'Gemi • Keşif', 'target': 'ship', 'ids': ['SHIPSCAN_ECON', 'SHIPSCAN_COMBAT']},
    'ship_combat': {'title': 'Gemi • Infra-Knife', 'target': 'ship', 'ids': ['SHIPMINIGUN', 'UT_SHIPMINI', 'UT_SHIPSHIELD']},
}


class LoadoutStore:
    def __init__(self, path=None):
        self.path = Path(path or ROOT / 'runtime' / 'user-loadouts.json')

    def all(self):
        user = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}
        return copy.deepcopy({**BUILTINS, **user})

    def save(self, title, target, ids):
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 80:
            raise ValueError('Profil adı 1–80 karakter olmalı.')
        if target not in ('exosuit', 'ship', 'multitool'):
            raise ValueError('Bilinmeyen donanım hedefi.')
        ids = list(dict.fromkeys(ids))
        if not ids or any(ident not in technologies() for ident in ids):
            raise ValueError('Profil yalnız katalogdaki sabit teknolojileri içermeli.')
        user = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}
        key = 'user_' + uuid.uuid4().hex
        user[key] = {'title': title.strip(), 'target': target, 'ids': ids}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(user, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temp, self.path)
        return key


def commands(profile, spec):
    if spec['kind'] != profile['target'] or spec['section'] != 'tech':
        raise ValueError('Donanım profili için uygun teknoloji envanterini seçin.')
    result = []
    for ident in profile['ids']:
        if ident not in technologies() or not compatible(technologies()[ident], spec['kind'], spec.get('selector', {}).get('type')):
            raise ValueError(f'{ident} seçilen hedefe uygun değil.')
        action = {'op': 'install_technology', 'id': ident, 'target': spec['kind']}
        if spec['kind'] != 'exosuit':
            action['selector'] = copy.deepcopy(spec['selector'])
        result.append(action)
    return result
