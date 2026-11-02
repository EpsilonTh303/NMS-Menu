# Envanter / koleksiyon 0.8 — 179666

## Kaynak ve kapsam

Kurulu GOG 7.04 ürün, madde ve difficultyconfig MBIN'leri HGPAKtool ile ayrı runtime
klasörüne çıkarıldı; yerel MBINCompiler 7.04.0.1 ile MXML'e çevrildi. Üretilen
`data/items.json` kaynak SHA256'larını ve 1100 normal envanter girdisini taşır.

CASING: StackMultiplier 2. High/Personal ürün tabanı 10 olduğundan 20; AMMO çarpanı
1000 fakat global ProductStackLimit 9999 ile sınırlı. Mevcut taze kayıtta görülen
BP_SALVAGE 30, MIRROR 20, TECH_COMP 40, NAV_DATA 40, HYPERFUEL1 20 değerleri formülle
uyumludur. Low/Normal/High ve farklı envanter grupları ayrı tanımlıdır.

Arşiv şeması taze 179666 kayıt kopyasında incelendi: ArchivedShipOwnership ve
ArchivedMultitools 18'er giriş, ShipOwnership 12 ve Multitools 6. Ship archive Ownership,
Customisation, UsesLegacyColours ve metadata; tool archive MultitoolData ve metadata içerir.

[Hello Games Worlds II](https://www.nomanssky.com/worlds-part-ii-update/) arşivin
18'er ek girişini ve gemi kargosunun temizlenmesini açıklar. Bizim uygulama kargoyu
native FleetManager ile önce ekzosuite taşır; yer yoksa hazırlama reddedilir. Hedef yığın sınırı da
kontrol edilir; kaynak miktarı sınırı aşarsa önce bölme gerekir, MaxAmount gerekirse
düşürülür. Tam dışa aktarım özgün gemi verisini korur. Tam gemi
apply öncesi mevcut harici garaja da alınır. Arşive aynı kargoyu ikinci kez koymaz.

## Doğrulama

99 Menu ve 13 FleetManager testi başarılı. Doluyken ekleme, eşya miktarı korunması,
metadata eşitliği, eski fingerprint, dolu/kapalı hedef, yanlış envanter, aktif alet
senkronizasyonu, süperşarjlı yuvaları koruma, 12 gemi doluyken arşivleme, kargo yeri
olmaması, son alet, yanlış arşiv kimliği ve tarif tekrarının no-op olması test edildi.

`tools/validate_workbench.py` her çalışmada güncel .hg/mf çiftini hash kontrolüyle yeni
runtime klasörüne kopyalar. Karma örnek: 12000 Carbon, 25 CASING, böl/birleştir/taşı,
miktar ayarı, Neutron Cannon seti, tarif, gemi ve aktif alet arşivi; ardından ikisini
geri getirme. Arşivlenmiş ve geri getirilmiş iki durumda GOG Write/Read JSON eşitliği
başarılı. 12/6/18/18 dizileri korundu. 26 envanter görünümü ortak snapshot'ta üretildi.
Canlı oyun kaydına ve oyun belleğine yazılmadı. 1100 girdinin hepsi oyun içinde denenmedi.

## Sınırlar

Aletin ortak prosedürel modelinde arşiv ailesi kesin belirlenemezse kullanıcı seçer;
özel modeller model yolu ve bilinen ödül tohumlarıyla tanınır. Native gemi arşivinde
organik / Corvette türleri henüz desteklenmez. Setler sabit katalog teknolojilerini
kullanır; S/X prosedürel modül tohumları kopyalanmaz. Miktar azaltma yalnız açık seçilmiş
yığın üzerinde yapılır; sıfır/silme desteklenmez. Bilinmeyen özel kargo hedefler arasında
aktarılmaz. Aktif gemi arşivi istasyonda kaydedilmiş olmayı gerektirir.

FleetManager kardeş klasörü Git deposu değildir; bu turdaki boş arşiv şablonu değişimi
`patches/fleet-archive-template.patch` içinde sürümlenir. Önceki Unicode codec düzeltmesi
gereklidir ve aynı çalışma alanında zaten uygulanmıştır. CapsLockFix değiştirilmedi.
