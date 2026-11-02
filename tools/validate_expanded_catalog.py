"""Opt-in developer check on a fresh, detached save copy; never calls apply."""
import copy
import argparse
import json
from pathlib import Path
import shutil
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nmsmenu.catalog_service import CatalogService
from nmsmenu.catalog_data import ship_profiles, tool_models
from nmsmenu.catalog_mutations import mutate
from nmsmenu.live_fleet import engine
from nmsmenu import weapons


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--codec-only', action='store_true', help='Skip the slower exhaustive in-memory profile checks')
    args = parser.parse_args()
    fleet, service = engine(), CatalogService()
    source = max(fleet.LIVE.glob('save*.hg'), key=lambda p: p.stat().st_mtime_ns)
    meta = source.with_name('mf_' + source.name)
    hashes = {p.name: fleet.digest(p) for p in (source, meta)}
    work = Path('runtime') / ('expanded-catalog-check-' + uuid.uuid4().hex)
    before = work / 'before'
    before.mkdir(parents=True)
    for p in (source, meta):
        shutil.copy2(p, before / p.name)
    if any(fleet.digest(source.parent / name) != h or fleet.digest(before / name) != h for name, h in hashes.items()):
        raise ValueError('Save changed while copying. Retry with a fresh copy.')
    original = fleet.decode(before / source.name)
    player = fleet.player(original)
    if not any(fleet.kind(s) == 'empty' for s in player['ShipOwnership']):
        raise ValueError('No empty native ship slot in the detached source.')
    active = weapons.summary(player)[next(i for i, p in enumerate(weapons.summary(player)) if p['active'])]
    selector = {k: active[k] for k in ('slot', 'seed', 'filename')}
    report = {'source': source.name, 'source_hashes': hashes, 'tested_ships': [], 'tested_tools': [], 'codec': []}
    def check(commands):
        data, result, exports = mutate(original, {'actions': commands}, service.ships, fleet, fleet.mutate)
        p = fleet.player(data)
        assert len(p['ShipOwnership']) == 12 and len(p['Multitools']) == 6
        for i, ship in fleet.owned(player):
            assert p['ShipOwnership'][i] == ship
        for i, tool in weapons.owned(player):
            assert p['Multitools'][i] == tool
        assert p['CurrentWeapon'] == player['CurrentWeapon']
        return data, result
    for key in ([] if args.codec_only else ship_profiles()):
        check([service.command('ship:' + key)])
        report['tested_ships'].append(key)
    print('Ship profile checks:', len(report['tested_ships']), flush=True)
    for key in ([] if args.codec_only else tool_models()):
        check([service.command('tool:' + key, selector=selector, name='Catalog Test')])
        report['tested_tools'].append(key)
    print('Tool profile checks:', len(report['tested_tools']), flush=True)
    ship_keys = [next(k for k, v in ship_profiles().items() if v['family'] == family)
                 for family in ('fighter', 'hauler', 'explorer', 'shuttle', 'solar')]
    models = ['staff', 'atlas_staff', 'ruin_staff', 'bone_staff', 'switch']
    number = 1 if source.name == 'save.hg' else int(source.stem[4:])
    for n, (ship, tool) in enumerate(zip(ship_keys, models)):
        commands = [service.command('ship:' + ship), service.command('tool:' + tool, selector=selector, name='Codec Test')]
        data, result = check(commands)
        output = work / f'codec-{n}'
        output.mkdir()
        for name in hashes:
            shutil.copy2(before / name, output / name)
        (output / 'plan.json').write_text(json.dumps({'actions': commands}, ensure_ascii=False, indent=2), encoding='utf-8')
        fleet.encode(data, output, number - 1)
        decoded = fleet.decode(output / source.name)
        if decoded != data:
            raise ValueError('Codec difference: ' + repr(fleet.differences(data, decoded)[:20]))
        report['codec'].append({'ship': ship, 'tool': tool, 'equal': True, 'changed_paths': result['changed_paths']})
        print('Codec OK:', ship, tool, flush=True)
    assert fleet.decode(before / source.name) == original
    (work / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report:', work / 'report.json')


if __name__ == '__main__':
    main()
