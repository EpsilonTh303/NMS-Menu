# Entegre filo motoru

Motor artik Menu kokundedir; ayri FleetManager klasoru gerekmez.
Eski islem yedekleri Menu/transactions/, harici garaj Menu/garage/
altinda korunur. Yerel test_fleet testleri ozel inspection kayitlari
gerektirir; bu kayitlar klona dahil edilmez. Sentetik testler Menu/tests/ icindedir.

Bu klasor Codex'in sonraki gemi ekle/sil/envanter isteklerinde kullanacagi
yerel aracidir. Canli kayitlara yalnizca `apply` ve `restore` yazar.
Internet, oyun bellegine mudahale veya mod kurulumu gerektirmez.

## Is akisi

Oyun tamamen kapali olmalidir. Her islem icin yeni JSON plan olusturulur;
asagidaki eski plan daha sonra yeniden uygulanmaz.

```powershell
python Menu/fleet.py inspect
python Menu/fleet.py prepare Menu/runtime/current-request.json
python Menu/fleet.py apply Menu/transactions/ISLEM_KLASORU
```

`prepare`: guncel kayitlarin tum `.hg` dosyalarini `before` klasorune alir,
secilen oyun yuvasinin auto/manual kayitlarini birbirinden bagimsiz duzenler,
yalnizca izinli alanlarin degistigini denetler, dosyalari kodlayip yeniden
okuyarak JSON esitligini dogrular. `manifest.json` degisiklik raporunu icerir.
Bu asamada canli kayit degismez.

`apply`: oyun hala kapaliysa ve tum kaynak dosyalarin SHA256 degerleri
yedekle ayniysa uygular. Degismis kaynak, ikinci uygulama ve kazara ayni
gemiyi ekleme durdurulur. Yazma hatasinda o islemdeki dosyalar geri yuklenir.
Windows/PC aniden kapanmasina karsi tum dosyalar icin tek atomik islem
garantisi yoktur; boyle bir durumda `before` yedegi vardir.

## Plan ornekleri

```json
{"save_slot":1,"actions":[{"op":"add","profile":"sentinel","name":"Yeni Gemi"}]}
```

```json
{"save_slot":1,"actions":[{"op":"remove","selector":{"name":"Gece Yelkencisi"},"preserve_cargo":true}]}
```

Seciciler: `name`, `type`, `seed`, veya insan icin 1'den baslayan `slot`.
Birden fazlasi birlikte kullanilabilir. Tam bir gemi eslesmesi zorunludur.
Oyun tarafindan uretilen ve kayitta yazmayan adlarla tahmin yapilmaz.
Desteklenen ekleme profilleri `catalog.json` icinde: `solar`, `sentinel`, `exotic`.
Koleksiyon profilleri: `starborn_runner`, `golden_vector`, `utopia_speeder`,
`blue_squid`. Bunlar da temel motorlar, otomatik sarj ve genis yuvalarla gelir.
Estetik secimler icin `preferences.json` okunur: kullanici Utopia Speeder'i
begendi ve Squid modelinin kaldirilmasini istedi.

`iron_vulture`, `boundary_herald`, `starborn_phoenix` profilleri de eklendi.
Model/tohum referansi TAZmd'nin herkese acik gemi paylasimlaridir:
https://www.tazmd.nl/starships . Iron Vulture siradan bir hauler tohumu
degildir; `ship-references/iron-vulture-ccd.json` icindeki uc S13 parca
grubu, metalik palet ve kaplama dogru CharacterCustomisationData yuvasina
yazilir. Tum gemi referansini ithal etmek yerine yerel surumun bos gemi
sablonu kullanilir; yalnizca model/tohum, temel istatistikler ve Iron Vulture
gorunumu referanstan alinir. Baska oyuncunun esyalari veya ilerlemesi alinmaz.
Plan ekleme isleminde `name`, `seed`, `class` degerlerini degistirebilir.

```json
{"save_slot":1,"actions":[{"op":"max_slots","scope":"exosuit"},{"op":"max_slots","scope":"ships"},{"op":"auto_recharge","scope":"ships"}]}
```

Karakter: 120 kargo / 60 teknoloji. Gemi turunun siniri kullanilir:
Fighter 100, Solar 110, Sentinel/Hauler 120 kargo; 60 teknoloji.
Mevcut gemilerin sinifi, istatistikleri, esyalari ve supercharged yuvalari
degismez. Kapasite editorle acilir; oyun ici sinif yukseltmesi yapilmaz.
Arac kalici teknoloji ekler; otomatik yakit dolumu `UT_LAUNCHCHARGE` ile
oyunun normal sarj mekanigini kullanir, aninda/sinirsiz yakit hilesi degildir.

Gemi silme sirasinda kargo karaktere tasinir; yer yoksa islem durur.
Kurulu teknolojiler dahil geminin tam kaydi `*-removed-ships.json` dosyasinda
ve `before` yedeginde kalir. Aktif gemi silinirse var olan bir gemi secilir.
Son geminin silinmesi engellenir.

## Donanim paketleri

`equip` islemi `loadouts.json` icindeki dogrulanmis paketi secilen gemiye
kurar. Ornek: `sentinel-loadout-and-exotic.json`. Var olan teknoloji ve
motorlar tasinmaz, silinmez veya degistirilmez. Tercih edilen yuva doluysa
yeni parca bos bir yuvaya konur. Ayni parca ikinci kez eklenmez.
Prosedurel silah/kalkan ailelerinde uc modul siniri kontrol edilir;
mevcut farkli modullerle asiri yukleme olusacaksa islem uygulanmadan durur.
Modul tohumlari S-sinifi normal rastgele ozellik uretir; en yuksek zar
sonucu veya belirli bir DPS degeri garanti edilmez.

