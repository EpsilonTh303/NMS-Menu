# Yerel katalog

`technologies.json`: kurulu GOG 179666 sürümünün GcTechnologyTable verisinden türetilen
149 teknoloji; 8 İngilizce yerelleştirme tablosundan 147 ad çözüldü. İki girdide ID gösterilir.
Prosedürel yükseltme paketleri, kırık yuva, onarım ve dummy kayıtları dahil edilmez.
Ham oyun dosyaları Git deposuna eklenmez. Kaynak MXML SHA256 JSON içinde tutulur.

Yeniden üretim: `python tools/build_catalog.py TABLE.MXML data/technologies.json`
ve her dil tablosu için tekrarlanabilir `--localisation LOC.MXML` argümanı.

`tool-models.json`: 12 yerel model yolu. Yollar kurulu EntitySceneMBIN arşivinde doğrulandı;
her modelin oyun içi görünümü ayrı ayrı test edilmedi. Yeni alet mevcut aletin donanımını
kopyalar; nadir modelin özel istatistiklerini garanti etmez.

Gemi profilleri FleetManager/catalog.json, estetik tercihler FleetManager/preferences.json
üzerinden okunur. Garaj ortak taramanın güncel verisidir. Katalog kurulumunda boş yer,
hedef türü, gerçek kaynak kimliği ve codec doğrulaması ayrıca zorunludur.


`reward-presets.json`: yerel rewardtable.mbin içinden 70 ek kişisel gemi model/tohum
profili ve 37 sabit alet görünüm tohumu. Gemi sınıfı S ve temel istatistik/donanım
editör seçimidir; özgün ödül yüklemesi değildir. Alet istatistikleri kaynakta kalır.
İçinde görünüm özelleştirmesi olan gemiler, organik gemiler ve yük gemileri elenir.
Her profil özgün reward_id taşır; model ve tohum çifti aynı tabloda tekilleştirilir.

Yeniden üretim: `python tools/build_reward_catalog.py REWARDTABLE.MXML data/reward-presets.json`
ve her dil tablosu için `--localisation LOC.MXML`. Kaynak SHA256 çıktı içindedir.

`reference-catalog.json`: kaynak bağlantıları ve destek durumu bulunan salt okunur
Tür rehberi. Referans kaydı `command()` tarafından reddedilir. Bu kayıtların varlığı
oyuna ekleme işleminin desteklendiği anlamına gelmez.
