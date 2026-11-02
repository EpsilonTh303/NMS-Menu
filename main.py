import argparse
import sys


if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='No Man’s Sky masaüstü kontrol paneli')
    parser.add_argument('--connect', action='store_true', help='Uyumluluk seçeneği; bağlantı artık açılışta otomatik')
    parser.add_argument('--classic', action='store_true', help='Önceki Tk arayüzünü aç')
    tabs = parser.add_mutually_exclusive_group()
    tabs.add_argument('--fleet', action='store_true', help='Canlı filo sekmesini aç')
    tabs.add_argument('--weapons', action='store_true', help='Silah koleksiyonu sekmesini aç')
    tabs.add_argument('--catalog', action='store_true', help='Ortak ekleme kataloğunu aç')
    tabs.add_argument('--inventory', action='store_true', help='Envanter, donanım ve arşiv ekranını aç')
    tabs.add_argument('--settings', action='store_true', help='Ayarlar / dil seçimi sekmesini aç (Qt)')
    tabs.add_argument('--capital', action='store_true', help='Yük gemisi ve fırkateyn sekmesini aç')
    args = parser.parse_args()
    if args.classic and args.settings:
        parser.error('--settings Qt arayüzünü gerektirir; --classic ile kullanılamaz.')
    if args.classic:
        from nmsmenu.ui import main
        main(connect=args.connect, fleet=args.fleet, weapons=args.weapons, catalog=args.catalog, inventory=args.inventory, capital=args.capital)
    else:
        from nmsmenu.qt_ui import main
        raise SystemExit(main(inventory=args.inventory or not (args.fleet or args.weapons or args.catalog or args.capital),
                              fleet=args.fleet, weapons=args.weapons, catalog=args.catalog, settings=args.settings, capital=args.capital))
