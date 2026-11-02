# Değişiklikler

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
