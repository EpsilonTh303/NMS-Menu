# Ekleme kataloğu — 179666 / 0.6

Yerel GcTechnologyTable: 393 kayıttan desteklenen Suit/Weapon/Ship aileleri için
149 sabit teknoloji. Procedural/RepairTech/BrokenSlotTech, DUMMY ve SHIP_LIFESUP
elenir. 8 İngilizce dil tablosu 147 adı çözer; iki ID olduğu gibi gösterilir.

7 çok amaçlı alet modelinin scene yolları EntitySceneMBIN arşivinde doğrulandı.
Sınıf ve ekipman seçilen mevcut aletten kopyalanır. Nadir modelin doğal istatistikleri
üretilmez. Her modelin görseli oyun içinde tek tek test edilmedi.

Doğrulama: taze kayıt kopyasına CANNON, UT_JET, Royal alet ve yeni tohumlu Utopia
ile dört işlem eklendi; 44 semantik fark, codec Write/Read JSON eşitliği başarılı.
Gemi/alet sabit dizi uzunlukları 12/6 kaldı. Canlı kayda veya oyun belleğine yazılmadı.
BOLT UsesAmmo=true / Chargeable=false olduğundan başlangıç miktarı UsesAmmo'yu da
hesaba katar; veri tablosundaki 200 değeri kullanılır. Kurulum boş geçerli yuva ister.

Uyumluluk hedefte yeniden kontrol edilir. Robot/alien/solar özel teknolojileri için
kısıtlar vardır. Testler veri bütünlüğünü ve mutasyon sınırlarını doğrular; her teknolojinin
oyun davranışını doğruladığı iddia edilmez. Çalışma dosyaları runtime/catalog-codec-* altında
Git dışında tutulur. Monkeymann deposuna gönderim yapılmadı.
