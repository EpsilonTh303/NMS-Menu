# Yerel katalog

`technologies.json`: kurulu GOG 179666 sürümünün GcTechnologyTable verisinden türetilen
149 teknoloji; 8 İngilizce yerelleştirme tablosundan 147 ad çözüldü. İki girdide ID gösterilir.
Prosedürel yükseltme paketleri, kırık yuva, onarım ve dummy kayıtları dahil edilmez.
Ham oyun dosyaları Git deposuna eklenmez. Kaynak MXML SHA256 JSON içinde tutulur.

Yeniden üretim: `python tools/build_catalog.py TABLE.MXML data/technologies.json`
ve her dil tablosu için tekrarlanabilir `--localisation LOC.MXML` argümanı.

`tool-models.json`: 7 yerel model yolu. Yollar kurulu EntitySceneMBIN arşivinde doğrulandı;
her modelin oyun içi görünümü ayrı ayrı test edilmedi. Yeni alet mevcut aletin donanımını
kopyalar; nadir modelin özel istatistiklerini garanti etmez.

Gemi profilleri FleetManager/catalog.json, estetik tercihler FleetManager/preferences.json
üzerinden okunur. Garaj ortak taramanın güncel verisidir. Katalog kurulumunda boş yer,
hedef türü, gerçek kaynak kimliği ve codec doğrulaması ayrıca zorunludur.
