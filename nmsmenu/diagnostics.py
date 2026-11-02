"""Console diagnostics; start.cmd also saves the complete child output."""
import faulthandler
import logging
import sys
import threading


def install():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s [%(threadName)s] %(name)s: %(message)s')
    if sys.stderr is not None:
        faulthandler.enable(all_threads=True)

    def report(kind, value, trace):
        logging.getLogger('menu').critical('Beklenmeyen hata', exc_info=(kind, value, trace))

    sys.excepthook = report
    threading.excepthook = lambda args: report(args.exc_type, args.exc_value, args.exc_traceback)
    logging.getLogger('menu').info('Menü başlatılıyor: Python %s', sys.version.split()[0])


def tk_error(kind, value, trace):
    logging.getLogger('menu.tk').error('Arayüz işlemi başarısız', exc_info=(kind, value, trace))
