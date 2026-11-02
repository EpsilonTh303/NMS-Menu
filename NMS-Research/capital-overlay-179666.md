# Yük gemisi, fırkateyn ve overlay — 2 Kasım 2026

## İncelenen kaynaklar

Veri alanları NMSE'nin `6e0fd3a3c92456ac7241e106856ca8be76b2e46b` sürümündeki
birincil kaynaklarla karşılaştırıldı. NMSE uygulaması çalıştırılmadı; üretim kodu
aktarılmadı. Aşağıdaki alanlar ve davranışlar bağımsız Python uygulamasına dayanak oldu:

- [FreighterLogic.cs](https://github.com/vectorcmdr/NMSE/blob/6e0fd3a3c92456ac7241e106856ca8be76b2e46b/Core/FreighterLogic.cs):
  `CurrentFreighter`, `PlayerFreighterName`, `FreighterInventory` ve teknoloji/kargo
  sınıf aynaları; üs verilerinin ayrı yapıda olması.
- [FrigateLogic.cs](https://github.com/vectorcmdr/NMSE/blob/6e0fd3a3c92456ac7241e106856ca8be76b2e46b/Core/FrigateLogic.cs):
  sefer katılımının `FleetExpeditions[].AllFrigateIndices` ile belirlenmesi;
  etkin sınıfın yalnız `InventoryClass` alanını yazmakla doğru üretilmemesi.
- [FrigatePanel.cs](https://github.com/vectorcmdr/NMSE/blob/6e0fd3a3c92456ac7241e106856ca8be76b2e46b/UI/Panels/FrigatePanel.cs):
  30 fırkateyn sınırı; `DamageTaken`/`RepairsMade`, ilk dört beceri ve normal kopyalama.
- [Waypoint güncellemesi](https://www.nomanssky.com/waypoint-update/): envanterlerde
  120 eşya / 60 teknoloji yuvasına kadar genişleme. Bu uygulama yük gemisinde
  120/60 açmayı S sınıfıyla sınırlar ve mevcut açık koordinatları korur.

## Yerel doğrulama

Güncel GOG `.hg` dosyası kaynak hash'i kontrol edilerek geçici klasöre kopyalandı
ve yalnız kopyası çözüldü. Freighter/Frigate alanları bu sürümün şemasıyla eşleşti.
Boş yük gemisi modeli ayrıca sahiplik yokluğu olarak ele alındı; envanter
şablonunun mevcut olması sahiplik kanıtı sayılmadı.

`capital.py` kaynak verinin derin kopyasında çalışır. Değişen yollar açık
izin listesiyle denetlenir; mevcut sepet/motor `prepare → rapor → apply`
akışına bağlanır. Seferde veya rapor bekleyen hedef reddedilir. Başka sefer
varken liste sonuna kopya eklemek indeksleri korur; kaldırma bütün sefer
raporlarının alınmasını gerektirir. Özellikler, diğer yedi beceri istatistiği,
geçmiş sayaçları ve bilinmeyen alanlar korunur. Silinen tam fırkateyn mevcut
motorun `*-removed-ships.json` dışa aktarımında `kind: frigate` ile saklanır.

Güncel kayıttaki bir fırkateynin kopyasında ad/beceri/onarım/kopyalama ve
ayrı, açıkça sentetik sahiplik eklenmiş yük gemisi şemasında sınıf/yuva/onarım
işlemleri gerçek codec ile yazılıp yeniden okundu. Her iki durumda JSON
eşitliği doğrulandı. Çıktılar `runtime/capital-codec-*/verification.json`
altındadır; canlı kayıt veya oyun belleği değiştirilmedi. Bu sonuçlar oyun içi
görünüm, sahiplik oluşturma ya da oynanış doğrulaması değildir.

## Overlay

v0.11 ekleme denemesinde oyun normal kapatıldı; taze auto/manual kayıtlar
bağımsız yedeklenip `freighter_create` için kodlandı ve çözülmüş JSON eşitliği
doğrulandı. Semantik fark yalnız model/ad/üç tohum alanlarıydı. Deneme
uygulandı; CapsLockFix ile oyun kayıt seçim ekranına açıldı. Windows UI
aracında basılı tutma desteklenmediği için kayıt yükleme onayı geçilemedi.
Oyun normal kapatılıp deneme tam kayıt yedeğinden geri alındı; yeni durum da
restore öncesi yedekte korundu. Bu işlem bir oynanış doğrulaması değildir.
Özellik bu yüzden açık deneysel onay gerektirir; mevcut sahiplik/üs/kargo
üzerine uygulanmaz. Görev, oda veya konum üretilmez.

Qt araç penceresi, `WindowStaysOnTopHint` ve çerçevesiz pencere ile mevcut
canlı UI modelini gösterir. v0.11 kontrolleri mevcut LiveBackend para, ayar ve
geri alma yollarına bağlanır; ayrı bellek bağlantısı veya yeni adres kullanılmaz.
Kısayol [RegisterHotKey](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-registerhotkey)
ile Ctrl+Shift+F8 olarak kaydedilir; panel kapandığında kayıt kaldırılır.
Qt [native event filter](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QAbstractNativeEventFilter.html)
yalnız bu hotkey kimliğini işler. CapsLock hook'u değiştirilmez. Özel tam ekran
üstüne render enjeksiyonu yoktur; pencere/kenarlıksız mod gerekir.

## Canlı gemi ekleme neden hâlâ kapalı?

İncelenen editörler sahipliği kayıt JSON'u üzerinden değiştirir; bu build için
oyun thread'inde kaynak tahsisi, envanter vektörü kurulumu ve spawn/mesh yenileme
adresleri doğrulanmadı. Mevcut canlı motor yalnız ayrılmış bellekteki sabit
envanter alanlarına izin verir. JSON'a gemi ekleyip açık oyunun kayıt dosyasını
ezmek veya sabit sahiplik dizisini büyütmek canlı gemi ekleme değildir.

Bu nedenle canlı ekleme düğmesi eklenmedi. Oyun kapalıyken gemi ekleme mevcut
katalogdan yapılabilir. Canlı destek için ayrı runtime araştırması ve kontrollü
oyun içi doğrulama gerekir; bu rapor o desteğin var olduğunu iddia etmez.
