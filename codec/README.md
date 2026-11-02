# Kayıt codec'i

Menu, kayıtları okumak ve yeniden kodlamak için **libNOM.io CLI 0.14.2**
Windows x64 sürümünü kullanır. Konum `codec/libNOM.io.cli.exe` dosyasıdır.

`setup.cmd` veya `python tools/install_codec.py` resmî sürümü indirir.
İndirme boyutu ve SHA-256 değeri `manifest.json` ile doğrulanmadan dosya
kullanıma alınmaz. `python tools/install_codec.py --check` indirmeden doğrular.
Kurucu codec'i çalıştırmaz; bozuk indirme mevcut dosyanın üzerine yazılmaz.

İkili dosya Git'e eklenmez. Sürüm kaynağı ve üçüncü taraf lisansı:

- [Resmî sürüm](https://github.com/zencq/libNOM.io/releases/tag/0.14.2)
- [Kaynak ve lisans](https://github.com/zencq/libNOM.io/tree/0.14.2)

Eski SolarShipFix yedekleri mevcut kurulumda `runtime/legacy-solar/`
altında korunur. Yeni işlemler için `fleet.py` kullanın.
