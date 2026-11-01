import argparse
import sys

from nmsmenu.ui import main

if __name__ == '__main__':
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='No Man’s Sky masaüstü kontrol paneli')
    parser.add_argument('--connect', action='store_true', help='Açılışta oyuna salt okunur ilk bağlantıyı kur')
    tabs = parser.add_mutually_exclusive_group()
    tabs.add_argument('--fleet', action='store_true', help='Canlı filo sekmesini aç')
    tabs.add_argument('--weapons', action='store_true', help='Silah koleksiyonu sekmesini aç')
    args = parser.parse_args()
    main(connect=args.connect, fleet=args.fleet, weapons=args.weapons)
