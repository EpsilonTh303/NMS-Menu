# Entegre filo motoru

`fleet.py`, Menu kökündeki yedekli kayıt işlem motorudur. Kataloglar ve
tercihler aynı klasörde; codec `codec/libNOM.io.cli.exe` konumundadır.
Ayrı FleetManager veya SolarShipFix kurulumu gerekmez.

Komutları **Menu klasöründen** çalıştırın. Aktif GOG kayıt dizini
`%APPDATA%/HelloGames/NMS/DefaultUser` konumudur. Yeni kayıt düzenlemeleri
için oyunu kaydedip tamamen kapatın; eski planları yeniden kullanmayın.

## İnceleme, hazırlama ve uygulama

```powershell
python fleet.py inspect
```

Çıktıdaki kayıt yuvasını, gemi türünü, tohumu ve yuva kimliğini doğrulayın.
Prosedürel adlar JSON içinde boş olabilir; adı tahmin ederek silme yapmayın.

Her istek için yeni bir JSON plan hazırlayıp `runtime/` altında saklayın.
Örneğin yalnız karakter envanterini genişleten plan:

```json
{"save_slot":1,"actions":[{"op":"max_slots","scope":"exosuit"}]}
```

```powershell
python fleet.py prepare runtime/yeni-istek.json
```

`prepare`, güncel kayıtları yedekler, auto/manual dosyalarını bağımsız işler,
izinli JSON farklarını denetler ve codec ile kodlama/yeniden okuma eşitliğini
doğrular. Bu aşamada canlı kayıt değişmez. Çıktıdaki işlem klasörünün
`manifest.json` raporunu inceleyin, ardından o klasörü kullanın:

```powershell
python fleet.py apply transactions/ISLEM_KLASORU
```

`apply`, oyunun kapalı ve kaynak hash’lerinin yedekle aynı olmasını gerektirir.
Değişen kaynak, ikinci uygulama ve belirsiz seçim reddedilir. Yazma hatasında
o işlemin kopyaları geri yüklenir. İşletim sistemi/elektrik kesintisine karşı
bütün dosyaları kapsayan tek atomik işlem garantisi yoktur; `before/` yedeği korunur.

## Plan eylemleri

Yük gemisi/fırkateyn sepet işlemleri `python -m nmsmenu.catalog_cli prepare PLAN.json`
üzerinden aynı `fleet.py` motorunu kullanır. Hazırlanan işlemi inceleyip
`python fleet.py apply transactions/ISLEM` ile uygulayın. `freighter_create`
deneyseldir: `experimental:true`, `model` (Normal/Capital/Pirate), `name`,
64 bit hex `seed`, `home_seed`, `crew_seed` gerekir. Yalnız boş sahiplik/NPC,
boş envanter ve yük gemisi üssü bulunmayan kayıt kabul edilir. Üs, oda,
teknoloji, görev veya spawn konumu oluşturulmaz. Oyun içi çağırma doğrulaması
henüz tamamlanmadı. Mevcut geminin üstüne yazma ve canlı ekleme yoktur.

| Eylem | Önemli alanlar |
| --- | --- |
| `add` | `profile`; isteğe bağlı `name`, `seed`, `class` |
| `remove` | Kesin `selector`, `preserve_cargo:true` |
| `repair_ship` | Kesin `selector`; gerektiğinde `compatibility_core` / `activate` |
| `equip` | Kesin `selector`, `loadouts.json` içinden `profile` |
| `max_slots` | `scope: "exosuit"` veya `"ships"` |
| `auto_recharge` | `scope: "ships"` |
| `garage_import` | Tam garaj `id`; değiştirme için `replace` seçicisi |

Seçici alanları `name`, `seed`, `type`, 1’den başlayan `slot` değerleridir;
birlikte kullanılabilir. Seçim tam olarak bir mevcut gemiyle eşleşmelidir.
Son gemi silinmez. Kargo korunacaksa ekzosuit kapasitesi yeterli olmalıdır.
Çıkan geminin tam verisi ve teknolojileri işlem yedeklerinde saklanır.

