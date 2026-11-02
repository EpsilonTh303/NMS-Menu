# Deneysel oyun içi gemi ödülü köprüsü

**Oyun içinde test edilmedi.** Yalnız SHA256 ile sabitlenmiş GOG 179666
sürümüne yöneliktir. Menü kendiliğinden kod enjekte etmez.

1. Oyunu mevcut CapsLockFix başlatıcınızla açın ve kaydı yükleyin.
2. `Menu/native-bridge.cmd` çalıştırın. İlk çalıştırma ayrı bir sanal ortama
   PyPI'den `pymhf[gui]==0.2.5` kurar; sonraki adım çalışan oyuna hook yükler.
3. Menüde **Canlı filo → Deneysel oyun içi gemi ödülü** bölümünü açın.
4. Yedi yerel ödülden birini seçin, test edilmemiş desteği kabul edip sıraya alın.
5. Oyun içinde doğal bir ödül alındığında, aynı callback içinde ek native
   gemi ödülü çağrısı denenir. Teslim/karşılaştırma ekranı açılabilir;
   eklemek istiyorsanız mevcut gemiyi takas etmek yerine filoya eklemeyi seçin.

Bu sürüm anında veya sınırsız gemi verme garantisi sunmaz. Normal Living Ship
profili çevrimdışı katalogdadır; köprüdeki organik seçenek yerel **The Wraith**
ödülüdür. Özel gemiler oyun tarafından kendi ödül parametreleriyle oluşturulur;
menüdeki çevrimdışı profilin sınıf/donanım/seed ayarları bu yola taşınmaz.

Her köprü yüklemesinde en fazla **bir native çağrı denemesi** yapılır. Native
çağrıdan sonra durum yalnız `dispatched` olur; gemi sahipliği doğrulanmış
sayılmaz. Aynı isteği yeniden deneme, otomatik takas, sabit sahiplik dizisini
büyütme veya doğrudan resource/vector pointer yazımı yoktur.

İstek 120 saniyede geçersizleşir. Köprü nonce'u, kayıt oturumu, sahip olunan
gemi kimlikleri, boş native yuva ve model/seed tekrarı denetlenir. İstekten
önce `%APPDATA%/HelloGames/NMS/DefaultUser` kayıtları hash doğrulamasıyla
`runtime/native-ship-bridge/backups/ISTEK_ID/` altına kopyalanır. Kuyruk,
heartbeat, alınmış istek ve sonuçlar aynı özel runtime dizininde tutulur.

## Tam kayıt geri alma

Oyunu normal kapatın. Açık oyunu zorla sonlandırmayın.

```powershell
python -m nmsmenu.runtime_ship restore-backup ISTEK_ID
```

Bu işlem **isteğin alındığı zamanki tam kayıt dosyalarına döner**; o zamandan
sonraki ilerleme eski kopyalarda yoktur. Yeni durum ayrıca mevcut `fleet.py`
motorunun `before-restore-*` ve rollback yedeklerinde korunur. Gemiye özel
geri alma değildir. Köprü otomatik restore yapmaz.

## İncelenen birincil kaynaklar

- [NMS.py types.py](https://github.com/monkeyman192/NMS.py/blob/master/nmspy/data/types.py): native ödül çağrısının ABI referansı.
- [NMS-Newton interactions.py](https://github.com/monkeyman192/NMS-Newton/blob/main/interactions.py): gerçek ödül callback'i, peek ayrımı ve tekrarlı çağrı gözlemi.
- [pyMHF hook tanımları](https://github.com/monkeyman192/pyMHF/blob/59112ba33e7cd06e2e3764c4cca92f98d13022a1/docs/docs/creating_hook_definitions.rst): method hook ve instance üzerinden çağrı API'si.
- [pyMHF 0.2.5](https://pypi.org/project/pyMHF/0.2.5/): isteğe bağlı bağımlılık, MIT lisanslı ayrı proje.

Uygulama bağımsız yazıldı; upstream mod uygulamaları kopyalanmadı. Yerel
reward tablosundan yalnız yedi tek-gemi ödülünün kimlik/model/seed bilgisi
`data/native-ship-rewards.json` içine çıkarıldı. `preflight` yalnız build
hash'i ve tekil native imza konumunu denetler; ABI ve oynanış testi değildir.
