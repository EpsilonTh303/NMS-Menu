# No Man’s Sky — Menu

## Kurulum ve doğrulama

Windows x64 ve Python 3.12 (Tkinter dahil) gerekir. İlk kurulumda `setup.cmd`
çalıştırın; PySide6 bağımlılıkları yalnız yerel `vendor/` klasörüne indirilir.
Ardından `start.cmd` ile açın. Kurulumdan sonra internet gerekmez.

Kontrol paneli ve filo işlem motoru aynı depodadır:

```text
oyun-klasörü/
  Menu/           # arayüz + fleet.py, catalog.json, loadouts.json, preferences.json
  SolarShipFix/   # libNOM.io.cli.exe; kayıt okuma/kodlama bağımlılığı
  Binaries/      # NMS.exe; yalnız canlı kontroller için
```

Filo motorunun kullanımı [FLEET_ENGINE.md](FLEET_ENGINE.md) içindedir.
Codec dosyası hâlâ `../SolarShipFix/libNOM.io.cli.exe` konumundan alınır.
Oyun, codec ikilileri, kullanıcı kayıtları, `transactions/`, `garage/`,
`inspection*/`, `runtime/` ve `vendor/` depoya dahil edilmez.
Sentetik testler kardeş FleetManager klasörü veya oyun kaydı gerektirmez.

Menu klasöründe son kontroller:

```powershell
python -m nmsmenu.i18n check
python -m unittest discover -s tests
git diff --check
```

116 sentetik test; dil dosyaları, sunum bağlamaları, entegre motor yolları ve işlem korumaları doğrulandı.
Bu testler oyun kayıtlarına yazmaz. Qt üzerinden canlı yazımın oyun içi
uçtan uca doğrulaması bu sürüm için yapılmadı.

Yerel inceleme kopyaları mevcutsa `python -m unittest test_fleet` ek 13 tarihsel
motor testini çalıştırır. Bu özel kayıtlar dağıtılmadığından temiz klonda ilgili
test sınıfı atlanır. Taşıma kanıtları ve eski değişen dosyaların kopyaları
`runtime/fleet-integration/` altındadır; işlem yedekleri `transactions/`, tam
gemi koleksiyonu `garage/` konumunda korunur.

## Ayarlar ve dil dosyaları

Qt görünümündeki **Ayarlar → Arayüz dili** seçimi anında uygulanır. Türkçe,
English, Русский ve Deutsch desteklenir. Seçim `runtime/ui-settings.json`
dosyasında hatırlanır; oyun kayıtları ve oyun dili değiştirilmez.
Doğrudan açmak için `python main.py --settings` kullanın.

Bütün çeviriler **her dil için ayrı** UTF-8 JSON dosyasında, `locales/`
klasöründedir: `tr.json`, `en.json`, `ru.json`, `de.json`. Türkçe kaynak cümle
sabit anahtardır; sağındaki değer ekranda gösterilir. Türkçe ifadeyi düzeltirken
anahtarı koruyup yalnız değeri değiştirebilirsiniz. Çeviri dosyalarını Luna
ajanları hazırladı; Türkçe metinler de Luna tarafından gözden geçirildi.

Yeni dil için bir JSON ekleyin; kodda dil listesi değiştirmek gerekmez.
Örneğin `python -m nmsmenu.i18n add fr --name Français` komutu `fr.json`
dosyasını bütün anahtarlarıyla hazırlar. `"_meta": {"name": "Français"}`
alanı dilin seçim listesindeki adıdır. Boş çevirileri doldurup Ayarlar'da
**Dil dosyalarını yenile** düğmesine basın. Yeni dosyalar Ayarlar sekmesi
açıldığında da listelenir. Eksik/boş çeviriler Türkçeye döner; durum, çeviri
kapsamı sayacından görülebilir.

Yeni metin ekleme akışı:

1. Kaynak Türkçe metni UI'da kullanın. Yeni Qt metinlerini `self.t("Metin")`
   veya `t("Metin")` ile işaretleyin. Mevcut Tk denetleyicilerindeki metinler
   sunum katmanında çevrilir; seçimler özgün değer/indekslerle çalışır.
2. `python -m nmsmenu.i18n sync` çalıştırın. Yeni anahtarlar `tr.json` içine,
   diğer dillere de boş değerlerle eklenir. Mevcut çeviriler ve elle eklenen
   anahtarlar korunur. İsterseniz JSON anahtarlarını elle de ekleyebilirsiniz.
