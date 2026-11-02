# Modüler tasarım

## v0.10 yük gemisi, fırkateyn ve oyun üstü panel

`capital.py` kimlik/sefer doğrulaması ve semantik izin listesiyle saf veri
dönüşümü yapar. `capital_ui.py` ortak taramadaki görünümü kullanır; komutlar
mevcut CatalogCart üzerinden işlem motoruna gider. Ayrı codec taraması veya
canlı sahiplik yazımı yoktur. Genişletme bütün açık koordinatları ve özel
yuvaları korur; kaldırmada tam fırkateyn işlem dışa aktarımında saklanır.

`overlay.py` mevcut LivePanel/LiveFleetPanel modelini okur; yeni bellek
erişimi açmaz. Ayrı Qt araç penceresi ve yalnız kayıtlı Ctrl+Shift+F8 mesajını
işleyen native event filter kullanılır. Kapatmada hotkey kaydı bırakılır.
Pencere/kenarlıksız mod hedeflenir; render/DLL enjeksiyonu yapılmaz.

## v0.8 envanter ve koleksiyon

Envanter, donanım, arşiv ve tarif eylemleri aynı CatalogCart üzerinden hazırlanır.
UI adaptörleri ortak disk snapshot kullanır; hedefin kesin slot/tohum/model kimliği ve
eşyanın bütün alanlarının SHA256 fingerprint'i mutasyonda tekrar kontrol edilir.

Envanter mutasyonu yalnız Slots ve aktif aletin Store aynasını değiştirebilir. Kargo
miktarları zorluk/grup tablosuyla sınırlandırılır; teknoloji taşınırken SpecialSlots
korunur. Arşiv gemi kaldırmasını native FleetManager'a devreder; kargo ekzosuite
taşınır ve tam gemi commit öncesi garaja gider. Bütün sabit diziler aynı uzunluktadır.

Bölüm sözleşmeleri ve gelecekteki frontend için [UI geçişi](UI_MIGRATION.md).

## v0.5 ortak tarama

SharedScan tek LiveBackend / ProcessMemory oturumunu para, ayar ve canlı filo
görünümleri için paylaşır. Canlı okuma ve kullanıcı yazımları aynı executor'da
seri çalışır. Kullanıcı eylemi nesli değişirse eski read sonucu çizilmez.
Yazma doğrulamaları cache kullanmaz; kendi taze capture / hash kontrolleri korunur.

DiskScanner her kayıt + metadata imzasını (mtime_ns, boyut) izler; değişen dosyayı
yerel geçici kopyaya alırken hash'leri doğrular, codec ile yalnız bir kez okur.
Aynı decoded player hem filo hem çok amaçlı alet listesine dağıtılır. Cache
çıktıları deep-copy ile döner. Disk okuması ayrı executor'dadır. Okuma hataları
modal istem olmadan durum alanına gider ve tekrar denemede 5 saniye beklenir.

Tk güncellemeleri ana thread'de, future polling ile yapılır. Bir render sonucu
devam eden yazma veya inceleme sonucunu ezmez. Oyun yokken bağlantı sessizce
yeniden denenir. Yenilemeyi kapatma ve normal pencere kapanışı otomatik
bağlanmayı durdurur; geçici ayarların eski geri alma davranışı korunur.

## v0.4 silah koleksiyonu

`WeaponPanel → WeaponBackend → python -m nmsmenu.weapon_cli → weapons.mutate →
mevcut FleetManager transaction motoru`

Silah mutator'ü yalnız Multitools girişine ve aktif alet kaldırılırsa üç aktif
kopyaya yazabilir. Şema anahtarları / sabit dizi uzunluğu korunur. Kesin seçim
slot + seed + filename ile yapılır. Tohum Seed alanındadır; Resource.Seed farklı
amaçlıdır ve görünüm tohumu diye değiştirilmez. Aktif aletin daha güncel
WeaponInventory kopyası ekleme / dışa aktarma için önceliklidir.

