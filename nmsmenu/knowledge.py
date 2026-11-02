"""Learn one validated recipe without touching mission or account reward flags."""
import copy

from .catalog_data import technologies
from .inventory import items


def mutate(original, action, fleet):
    ident, kind = action['id'], action['kind']
    if kind == 'technology' and ident in technologies():
        field = 'KnownTech'
    elif kind == 'product' and ident in items() and items()[ident]['kind'] == 'Product' and items()[ident]['craftable']:
        field = 'KnownProducts'
    else:
        raise ValueError('Bu girdinin öğrenilebilir tarifi katalogda doğrulanmadı.')
    data = copy.deepcopy(original)
    known = fleet.player(data)[field]
    if not isinstance(known, list) or not all(isinstance(k, str) and k.startswith('^') for k in known):
        raise ValueError('Tarif bilgisi şeması doğrulanamadı.')
    already = '^' + ident in known
    if not already:
        known.append('^' + ident)
    paths = fleet.differences(original, data)
    prefix = fleet.PREFIX + field
    if not all(path == prefix or path.startswith(prefix + '/') for path in paths):
        raise ValueError('Tarif işlemi izinli alanları aştı.')
    return data, {'op': 'learn_recipe', 'id': ident, 'kind': kind, 'already_known': already}, paths
