# İstasyon NPC hasarı — ikinci inceleme / negatif test

2 Kasım 2026, GOG 179666; EXE hash'i önceki build profiliyle aynı.

## Silah kısıtı

[Weapon Wheel kaynağındaki](https://github.com/YouFokinWotM8/No-Man-s-Sky-Weapon-Wheel)
sekiz imza yerel .text bölümünde tek tek eşleşti. İndirilen Python mod dosyası
çalıştırılmadı; AST'den yalnız sabit imza metinleri okundu. Capstone ile yerel
binary incelendi. Bulunan önemli RVA'lar:

| Aday | RVA |
|---|---|
| Primary setter | `0x13F7AA0` |
| Secondary setter | `0x13FCC00` |
| Pending mode yazımı | `0x13F7E77` |
| Weapon wrapper | `0x13FCD60` |
| Weapon state / visibility adayı | `0x13E9F00` |

Wrapper, Application.mpData + `0x57A584` ortam değeri 2 olduğunda native cycle
yolundan çıkıyor. Bu, tek başına ateş / görünürlük kısıtının tamamı değil.
`0x13E9F00` adayı üç durum döndürüyor; isim / semantik kesin doğrulanmadı.

**Kontrollü test:** Kullanıcı istasyonda Esc ile duraklattı. Bu adayın başındaki
iki tam 5-byte komut, en fazla 90 saniyelik ayrı bir test betiğinde return-2
stub'ıyla değiştirildi. Kod öncesi / sonrası ve EXE hash'i doğrulandı; sayfa
koruması tekrar kuruldu. Kullanıcı oyuna dönüp silahı eline alamadığını bildirdi.
Test durduruldu; özgün 10 byte yeniden okuma ile doğrulandı ve audit'e yazıldı.
Bu aday **başarısızdır** ve üretim menüsünde toggle olarak kullanılmaz.

Başarısız ilk betik başlatması araştırma klasöründeki types.py'nin stdlib'i
gölgelemesi nedeniyle ctypes import'unda durdu; o denemede bellek değişmedi.
Asıl test `python -P` ile yapıldı. Ham betik / disassembly / imza sonuçları
Git dışındaki runtime/research içinde tutuluyor.

## NPC hedef / sağlık bileşenleri

Arşivler HGPAK v2, PSARC değil. Resmî
[HGPAKtool](https://github.com/monkeyman192/HGPAKtool) 1.1.3 ve
[MBINCompiler v7.04.0-pre1](https://github.com/monkeyman192/MBINCompiler/releases/tag/v7.04.0-pre1)
yalnız runtime analiz dizinine alındı.

NpcGek / NpcKorvax / NpcVykeen scene dosyaları `NMSARC.EntitySceneMBIN.pak`
içinde, bağlı entity dosyaları `NMSARC.Precache.pak` içinde bulundu.
Üç entity MBIN'i kopyaya çıkarılıp 7.04.0.1 compiler ile MXML'e çevrildi.

Üçünün bileşen listesinde audio, animasyon, interaction, physics, NPC,
character interface, player character, IK, scan-to-reveal, network bileşenleri
var. **GcShootableComponentData listede yok.** Bu, standart ateş edilebilir
hedef / sağlık bileşeninin bu üç assette bulunmadığına dair kanıttır; runtime'da
başka hasar yollarının var olmadığını ispatlamaz. Physics NoFireCollide=false
gözlendi. Sadece silah kullanımını açmanın NPC hasarını sağlaması garanti değil.

Entity düzenleyip bileşen ekleme henüz denenmedi: NPC yaşam döngüsü, ölüm /
interaction temizliği, yeniden spawn ve asset değişiminin diğer alanlardaki
NPC'lere etkisi ayrı doğrulama ister. Mevcut NPC assetlerine veya mod klasörüne
dosya kurulmadı; kayıt dosyasına yazılmadı.

## HGPAKtool API notu / olası upstream raporu

`with HGPAKFile(...) as pak` ile tüm index yüklendikten sonra aynı nesnede
`extract_specific(single_path, as_buffer=False)` çağrısı testte ilk index
öğesinin verisini döndürdü. `extract_specific` self.files sözlüğünü temizlemeden
dolduruyor ve sonra tüm sözlükte ilk çıkan öğeyi tekli sonuç olarak döndürüyor.
Bu nedenle ilk yanlış çıkarımlar kullanılmadı; taze `HGPAKFile(path)` nesnesinde
extract_specific çağrısıyla doğru NPC dosyaları alındı. İlgili doğru dosya
boyutları 129152 / 151559 / 117414 byte scene, 311688 / 311760 / 311728 byte entity.

Bu bulgu güncel upstream üzerinde küçük bir test ile yeniden doğrulanıp ayrı
issue adayı yapılabilir. Kullanıcı daha önce araştırmaları saklamayı istedi;
burada yalnız not hazırlandı, dışarıya gönderim yapılmadı. Oyun binary / asset
dosyaları Git deposuna eklenmez.

## Sonuç

NPC hasarı henüz çalışır duruma getirilmedi. Başarısız kod adayı geri alındı.
Menüde istasyon silah / NPC hasarı seçenekleri bu nedenle pasif kalır.
