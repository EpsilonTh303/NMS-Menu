# No Man’s Sky — Menu

Offline GOG kurulumu için Türkçe masaüstü kontrol paneli. **v0.2 oyun açıkken
çalışan canlı veri kontrolleri içerir; ayrı masaüstü penceresidir.** Python 3.12
ve standart Tkinter kullanır; pip paketi, internet veya oyun enjeksiyonu gerekmez.

## Başlatma

`start.cmd` dosyasına çift tıklayın veya bu klasörde `python main.py` çalıştırın.
Mevcut CapsLockFix oyun başlatıcısını normal şekilde kullanmaya devam edin.
Menu oyunu başlatmaz veya kapatmaz.

## Oyun açıkken kullanım

1. Oyunu normal CapsLockFix başlatıcısıyla açıp kaydınızı yükleyin.
2. Menu'yu açın; **Canlı kontroller → Açık oyuna bağlan** seçin.
3. Units / nanit / quicksilver için yeni miktarı ayraçsız tam sayı girip
   **Miktarı ayarla** seçin. Oyun kaydederse bu değer kalıcı olabilir.
   Para göstergesi yenilenmezse oyun envanterini kapatıp yeniden açın.
4. Alt listeden hız, jetpack, dayanıklılık, yaşam desteği veya kalkan yenilenmesi
   ayarı seçin, yeni değer girip **Oyunda hemen uygula** seçin.
5. **Canlı değerleri yenile** ile yeniden okuyun. Menü otomatik miktar dondurmaz.
6. **Ayarları geri al ve bağlantıyı kes** geçici ayarları özgün değerlerine
   döndürür. Normal pencere kapanışı da bunu yapar. Para otomatik geri alınmaz;
   ayrı **Son para işlemini geri al** düğmesi vardır.

12 canlı yapılandırma alanı ve 3 para birimi desteklenir. Yürüme/koşma, jetpack
itişi/dolumu, dayanıklılık tüketimi/yenilenmesi, beş yaşam desteği tüketim koşulu
ve karakter kalkan yenilenmesi. Dayanıklılık / yaşam desteği tüketim alanlarında
0 tüketim katsayısını sıfırlar; jetpack dolumunu artırmak sınırsız jetpack değildir.
Bu sürüm ölümsüzlük, canlı gemi ekleme veya sınırsız gemi yakıtı sağlamaz.

Canlı yazma yalnız doğrulanmış **179666 GOG EXE hash'i** ve kod kontrolüyle
açılır. Ana menüde para kontrolleri kilitli kalır. Kayıt yükledikten sonra
**Canlı değerleri yenile** seçin. Yeni oyun sürümünde profil yeniden doğrulanmalı.
DLL enjeksiyonu, uzak thread, instruction patch veya canlı kayıt dosyasına yazma
yapılmaz. İşlemler `runtime/live-audit.jsonl` içine byte düzeyinde kaydedilir.

Başka bir araç aynı değeri değiştirdiyse geri alma üzerine yazmaz. Oyun kapandıysa
bağlantıyı kesip yeniden bağlanın. Ani panel sonlanmasında geçici ayarlar oyun
yeniden başlatılana kadar kalabilir. Normal kapanışın hata vermesi durumunda
günlükteki ilk değerler elde kalır; uyuşmazlıklar otomatik ezilmez.

Beklenen komşu klasörler: `../FleetManager` ve `../SolarShipFix`.
Panel tek başına taşınabilir dağıtım değildir. Codec mevcut FleetManager'ın
kullandığı `libNOM.io.cli.exe` dosyasıdır. Kayıt konumu:
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
2. Panelde **Kayıtları yenile** ile doğru kayıt yuvasını seçin.
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
- `tests/test_live.py`: build, oturum, byte eşitliği, günlük ve canlı geri alma testleri.
- `tests/test_safety.py`: kimlik, kargo, işlem yolu, inceleme ve taze plan kontrolleri.
- `runtime/`: üretilen istekler; Git dışında. Asıl yedekler FleetManager'da kalır.

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s ../FleetManager -p test_fleet.py
```

Git deposu yalnız bu klasördedir. Oyun dosyaları, canlı kayıtlar, garaj ve
işlem yedekleri depoya alınmaz. Yerel `main` dalı kullanılır; remote kurulmadı.
