"""Feature registry. Planned features never register executable actions."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    key: str
    title: str
    status: str
    features: str


MODULES = (
    Module('fleet', 'Gemi filosu', 'Hazır', 'Katalogdan ekle, kesin kimlikle kaldır, onar, donanım paketi kur.'),
    Module('inventory', 'Envanter ve kalkış', 'Hazır', 'Karakter / gemi yuvalarını aç, normal kalkış otomatik şarj teknolojisi ekle.'),
    Module('garage', 'Harici garaj', 'Hazır', 'Tam gemi kopyalarını arşivle, listele, boş yuvaya veya seçilen geminin yerine al.'),
    Module('transactions', 'Yedek ve geri alma', 'Hazır', 'Taze plan, codec kontrolü, fark incelemesi, kaynak hash kontrolü, tam kayıt geri alma.'),
    Module('economy', 'Para birimleri', 'Planlandı', 'Units, nanit ve quicksilver: alanlar / sınırlar doğrulandıktan sonra miktar düzenleme.'),
    Module('items', 'Eşya ve üretim', 'Planlandı', 'Eşya kataloğu, miktar, tarif ve üretim kilitleri; kimlik ve yığın sınırı doğrulaması gerekir.'),
    Module('multitool', 'Çok amaçlı alet', 'Planlandı', 'Alet, yuva, sınıf ve teknoloji; kayıt şeması ve kapasite kuralları araştırılacak.'),
    Module('freighter', 'Yük gemisi ve fırkateyn', 'Planlandı', 'Envanter, filo ve seferler; görev durumlarını koruyan ayrı işlem motoru gerekir.'),
    Module('player', 'Karakter ve zorluk', 'Araştırma', 'Sağlık, hasar, tüketim ve inşa maliyeti; önce oyunun kendi ayarları değerlendirilecek.'),
    Module('travel', 'Keşif ve seyahat', 'Araştırma', 'Koordinat, itibar, kelimeler ve keşif; görev / konum tutarlılığı doğrulanmalı.'),
    Module('base', 'Üs ve yerleşim', 'Araştırma', 'Üs parçaları, enerji ve yerleşim; sahiplik / konum verileri araştırılmalı.'),
    Module('runtime', 'Oyun içi overlay / canlı hile', 'Ayrı proje', 'Bu sürüm kayıt editörüdür. Overlay, ölümsüzlük, uçuş ve zaman kontrolü uygulanmadı.'),
)

OPERATIONS = {
    'Gemi ekle': 'add',
    'Seçili gemiyi kaldır (kargoyu koru)': 'remove',
    'Seçili gemiyi onar ve şarj et': 'repair_ship',
    'Seçili gemiye donanım paketi kur': 'equip',
    'Karakter envanterini genişlet': 'exosuit_slots',
    'Tüm gemilerin envanterini genişlet': 'ship_slots',
    'Tüm gemilere kalkış otomatik şarjı': 'auto_recharge',
    'Garajdan boş yuvaya al': 'garage_import',
    'Garajdan seçili geminin yerine al': 'garage_replace',
}


def selector(ship):
    if not ship:
        raise ValueError('Önce taze kayıt listesinden bir gemi seçin.')
    # Procedural name may be absent; identity never relies on the display label.
    return {key: ship[key] for key in ('slot', 'seed', 'type')}


def build_plan(operation, slot, ship=None, profile='', garage_id=''):
    if type(slot) is not int or not 1 <= slot <= 15:
        raise ValueError('Kayıt yuvası 1–15 olmalı.')
    if operation == 'add':
        if not profile:
            raise ValueError('Katalog profili seçin.')
        action = {'op': 'add', 'profile': profile}
    elif operation in ('remove', 'repair_ship', 'equip'):
        action = {'op': operation, 'selector': selector(ship)}
        if operation == 'remove':
            action['preserve_cargo'] = True
        if operation == 'equip':
            if not profile:
                raise ValueError('Donanım paketi seçin.')
            action['profile'] = profile
    elif operation in ('exosuit_slots', 'ship_slots'):
        action = {'op': 'max_slots', 'scope': 'exosuit' if operation == 'exosuit_slots' else 'ships'}
    elif operation == 'auto_recharge':
        action = {'op': operation, 'scope': 'ships'}
    elif operation in ('garage_import', 'garage_replace'):
        if len(garage_id) != 64 or any(c not in '0123456789abcdef' for c in garage_id):
            raise ValueError('Listeden geçerli bir garaj kaydı seçin.')
        action = {'op': 'garage_import', 'id': garage_id}
        if operation == 'garage_replace':
            action['replace'] = selector(ship)
    else:
        raise ValueError('Bu özellik henüz uygulanmadı.')
    return {'save_slot': slot, 'actions': [action]}