3. Dil JSON'larındaki değerleri doldurun. `{v0}`, `{v1}` gibi değişkenleri
   aynen koruyun. `python -m nmsmenu.i18n check` eksik çevirileri ve değişken
   hatalarını dosya/anahtar bazında listeler.

Gemi/alet adları, tohumlar, eşya ID'leri, JSON raporları ve kayıt dosyası
adları çeviri amacıyla değiştirilmez. Oyun kataloglarındaki özel adlar ayrıca
oyun içi metinlerin tam yerelleştirmesi değildir. `--classic` eski Türkçe
Tk görünümüdür; dil seçimi Qt sunumunda desteklenir.

## Referans tasarımı / Qt arayüzü

`start.cmd` artık PySide6/Qt görünümünü açar. Koyu uzay teması, referanstan
alınan üst görsel, mercan sekmeler, yuvarlatılmış paneller ve çizilen envanter
hücreleri kullanılır. Varsayılan ekran envanterdir. `--fleet`, `--weapons`,
`--catalog` seçenekleri korunur. Dar ekranlarda bölüm kaydırılır.

Sekme/düğme simgeleri ve sayaç kartları yerel `nmsmenu/icons.py` vektör
çizimlerini kullanır; harici ikon fontu gerekmez. Otomatik bağlantı anahtarı
gerçek checkbox durumunu, sayı okları özgün Spinbox sınırlarını kullanır.
Bağlantı noktası yalnız denetleyici bağlı ve güncel dediğinde yeşildir.
Boş açık yuvalar +, eşya listeleri renkli kaynak simgeleriyle gösterilir.

`python main.py --classic` önceki Tk görünümünü açar. Qt sunumu, gizli Tk
denetleyicilerinin değişkenlerini ve özgün komutlarını kullanır; kayıt ve bellek
işlemlerini yeniden uygulamaz. Hazırlama, rapor inceleme, kilitli apply,
hash/codec/yedek kontrolleri aynı denetleyicilerden geçer. Canlı yazım bu
görünümde oyun içinde ayrıca denenmedi; görsel doğrulama ve bağlama testleri
kayıt değişikliği yapmadan yürütülür.

PySide6 yalnız `vendor/` içine kuruludur. Yeniden kurulum:
`python -m pip install --target vendor -r requirements-qt.txt`.
Görsel dosyası `assets/reference-banner.png`, kaynak `nmsmenu/qt_ui.py`.
Arayüz adaptör testleri: `python -m unittest discover -s tests -p test_qt_ui.py`.


Offline GOG kurulumu için Türkçe masaüstü kontrol paneli. **v0.8 oyun açıkken
çalışan canlı veri kontrolleri içerir; ayrı masaüstü penceresidir.** Python 3.12
ve yerel PySide6/Qt görünümünü kullanır; işlem denetleyicileri Tk katmanında
korunur. Kurulumdan sonra internet veya oyun enjeksiyonu gerekmez.

## Başlatma

`start.cmd` dosyasına çift tıklayın veya bu klasörde `python main.py` çalıştırın.
Mevcut CapsLockFix oyun başlatıcısını normal şekilde kullanmaya devam edin.
Menu oyunu başlatmaz veya kapatmaz.

## Otomatik ortak bağlantı ve tarama

Menu açılınca bağlantı kendiliğinden kurulur; `--connect` artık gerekli değildir
(eski komutlar için kabul edilir). Bölüm başına ayrı okuma düğmeleri kaldırıldı.
Üstteki **Tümünü yenile** bütün bölümleri ortak veriden günceller.

- Para / canlı ayarlar ve canlı filo yaklaşık 2 saniyede bir tek süreç bağlantısı
  üzerinden okunur. Oyun sonlanırsa durum gösterilir, yeniden açılınca tekrar
  bağlanılır. Ana menüde oyuncu kontrolleri kilitli kalır.
- Filo ve silah **disk listesi** aynı kayıt çözümlemesini paylaşır. Her değişen
  dosya bir kez okunur; değişmeyen kayıt tekrar codec'e gönderilmez. Auto/manual
  farklı dosyalar olarak korunur. Uzun okuma ayrı arka planda çalışır.
