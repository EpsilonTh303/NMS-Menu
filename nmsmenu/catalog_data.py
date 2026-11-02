"""Catalog repository with no UI dependency."""
from functools import lru_cache

from .backend import ROOT, read_json


@lru_cache(maxsize=1)
def technologies():
    return {entry['id']: entry for entry in read_json(ROOT / 'data' / 'technologies.json')['technologies']}


@lru_cache(maxsize=1)
def tool_models():
    return read_json(ROOT / 'data' / 'tool-models.json')


def compatible(entry, target, ship_type=None):
    category, ident = entry['category'], entry['id']
    if target == 'exosuit':
        return category == 'Suit'
    if target == 'multitool':
        return category == 'Weapon'
    if target != 'ship':
        return False
    if ident == 'SOLAR_SAIL':
        return ship_type == 'solar'
    if ident in ('LAUNCHER_SPEC', 'SHIPJUMP_SPEC', 'HYPERDRIVE_SPEC'):
        return ship_type == 'alien'
    if ship_type == 'alien':
        return category in ('AlienShip', 'AllShips')
    if ship_type == 'sentinel':
        return category in ('RobotShip', 'AllShips', 'AllShipsExceptAlien') or ident in ('LAUNCHER', 'SHIPJUMP1', 'SHIPSHIELD')
    if ship_type not in ('fighter', 'solar', 'hauler', 'explorer', 'shuttle', 'exotic', 'starborn', 'golden', 'utopia', 'boundary'):
        return False
    return category in ('Ship', 'AllShips', 'AllShipsExceptAlien')
