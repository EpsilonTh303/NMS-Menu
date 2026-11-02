import hashlib
import sys

from .live import BUILD_HASH, EXE
from .live_fleet import engine
from . import catalog_mutations


def main():
    fleet = engine()
    native = fleet.mutate
    def mutate(original, plan, catalog):
        if hashlib.sha256(EXE.read_bytes()).hexdigest() != BUILD_HASH:
            raise ValueError('Bu oyun sürümünün teknoloji / model kataloğu doğrulanmadı.')
        return catalog_mutations.mutate(original, plan, catalog, fleet, native)
    fleet.mutate = mutate
    fleet.main()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        sys.exit(1)
