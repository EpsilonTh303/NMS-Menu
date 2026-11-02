# Katalog araştırması — 2 Kasım 2026 / kurulu 179666

Önceki 10 gemi profili ve 7 alet modeli oyundaki toplam çeşit sayısı değildi.
Tür, benzersiz model dosyası, sabit ödül tohumu ve sahiplik kapasitesi ayrı kavramlardır.

## İnternetten doğrulanan kapsam

- Hello Games [Outlaws](https://www.nomanssky.com/outlaws-update/): Solar ailesi ve prosedürel varyasyonlar.
- [Interceptor](https://www.nomanssky.com/interceptor-update/): ele geçirilebilir Sentinel gemileri ve çok sayıda prosedürel görünüm.
- [Living Ship](https://www.nomanssky.com/living-ship-update/): yaşayan gemiler ve ayrı organik teknolojiler.
- [Voyagers](https://www.nomanssky.com/voyagers-update/): modüllerden yapılan Corvette ve iç yerleşimi.
- [Echoes](https://www.nomanssky.com/echoes-update/): Autophage ve asa inşası.
- [Omega](https://www.nomanssky.com/omega-update/): Starborn Runner, Atlas Sceptre ve ele geçirilebilir pirate dreadnought.
- [Worlds II](https://www.nomanssky.com/worlds-part-ii-update/): Titan seferinin özel yaşayan gemisi The Wraith.
- [NMSE StarshipLogic](https://github.com/vectorcmdr/NMSE/blob/main/Core/StarshipLogic.cs)
  ve [MultitoolLogic](https://github.com/vectorcmdr/NMSE/blob/main/Core/MultitoolLogic.cs):
  model yolu ve ortak multitool modelinin farklı ailelerce kullanılması için çapraz kontrol.
  Kod kopyalanmadı; yerel tablo ve varlıklar esas alındı.

## Uygulanan genişletme

Yerel `rewardtable.mbin` / SHA256 `403f80ae19902bc4d2785c88fe420b4610f5724adb19bc77daebb0ce428619f0`
(MXML kaynağının hash'i) içinden 70 ek kişisel gemi modeli/tohum profili ve 37 sabit
alet görünüm tohumu çıkarıldı. Gemiler tam ödül envanteri olarak aktarılmaz:
S sınıfı, belirtilmiş editör istatistikleri ve temel teknoloji paketi kullanılır.
Aletlerin sınıfı ve donanımı seçilen mevcut aletten gelir; doğal aile bonusları üretildiği
iddia edilmez. Görünüm tohumu sabittir; kaynak şekil/özelleştirme farkları görünümü etkileyebilir.

Toplam **80 gemi profili/tohum seçeneği**, **49 alet modeli/tohum seçeneği**,
**149 sabit teknoloji**. Alet seçeneklerinde **12 farklı model yolu** vardır;
geri kalanlar aynı modelin belirli ödül tohumlarıdır. Sahiplik sınırları 12 gemi / 6 alet kalır.

Yeni benzersiz alet modelleri: Switch, Staff, Atlas Staff, Ruin Staff, Bone Staff.
NPC asası ve efekt/muzzle modelleri oyuncu silahı diye eklenmedi. Bütün yeni model
referansları kurulu EntitySceneMBIN arşivinde bulundu. İnternet sayfalarının güncel
sürümüyle kurulu 7.04 arasında olabilecek farklarda yerel dosyalar esas alınır.

Organik gemi, The Wraith, Corvette ve büyük filo kayıtları ayrı doğrulanmış sahiplik
adaptörleri gerektirdiğinden rehber olarak gösterilir; komut üreticisi eklemeyi reddeder.
Görev, sefer ödülü, platform hakkı veya yeni keşif kilidi açılmaz.

## Yeniden doğrulama

`tools/build_reward_catalog.py` kaynak kimliği/model/tohumu tekrar üretir.
`tools/validate_expanded_catalog.py` en yeni kaydı kaynak hash'iyle ayrı runtime klasörüne
kopyalar; mevcut gemi ve aletleri koruma kontrollerini yapar, beş farklı gemi ailesi ile
beş yeni alet modelinden karma örnekleri gerçek GOG codec Write/Read eşitliğine gönderir.
Canlı kayda veya oyun belleğine yazmaz. Dosyalar runtime dışında dışa aktarılmaz.

Monkeymann deposuna henüz gönderim yapılmadı. Bu belge ve derleyiciler aktarılabilecek
bulgulardır; ham oyun tabloları ve kullanıcının kayıtları Git'e eklenmez.


## Windows codec karakter düzeltmesi

Gerçek round-trip kontrolü, yeni gemi adındaki U+2022 karakterinin OEM/UTF-8
karışmasıyla farklı karakterlere dönüştüğünü yakaladı. `FleetManager/fleet.py:encode`
artık codec stdin'ine `ensure_ascii=True` ile ASCII JSON gönderir. JSON parse edildiğinde
Unicode metin geri oluşur; sabit envanter ve kaynak hash güvenlik kuralları değişmez.
Regresyon testi Türkçe harfler ve U+2022 için ASCII/cp437/cp1252/UTF-8 okumalarının
aynı JSON değerini verdiğini doğrular. Kardeş FleetManager klasörü Git deposu olmadığından
aynı düzeltmenin uygulanabilir diff'i Menu/patches/fleet-codec-unicode.patch içinde tutulur.


## Sonuç

73 Menu testi ve 13 FleetManager testi geçti (86 toplam). Taze kopyada 70 yeni gemi
ve 49 alet profilinin her biri ayrı ayrı mevcut sahipliği korudu. Unicode düzeltmesinden
sonra beş karma GOG codec round-trip eşitliği geçti: Horizon + Staff, Hauler + Atlas
Sceptre, Explorer + Pillar of Titan, Shuttle + Basilisk Crown, Solar + Switch.
Bu testler dosya/veri tutarlılığını doğrular; bütün görünümler oyun içinde denenmedi.