- Garaj ve işlem geçmişi de aynı ortak sonuçla otomatik dolar. Yeni transaction
  veya garaj kaydı listeleri güncellerken değişmeyen oyun kaydı tekrar çözülmez.
- Testte canlı filo hızlıca geldi; iki disk kaydının ilk okumasıyla bütün
  listelerin dolması yaklaşık 18.4 saniye sürdü. Silah koleksiyonu disk görünümüdür;
  oyun henüz kaydetmediyse o ilerlemeyi anlık bellek verisi gibi göstermez.
- Otomatik yenileme listelerdeki seçimi ve girilen hedef miktarları korur.
  Bir yazma işlemi sırasında canlı okuma aynı işçide sıraya girer; eski sonuç
  yeni yazım sonucunun üzerine çizilmez.
- Üstteki otomatik bağlantı kutusunu kapatarak yenilemeyi durdurabilirsiniz.
  **Ayarları geri al ve bağlantıyı kes** otomatik yeniden bağlanmayı da durdurur.

İşlem hazırlama yine her istek için yeni kaynak / plan / codec doğrulaması yapar.
Ortak görüntü cache'i yazma sırasında doğrulama veya yedek yerine kullanılmaz.

## Katalog ve toplu ekleme (0.7)

**Katalog / toplu ekle** sekmesi: 149 teknoloji, 49 çok amaçlı alet modeli/tohum seçeneği,
80 gemi profili/tohum seçeneği ve ortak taramadan gelen harici garaj. `python main.py --catalog`
ile doğrudan açılır. Utopia Speeder öne çıkar; Squid varsayılan olarak gizlidir.

1. Disk kaydını, içerik türünü ve teknoloji hedefini seçin. Arama isim veya ID ile çalışır.
2. Birden çok satır seçip sepete ekleyin. Uygunluk filtresi hedef dışındaki teknolojileri eler.
3. Sepeti inceleyin, oyunda kaydedip oyunu tamamen kapatın ve yeni plan hazırlayın.
4. Semantik raporu inceleyip uygulayın. Kaynak hash, yedek ve codec round-trip kontrolü zorunludur.

**80 / 49 sayıları oyundaki toplam gemi veya silah türü sayısı değildir.** 12 benzersiz alet model yolu
ve 37 yerel ödül tohumu vardır. Gemi listesine 70 yerel ödül modeli/tohum profili eklendi.
Avcı, nakliye, kaşif, mekik ve Solar varyantları; Horizon Vector NX, Golden Rasamama S36
ve Vintage Interceptor dahil. Özgün ödül sınıfı/istatistikleri yerine editörün S sınıfı temel
donanımı kullanılır. Ödül hakkı veya sefer tamamlama durumu değiştirilmez.

Aile filtresi, seçili içerik ayrıntıları ve kaynak bağlantıları bulunur. **Tür rehberi**
Living Ship, The Wraith, Corvette ve büyük filo gemilerinin destek durumunu açıklar;
bu kayıtlar eklenebilir seçenekler gibi gösterilmez. Teknoloji açıklamaları yerel dil
tablolarından gelir. Güncel araştırma: [katalog kaynakları](NMS-Research/catalog-expansion-179666.md).

Alet modelleri kaynak aletin sınıfını, donanımını ve yuvalarını kullanır; model/tohum
atanır. Hazır ödül tohumu varsa varsayılan olarak kullanılır; rastgele tohum ayrıca seçilebilir.
Kaynak ve aktif alet korunur. Gemi profilleri boş yer ister; yeni tohum seçeneği
aynı profilden farklı tohumlu kopya oluşturabilir. Görünümün benzersizliği garanti edilmez.
Teknolojiler ilk boş geçerli yuvaya kurulur, mevcut teknoloji tekrar kurulmaz; yeterli yer
yoksa hazırlama durur. Bu işlem kendiliğinden yuva açmaz. 12 gemi ve 6 alet sınırı korunur.

Katalog oyun açıkken görüntülenebilir; sahiplik ve teknoloji kurulumu **oyun kapalıyken**
uygulanır. Liste ortak taramayı kullanır. Bütün 149 teknoloji için tek tek oyun içi test
yapılmadı; katalog yerel tablodan türetilir ve uyumluluk kuralları uygulanır.

