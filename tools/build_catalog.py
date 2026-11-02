"""Build compact facts-only catalog data from local 7.04 MXML exports."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def build(table, localisation, destination):
    names = {}
    for path in localisation:
        for row in ET.parse(path).getroot().find("Property[@name='Table']"):
            value = row.find("Property[@name='English']")
            if value is not None:
                names[row.get('_id')] = re.sub(r'<[^>]*>', '', value.get('value', ''))
    entries = []
    supported = {'Suit', 'Weapon', 'Ship', 'AllShipsExceptAlien', 'AllShips', 'AlienShip', 'RobotShip'}
    for row in ET.parse(table).getroot().find("Property[@name='Table']"):
        def value(key):
            child = row.find(f"Property[@name='{key}']")
            return child.get('value', '') if child is not None else ''
        category = row.find("Property[@name='Category']/Property").get('value')
        ident = value('ID')
        if category not in supported or any(value(k) == 'true' for k in ('Procedural', 'RepairTech', 'BrokenSlotTech')):
            continue
        if ident.startswith('DUMMY_') or ident == 'SHIP_LIFESUP':
            continue
        entries.append({'id': ident, 'title': names.get(value('Name'), ident), 'name_key': value('Name'),
                        'description': names.get(value('Description'), ''),
                        'category': category, 'charge': int(value('ChargeAmount') or 0),
                        'chargeable': value('Chargeable') == 'true', 'uses_ammo': value('UsesAmmo') == 'true',
                        'upgrade': value('Upgrade') == 'true'})
    result = {'schema': 1, 'game_build': '179666',
              'source_sha256': hashlib.sha256(Path(table).read_bytes()).hexdigest(),
              'validation': 'local-game-table; installation needs transaction and codec validation', 'technologies': entries}
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return len(entries)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('table', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--localisation', type=Path, action='append', default=[])
    args = parser.parse_args()
    print(build(args.table, args.localisation, args.output))
