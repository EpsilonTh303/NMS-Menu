# Değişiklikler

## 0.10.0 — 2 Kasım 2026

- Yük gemisi/fırkateyn sekmesi ve ortak sepete bağlanan çevrimdışı işlemler.
- Yük gemisi adı/sınıfı, onarım/şarj ve S sınıfında 120/60 yuva; mevcut envanter ızgarasına yük gemisi ekleme.
- Fırkateyn adı, dört beceri, onarım, normal türleri 30 sınırıyla kopyalama ve tam yedekli kaldırma.
- Sefer/rapor durumunda düzenleme, sefer listesi doluyken kaldırma engeli; görev indeksleri korunur.
- Dört dilde yeni metinler ve Ctrl+Shift+F8 ile ayrı Qt overlay paneli; enjeksiyon veya canlı sahiplik yazımı yok.
- Güncel kayıt kopyasında fırkateyn ve sentetik yük gemisi için iki codec round-trip eşitliği; canlı kayıt değişmedi.

## 0.9.0 — 2 Kasım 2026

- FleetManager motoru ve katalogları Menu köküne entegre edildi; ayrı klasör bağımlılığı kaldırıldı.
- Garaj ve işlem yedekleri hash doğrulamasıyla korundu; son işlem geri alma işaretçileri yeni konuma taşındı.
- Kayıt codec'i `codec/` içine alındı; resmî sürüm için boyut/SHA-256 doğrulamalı kurulum eklendi.
- Eski Solar düzeltme yedekleri `runtime/legacy-solar/` altında korundu; dış klasör bağımlılığı kaldırıldı.
- Referansa göre Qt masaüstü görünümü, yerel vektör simgeleri ve envanter çizimi.
- Ayarlar sekmesi; anlık ve kalıcı Türkçe, İngilizce, Rusça ve Almanca seçimi.
- Dil başına ayrı JSON, 525 kaynak metin, dosyadan dil keşfi ve Türkçe yedek metinler.
- Yeni metin/dil ekleme, dosya yenileme ve değişken/eksik çeviri kontrol araçları.
- Mevcut Tk denetleyicileri, işlem doğrulamaları ve `--classic` görünümü korunur.
- Yerel bağımlılık kurulumu ve temiz klonda test klasörü oluşturma; sentetik ve yerel motor regresyon testleri.

## 0.8.0 — 2 Kasım 2026

- Yerel ürün/madde tablolarından 1100 eşya ve zorluk/envanter grubuna göre gerçek yığın sınırları.
- Ortak snapshot ile envanter ızgarası, miktar, taşıma, bölme ve birleştirme; kesin eşya fingerprint'i.
- 5 hazır donanım seti ve kişisel sabit teknoloji setleri; mevcut donanımı koruyarak eksikleri kurma.
- 18 gemi / 18 alet yerleşik arşivi; kargoyu koruma, tam gemi garaj dışa aktarımı ve boş aktif yuvaya geri getirme.
- Seçili tarif öğrenme, favoriler ve son kullanılanlar; UI bağımsız servisler ve ortak işlem sepeti.
- 12 aktif gemi doluyken boş arşiv şablonundan aynı şemayla kaldırmayı destekleyen FleetManager düzeltmesi.
- 99 Menu + 13 FleetManager testi; güncel kayıt kopyasında arşivlenmiş/geri getirilmiş iki tam codec eşitliği.

## 0.7.0 — 2 Kasım 2026

- Resmî güncelleme sayfaları ve NMSE kaynaklarıyla gemi / alet ailelerinin araştırılması.
- Yerel ödül tablosundan 70 ek gemi profili ve 37 alet görünüm tohumu; toplam 80 / 49 seçenek.
- 5 yeni alet modeli: Switch, Voltaic Staff, Atlas Sceptre, Pillar of Titan, Basilisk Crown.
- Aile filtresi, içerik ayrıntısı, model/tohum ve kaynak bilgisi; teknoloji açıklamaları.
- Ayrı tür rehberi; Living Ship, Wraith, Corvette ve büyük filo için açık destek durumu.
- Windows codec stdin karakter kodlaması düzeltildi; Unicode JSON kaçışları ve regresyon testi.
- Katalog sayılarının oyun toplamı olmadığı açıklanır; ödül görünümü ile kaynak istatistikleri ayrılır.

