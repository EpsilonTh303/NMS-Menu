# Silah / çok amaçlı alet araştırması — GOG 179666

2 Kasım 2026. Bu çalışma yeni istek için taze DefaultUser kayıtlarından yapıldı.
Kullanıcının açık oyunundaki aletler veya istasyon davranışı değiştirilmedi.

## Doğrulanan kayıt şeması

- Sahiplik alanı bu kayıtta `Multitools`; eski `WeaponOwnership` varsayımı yanlış.
- Sabit 6 giriş; sahiplik `Seed[0]` ile belirleniyor. 18 girişlik
  `ArchivedMultitools` ayrıca mevcut ve bu modül tarafından değiştirilmez.
- Model `Resource.Filename`, görünüm tohumu aletin kendi `Seed` alanında.
  `Resource.Seed` örneklerinde false/0; görünüm tohumu diye bu alana yazılmaz.
- Aktif alet kimliği `CurrentWeapon.Filename` + `CurrentWeapon.GenerationSeed`.
- Aktif envanter `WeaponInventory`, yerleşim `WeaponLayout` alanlarında ayrıca
  tutuluyor. Aktif aletin donanımı için en güncel kopya buradan alınır.
- Kayıtta iki sahip olunan alet ve dört boş giriş gözlendi. İsimler boş olduğu
  için arayüz tohum / yuva / model kimliğiyle seçim yapar.

Taze kayıt kopyasında ekleme için 21 ve aktif aleti kaldırma için 47 semantik
yol değişti. İki işlem de gerçek GOG codec ile yeniden okununca düzenlenen JSON
ile tamamen eşleşti. Bu testler canlı .hg dosyalarını veya oyun belleğini değiştirmedi.

## Uygulanan özellikler

Oyun kapalıyken, seçili aletin model ailesi / sınıf / donanımını koruyup yeni
görünüm tohumu ile boş yuvaya ekleme. Kaynak ve diğer aletler değiştirilmez.
Bu bir nadir silah kataloğu veya belirli bir görsel sonucu garanti eden profil
değildir. Yeni görünüm prosedüreldir; özelleştirilmiş modeller aynı parça
görünümünü koruyabilir.

Kesin kimlikle kaldırma: tüm alet verisi ve aktif kopyadaki envanteri işlem
klasörüne dışa aktarılır. Son aletin silinmesi engellenir. Aktif alet kaldırılırsa
kalan ilk alet seçilir ve üç aktif kopya senkronlanır. Dizi uzunluğu korunur.

FleetManager'ın mevcut stopped / snapshot / prepare / encode / decode / commit /
restore motoru, bağımsız silah mutator'üyle yeniden kullanılır. FleetManager'ın
kaynak kodu değiştirilmedi. Auto/manual bağımsız düzenlenir; kaynak hash'leri
ve codec eşitliği doğrulanmadan apply yapılmaz. Tam kayıt restore aynı işlem
zamanına döner; daha yeni kayıt önce ayrıca yedeklenir.

## İstasyon silah kilidi ve NPC hasarı: açık kalan çalışma

PlayerGlobals ve diğer dışa aktarılmış alanlarda istasyonda silah kullanımını
açan, bu build için doğrulanmış bir boolean bulunmadı. Bu tarama böyle bir yolun
hiç olmadığı anlamına gelmez. Canlı konum enum'unu sahte gezegen değeriyle
değiştirmek veya doğrulanmamış branch'leri NOP yapmak uygulanmadı.

NMS.py'nin eski PlayerWeapon.Update imzası yerel binary'de eşleşmedi.
GetChargeTime imzası tek kez `0x13FD020` RVA'da eşleşti; bu fonksiyonun
çağıranları statik incelendi. Güncel weapon-mode offset'i aday kodda `0xF74`,
eski tanımda `0xF6C`. Bu gözlem tek başına silah kısıtını güvenle kaldırmaya
yeterli değil. Kod veya oyun belleği bu araştırma sırasında yamalanmadı.

Silahı çıkarma / ateş etme kontrolü ile istasyon NPC'sinin hedeflenebilirliği,
çarpışma ve hasar bileşenleri ayrı ayrı doğrulanmalı. NPC hasar bileşeni / sağlık
yaşam döngüsü henüz çözümlenmedi. Arayüzde bu iki seçenek açıkça pasif.
NPC'lerin hasar alabileceği veya istasyonda ateşin çalıştığı iddia edilmez.

## Kaynaklar ve upstream adayları

- [NMSE MultitoolLogic](https://github.com/vectorcmdr/NMSE/blob/main/Core/MultitoolLogic.cs):
  sahipliği Seed geçerliliğinden tanıma ve aktif model / tohum / envanter kopyasını
  senkron tutma için karşılaştırma kaynağı. Kod bağımsız yazıldı.
- [NMS.py types, 179105](https://github.com/monkeyman192/NMS.py/blob/9efb09ccb6/nmspy/data/types.py):
  PlayerMultitoolOwnership ve PlayerWeapon fonksiyon / alan tanımları.
- [NMSE kullanıcı rehberi](https://github.com/vectorcmdr/NMSE/blob/main/docs/user/README.md).

Upstream'e olası not: 179666'da ownership şeması ve bazı weapon offset'lerinin
eski tanımlardan farklılığı build-hash ile belgelenebilir. Güncel kaynakta hata
olduğu henüz gösterilmedi. Dışarıya issue veya PR gönderilmedi.
