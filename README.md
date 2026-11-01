# No Man’s Sky — Menu

Offline GOG kurulumu için Türkçe masaüstü kontrol paneli. **v0.1 çalışan temel
sürümdür; oyundaki her şeyi kontrol eden bir overlay değildir.** Python 3.12
ve standart Tkinter kullanır; pip paketi, internet veya oyun enjeksiyonu gerekmez.

## Başlatma

`start.cmd` dosyasına çift tıklayın veya bu klasörde `python main.py` çalıştırın.
Mevcut CapsLockFix oyun başlatıcısını normal şekilde kullanmaya devam edin.
Menu oyunu başlatmaz veya kapatmaz.

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
şarj, anlık veya sınırsız yakıt değildir. Para ve diğer planlanan özellikler
henüz uygulanmadı; [ROADMAP.md](ROADMAP.md) kapsamı ve sıralamayı açıklar.

## Kullanım

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
- `tests/test_safety.py`: kimlik, kargo, işlem yolu, inceleme ve taze plan kontrolleri.
- `runtime/`: üretilen istekler; Git dışında. Asıl yedekler FleetManager'da kalır.

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s ../FleetManager -p test_fleet.py
```

Git deposu yalnız bu klasördedir. Oyun dosyaları, canlı kayıtlar, garaj ve
işlem yedekleri depoya alınmaz. Yerel `main` dalı kullanılır; remote kurulmadı.
