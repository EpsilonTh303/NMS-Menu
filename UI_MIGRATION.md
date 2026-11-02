# Arayüz geçişi için sınırlar

Yeni ekran mevcut Tk görünümünün yerine geçebilir. Katalog ve kayıt kurallarını görünüme taşımayın.

- `catalog_data.py`: sürümlü JSON katalog yükleme ve hedef uyumluluğu.
- `catalog_service.py`: Tk bağımlılığı olmayan `CatalogItem`, arama, komut üretimi ve `CatalogCart`.
- `catalog_ui.py`: yalnızca mevcut Tk sunumu, kullanıcı seçimi ve async sonuçların çizimi.
- `catalog_backend.py`: subprocess üzerinden prepare/apply/restore adaptörü.
- `catalog_cli.py` / `catalog_mutations.py`: taze kayıt üzerinde izinli mutasyonlar; FleetManager işlem motoru.
- `shared_scan.py`: bütün ekranların paylaştığı salt okunur `saves` / `garage` / `history` snapshot'ı.

Yeni UI aynı `CatalogService.items()` sonucundaki sabit `key` kimliklerini saklamalı;
etiketlerden komut üretmemeli. `command()` kesin slot/tohum/model seçicisi döndürür.
Sepet dışarıya derin kopya verir, farklı kayıt yuvalarını karıştırmaz ve her değişiklikte
`revision` artırır. Prepare sonucu yalnız aynı revision için geçerlidir; apply öncesinde de
kontrol edilir. Apply düğmesi sadece değişiklik içeren, başarıyla hazırlanmış raporla açılır.

İlk ortak disk taraması codec süresince gecikebilir. Yeni UI tarama veya codec işini ana
çizim döngüsüne taşımamalı; her ekran için yeniden tarama başlatmamalı. Yenilemede seçimler
slot/tohum üzerinden korunmalı. Snapshot yazılabilir kayıt kaynağı değildir.

Yazma akışı: oyun kapalı kontrolü → taze kaynak/yedek → plan → semantik fark → codec
round-trip → rapor inceleme → kaynak hash ve oyun kapalı kontrolü → apply. Restore tam
kayıt zamanına döner ve daha yeni durumu ayrıca yedekler. Bu kontroller görünüm değişse de korunmalı.
