# Yapılabilecekler ve geliştirme sırası

Bu tablo aday kapsamdır. “Planlandı” ve “araştırma” çalışan özellik vaadi değildir.
Oyun içindeki her davranış kayıt dosyasından yönetilemez; canlı motor durumunu
gerektiren özellikler farklı teknik altyapı ve sürüm doğrulaması ister.

| Alan | Aday kontroller | Durum / koşul |
|---|---|---|
| Filo | Ekle, kaldır, onar, donanım kur | v0.1 hazır; doğrulanmış katalog / motor |
| Envanter | Karakter ve gemi yuvaları | v0.1 hazır; tür kapasitesi korunur |
| Kalkış | Otomatik şarj teknolojisi | v0.1 hazır; normal oyun mekaniği |
| Garaj | Arşiv, liste, içe aktar, değiştir | v0.1 hazır; 12 aktif gemi korunur |
| Yedek | Hazırla, fark incele, uygula, geri al | v0.1 hazır; tam kayıt geri alma |
| Ekonomi | Units, nanit, quicksilver miktarı | v0.2 canlı; doğrulanmış 179666 GOG build'i |
| Eşya | Arama, miktar, malzeme ve yakıt | Kimlik kataloğu, yığın sınırları ve boş yuva kuralları |
| Tarif / teknoloji | Tarif açma, teknoloji kurulumu | Kilit ve ön koşullar araştırılacak |
| Çok amaçlı alet | Model, sınıf, yuva, teknoloji | Şema / teknoloji uyumluluğu doğrulanacak |
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
3. **v0.3 adayı:** arama yapılabilir eşya / teknoloji kataloğu ve envanter
   hedefi. Mevcut eşya ve teknolojileri koruyan işlemler geliştir.
4. **Sonraki:** çok amaçlı alet, yük gemisi, fırkateyn; her biri kendi test
   fixture'ları ve ön koşullarıyla bağımsız modül olarak eklenir.
5. **Araştırma:** seyahat, üs, ilerleme ve canlı overlay. Teknik olarak
   doğrulanamayan kontroller arayüzde çalışır gibi gösterilmez.

Hiçbir aşama mevcut CapsLockFix başlatıcısını değiştirmeyi gerektirmez.
