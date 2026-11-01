# NMS araştırma notları

Bu klasör doğrulanan bulguları, kaynakları ve daha sonra upstream'e iletilebilecek
aday notları saklar. Henüz dışarıya gönderim yapılmadı. Çalışma tarihi:
2 Kasım 2026 (Asia/Baku).

- [179666 canlı veri profili](build-179666.md)
- [179666 canlı filo ve envanter bulguları](live-fleet-179666.md)
- [179666 silah koleksiyonu ve istasyon araştırması](weapons-179666.md)
- [İstasyon NPC hasarı: ikinci inceleme ve başarısız aday testi](station-combat-investigation.md)
- [Kaynaklar ve upstream adayları](upstream-notes.md)

Ham araştırma indirmeleri `../runtime/research` içinde Git dışında tutulur.
Capstone yalnız yerel analiz için `../runtime/analysis-tools` altına kuruldu;
menüyü çalıştırmak için gerekli değildir. İncelenen üçüncü taraf kaynak kodu
çalıştırılmadı, projeye vendoring yapılmadı. Menüye eklenen canlı adaptör bağımsız
Windows API uygulamasıdır; DLL enjeksiyonu veya instruction patch kullanmaz.

Buradaki RVA / offset değerleri yalnız belirtilen hash'e aittir. Başka build için
doğrulanmadan kullanılmamalıdır. Kaynak kodla gözlem arasında fark bulunması tek
başına kaynak projede hata olduğunu göstermez; sürüm / platform farkı olabilir.
