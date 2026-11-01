# Modüler tasarım

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

UI özellik listesi `MODULES`, çalıştırılabilir eylemler `OPERATIONS` ile
tanımlanır. Araştırma / plan durumundaki modüller çalıştırılamaz. Yeni oyun
sürümü geldiğinde codec ve şema tekrar doğrulanmadan uyumluluk iddia edilmez.

## Bağımlılık ve dağıtım

Python standart kütüphanesi + komşu FleetManager ve mevcut codec. İlk Git deposu
Menu kapsamındadır; FleetManager ayrı, mevcut bağımlılıktır. Tam taşınabilir
paket için bu bağımlılığın sürüm / dağıtım modeli ayrıca tasarlanmalıdır.
Kaynak kontrolü yalnız kod / doküman / sentetik testleri içerir.
