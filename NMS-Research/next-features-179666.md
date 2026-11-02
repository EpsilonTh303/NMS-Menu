# Menüye eklenebilecekler — 2 Kasım 2026

Bu çalışma özellik araştırması ve önceliklendirmedir. Yeni oyun kontrolü eklenmedi;
kayıt veya oyun belleği değiştirilmedi. Mevcut v0.7 kodu, yerel arşiv indeksleri,
Hello Games güncelleme sayfaları ve NMSE geliştirici belgeleri incelendi.
Aşağıdaki uygulanabilirlik sırası kendi mühendislik değerlendirmemizdir; başka bir
editörde bulunması bizim sürümümüzde doğrulandığı anlamına gelmez.

## Öncelik sırası

| Öncelik | Aday | Somut kullanım | Gereken doğrulama |
|---|---|---|---|
| 1 | Eşya ve malzeme kataloğu | Karbon, ferrit, yakıt, mühimmat, üretim bileşeni ve genişleme eşyası ekle; miktar seç | Ürün/madde kimliği, envanter grubu, yığın üst sınırı, mevcut yığın + boş yer; görev eşyalarını ayrı tut |
| 2 | Envanter ızgarası | Eşyaları gör, taşı, yığın birleştir/böl; dolu/boş alanı gör | Kargo ve teknoloji hedefi ayrımı, eşyaların korunması, supercharged teknoloji yerleşimini koruma |
| 3 | Donanım profilleri | Keşif, madencilik, savaş ve ticaret setlerini kaydet/uygula | Eksik teknolojiyi ekle; ön koşul, aile aşırı yüklenmesi ve bitişiklik etkilerini değerlendir; kendiliğinden sökme yok |
| 4 | Silah koleksiyonu + yerleşik arşiv | Alet yuvaları, mevcut donanım, arşivdekiler; dışa/içe aktar | Aktif/depodaki envanter kopyası, kesin kimlik, boş aktif yuva, arşiv şeması |
| 5 | Tarif / yapı planı bilgisi | Seçilen teknoloji veya ürünün tarifini öğren; bilinen/bilinmeyen filtresi | KnownTech / KnownProducts ayrımı, yalnız eksik kayıtlar, görev/sefer bayraklarını topluca değiştirmeme |
| 6 | Katalog kullanım kolaylığı | Favoriler, son kullanılanlar, kullanıcı profilleri, miktar; hedefte zaten var / boş yer göstergesi | Yeni UI'dan bağımsız servis ve kalıcı kullanıcı tercihleri; ortak snapshot genişletme |
| 7 | Yük gemisi, fırkateyn, squadron | Önce liste, hasar onarımı ve envanter; ardından sınıf/özellik | Üs, aktif sefer, pilot ve istatistik bağımlılıklarına ayrı adaptör |
| 8 | Exocraft | Araç envanteri, yakıt, mevcut teknoloji, Minotaur AI kontrolü | Araç başına şema, aktif konuşlandırma ve sahiplik kontrolü |
| 9 | Living Ship / Wraith | Organik çekirdekli gemi ve uygun teknoloji paketi | Normal gemiden ayrı organik kaynak/enventar/sahiplik üretimi; oyun içi uçuş testi |
| 10 | Seyahat defteri | Mevcut adresi kopyala, portal kodu dönüştür, favori konumları sakla | Salt okunur araçlar önce; ışınlama daha sonra güvenli spawn ve galaksi kontrolüyle |
| 11 | Evcil hayvan ve yumurta | Koleksiyon, ad, boyut, güven ve yumurta bilgisi | Model parçaları, cins ve oyun kuralı kısıtları; ayrı modül |
| 12 | Corvette / uzay istasyonu / üs | Önce modül listesi ve dışa aktarma, ardından yapı düzenleme | Gövde modelinden fazlası: iç yerleşim, konum, üs sahipliği ve modül bağları |