Yeni arayüz için [servis sınırları](UI_MIGRATION.md) ve [veri kaynağı](data/README.md).

## Envanter, donanım ve yerleşik arşiv (0.8)

Doğrudan `python main.py --inventory` veya **Katalog / toplu ekle → Envanter / donanım / arşiv**.
Bütün listeler aynı ortak taramanın disk görüntüsünü kullanır. Oyun açıkken görüntüleme,
oyun kapalıyken yeni plan / uygulama akışı korunur.

- **1100 eşya / madde:** katalogda isim, ID veya bazı yaygın Türkçe adlarla ara; miktar ve
  ekzosuit/gemi hedefi seç. Önce uyumlu yığınlar doldurulur, kalanı boş yuvalara bölünür.
  Yığın sınırı yerel High/Normal/Low zorluk, envanter grubu ve eşya çarpanından hesaplanır.
  Görev, yaratık yumurtası, görünüm hakkı ve inşa parçası sınıfları genel ekleme listesi değildir.
- **Envanter ızgarası:** eşya seç, hedef envanter ve 1 tabanlı X/Y koordinatı seç;
  taşı, yığını böl, miktarı ayarla veya yığınları birleştir. Dolu/kapalı yuvanın üzerine yazılmaz.
  Teknoloji aynı envanter içinde taşınabilir; süperşarjlı yuvaların yerleri korunur.
  Hedefler arasında yalnız desteklenen normal kargo taşınır. Miktar sıfırlama / silme yoktur.
- **5 hazır donanım seti:** ekzosuit keşif, alet madencilik/tarama, alet Neutron Cannon,
  gemi keşif ve gemi Infra-Knife. Mevcut teknoloji sökülmez; eksikler kurulur.
  Kendi sabit teknoloji setini de yerel menüye kaydet. Prosedürel yükseltmeler setlere aktarılmaz.
- **Yerleşik arşiv:** 18 gemi ve 18 alet. Gemi kargosu ekzosuite taşınır, yer yoksa işlem durur;
  outgoing tam gemi apply öncesinde ayrıca harici garaja alınır. Son gemi/aleti korur.
  Geri alma boş aktif yuva ister; 12 aktif gemi / 6 alet sınırı değişmez. Aktif gemi için
  istasyonda kaydedilmiş olmalı. Ortak model aletin ailesi otomatik belirlenemiyorsa doğru
  Pistol/Rifle/Alien/Pristine ailesini kullanıcı seçer; özel modeller otomatik tanınır.
- **Tarif öğren:** katalogda seçili sabit teknoloji veya üretilebilir ürünü sepete ekler.
  KnownTech/KnownProducts güncellenir; görev ve sefer bayrakları topluca değiştirilmez.
- **Favoriler / son kullanılanlar:** yerel menü tercihleridir. Donanım setleriyle birlikte
  `runtime` altında saklanır; Git'e veya oyun kaydına eklenmez.

Her düğme önce **ortak sepete** işlem ekler. Ardından **Sepet ve işlem raporu → Yeni planı
hazırla → raporu incele → uygula**. En fazla 256 işlem; sepet değişirse eski rapor geçersizdir.
Liste değişmiş bir eşya/alet seçicisiyle yazma reddedilir. Tam kayıt geri alma işlem öncesinin
bütün ilerlemesine döner; daha yeni durum ayrıca yedeklenir.

[0.8 doğrulama ve veri kaynakları](NMS-Research/workbench-179666.md).

## Silah koleksiyonu: çok amaçlı alet ekle / kaldır

**Bu bölüm oyun kapalıyken çalışır.** Canlı silah sahipliği ve istasyon savaş
modu henüz desteklenmiyor. Liste oyun açıkken salt okunur görüntülenebilir.

1. **Silah koleksiyonu** bölümünde ortak listenin dolmasını bekleyin. Kaydı seçip aleti
   yuva / tohum kimliğiyle doğrulayın; prosedürel isimler boş olabilir.
2. Yeni alet için mevcut bir aleti kaynak seçin, ad girin ve **Seçili aletin
   donanımıyla yeni alet** planını hazırlayın. Kaynağın model ailesi, sınıfı,
   teknolojileri ve yuvaları kopyalanır; farklı prosedürel tohum kullanılır.
   Aktif alet değişmez. Ayrı model seçimi için yeni Katalog bölümünü kullanın.