FleetManager modülü ayrı CLI sürecinde yüklenip yalnız mutate fonksiyonu bu
komut için bağlanır; mevcut dosyası veya filo kuralları değiştirilmez. stopped,
snapshot, codec eşitliği, kaynak / stage hash doğrulamaları ve tam kayıt restore
aynen korunur. Silinen alet export'u legacy dosya adına ek olarak açıkça
*-removed-multitools.json ismiyle de tutulur. Oyun açıkken sahiplik yazımı yoktur.

İstasyon silah / NPC hasarı kontrolleri uygulanmadı; UI pasif durumunu belirtir.

## v0.3 canlı filo projeksiyonu

`LiveFleetPanel → LiveFleet → canlı capture + taze disk kopyası → fleet.mutate →
GOG codec round-trip → izinli sabit byte diff → LiveBackend.write_checked`

Sabit 12 sahiplik girişi salt okunur kimlik kaynağıdır. Üç envanter dizisi,
öğe / özel yuva vektörleri ve aktif gemi numarası yakalanır. Eski kaynakta
yanlış olan teknoloji dizi offset'i bu build'de `0xAB28` olarak doğrulandı.
Pasif teknolojilerin `Amount=-1` işareti ve boyut dışı eski bitler korunur.

Onarımda yalnız mevcut teknoloji miktarı / hasarı / kurulu bayrağı; genişletmede
yalnız grid maskesi / boyut / kapasite yazılır. Pointer, vektör uzunluğu, eşya
kimliği, konum, model ve sahiplik yazımı yoktur. FleetManager işlem motoru
değiştirilmeden doğrudan yeniden kullanılır. Kopya codec çıktısı hiçbir zaman
DefaultUser'a uygulanmaz; auto/manual dosyalarına yazılmaz.

Offline ve duraklatılmış motor, değişmeyen oturum / aktif gemi ve capture
eşitliği her yazım öncesi kontrol edilir. Kendi yazımları shadow capture'a
işlenir. Hata geri alması pointer / yapı eşitliğini ve beklenen byte'ları
doğrular. Çok alanlı yazım güç kesintisinde atomik değildir; kısmi hata ve geri
alma çakışmaları manifestte kalır. Kullanıcı yeni ilerleme yaptıysa normal geri
alma reddedilir. Bu, tüm kaydı eski zamana döndüren FleetManager.restore'dan farklıdır.

## v0.2 canlı veri yolu

`LivePanel → LiveBackend → ProcessMemory → Windows Read/WriteProcessMemory`

Bu yol FleetManager'dan bağımsızdır. Gemi / envanter işlemleri eski güvenli kayıt
yolunda kalır. Canlı backend önce EXE SHA256 ve yüklenen kod anchor'ını doğrular;
yalnız sabit listeli float32 ayar ve uint32 para alanlarına yazabilir. Keyfi adres
ve kod yaması arayüzü yoktur. ASLR modül tabanıyla çözülür. Oyunun kapanması,
kayıt yuvası değişmesi veya beklenen byte'ların farklılaşması yazmayı durdurur.

Yazım: ön değer oku → eşitliği kontrol et → intent günlüğü → dört byte yaz →
yeniden okuyup doğrula → sonuç günlüğü. Geçici ayarların ilk değerleri ve en son
yazılan byte'ları saklanır; çıkışta hâlâ son yazılan byte'larsa geri alınır.
Para değişiklikleri oyun autosave'iyle kalıcı olabilir; ayrı, koşullu tek adım
geri alma sunulur. Panel hiçbir anda aktif kayıt dosyasına canlı yazmaz.

Süreç erişimi yalnız query / VM read / VM write / VM operation hakları ister;
debug ayrıcalığı, tüm süreç hakları, DLL enjeksiyonu, remote thread veya oyun
duraklatma kullanılmaz. İşletim sistemi erişimi reddederse hata gösterilir.
Mevcut CapsLockFix başlatıcısına dokunulmaz.

