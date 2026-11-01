# Canlı filo: GOG 179666

2 Kasım 2026 tarihinde mevcut oyun sürecinde salt okunur alanlar ve geri
alınabilir envanter işlemleri incelendi. Kullanıcı oyunda Esc duraklatma
menüsünü açtı; Application.mbPaused bayrağı 0'dan 1'e geçtiği gözlendi.

## Doğrulanan yerleşim

PlayerState, Application.mpData + `0xB940` başlangıcındadır.

| Alan | PlayerState offset | Stride / tür |
|---|---|---|
| Gemi kaynakları | `0x17EE0` | 12 × `0x48` |
| Ana gemi kargo envanteri | `0x7458` | 12 × `0x248` |
| Eski Cargo envanteri | `0x8FC8` | 12 × `0x248` |
| Teknoloji envanteri | **`0xAB28`** | 12 × `0x248` |
| Aktif gemi | `0x182A0` | uint32, 0 tabanlı |

Yakın tarihli 179105 NMS.py kaynak tanımında teknoloji dizisi `0xAA28`.
Bu adres yerel 179666 kurulumunda geçerli inventory header vermedi;
`0xAB28` canlı teknoloji öğeleri, sınıf, boyut ve slotlarla doğrulandı.
Bu bir sürüm farkı gözlemidir; güncel upstream'in yanlış olduğu iddiası değildir.

ResourceElement: filename dinamik string pointer'ı `+0x10`, uzunluk `+0x18`,
uint64 seed `+0x30`. Yalnız okunur; pointer / resource handle yazılmaz.

InventoryStore: 16 uint64 grid satırı `+0x00`, int16 width / height / capacity
`+0x80/+0x82/+0x84`. Item vector header `+0x88`: uint32 allocation capacity,
uint32 length, uint64 pointer. Özel slot vector header `+0xC0` aynı biçimdedir.

InventoryElement: `0x30` byte; ID 16 byte `+0`, X/Y int32 `+0x10/+0x14`,
Amount int32 `+0x18`, DamageFactor float32 `+0x1C`, MaxAmount int32 `+0x20`,
Type int32 `+0x24`, AddedAutomatically / FullyInstalled bool `+0x28/+0x29`.
Türler gözlenen eşya ve kayda göre Substance=0, Technology=1, Product=2.

## Önemli çalışma zamanı farkları

- Bazı pasif / tüketimsiz teknolojilerde `Amount=-1` gözlendi. Bu değer,
  tükenmiş batarya gibi ele alınmadı. Onarımda bu işaret korunur.
- Yeni alınmış bir Fighter'da Width=7, Height=5, Capacity=24 iken 16 satırlık
  grid buffer'ında altıncı satırda da eski bitler vardı. Taze codec kaydı yalnız
  aktif 7×5 dikdörtgende 24 valid slot içeriyordu. Tüm 16 satırın popcount'unu
  kapasite saymak yanlıştı. Kullanılmayan bitler noop / onarımda korunur.
- Source snapshot'taki filo ile canlı filo kimliği eşleşmeden düzenleme yapılmaz.
  Yeni geminin henüz autosave'e geçmemesi durumunda önce oyun içi kayıt gerekir.
- Gösterilen isim yerine tür + seed + slot seçicisi kullanılır; prosedürel
  isim JSON'da bulunmayabilir. Native aktif sahiplik dizisi 12 olarak korunur.

## Uygulanan yaklaşım ve test

Canlı envanterler taze kayıt kopyasının envanter alanlarına yansıtılır.
FleetManager.mutate ile onarım / max_slots kuralı uygulanır. -1 runtime işareti
korunur. Staged çıktı gerçek GOG codec ile yazılır ve yeniden okuma JSON eşitliği
aranır. Canlı dosyaya uygulanmaz; yalnız izinli sabit bellek alanları projekte edilir.

Onarım için aktif olmayan 1. gemide 5 alanlık canlı uygulama ve özgün capture'a
koşullu geri alma testi başarılı oldu. Kargo byte'ları değişmedi. İlk test komutunun
Türkçe çıktı kodlaması apply sonrasında hata verdi; kendi işlem manifestiyle geri
alma ayrı komutta tamamlandı ve tam capture eşitliği doğrulandı.

Tüm mevcut gemiler için yuva genişletme yolunda 30 alanlık canlı uygulama /
yeniden okuma / koşullu geri alma testi de geçti. Son adımda tüm özgün capture
byte'ları eşleşti; kargo, sahiplik ve model alanlarında değişiklik kalmadı.

Bellek işlemleri Esc ile duraklatılmış offline motorda yapılır. Application
başlangıcına göre `mbPaused=0xB8D5`, `mbMultiplayerActive=0xB8D8` kontrol edilir.
Uygulama sırasında pause kapanırsa / oturum veya envanter değişirse yazım durur.
Hata geri alması da pointer / yapı ve beklenen byte koşullarına bağlıdır.

## Henüz doğrulanmayan sahiplik işlemleri

Canlı ekleme / silme / model değiştirme için yalnız ResourceElement kopyalamak
yeterli kabul edilmedi. Şu parçalar henüz oyun thread'inde doğrulanmadı:
ship ownership oluşturma / kaldırma, inventory vector allocation / destructor,
resource handle yaşam döngüsü, spawn / destroy, mesh refresh ve aktif gemi değişimi.
Kaynakta sGcShipData alanlarının bazıları zaten belirsiz olarak işaretlenmiş.
Bu işlemlerin aktif düğmeleri eklenmedi. Mevcut kapalı-oyun FleetManager yolu korunur.
