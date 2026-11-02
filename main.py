import argparse
import sys

from nmsmenu.ui import main

if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='No Man’s Sky masaüstü kontrol paneli')
    parser.add_argument('--connect', action='store_true', help='Uyumluluk seçeneği; bağlantı artık açılışta otomatik')
    tabs = parser.add_mutually_exclusive_group()
    tabs.add_argument('--fleet', action='store_true', help='Canlı filo sekmesini aç')
    tabs.add_argument('--weapons', action='store_true', help='Silah koleksiyonu sekmesini aç')
    tabs.add_argument('--catalog', action='store_true', help='Ortak ekleme kataloğunu aç')
    tabs.add_argument('--inventory', action='store_true', help='Envanter, donanım ve arşiv ekranını aç')
    args = parser.parse_args()
    main(connect=args.connect, fleet=args.fleet, weapons=args.weapons, catalog=args.catalog, inventory=args.inventory)