3. Kaldırmak için tam kimliği doğrulanmış aleti seçip kaldırma planını hazırlayın.
   Tüm veri / donanım işlem klasöründe `*-removed-multitools.json` olarak saklanır.
   Motorun uyumluluk amaçlı `*-removed-ships.json` kopyası da aynı dışa aktarımı içerir.
4. Oyunda kaydedip tamamen kapatın; yeni planın raporunu inceleyip uygulayın.
   Son alet silinemez. Aktif alet kaldırılırsa raporda belirtilen kalan alet
   otomatik seçilir; aktif envanter, yerleşim ve model / tohum kopyaları senkronlanır.

6 sabit aktif giriş ve diğer sahip olunan aletler korunur. Hazırlama, auto/manual
dosyalarını ayrı ayrı düzenler; her dosyada seçici tek aletle eşleşmelidir. Değişen
kaynak dosyaları, codec uyuşmazlığı ve tekrarlanan apply reddedilir.
**Tam kayıt geri alma** ilgili işlemden önceki iki kayda döner; daha sonraki tüm
ilerleme eski kayıtta bulunmaz. Mevcut durum ayrıca yedeklenir.

İstasyonda silah çıkarma / ateş etme ve NPC'lere hasar seçenekleri henüz
doğrulanmadığı için pasiftir. [Araştırma notları](NMS-Research/weapons-179666.md)
mevcut bulguları ve açık kalan işleri açıklar.

## Oyun açıkken kullanım

1. Oyunu normal CapsLockFix başlatıcısıyla açıp kaydınızı yükleyin.
2. Menu'yu açın; **Canlı kontroller** bölümünde otomatik bağlantıyı bekleyin.
3. Units / nanit / quicksilver için yeni miktarı ayraçsız tam sayı girip
   **Miktarı ayarla** seçin. Oyun kaydederse bu değer kalıcı olabilir.
   Para göstergesi yenilenmezse oyun envanterini kapatıp yeniden açın.
4. Alt listeden hız, jetpack, dayanıklılık, yaşam desteği veya kalkan yenilenmesi
   ayarı seçin, yeni değer girip **Oyunda hemen uygula** seçin.
5. Değerler otomatik yenilenir; gerekirse üstteki **Tümünü yenile** seçin. Menü otomatik miktar dondurmaz.
6. **Ayarları geri al ve bağlantıyı kes** geçici ayarları özgün değerlerine
   döndürür. Normal pencere kapanışı da bunu yapar. Para otomatik geri alınmaz;
   ayrı **Son para işlemini geri al** düğmesi vardır.

12 canlı yapılandırma alanı ve 3 para birimi desteklenir. Yürüme/koşma, jetpack
itişi/dolumu, dayanıklılık tüketimi/yenilenmesi, beş yaşam desteği tüketim koşulu
ve karakter kalkan yenilenmesi. Dayanıklılık / yaşam desteği tüketim alanlarında
0 tüketim katsayısını sıfırlar; jetpack dolumunu artırmak sınırsız jetpack değildir.
Bu sürüm ölümsüzlük, canlı gemi ekleme veya sınırsız gemi yakıtı sağlamaz.

## Canlı filo: oyun kapanmadan onarım ve gemi yuvaları

1. Oyunda kayıt içine girin. **Esc ile duraklatma menüsünü açın**; hazırlama,
   uygulama ve geri alma boyunca bu menüde kalın. Motorun duraklatma bayrağı
   ayrıca kontrol edilir; multiplayer etkinse işlem açılmaz.
2. **Canlı filo → Oyuna bağlan / canlı filoyu yenile** seçin. Liste doğrudan
   bellekten okunur; seçimi gemi yuvası + tür + tohum ile doğrulayın.
3. **Seçili gemiyi onar / şarj et** veya **Tüm gemilere maksimum yuva** için
   plan hazırlayın. İkinci seçenek bütün mevcut gemileri kapsar.
4. İşlem, taze GOG kayıt kopyasındaki canlı envanter projeksiyonunu FleetManager
   kurallarıyla düzenler. Gerçek codec yeniden okuma eşitliği doğrulanır.
   Bu aşamada canlı kayıt veya belleğe yazılmaz. Yeni gemi henüz kayda geçmemişse
   önce oyunda kaydetmeniz istenir; oyunu kapatmanız gerekmez.
