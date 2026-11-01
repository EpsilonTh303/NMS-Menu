# Kaynaklar ve upstream'e iletilebilecek aday notlar

## Kaynaklar

- [monkeyman192/NMS.py](https://github.com/monkeyman192/NMS.py).
- [179105 güncellemesi, types.py](https://github.com/monkeyman192/NMS.py/blob/9efb09ccb6/nmspy/data/types.py):
  PlayerState alanları, GameState ve Application.Data ilişkisi. Buradaki yakın
  sürüm tanımları yerel 179666 GOG belleğiyle karşılaştırıldı.
- [Aynı commit exported_types.py](https://github.com/monkeyman192/NMS.py/blob/9efb09ccb6/nmspy/data/exported_types.py):
  GcPlayerGlobals alan türleri / offset'leri için referans.
- [globals.py](https://github.com/monkeyman192/NMS.py/blob/master/nmspy/globals.py):
  MBIN yol dizesinden global konumu çözme yaklaşımı. Yerel araç PE bölüm RVA ve
  dosya offset'lerini ayırarak analiz yaptı.
- [xesdoog/NMM pointers.cpp](https://github.com/xesdoog/NMM/blob/master/src/memory/pointers.cpp):
  Eski canlı patch imzaları karşılaştırma amacıyla incelendi; yerel .text içinde
  denenen on imza eşleşmedi. Hiçbiri belleğe uygulanmadı.
- [Microsoft ReadProcessMemory](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory),
  [WriteProcessMemory](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-writeprocessmemory):
  bağımsız adaptörün kullandığı Windows API'leri.

## Aday katkılar — henüz hata raporu veya PR değil

Yeni ek: [canlı filo bulguları](live-fleet-179666.md) teknoloji dizisi sürüm
farkı (`0xAA28` → `0xAB28`), vector header biçimi, pasif teknoloji `-1`
işareti ve grid boyutları dışındaki eski bitler için doğrulama notları içerir.

1. **GOG 179666 uyumluluk notu:** PlayerState para offset'leri ve yukarıdaki
   global alanların 179105 tanımlarıyla eşleştiğine dair build-hash'li gözlem.
   Bu yalnız belirtilen alanlar için kanıttır; tüm yapının uyumlu olduğu anlamına gelmez.
2. **PE adres dönüşümü için test önerisi:** global çözümlemede dosya raw offset'i
   ile mapped RVA ayrımını, signed RIP displacement'i ve bulunamayan pointer
   durumlarını sentetik PE fixture ile kapsamak yararlı olabilir. Mevcut upstream
   kurulumunda doğrulanmış bir hata iddiası yoktur; önce minimal repro gerekir.
3. **Ana menü / kayıt yükleme ön koşulu:** oyuncu pointer'ının okunabilir olması
   aktif oyuncu verisinin hazır olduğu anlamına gelmedi. İstatistikler ana menüde
   sıfır, kayıt yüklendiğinde geçerliydi. Örnek modlarda bu durum belgelenebilir.
4. **Platform / sürüm etiketleme:** imza uyumsuzluğunu oyun hatası olarak
   değerlendirmeden önce exe hash'i, sürüm ve dağıtım kanalını kaydetmek yararlı.

İleride gönderilecek katkı, güncel upstream commit'i üzerinde yeniden doğrulanmalı;
kişisel kayıtlar, işlem yedekleri, günlükler veya üçüncü taraf oyunun binary'si
paylaşılmamalı. Kaynak projenin katkı / lisans kuralları gönderim sırasında okunmalı.