## Yerel olarak görülen dayanaklar

Kurulu NMSARC.Precache.pak indeksinde şu kaynaklar bulundu:

- `metadata/reality/tables/nms_reality_gcproducttable.mbin`
- `metadata/reality/tables/nms_reality_gcsubstancetable.mbin`
- `metadata/reality/tables/nms_reality_gcproceduraltechnologytable.mbin`
- `metadata/reality/tables/inventorytable.mbin`

Bunlar eşya kataloğunun yerel kaynakları olabilir; bu araştırmada tabloların tüm
içeriği çıkarılıp yığın kuralları doğrulanmadı. Mevcut teknoloji/ödül katalog derleyicileri
ve sepet motoru yeniden kullanılabilir. SharedScan şu anda tam eşya/arşiv görünümü
sunmaz; yeni ekranlar için aynı ortak snapshot genişletilmeli, ayrı taramalar eklenmemeli.

## Yerleşik arşiv bulgusu

Hello Games, [Worlds II arşiv notlarında](https://www.nomanssky.com/worlds-part-ii-update/)
aktif filoya ek 18 gemi ve taşınan aletlere ek 18 çok amaçlı alet arşivlenebildiğini
belirtiyor. Bu, 12 aktif gemi / 6 aktif alet sınırını kaldırmaz. Yerleşik gemi arşivi
teknolojiyi tutar, gevşek kargoyu temizler. Mevcut harici garaj tam gemi/kargo/teknoloji
saklar; iki yöntem birbirinin yerine sessizce geçirilmemeli. Yeni adaptör kargoyu
önce korumalı veya dolu kargoyla arşivlemeyi reddetmeli.

## Diğer kaynaklar ve kapsam

[NMSE kullanıcı belgesi](https://github.com/vectorcmdr/NMSE/blob/main/docs/user/README.md)
eşya/teknoloji envanterleri, bilinen tarifler, araçlar, fırkateynler, pilotlar ve evcil
hayvan verilerinin bir kayıt editöründe yönetildiğini gösteriyor. Bu yalnız teknik
araştırma için dayanak; NMSE kodu kopyalanmadı, bizim canlı kontrollerimiz doğrulanmış sayılmaz.

[Waypoint](https://www.nomanssky.com/waypoint-update/) oyunun kendi zorluk seçeneklerinde
üretim maliyeti, yakıt ve savaş ayarları bulunduğunu açıklıyor. Menüde benzer kontroller
istersek önce yerleşik seçenekleri değerlendirmek uygun; kalıcı kilitli ayarlar ayrıca ele alınmalı.

[Cosmos](https://www.nomanssky.com/cosmos-update/) istasyon yönetimi, yörüngesel inşa ve
uzay haritasını tanımlıyor. Bunlar gelecekteki modüller için aday; sahiplik/üs yapıları
araştırılmadan basit aç/kapat kontrolü gibi sunulmamalı.

## Yeni UI için öneri

Ana görünümde bağlantı durumu, aktif kayıt, veri yaşı ve son işlem; katalogda favoriler,
görsel/kategori kartları, ayrıntılar ve hedef uyumluluğu; ayrı envanter ızgarası ile
sepet/rapor görünümü. Kısayollar uygulama odaklı olmalı; CapsLockFix başlatıcısı veya
CapsLock davranışı değiştirilmemeli. Ürün kuralları CatalogService benzeri servislere
konmalı; Tk ya da gelecek frontend aynı komutları kullanmalı.

Önerilen ilk paket: eşya ekleme + envanter görünümü + donanım profilleri. Sahiplik,
eşya türü ve teknoloji ekleme işlemleri mevcut güvenli kayıt akışıyla, oyun kapalıyken
uygulanmalı. Canlı yazma her özellik için ayrı doğrulama işidir. İstasyon NPC hasarı
hâlâ doğrulanmış değil; yapılabilirliği kesinmiş gibi planlanmamalı.
