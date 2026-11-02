"""Fresh-copy integration check. Never prepares/applies against live save files."""
import copy
import json
from pathlib import Path
import shutil
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nmsmenu import inventory, archives, loadouts, weapons
from nmsmenu.catalog_mutations import mutate
from nmsmenu.catalog_service import CatalogService
from nmsmenu.live_fleet import engine


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    fleet = engine()
    source = max(fleet.LIVE.glob('save*.hg'), key=lambda p: p.stat().st_mtime_ns)
    meta = source.with_name('mf_' + source.name)
    work = Path('runtime') / ('workbench-check-' + uuid.uuid4().hex)
    before = work / 'before'
    before.mkdir(parents=True)
    hashes = {p.name: fleet.digest(p) for p in (source, meta)}
    for p in (source, meta):
        shutil.copy2(p, before / p.name)
    assert all(fleet.digest(source.parent / n) == h and fleet.digest(before / n) == h for n, h in hashes.items())
    original = fleet.decode(before / source.name)
    data = copy.deepcopy(original)
    service = CatalogService()
    plan, events, exports = [], [], []
    spec = {'kind': 'exosuit', 'section': 'cargo'}
    def run(actions):
        nonlocal data
        data, result, outgoing = mutate(data, {'actions': actions}, service.ships, fleet, fleet.mutate)
        plan.extend(copy.deepcopy(actions))
        events.extend(result['events'])
        exports.extend(outgoing)
    def first(ident):
        return next(p for p in fleet.player(data)['Inventory']['Slots'] if p['Id'] == '^' + ident)
    def free(inv):
        occupied = [p['Index'] for p in inv['Slots']]
        return next(p for p in inv['ValidSlotIndices'] if p not in occupied)
    run([{'op': 'add_item', 'inventory': spec, 'id': 'FUEL1', 'amount': 12000},
         {'op': 'add_item', 'inventory': spec, 'id': 'CASING', 'amount': 25}])
    run([{'op': 'split_item', 'inventory': spec, 'item': inventory.fingerprint(first('CASING')), 'amount': 3,
          'destination': spec, 'position': free(fleet.player(data)['Inventory'])}])
    run([{'op': 'merge_stacks', 'inventory': spec}])
    p = fleet.player(data)
    ship = next(s for s in fleet.fleet_summary(p) if s['slot'] != p['PrimaryShip'] + 1 and s['type'] in archives.SHIP_CLASSES)
    selector = {k: ship[k] for k in ('slot', 'seed', 'type')}
    target = {'kind': 'ship', 'section': 'cargo', 'selector': selector}
    run([{'op': 'move_item', 'inventory': spec, 'item': inventory.fingerprint(first('CASING')), 'destination': target,
          'position': free(p['ShipOwnership'][ship['slot'] - 1]['Inventory'])}])
    p = fleet.player(data)
    moved = next(i for i in p['ShipOwnership'][ship['slot'] - 1]['Inventory']['Slots'] if i['Id'] == '^CASING')
    run([{'op': 'set_item_amount', 'inventory': target, 'item': inventory.fingerprint(moved), 'amount': 10}])
    tool = next(t for t in weapons.summary(fleet.player(data)) if t['active'])
    tool_selector = {k: tool[k] for k in ('slot', 'seed', 'filename')}
    tool_spec = {'kind': 'multitool', 'section': 'tech', 'selector': tool_selector}
    run(loadouts.commands(loadouts.BUILTINS['tool_combat'], tool_spec))
    run([{'op': 'learn_recipe', 'kind': 'product', 'id': 'CASING'}])
    run([{'op': 'archive_ship', 'selector': selector},
         {'op': 'archive_tool', 'selector': tool_selector, 'weapon_class': 'Pistol'}])
    print('Mixed item, move/split/merge, loadout, recipe and archive mutations OK.', flush=True)
    number = 1 if source.name == 'save.hg' else int(source.stem[4:])
    def codec(label):
        output = work / label
        output.mkdir()
        for name in hashes:
            shutil.copy2(before / name, output / name)
        fleet.encode(data, output, number - 1)
        decoded = fleet.decode(output / source.name)
        if decoded != data:
            raise ValueError('Codec difference: ' + repr(fleet.differences(data, decoded)[:20]))
        p = fleet.player(decoded)
        assert [len(p[k]) for k in ('ShipOwnership', 'Multitools', 'ArchivedShipOwnership', 'ArchivedMultitools')] == [12, 6, 18, 18]
        print('Codec equality OK:', label, flush=True)
    codec('archived')
    snapshot = archives.snapshot(fleet.player(data), fleet)
    archived_ship = next(a for a in snapshot if a['kind'] == 'ship' and a['selector']['seed'] == ship['seed'])
    archived_tool = next(a for a in snapshot if a['kind'] == 'multitool' and a['selector']['seed'] == tool['seed'])
    run([{'op': 'restore_archived_ship', 'selector': archived_ship['selector']},
         {'op': 'restore_archived_tool', 'selector': archived_tool['selector']}])
    codec('restored')
    assert all(fleet.digest(before / n) == h for n, h in hashes.items())
    report = {'source': source.name, 'source_hashes': hashes, 'events': events,
        'changed_paths': fleet.differences(original, data), 'codec_states': ['archived', 'restored'],
        'inventory_views': len(inventory.snapshot(fleet.player(data), fleet)), 'export_count': len(exports)}
    (work / 'plan.json').write_text(json.dumps({'actions': plan}, ensure_ascii=False, indent=2), encoding='utf-8')
    (work / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report:', work / 'report.json', flush=True)


if __name__ == '__main__':
    main()