Exotic profili beyaz-altin Guppy (`Altin Inci`, 0xD387D71BEDC8BB91), standart
temel motorlar ve otomatik kalkis sarji ile gelir; 105 kargo/60 teknoloji
yuvasi aciktir. Eklenince mevcut aktif gemi secimi degismez.

## Sentinel cagirma uyumluluk duzeltmesi

`repair_ship` secilen geminin teknolojilerini onarir ve sarj eder.
Sentinel icin `compatibility_core:true`, kendi robot parcalarini koruyarak
standart `LAUNCHER` ve `SHIPJUMP1` modullerini ekler. Bu, saglam robot
teknolojilerine ragmen ilk cagirmada alinan kritik hasar uyarisi icin
geri alinabilir bir uyumluluk denemesidir; kesin motor hatasi teshisi degildir.
`activate:true` yalnizca kaydedilmis konum `InStation` ise aktif gemiyi secer;
istasyon konumunu ve spawn donusumlerini degistirmez.

1 Kasim 2026: kullanici `20261101-172755-58c6ae` islemi sonrasinda Kara
Muhafiz'i oyun icinde kullanabildigini ve sorunun cozuldugunu dogruladi.
Yeni Sentinel profili artik robot teknolojilerinin yaninda bu iki standart
motoru da icerir. Iki motorun eklenmesi ve istasyonda aktiflestirme birlikte
denendi; hangisinin tek basina yeterli oldugu ya da oyunun kesin ic nedeni
ayristirilmadi. Yeni eklemelerde normalde kullanicinin aktif gemisi degismez;
sorun yinelenirse `repair_ship` istasyon etkinlestirme yolu kullanilabilir.

## Geri alma

Oyun kapaliyken `Son-Islemi-Geri-Al.cmd` dosyasina cift tiklamak son uygulanan
filo islemini geri alir. Kod tarafindan ayni islem ikinci kez geri alinmaz.

```powershell
python Menu/fleet.py restore Menu/transactions/ISLEM_KLASORU
```

Bu komut o islemden onceki iki oyun kaydini tam geri getirir. Aradan gecen
ilerleme bu eski kayitta yoktur; geri almadan once guncel kayitlar da ayrica
yedeklenir. Hesap dosyalarina ve diger oyun yuvalarina yazilmaz.
Eski SolarShipFix geri alma araci daha eski (16:46) kayda doner; yeni islemler
icin kendi transaction geri alma komutu tercih edilmelidir.

## Sinirsiz dosya garaji ve aktif gemi siniri

Oyunun 12 aktif gemi siniri KALDIRILMADI. Kayit dizileri 12/12/26 olarak
korunur. Oyun ici 18 gemilik arsiv de degistirilmez. Bu surum icin dogrulanmis
bir aktif kapasite yamasi bulunamadi. Dis garaj, disk kapasitesi disinda
sayisal bir limit koymadan tam gemi kopyalari saklar; oyun icinde bunlarin
hepsi ayni anda cagirilamaz. Gecis icin oyun kapatilir ve bir islem uygulanir.

```powershell
python Menu/fleet.py garage-snapshot
python Menu/fleet.py garage-list
```

Ilk komut en yeni auto/manual kaydini okuyup aktif gemileri kargo,
teknoloji, model, tohum ve gorunumleriyle `garage/*.json` dosyalarina alir.
Gemileri oyundan kaldirmaz ve canli kayda yazmaz. Her kayit iceriginin SHA256
ozetiyle tanimlanir; farkli kargo/teknoloji yeni bir surum olarak saklanir.

Garajdan bos bir aktif yuvaya alma plani:

```json
{"save_slot":1,"actions":[{"op":"garage_import","id":"GARAGE_LIST_ILE_GELEN_TAM_64_KARAKTER_ID"}]}
```

12 yuva doluysa hangi geminin yerine gelecegi belirtilir:

```json
{"save_slot":1,"actions":[{"op":"garage_import","id":"GARAGE_LIST_ILE_GELEN_TAM_64_KARAKTER_ID","replace":{"name":"Yerine alinacak aktif gemi"}}]}
```

`prepare`/`apply` akisiyla uygulanir. Cikan geminin tam verisi, canli dosyalar
degistirilmeden ONCE garaja yazilir. Kargo karaktere tasinmaz: cikan gemiyle
birlikte garajda kalir ve geri alindiginda gelir. Giren geminin kargosu ve
teknolojileri korunur. Aktif gemi degistirilecekse istasyonda kaydedilmis
olmak gerekir. Yeni gemi ayni yuva numarasini kullanir; diger gemiler korunur.
Ayni model/tohumun aktif kopyasini eklemek, bozuk checksum ve farkli kayit
surumunu karistirmak reddedilir. Garaj haricindeki rastgele dosyalar alinmaz.

Kaynaklar: https://www.nomanssky.com/worlds-part-ii-update/ (18 oyun ici
arsiv); https://github.com/vectorcmdr/NMSE/blob/main/docs/user/README.md
(12 aktif); https://github.com/zencq/nomnom/wiki/Save.-Starship (harici koleksiyon).

## Kontroller

```powershell
python -m unittest discover -s Menu -p test_fleet.py
```

Codec: `../SolarShipFix/libNOM.io.cli.exe`, resmî libNOM.io 0.14.2 surumu.
Guncellemede codec'in destegi ve yeniden okuma dogrulamasi kontrol edilir.
Kaynaklar: katalogdaki gemi referanslari; NMSE `Core/StarshipLogic.cs`;
https://www.nomansskyresources.com/starship-blueprints/launch-auto-charger
