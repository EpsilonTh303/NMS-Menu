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


0.7: `CatalogItem.family` aile filtresinin, `addable` rehber kayıtlarının sözleşmesidir.
`CatalogService.detail(key)` görünümden bağımsız ve derin kopyalı içerik bilgisi döndürür.
`counts()` seçenek sayısı verir; oyun içi toplam tür sayısı olarak etiketlenmemeli.
Sabit ödül tohumu varsayılandır; rastgele alet tohumu açık kullanıcı seçeneğidir.
Yeni gemi referansları doğrudan FleetManager native mutasyonuna veri olarak iletilir;
codec / hash / durdurulmuş süreç kontrolleri aynı motor üzerinden yürür.


0.8: `inventory.py` saf envanter çözümleme, fingerprint, miktar ve taşıma kurallarıdır.
`archives.py` native arşiv kimliği ve koruma kurallarını; `loadouts.py` setleri;
`knowledge.py` seçili tarif bilgisini yönetir. Yeni frontend bunları yeniden yazmamalı.
`DiskScanner` aynı çözümlemeden `inventories` ve `archives` snapshot'ı üretir.
`inventory_ui.py` yalnız Tk adaptörüdür; mutasyonlar ortak `catalog_mutations` / CLI
üzerinden mevcut FleetManager hazırlama/codec/hash/commit motoruna gider. Favori ve set
tercihleri yerel runtime dosyalarıdır. UI sekmeleri ayrı disk/process taraması yapmaz.