Profilin teknik bulguları `NMS-Research` altında tutulur. Bilinmeyen EXE'de
global alanlar veya eski imzalar denenmez. Ana menüde yapılandırma okunabilir;
oyuncu verisi yüklenene kadar para kontrolleri kilitlidir.

## Katmanlar

`Tk arayüz → modül plan üreticisi → backend adaptörü → FleetManager → GOG codec`

Arayüz kayıt JSON alanlarını değiştirmez. Modüller plan üretir. FleetManager
güncel kaydı yedekler, yalnız izinli alanları değiştirir, codec ile yeniden
okuyup JSON eşitliğini doğrular. Başarılı hazırlama canlı kayda yazmaz.
Uygulama öncesinde kullanıcı semantik raporu inceler; panel rapor manifestinin
SHA256 değerini bağlar. Rapor değişirse panel uygulamayı durdurur. Asıl motor
kaynak ve staged dosya hash'lerini de doğrular.

## Bir eylemin yaşam döngüsü

1. UI girdisi → kimlik / profil / hedef kayıt yuvası doğrulaması.
2. Kullanıcıya oyunu kapatma istemi; motor ayrıca NMS süreç kontrolü yapar.
3. Yeniden inspect → UUID ile yeni JSON istek → yeni prepare işlemi.
4. Rapor / plan incelemesi → kullanıcı uygulaması → motor apply.
5. İşlem klasörü / yedek saklama → gerekirse açık kapsamlı restore.

Bir işlem çalışırken ikinci işlem çalışmaz ve panel kapatılamaz. Tk
güncellemeleri ana iş parçacığında gerçekleşir. Panel oyun sürecini sonlandırmaz.
Çok dosyalı yazımın güç kesintisinde tek atomik işlem garantisi yoktur;
bu durumda işlem klasöründeki before yedeği korunur.

## Yeni özellik ekleme sözleşmesi

Her modül için: desteklenen oyun / kayıt sürümü, okunacak alanlar, izinli yazma
yolları, değer sınırları, korunacak veriler, ön koşullar, semantik rapor ve geri
alma kapsamı tanımlanır. Sonra kopya fixture üzerinde izinli fark testi ve gerçek
codec round-trip testi geçer. Canlı kayıtla deney yapmak özellik doğrulaması
yerine geçmez. Yalnız doğrulanan özellik çalıştırılabilir eyleme dönüştürülür.

Filo / envanter / kalkış işlemleri FleetManager üzerinden kalır. Yeni para,
eşya vb. modüller ayrı dosyalarda plan üretir; ilk canlı yazımdan önce motorun
izinli işlem desteği ve testleri genişletilir. Genel amaçlı keyfi JSON alanı
yazma veya rastgele terminal komutu çalıştırma arayüzü eklenmez.

UI özellik listesi `MODULES`, kayıt eylemleri `OPERATIONS`, canlı alanlar
`live.SETTINGS` / `live.CURRENCIES` ile
tanımlanır. Araştırma / plan durumundaki modüller çalıştırılamaz. Yeni oyun
sürümü geldiğinde codec ve şema tekrar doğrulanmadan uyumluluk iddia edilmez.

## Bağımlılık ve dağıtım

Python, PySide6 ve Menu kökündeki entegre `fleet.py` motoru kullanılır.
`FLEET = ROOT`; kataloglar, işlem geçmişi ve garaj aynı kökte çözümlenir.
Codec `codec/libNOM.io.cli.exe` konumundadır; kurucu resmî sürümü hash ile doğrular.
Ayrı FleetManager veya SolarShipFix klasörü gerekmez. Kaynak kontrolü kod, kataloglar, belgeler ve sentetik testleri
içerir. Yerel garaj, geçmiş işlem yedekleri ve inceleme kayıtları Git dışındadır.
