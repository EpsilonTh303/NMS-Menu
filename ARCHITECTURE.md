# Modüler tasarım

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

Python standart kütüphanesi + komşu FleetManager ve mevcut codec. İlk Git deposu
Menu kapsamındadır; FleetManager ayrı, mevcut bağımlılıktır. Tam taşınabilir
paket için bu bağımlılığın sürüm / dağıtım modeli ayrıca tasarlanmalıdır.
Kaynak kontrolü yalnız kod / doküman / sentetik testleri içerir.