## 0.6.0 — 2 Kasım 2026

- 149 teknoloji, 7 alet modeli, 10 gemi profili ve dinamik garaj için arama / filtre / çoklu seçim.
- Ortak kayıt taramasından beslenen, hedef kimliği doğrulanan toplu ekleme sepeti.
- Teknoloji uygunluğu, boş yuva, aktif alet senkronizasyonu ve değişmeyen kaynak denetimi.
- UI bağımsız katalog / sepet servisleri; sepet değişince eski hazırlama raporu geçersizleşir.
- Taze kayıt kopyasında dört işlemlik karma sepet codec round-trip doğrulaması; canlı kayda yazılmadı.

## 0.5.0 — 2 Kasım 2026

- Açılışta otomatik süreç bağlantısı, ortak canlı yenileme ve yeniden bağlanma.
- Filo / silah disk listeleri için tek codec okuması ve değişen dosya cache'i.
- Uzun disk okumasını canlı bağlantıdan ayırma; seçimi / hedef girdilerini koruma.
- Tek Tümünü yenile düğmesi; bölüm başına okuma düğmeleri kaldırıldı.
- İstasyon silah adayı kontrollü testte başarısız oldu ve geri alındı.
- NPC entity bileşenleri ve HGPAKtool API çıkarımı için yeni araştırma notları.

## 0.4.0 — 2 Kasım 2026

- Oyun kapalıyken çok amaçlı alet ekleme / kaldırma ve taze kayıt listesi.
- Mevcut aletin model ailesi / sınıf / donanımından yeni tohumla boş yuvaya ekleme.
- Son aleti koruma, tam donanım dışa aktarımı, aktif alet kopyalarını senkron tutma.
- FleetManager'ın mevcut yedek / codec / hash / apply / restore motoruyla bağımsız silah modülü.
- İstasyon silah kullanımı ve NPC hasarı için kaynak / binary araştırması; bu seçenekler henüz uygulanmadı.

## 0.3.0 — 2 Kasım 2026

- Doğrudan bellekten 12 girişlik filo listesi; model / tohum / yuva kimliği.
- Oyun kapanmadan, Esc duraklatma menüsünde mevcut gemi onarma / şarj etme.
- Aynı koşullarda bütün mevcut gemilerin yuvalarını FleetManager tür sınırlarıyla açma.
- Taze kaynak kopyası, canlı envanter projeksiyonu, gerçek codec round-trip ve rapor incelemesi.
- Alan bazlı, koşullu canlı geri alma; kargo / pointer / sahiplik korunması.
- 179666 teknoloji dizi offset'i, pasif teknoloji -1 değeri ve boyut dışı bitler için araştırma notları.
- Canlı gemi ekleme, silme, model / tohum değiştirme henüz uygulanmadı.

## 0.2.0 — 2 Kasım 2026

- Oyun açıkken bağlanan ayrı canlı kontrol sekmesi.
- Units, nanit, quicksilver için miktar ayarlama ve koşullu tek adım geri alma.
- Hız, jetpack, dayanıklılık, yaşam desteği ve kalkan için 12 canlı ayar.
- EXE hash / canlı kod / oturum / beklenen byte doğrulamaları ve yazım günlüğü.
- Normal kapanışta geçici ayarları geri alma; para için ayrı geri alma.
- 179666 GOG üzerinde canlı ayar yazma / yeniden okuma / özgün byte'a dönüş testi.
- NMS-Research klasöründe build profili, kaynaklar ve upstream aday notları.
- Açılışta bağlantı için isteğe bağlı `python main.py --connect`.

## 0.1.0 — 1 Kasım 2026

- Filo / envanter masaüstü arayüzü ve mevcut FleetManager adaptörü.
- İşlem raporu, garaj, tam kayıt geri alma, modül planı ve yerel Git.