5. Raporu inceleyip **İncelediğim canlı filo planını uygula** seçin. Her yazımdan
   önce duraklatma, oturum, gemi kimliği, envanter başlıkları ve içerikleri
   kontrol edilir. Değişiklik varsa yeni plan gerekir.
6. **Son canlı filo işlemini geri al**, ilgili filo verisi hâlâ aynıysa yalnız
   yazılan alanları geri döndürür. Oyun normal şekilde kaydederse değişiklikler
   kalıcı olabilir. Envanter görünümü gerekiyorsa kapatılıp açılabilir.

Kargo öğelerine, teknoloji kimliklerine / konumlarına, vektör pointer'larına,
sahiplik dizilerine ve gemi modellerine yazılmaz. Açık yuvalar azaltılmaz.
Geçici yapılandırma ayarlarından farklı olarak filo işlemleri pencere kapanırken
otomatik geri alınmaz. Uygulama anındaki bellek görüntüsü, taze kaynak kopyası,
staged codec çıktısı ve manifest `runtime/live-fleet/<işlem>` altında tutulur.
Bu kaynak .hg yedeği son disk kaydının zamanına aittir; canlı ilerlemenin tamamını
içerdiği iddia edilmez. JSON projeksiyonu yalnız filo envanterlerini canlandırır.

**Canlı gemi ekleme / silme, model / tohum değiştirme, gemi değiştirme ve yeni
teknoloji ekleme henüz desteklenmiyor.** Bunlar oyun thread'inde sahiplik,
kaynak tahsisi ve spawn / mesh yenileme işlemlerinin doğrulanmasını gerektirir.

Canlı yazma yalnız doğrulanmış **179666 GOG EXE hash'i** ve kod kontrolüyle
açılır. Ana menüde para kontrolleri kilitli kalır. Kayıt yükledikten sonra
otomatik yenilemeyi bekleyin. Yeni oyun sürümünde profil yeniden doğrulanmalı.
DLL enjeksiyonu, uzak thread, instruction patch veya canlı kayıt dosyasına yazma
yapılmaz. İşlemler `runtime/live-audit.jsonl` içine byte düzeyinde kaydedilir.

Başka bir araç aynı değeri değiştirdiyse geri alma üzerine yazmaz. Oyun kapandıysa
bağlantıyı kesip yeniden bağlanın. Ani panel sonlanmasında geçici ayarlar oyun
yeniden başlatılana kadar kalabilir. Normal kapanışın hata vermesi durumunda
günlükteki ilk değerler elde kalır; uyuşmazlıklar otomatik ezilmez.

Filo motoru Menu içine entegredir; ayrı FleetManager klasörü gerekmez.
Kayıt codec'i `../SolarShipFix/libNOM.io.cli.exe` dosyasıdır. Kayıt konumu:
`%APPDATA%/HelloGames/NMS/DefaultUser`.

## Şu anda çalışanlar

- Taze kayıt ve filo görünümü; 1–15 oyun kayıt yuvası seçimi.
- Katalogdan gemi ekleme (varsayılan tercih Utopia Speeder).
- Tür + tohum + yuva ile seçili gemiyi kaldırma; kargoyu koruma.
- Seçili gemiyi onarma / şarj etme ve doğrulanmış donanım paketi kurma.
- Karakter / mevcut gemi envanterini motorun doğruladığı sınırlara genişletme.
- Gemilere normal kalkış otomatik şarj teknolojisi ekleme.
- Harici garaja tam gemi arşivi; listeleme, boş yuvaya alma veya gemi değiştirme.
- Yeni işlem hazırlama, semantik rapor inceleme, uygulama ve tam kayıt geri alma.

Aktif gemi sınırı **12**. Harici garaj bu sınırı artırmaz. Normal otomatik
şarj, anlık veya sınırsız yakıt değildir. [ROADMAP.md](ROADMAP.md) kalan kapsamı
ve [NMS-Research](NMS-Research/README.md) doğrulanan canlı bulguları açıklar.

## Oyun kapalıyken filo / kayıt düzenleme

1. Oyunda kaydedin ve oyunu tamamen kapatın.
2. Ortak listeden doğru kayıt yuvasını seçin; gerekirse üstteki **Tümünü yenile** seçin.
3. Gerekiyorsa gemiyi tür / tohum / yuva ile doğrulayarak seçin.
   Prosedürel adın kayıtta bulunmaması normaldir; panel ad tahmini yapmaz.
