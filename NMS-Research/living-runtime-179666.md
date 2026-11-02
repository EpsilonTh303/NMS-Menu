# Living Ship ve runtime ekleme araştırması

2 Kasım 2026; GOG 179666, SHA256
`a91e3df36b049c4f5dbc6784a2943b803333bf8e4a23b4d165d1ab3cf83d4ffe`.

## Organik profil

[Hello Games](https://www.nomanssky.com/living-ship-update/) organik gemilerin
ayrı teknoloji kullandığını belirtir. Model ve 10×12 / 10×6 üst boyutları
[NMSE StarshipLogic.cs](https://github.com/vectorcmdr/NMSE/blob/6e0fd3a3c92456ac7241e106856ca8be76b2e46b/Core/StarshipLogic.cs)
ile karşılaştırıldı. Kurulu `NMSARC.EntitySceneMBIN.pak` içindeki model kaydı
doğrudan doğrulandı: `MODELS/COMMON/SPACECRAFT/S-CLASS/BIOPARTS/BIOSHIP_PROC.SCENE.MBIN`.

Yerel teknoloji tablosunda LAUNCHER_SPEC, SHIPJUMP_SPEC, HYPERDRIVE_SPEC,
SHIELD_ALIEN, SHIPGUN_ALIEN, SHIPLAS_ALIEN ve CHARGER_ALIEN mevcut. Profil
yalnız bu organik çekirdeği kullanır. İstatistikler editör profilidir; doğal
üretim veya bir sefer ödülünün birebir kopyası olduğu iddia edilmez.

Taze GOG kaydının ayrı kopyasında yeni giriş boş native yuvaya eklendi.
Mevcut gemiler ve aktif gemi eşitliği, 12 giriş sınırı, kaynak hash'leri ve
gerçek codec encode/decode JSON eşitliği geçti. Yerel kanıt
`runtime/living-codec-72a94989e9/verification.json` içindedir ve Git'e dahil
edilmez. Bu kontrol oynanış/çağırma testi değildir. Starbirth görevi ve
ödül hakları değiştirilmez. Canlı kayda Living Ship yazılmadı.

## Oyun açıkken ekleme

[NMS.py](https://github.com/monkeyman192/NMS.py) 179105 ve güncel yapı
tanımlarındaki imzalar yalnız PE'nin çalıştırılabilir bölümlerinde arandı.
İki referansta da aşağıdaki adaylar yerel binary'de tekil eşleşti:

| İşlev | Yerel RVA |
| --- | --- |
| PlayerShipOwnership constructor | `0x2CD230` |
| UpdateMeshRefresh | `0x559ED0` |
| Update | `0x54FDE0` |
| SpawnNewShip | `0x551D10` |
| GetShipComponent | `0x554F00` |
| GiveGenericReward | `0xF03D60` |

179105 DestroyShip imzası `0x552A50` adresinde tekil eşleşti; güncel
imza eşleşmedi. Sürüm başına doğrulama gerekliliği somut olarak görüldü.

SpawnNewShip'in imzası zaten sahip olunan bir gemi indeksini alır. Bu,
boş sahiplik kaydının resource ve envanterlerini kuran bir ekleme API'si
değildir. GiveGenericReward da doğru manager instance'ı, görev bağlamı,
parametre ömürleri ve oyun thread'i gerektirir. Bunlar henüz doğrulanmadı.
İmza eşleşmesi çağrı güvenliği veya tüm sınıf yerleşiminin uyumu değildir.
v0.13'te bu ödül çağrısı için ayrı, açık opt-in gerektiren deneysel mod yazıldı:
[native_bridge](../native_bridge/README.md). Mod burada oyuna yüklenmedi veya
çalıştırılmadı; native teslim/oynanış doğrulanmış sayılmaz.

## Oyun içi test engeli

Oyun CapsLockFix ile açıldı; kayıt seçim ekranı görüldü. Windows kontrol
aracı basılı tuş/fare desteklemiyor. MouseClickSpeedMultiplier için ayrı
yedekli 1.0, 100.0 ve 0.001 denemeleri kısa tıklamayla kayıt onayını
geçirmedi. Eski 0.5 değeri test sonunda geri yüklendi. Yük gemisi test
işlemi de oyun normal kapatıldıktan sonra, yeni durum ayrıca yedeklenerek
test öncesi tam kayda geri alındı. Kayıt yüklenmesi sağlanamadığı için
yük gemisi çağırma, Living Ship oynanış ve canlı ekleme testi tamamlanmadı.
