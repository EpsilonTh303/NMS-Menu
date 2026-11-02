"""Extract model/seed facts from the installed reward table; no save writes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def build(table, localisations, destination):
    names = {}
    for path in localisations:
        for row in ET.parse(path).getroot().find("Property[@name='Table']"):
            node = row.find("Property[@name='English']")
            if node is not None:
                names[row.get('_id')] = re.sub('<[^>]*>', '', node.get('value', ''))
    root = ET.parse(table).getroot()
    parents = {child: parent for parent in root.iter() for child in parent}
    def value(row, name):
        node = row.find(f"Property[@name='{name}']")
        return node.get('value', '') if node is not None else ''
    def reward_id(row):
        while row in parents and not row.get('_id'):
            row = parents[row]
        return row.get('_id', '')
    tools, ships, seen_tools, seen_ships = {}, {}, set(), set()
    families = {'FIGHTER_PROC': ('fighter', 'Avcı', 100),
                'DROPSHIP_PROC': ('hauler', 'Nakliye', 120),
                'SCIENTIFIC_PROC': ('explorer', 'Kaşif', 105),
                'SHUTTLE_PROC': ('shuttle', 'Mekik', 110),
                'SAILSHIP_PROC': ('solar', 'Solar', 110),
                'FIGHTERSPECIALSWITCH': ('fighter', 'Horizon Vector NX', 100),
                'RASAMAMAGOLD': ('fighter', 'Golden Rasamama S36', 100),
                'VINTAGEINTERCEPTOR': ('fighter', 'Vintage Interceptor', 100)}
    core = {'LAUNCHER': 200, 'SHIPJUMP1': 200, 'SHIPSHIELD': 200,
            'SHIPGUN1': 100, 'HYPERDRIVE': 120, 'UT_LAUNCHCHARGE': 100}
    for row in root.findall(".//Property[@value='GcRewardSpecificShip']/Property"):
        res = row.find("Property[@name='ShipResource']")
        model, seed = value(res, 'Filename'), int(value(res, 'Seed'))
        stem = Path(model).name.split('.')[0]
        ident = reward_id(row)
        # Only individually identified local rewards with ordinary ship schemas.
        # Living ships and corvettes need their own verified ownership adapter.
        if stem not in families or not ident or (model, seed) in seen_ships:
            continue
        if any(len(p) for p in row.find("Property[@name='Customisation']")):
            continue
        seen_ships.add((model, seed))
        family, label, capacity = families[stem]
        title = names.get(value(row, 'NameOverride')) or f'{label} • {ident}'
        technology = dict(core)
        if family == 'solar':
            technology['SOLAR_SAIL'] = 100
        ships[ident.lower()] = {'name': title, 'model': model, 'seed': f'0x{seed:X}', 'class': 'S',
            'cargo_slots': capacity, 'tech_slots': 60,
            'stats': {'SHIP_DAMAGE': 50.0, 'SHIP_SHIELD': 30.0, 'SHIP_HYPERDRIVE': 30.0, 'SHIP_AGILE': 40.0},
            'technology': technology, 'family': family, 'reward_id': ident,
            'sources': ['local:metadata/reality/tables/rewardtable.mbin'],
            'note': 'Yerel ödül model/tohum referansı; S sınıfı ve temel donanım editör profilidir. Ödül kilidi açılmaz.'}
    for row in root.findall(".//Property[@value='GcRewardSpecificWeapon']/Property"):
        res = row.find("Property[@name='WeaponResource']")
        model, seed = value(res, 'Filename'), int(value(res, 'GenerationSeed'))
        ident = reward_id(row)
        if not seed or not ident or (model, seed) in seen_tools:
            continue
        seen_tools.add((model, seed))
        weapon_class = row.find("Property[@name='WeaponType']/Property").get('value')
        title = names.get(value(row, 'NameOverride')) or f'{weapon_class} • {ident}'
        tools[ident.lower()] = {'title': title, 'model': model, 'seed': f'0x{seed:X}',
            'family': weapon_class, 'reward_id': ident,
            'note': 'Yerel ödülün görünüm tohumu; sınıf/donanım kaynak aletten kopyalanır. Özgün ödül istatistikleri aktarılmaz.'}
    result = {'schema': 1, 'game_build': '179666',
              'source_sha256': hashlib.sha256(Path(table).read_bytes()).hexdigest(),
              'ship_profiles': ships, 'tool_presets': tools}
    Path(destination).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return len(ships), len(tools)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('table', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--localisation', action='append', default=[], type=Path)
    args = parser.parse_args()
    print(build(args.table, args.localisation, args.output))
