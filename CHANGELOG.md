# Değişiklikler

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