4. Eylem ve gerekiyorsa katalog / donanım / garaj kaydını seçin.
5. **Planı hazırla**: canlı kayıt değişmez. Her isteğe yeni plan ve işlem üretilir.
6. Rapordaki planı, değişen yolları ve sonuç filosunu inceleyin.
7. **İncelediğim işlemi uygula**: oyun kapalı ve kaynak hash'leri aynıysa yazılır.

Görünüm auto/manual çiftinin diskte en yeni olanını gösterir. İşlem motoru
bu iki kaydı ayrı ayrı düzenler; birini diğerinin üzerine kopyalamaz.
Seçilen gemi diğer kayıtta aynı kimlikle bulunmazsa hazırlama reddedilir.
Kaldırmada kargoya yer yoksa veya son gemi silinecekse motor işlemi durdurur.
Garaj değişiminde çıkan geminin kargo ve teknolojisi tam arşivle korunur.

**Geri alma:** geçmişten bir `applied` işlem seçip raporunu inceleyin.
Geri alma o işlem öncesindeki tam oyun kayıtlarına döner; aradaki ilerleme
eski kayıtta yoktur. Güncel kayıt ayrıca işlem klasörüne yedeklenir.
Geri alınmış işlemler yeniden geri alınamaz. Yeni istek için daima yeni plan gerekir.

## Yapı ve doğrulama

- `nmsmenu/ui.py`: masaüstü arayüz; uzun işlemler tek arka plan işçisinde.
- `nmsmenu/modules.py`: özellik kayıt defteri ve izinli plan üreticileri.
- `nmsmenu/backend.py`: mevcut FleetManager'a subprocess adaptörü.
- `nmsmenu/live.py`: build'e bağlı canlı ayar / para işlemleri ve geri alma.
- `nmsmenu/winmem.py`: dar kapsamlı Windows süreç bellek adaptörü.
- `nmsmenu/live_ui.py`: oyun açıkken kullanılabilen kontrol sekmesi.
- `nmsmenu/live_fleet.py`: FleetManager kurallarıyla taze canlı envanter projeksiyonu.
- `nmsmenu/live_fleet_ui.py`: canlı filo inceleme / uygulama / koşullu geri alma sekmesi.
- `nmsmenu/weapons.py`: sabit alet sahipliği ve aktif kopya senkronizasyonu.
- `nmsmenu/weapon_cli.py`, `weapon_backend.py`, `weapon_ui.py`: silah işlemleri,
  mevcut FleetManager transaction motoru ve masaüstü sekmesi.
- `tests/test_live.py`: build, oturum, byte eşitliği, günlük ve canlı geri alma testleri.
- `tests/test_safety.py`: kimlik, kargo, işlem yolu, inceleme ve taze plan kontrolleri.
- `fleet.py`, `catalog.json`, `loadouts.json`, `preferences.json`: entegre filo motoru.
- `FLEET_ENGINE.md`: motorun işlem ve geri alma belgeleri.
- `transactions/`, `garage/`: taşınan işlem yedekleri ve tam gemi arşivi; Git dışında.
- `runtime/`: üretilen istekler ve taşıma doğrulama manifesti; Git dışında.

```powershell
python -m unittest discover -s tests -v
python -m unittest test_fleet
```

Git deposu yalnız bu klasördedir. Oyun dosyaları, canlı kayıtlar, garaj ve
işlem yedekleri depoya alınmaz. Yerel `main` dalı kullanılır; remote kurulmadı.


0.7, artık entegre `fleet.py` codec girişinde Unicode korumasını da düzeltir.
Bu çalışma alanında uygulanmıştır. Ayrı bir kopyaya taşırken aynı düzeltmenin diff'i
`patches/fleet-codec-unicode.patch` içindedir. Round-trip eşitliği yine zorunludur.

0.8 yerleşik arşivi dolu 12 gemilik filoda da kullanabilmek için entegre motorun
boş gemi şablonuna aynı şemadaki boş arşiv Ownership girişini yedek kaynak ekler.
Düzeltme bu çalışma alanında uygulanmıştır; taşınabilir diff `patches/fleet-archive-template.patch`.
