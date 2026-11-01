"""Use FleetManager's backup/codec/hash/commit engine for multitool plans."""
import json
import sys

from .live_fleet import engine
from . import weapons


def main():
    fleet = engine()
    fleet.mutate = lambda original, plan, catalog: weapons.mutate(original, plan, catalog, fleet)
    if sys.argv[1:] == ['inspect']:
        for file in sorted(fleet.LIVE.glob('save*.hg')):
            p = fleet.player(fleet.decode(file))
            print(json.dumps({'file': file.name, 'multitools': weapons.summary(p)}, ensure_ascii=False))
    else:
        fleet.main()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        sys.exit(1)
