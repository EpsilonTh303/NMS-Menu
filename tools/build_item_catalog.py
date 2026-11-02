"""Derive ordinary inventory items and exact stack rules from local 7.04 tables."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


def build(source, localisations, destination):
    source = Path(source)
    names = {}
    for path in localisations:
        for row in ET.parse(path).getroot().find("Property[@name='Table']"):
            node = row.find("Property[@name='English']")
            if node is not None:
                names[row.get('_id')] = re.sub('<[^>]*>', '', node.get('value', ''))
    def val(row, key):
        p = row.find(f"Property[@name='{key}']")
        return p.get('value', '') if p is not None else ''
    entries = []
    allowed = {'Component', 'Consumable', 'Tradeable', 'Fish', 'SpaceSalvage'}
    curiosity = {'BP_SALVAGE', 'NAV_DATA', 'SUIT_INV_TOKEN', 'SHIP_INV_TOKEN', 'WEAP_INV_TOKEN',
                 'FREI_INV_TOKEN', 'SALVAGE_TECH1', 'SALVAGE_TECH2', 'SALVAGE_TECH3', 'SALVAGE_TECH4',
                 'FRIG_TOKEN', 'STATION_KEY', 'FACT_TOKEN', 'TECHFRAG', 'SENTINEL_LOOT'}
    aliases = {'FUEL1': 'karbon carbon', 'FUEL2': 'yoğunlaştırılmış karbon', 'LAND1': 'ferrit tozu',
               'LAND2': 'saf ferrit', 'OXYGEN': 'oksijen', 'CATALYST1': 'sodyum', 'AMMO': 'mühimmat mermi',
               'HYPERFUEL1': 'warp yakıtı', 'LAUNCHFUEL': 'kalkış yakıtı', 'BP_SALVAGE': 'kurtarılmış veri'}
    files = ['nms_reality_gcproducttable.MXML', 'nms_reality_gcsubstancetable.MXML', 'difficultyconfig.MXML']
    for file, kind in zip(files[:2], ('Product', 'Substance')):
        for row in ET.parse(source / file).getroot().find("Property[@name='Table']"):
            ident = val(row, 'ID')
            category = row.find("Property[@name='Type']/Property") if kind == 'Product' else row.find("Property[@name='Category']/Property")
            category = category.get('value')
            if not ident or ident.startswith(('DUMMY', 'TEST', 'DEBUG', 'MISSION', 'QUEST')):
                continue
            if kind == 'Product' and category not in allowed and ident not in curiosity:
                continue
            multiplier = int(val(row, 'StackMultiplier') or 0)
            if multiplier < 1:
                continue
            requirements = row.find("Property[@name='Requirements']")
            entries.append({'id': ident, 'kind': kind, 'title': names.get(val(row, 'NameLower')) or names.get(val(row, 'Name'), ident),
                'description': names.get(val(row, 'Description'), ''), 'category': category,
                'stack_multiplier': multiplier, 'craftable': val(row, 'IsCraftable') == 'true',
                'aliases': aliases.get(ident, ''),
                'requirements': [{'id': val(r, 'ID'), 'amount': int(val(r, 'Amount') or 0)} for r in requirements] if requirements is not None else []})
    rules = {}
    for row in ET.parse(source / files[2]).getroot().find("Property[@name='InventoryStackLimitsOptionData']"):
        rules[row.get('name')] = {kind: {'limit': int(val(row, kind + 'StackLimit')),
            'groups': {g.get('name'): int(g.get('value')) for g in row.find(f"Property[@name='Max{kind}StackSizes']")}}
            for kind in ('Substance', 'Product')}
    result = {'schema': 1, 'build': '179666', 'sources': {f: hashlib.sha256((source / f).read_bytes()).hexdigest() for f in files},
              'stack_rules': rules, 'items': entries}
    Path(destination).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return len(entries)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--localisation', type=Path, action='append', default=[])
    a = p.parse_args()
    print(build(a.source, a.localisation, a.output))
