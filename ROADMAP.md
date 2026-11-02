# Yapılabilecekler ve geliştirme sırası

Bu tablo aday kapsamdır. “Planlandı” ve “araştırma” çalışan özellik vaadi değildir.
Oyun içindeki her davranış kayıt dosyasından yönetilemez; canlı motor durumunu
gerektiren özellikler farklı teknik altyapı ve sürüm doğrulaması ister.

| Alan | Aday kontroller | Durum / koşul |
|---|---|---|
| Filo | Ekle, kaldır, onar, donanım kur | v0.1 hazır; doğrulanmış katalog / motor |
| Canlı filo | Listele, mevcut gemiyi onar / şarj et, tüm gemilerin yuvalarını aç | v0.3; oyun açık, offline, Esc duraklatma menüsünde |
| Envanter | Karakter ve gemi yuvaları | v0.1 hazır; tür kapasitesi korunur |
| Kalkış | Otomatik şarj teknolojisi | v0.1 hazır; normal oyun mekaniği |
| Garaj | Arşiv, liste, içe aktar, değiştir | v0.1 hazır; 12 aktif gemi korunur |
| Yedek | Hazırla, fark incele, uygula, geri al | v0.1 hazır; tam kayıt geri alma |
| Ekonomi | Units, nanit, quicksilver miktarı | v0.2 canlı; doğrulanmış 179666 GOG build'i |
| Eşya | Arama, miktar, malzeme ve yakıt | Kimlik kataloğu, yığın sınırları ve boş yuva kuralları |
| Tarif / teknoloji | 149 sabit teknolojiyi uygun hedefe kurma | v0.6–0.7 hazır; tarif öğrenme ayrı aday |
| Çok amaçlı alet | Kaynak donanımla ekle / kaldır; 49 model/tohum seçeneği | v0.7; oyun kapalı, 12 benzersiz model yolu |
| İstasyon savaş kontrolü | Silah çıkarma / ateş etme aç-kapat, NPC hasarı | Araştırma; çalıştırılamaz |
| Yük gemisi | Model, sınıf, envanter | Aktif gemi ve üs bağımlılıkları araştırılacak |
| Fırkateyn | Filo ve sefer | Aktif görev ve zaman tutarlılığı araştırılacak |
| Exocraft / evcil hayvan | Sahiplik, özellik ve envanter | Ayrı şema ve kimlik kuralları gerekli |
| Karakter | Hız, jetpack itiş/dolum, dayanıklılık, yaşam desteği, kalkan yenilenmesi | v0.2 canlı; 12 yapılandırma alanı. Doğrudan sağlık / ölümsüzlük yok |
| Zorluk | Tüketim, hasar, üretim / satın alma maliyeti | Önce yerleşik oyun seçenekleri incelenecek |
| Keşif | İtibar, dil, tarif / keşif kilitleri | Görev tutarlılığı ve sürüm doğrulaması gerekli |
| Seyahat | Koordinat, portal, istasyon | Güvenli spawn ve galaksi tutarlılığı gerekli |
| Üs / yerleşim | Parçalar, enerji, kaynaklar | Konum ve sahiplik bağımlılıkları araştırılacak |
| Canlı mod | Bellek üzerinden para / yapılandırma | v0.2 hazır; ayrı masaüstü penceresi |
| Overlay / geniş canlı mod | Oyun içi arayüz, anlık yakıt, uçuş, zaman, ölümsüzlük | Araştırma; bu sürümde yok |

## Aşamalar

1. **v0.1:** bağımlılıksız masaüstü paneli, doğrulanmış filo motoru, kayıt
   yuvası seçimi, rapor / yedek akışı, yerel Git ve güvenlik testleri.
2. **v0.2 tamamlandı:** ayrı canlı backend; build hash ve kod anchor kontrolü,
   para birimleri ve 12 global ayar, yazım günlüğü ve koşullu geri alma. Canlı
   yazma / okuma / özgün değere dönüş yürüme hızıyla doğrulandı. Araştırma arşivi
   `NMS-Research` altında. Diğer ayarların oyun içi davranışı kullanıcıyla denenebilir.
3. **v0.3 tamamlandı:** mevcut gemilere canlı envanter projeksiyonu, FleetManager
   kuralları / codec kontrolü, duraklatma doğrulaması ve koşullu alan bazlı geri alma.
   Sahiplik ekleme / silme ve model değiştirme henüz canlı desteklenmiyor.
4. **v0.4–v0.7 tamamlandı:** alet sahipliği, ortak otomatik tarama, UI bağımsız
   katalog/sepet, 80 gemi profili/tohum seçeneği, 49 alet seçeneği, 149 teknoloji.
   Bunlar oyundaki toplam tür sayıları değildir. Ayrıntılar / aile filtresi / rehber bulunur.
5. **Önerilen sonraki paket:** eşya/malzeme kataloğu ve miktar → envanter ızgarası →
   donanım profilleri. Henüz uygulanmadı. Yerel ürün/madde tabloları kaynak olarak bulundu.
6. **Koleksiyon:** silah envanteri ve yerleşik gemi/alet arşivi. Resmî oyunda ek 18'er
   arşiv girişi var; gemi arşivinde kargo korunmadığı için mevcut tam garajdan farklıdır.
7. **Sonraki modüller:** tarif bilgisi, yük gemisi/fırkateyn/squadron, Exocraft, organik gemiler.
8. **Araştırma:** seyahat, evcil hayvan, Corvette, istasyon/üs yönetimi, canlı sahiplik ve overlay.
   Teknik olarak doğrulanamayan kontroller çalışır gibi gösterilmez.

[2 Kasım özellik araştırması ve öncelikler](NMS-Research/next-features-179666.md)
kaynakları, adayların bağımlılıklarını ve yeni UI için önerileri içerir.

Hiçbir aşama mevcut CapsLockFix başlatıcısını değiştirmeyi gerektirmez.