Aktif gemiyi değiştiren yollar kayıtlı istasyon konumunu gerektirir; motor
konumu veya spawn dönüşümünü değiştirmez. Normal eklemede mevcut aktif gemi korunur.

Gemi profilleri `catalog.json`, donanımlar `loadouts.json`, estetik tercihler
`preferences.json` içindedir. Özel görünüm verileri `ship-references/` altında
çözülür. Profil referansları katalog içindeki kaynak alanlarında yer alır.

## Kapasite ve donanım

12 aktif gemi sınırı kaldırılmaz; sahiplik dizileri genişletilmez. Karakter
120 kargo/60 teknoloji; gemide doğrulanmış tür kapasitesi kullanılır.
Mevcut eşya konumları ve süperşarjlı yuvalar korunur; sığmayan işlem durur.

Donanım kurulumu var olan teknolojiyi sökmez veya taşımaz; eksik parçaları
uygun boş yuvalara ekler. Prosedürel yükseltme ailelerinin modül sınırı
kontrol edilir. En yüksek rastgele istatistik veya belirli DPS garanti edilmez.
Kalkış otomatik şarjı `UT_LAUNCHCHARGE` oyun teknolojisidir; anında sınırsız yakıt değildir.

## Harici garaj

```powershell
python fleet.py garage-snapshot --save-slot 1
python fleet.py garage-list
```

Garaj, tam gemi/kargo/teknoloji/model/görünüm kopyalarını içerik SHA-256
kimliğiyle `garage/` altında saklar. Snapshot gemiyi oyundan kaldırmaz ve
canlı kayda yazmaz. Yüklerken checksum ve kayıt sürümü doğrulanır.

```json
{"save_slot":1,"actions":[{"op":"garage_import","id":"TAM_64_KARAKTER_GARAJ_ID"}]}
```

Dolu filoda değiştirilecek gemi açıkça belirtilir:

```json
{"save_slot":1,"actions":[{"op":"garage_import","id":"TAM_64_KARAKTER_GARAJ_ID","replace":{"slot":3,"seed":"DOGRULANMIS_TOHUM"}}]}
```

Değiştirmede çıkan tam gemi, canlı yazımdan önce garaja aktarılır. Kargosu
ve teknolojisi o gemiyle arşivde kalır; gelen geminin içeriği korunur.
Harici garaj aktif gemi kapasitesini artırmaz.

## Geri alma

```powershell
python fleet.py restore transactions/ISLEM_KLASORU
python fleet.py restore-last
```

Geri alma, ilgili işlemden **önceki tam kayıt durumuna** döner. O zamandan
sonraki ilerleme eski kayıtta yoktur; geri almadan önce güncel kayıt ayrıca
yedeklenir. Yalnız uygulanmış işlemler geri alınabilir. `Son-Islemi-Geri-Al.cmd`
aynı motorun `restore-last` komutunu kullanıcı onayıyla çağırır.

Mevcut kurulumdan taşınan eski Solar yedekleri `runtime/legacy-solar/` altında
korunur. Oradaki `Solar-Oncesine-Don.cmd`, daha eski **1 Kasım 2026 16:46**
kayıt durumuna döner ve yeni durumu ayrıca yedekler; güncel işlem geri alma
komutunun yerine kullanılmamalıdır. Eski `prepare_solar.py` yeni isteklerde çalıştırılmaz.

## Doğrulama ve bağımlılıklar

```powershell
python tools/install_codec.py --check
python -m unittest discover -s tests
python -m unittest test_fleet
```

Son komut yalnız yerel tarihsel inceleme kayıtları varsa 13 ek regresyon testi
çalıştırır; bu özel kayıtlar Git’e dahil edilmez. Diğer testler sentetiktir.
Codec sürümü ve hash’i [codec/manifest.json](codec/manifest.json) içinde,
kurulum ve üçüncü taraf kaynakları [codec/README.md](codec/README.md) içindedir.
