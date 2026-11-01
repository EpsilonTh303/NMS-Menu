"""Build-pinned live data editing. Never patches instructions or save files."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import uuid

from .winmem import ProcessMemory

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT.parent / 'Binaries' / 'NMS.exe'
BUILD_HASH = 'a91e3df36b049c4f5dbc6784a2943b803333bf8e4a23b4d165d1ab3cf83d4ffe'
ROOT_RVA = 0x6E8D9A8
PLAYER_OFFSET = 0xB940
PLAYER_GLOBALS = 0x522E630


@dataclass(frozen=True)
class Setting:
    title: str
    offset: int
    minimum: float
    maximum: float
    note: str


SETTINGS = {
    'walk': Setting('Yürüme hızı', 0x12EC, 0.5, 25, 'Normal değer yaklaşık 4.4.'),
    'run': Setting('Koşma hızı', 0x12D4, 1, 40, 'Normal değer 8.'),
    'jet_force': Setting('Jetpack ileri itişi', 0x14A4, 1, 100, 'Normal değer 31; uçuş davranışını etkiler.'),
    'jet_fill': Setting('Jetpack dolum hızı', 0x1490, 0.1, 10, 'Normal değer 0.5; sınırsız yakıt değildir.'),
    'stamina_drain': Setting('Dayanıklılık tüketimi', 0x18F0, 0, 1, '0 = bu tüketim katsayısı sıfır; normal 0.1.'),
    'stamina_fill': Setting('Dayanıklılık yenilenmesi', 0x18F8, 0.01, 10, 'Yüksek değer daha hızlı yenilenir.'),
    'life_low': Setting('Yaşam desteği / düşük tüketim', 0x110C, 0, 5, '0 = bu koşuldaki tüketim sıfır.'),
    'life_medium': Setting('Yaşam desteği / orta tüketim', 0x1110, 0, 5, '0 = bu koşuldaki tüketim sıfır.'),
    'life_high': Setting('Yaşam desteği / yüksek tüketim', 0x1108, 0, 5, '0 = bu koşuldaki tüketim sıfır.'),
    'life_water': Setting('Yaşam desteği / derin su', 0x1100, 0, 10, '0 = bu koşuldaki tüketim sıfır.'),
    'life_space': Setting('Yaşam desteği / uzay', 0x1104, 0, 5, '0 = bu koşuldaki tüketim sıfır.'),
    'shield_fill': Setting('Karakter kalkan yenilenmesi', 0x1818, 0.1, 100, 'Normal değer 10; ölümsüzlük değildir.'),
}
CURRENCIES = {'Units': 0x89C, 'Nanit': 0x8A0, 'Quicksilver': 0x8A4}


class LiveBackend:
    def __init__(self, exe=EXE, journal=ROOT / 'runtime' / 'live-audit.jsonl', factory=ProcessMemory):
        self.exe, self.journal, self.factory = Path(exe), Path(journal), factory
        self.memory = None
        self.originals = {}
        self.last_values = {}
        self.currency_undo = None

    def connect(self):
        if self.memory:
            raise RuntimeError('Zaten bağlı. Önce bağlantıyı kesin.')
        if hashlib.sha256(self.exe.read_bytes()).hexdigest() != BUILD_HASH:
            raise RuntimeError('Bu NMS.exe sürümü doğrulanmadı; canlı yazma açılmadı.')
        memory = self.factory(self.exe, writable=True)
        try:
            if memory.read(memory.base + 0x597739, 7) != bytes.fromhex('48 8B 0D 68 62 8F 06'):
                raise RuntimeError('Canlı kod doğrulaması başarısız; bağlantı kurulmadı.')
            self.memory = memory
            state = self.snapshot()
            for key, value in state['settings'].items():
                setting = SETTINGS[key]
                if not math.isfinite(value) or not 0 <= value <= max(setting.maximum * 10, 100):
                    raise RuntimeError('Yapılandırma alanları bu oturumda doğrulanamadı.')
            self.log({'event': 'connected', 'pid': memory.pid, 'build': BUILD_HASH})
            return state
        except BaseException:
            self.memory = None
            memory.close()
            raise

    def log(self, event):
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        entry = {'time': datetime.now(timezone.utc).isoformat(), **event}
        with self.journal.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def require_memory(self):
        if not self.memory or not self.memory.alive():
            raise RuntimeError('Oyun bağlantısı yok veya oturum kapandı. Yeniden bağlanın.')
        return self.memory

    def player(self):
        m = self.require_memory()
        pointer = struct.unpack('<Q', m.read(m.base + ROOT_RVA, 8))[0]
        slot, mode = struct.unpack('<II', m.read(m.base + ROOT_RVA + 8, 8))
        if not 0 < pointer < 0x7FFFFFFFFFFF or slot > 14 or mode > 10:
            raise RuntimeError('Oyuncu oturumu henüz hazır değil.')
        p = pointer + PLAYER_OFFSET
        stats = struct.unpack('<6I', m.read(p + 0x890, 24))
        primary = struct.unpack('<I', m.read(p + 0x182A0, 4))[0]
        if stats[1] == 0 and stats[2] == 0 or primary >= 12:
            raise RuntimeError('Ana menü / yükleme ekranı: önce kayıt içine girin.')
        return p, (m.pid, pointer, slot), stats

    def snapshot(self):
        m = self.require_memory()
        settings = {key: struct.unpack('<f', m.read(m.base + PLAYER_GLOBALS + field.offset, 4))[0]
                    for key, field in SETTINGS.items()}
        result = {'pid': m.pid, 'settings': settings, 'currencies': {}, 'loaded': False}
        try:
            _, identity, stats = self.player()
            result.update(loaded=True, save_slot=identity[2] + 1,
                          currencies=dict(zip(CURRENCIES, stats[3:])))
        except RuntimeError as exc:
            result['player_status'] = str(exc)
        return result

    def write_checked(self, address, before, after, label):
        m = self.require_memory()
        if m.read(address, len(before)) != before:
            raise RuntimeError('Değer işlem sırasında değişti; yeniden okuyun.')
        operation = uuid.uuid4().hex
        self.log({'event': 'intent', 'id': operation, 'pid': m.pid,
                  'address': hex(address), 'label': label, 'before': before.hex(), 'after': after.hex()})
        try:
            m.write(address, after)
            if m.read(address, len(after)) != after:
                raise RuntimeError('Canlı yazma sonrası doğrulama başarısız.')
            self.log({'event': 'verified', 'id': operation})
        except BaseException:
            # Only restore our exact bytes; never overwrite a newer game value.
            if m.alive() and m.read(address, len(after)) == after:
                m.write(address, before)
            raise

    def set_setting(self, key, value):
        field = SETTINGS[key]
        value = float(value)
        if not math.isfinite(value) or not field.minimum <= value <= field.maximum:
            raise ValueError(f'{field.title}: {field.minimum}–{field.maximum} aralığı gerekli.')
        m = self.require_memory()
        address = m.base + PLAYER_GLOBALS + field.offset
        before = m.read(address, 4)
        if key in self.last_values and before != self.last_values[key]:
            raise RuntimeError('Ayar oyun veya başka araç tarafından değiştirildi; bağlantıyı yenileyin.')
        after = struct.pack('<f', value)
        self.write_checked(address, before, after, key)
        self.originals.setdefault(key, before)
        self.last_values[key] = after
        return self.snapshot()

    def restore_settings(self):
        m = self.require_memory()
        conflicts = []
        for key in list(self.originals):
            address = m.base + PLAYER_GLOBALS + SETTINGS[key].offset
            if m.read(address, 4) != self.last_values[key]:
                conflicts.append(key)
                continue
            self.write_checked(address, self.last_values[key], self.originals[key], 'restore:' + key)
            del self.originals[key]
            del self.last_values[key]
        if conflicts:
            raise RuntimeError('Başka değişiklik bulundu; üzerine yazılmadı: ' + ', '.join(conflicts))
        return self.snapshot()

    def set_currency(self, key, value):
        if type(value) is not int or not 0 <= value <= 2_000_000_000:
            raise ValueError('Para miktarı 0–2.000.000.000 arasında tam sayı olmalı.')
        p, identity, _ = self.player()
        address = p + CURRENCIES[key]
        before = self.memory.read(address, 4)
        after = struct.pack('<I', value)
        if self.player()[1] != identity:
            raise RuntimeError('Kayıt oturumu değişti; yeniden okuyun.')
        self.write_checked(address, before, after, key)
        self.currency_undo = (key, identity, before, after)
        return self.snapshot()

    def undo_currency(self):
        if not self.currency_undo:
            raise ValueError('Geri alınacak para işlemi yok.')
        key, identity, before, after = self.currency_undo
        p, current, _ = self.player()
        if current != identity:
            raise RuntimeError('Farklı oyun / kayıt oturumu; para geri alınmadı.')
        self.write_checked(p + CURRENCIES[key], after, before, 'undo:' + key)
        self.currency_undo = None
        return self.snapshot()

    def disconnect(self):
        if not self.memory:
            return
        if self.memory.alive() and self.originals:
            self.restore_settings()
        self.memory.close()
        self.memory = None
        self.originals.clear()
        self.last_values.clear()
        self.currency_undo = None

    def forget_closed_session(self):
        if self.memory and self.memory.alive():
            raise RuntimeError('Oyun hâlâ açık; önce ayarları geri alın.')
        if self.memory:
            self.memory.close()
        self.memory = None
        self.originals.clear()
        self.last_values.clear()
        self.currency_undo = None
