"""Extract Turkish presentation strings and f-string templates without imports."""
import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRA = [
    'Bağlı ve kayıt yüklü', 'Canlı bağlantı / kayıt bekleniyor',
    'Oyun üstü paneli etkinleştir',
    'Ctrl+Shift+F8 ile gizle/göster. Pencere veya kenarlıksız mod gerekir.',
    'Sanayi', 'Ticaret', 'Hasar', 'Sefer', 'Combat', 'Exploration', 'Mining', 'Diplomacy', 'Support',
    'Aktif', 'Ekzosuit', 'Favoriler', 'Filo rehberi', 'Garaj', 'Gemi', 'Gemi rehberi',
    'Kargo', 'Silah rehberi', 'Teknoloji rehberi', 'Yuva', 'Ad', 'Tip',
    'Alien', 'AlienShip', 'AllShips', 'AllShipsExceptAlien', 'Atlantid', 'Catalyst',
    'Component', 'Consumable', 'Curiosity', 'Earth', 'Exotic', 'Fish', 'Flora', 'Fuel',
    'Metal', 'Pistol', 'Pristine', 'Procedural', 'Rifle', 'RobotShip', 'Royal', 'Sentinel',
    'Ship', 'SpaceSalvage', 'Special', 'Staff', 'Stellar', 'Suit', 'Tradeable', 'Weapon',
    'Seçenek sayıları oyundaki toplam tür sayısı değildir.',
    'Dil dosyalarını yenile', 'Çeviri kapsamı: {v0}/{v1}', 'Eksik çeviriler Türkçe gösterilir.',
    'Yeni bir dil eklemek için locales klasörüne bir JSON dosyası ekleyin.',
    'Ayarlar', 'Dil', 'Arayüz dili', 'Dil değişikliği hemen uygulanır ve bu bilgisayarda saklanır.',
    'Dil tercihi kaydedilemedi: {v0}', 'Dil tercihi kaydedildi.',
    'Mod Merkezi', 'Envanter ve Koleksiyon', 'Modüler envanter, eşya ve koleksiyon yöneticisi',
    'Offline GOG', 'Canlı filo: Esc', 'Kayıt dosyası düzenleme: oyun kapalıyken',
    'Gemi profili', 'Alet / tohum varyantı', 'Teknoloji', 'Eşya', 'Garaj kaydı',
    'Tamam', 'Evet', 'Hayır', 'İptal',
]


def extract():
    messages = set(EXTRA)
    for path in sorted((ROOT / 'nmsmenu').glob('*.py')):
        if path.stem in ('icons', 'i18n'):
            continue
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        if path.stem in ('qt_ui', 'overlay'):
            # Qt presentation strings are explicitly marked with t("...").
            # Avoid treating stylesheets, SVG, or HTML markup as messages.
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ''
                if name in ('t', 'text') and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    messages.add(node.args[0].value)
            continue

        def visit(node):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                return  # docstrings
            if isinstance(node, ast.JoinedStr):
                parts, n = [], 0
                for value in node.values:
                    if isinstance(value, ast.Constant):
                        parts.append(value.value)
                    else:
                        parts.append('{v' + str(n) + '}')
                        n += 1
                add(''.join(parts))
                return
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                add(node.value)
            for child in ast.iter_child_nodes(node):
                visit(child)

        def add(value):
            if len(value.strip()) < 2:
                return
            visible = re.sub(r'\{v\d+\}', '', value)
            if value == 'Segoe UI' or re.fullmatch(r'(?:(?:[A-F0-9]{2}|\?{1,2}) ?)+', value):
                return
            if value and (re.search('[çğıöşüÇĞİÖŞÜ]', value) or
                          (' ' in visible and re.search('[A-Za-z]', visible) and len(visible.strip()) > 2) or
                          value in ('ID', 'X:', 'Y:', 'Units', 'Quicksilver', 'Type', 'Seed', 'Normal', 'Hepsi', 'Katalog', 'Tarif', 'Profil', 'Para', 'Hedef', 'Nanit', 'Otomatik', 'Plan', 'Durum', 'X / Y')):
                messages.add(value)
        visit(tree)
    return {key: key for key in sorted(messages)}


if __name__ == '__main__':
    messages = extract()
    path = ROOT / 'locales' / 'tr.json'
    existing = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    for key, value in messages.items():
        existing.setdefault(key, value)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(messages)} messages')
