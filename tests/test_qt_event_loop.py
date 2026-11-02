"""Exercise the real Windows message loop in a child: GIL failures are fatal."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


def probe(native_hotkey=False):
    import ctypes
    from unittest.mock import patch
    from nmsmenu.qt_ui import Q, QtCore, Window, run_event_loop
    from nmsmenu.i18n import Translator, atomic_json
    from nmsmenu.shared_scan import DiskScanner, SharedScan

    app = Q.QApplication([])
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'runtime') as temp, \
            patch.object(SharedScan, 'fast', return_value={'live': None, 'fleet': [], 'error': ''}), \
            patch.object(DiskScanner, 'signature', return_value=()), \
            patch.object(DiskScanner, 'scan', return_value={'saves': [], 'garage': [], 'history': [], 'errors': []}):
        settings = Path(temp) / 'settings.json'
        if native_hotkey:
            atomic_json(settings, {'overlay_hotkey': 'Ctrl+Alt+Shift+F24'})
        w = Window(translator=Translator(settings=settings))
        counts = {'qt': 0, 'tk': 0, 'shown': False, 'hidden': False, 'native': False}
        failures = []
        w.legacy.report_callback_exception = lambda *error: failures.append(str(error[1]))
        timer = QtCore.QTimer(w)
        timer.timeout.connect(lambda: counts.update(qt=counts['qt'] + 1))
        timer.start(30)

        def exercise():
            counts['tk'] += 1
            w.resize(1100 + counts['tk'] % 3, 740)
            w.main_book.setCurrentIndex(w.settings_index)
            if native_hotkey:
                assert w.overlay_hotkey.registered, f'Hotkey error: {w.overlay_hotkey.error_code}'
                # A real WM_HOTKEY must pass through Qt's native filter.
                user32 = ctypes.WinDLL('user32', use_last_error=True)
                from ctypes import wintypes
                user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
                user32.PostMessageW.restype = wintypes.BOOL
                assert user32.PostMessageW(int(w.winId()), 0x0312, w.overlay_hotkey.identifier, 0)
            else:
                w.shortcut_overlay()
            w.legacy.after(150, check_shown)

        def check_shown():
            counts['shown'] = bool(w.overlay_panel and w.overlay_panel.isVisible())
            counts['native'] = native_hotkey and counts['shown']
            if native_hotkey:
                assert w.overlay_panel.window_api().GetForegroundWindow() == int(w.overlay_panel.winId()), 'Overlay did not receive foreground input'
                assert not w.overlay_panel.testAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
            w.shortcut_overlay()
            counts['hidden'] = not w.overlay_panel.isVisible()
            # Modal Qt dialogs run a nested loop; pending Tk callbacks must
            # also survive that path and a later normal close.
            dialog = Q.QMessageBox(parent=w)
            dialog.setText('UI loop test')
            QtCore.QTimer.singleShot(100, dialog.accept)
            dialog.exec()
            w.legacy.after(300, w.close)

        w.show()
        w.legacy.after(200, exercise)
        w.legacy.after(5000, w.close)
        run_event_loop(app, w)
        assert not failures, failures
        assert counts['qt'] >= 2 and counts['tk'] and counts['shown'] and counts['hidden'], counts
        if native_hotkey:
            assert counts['native'], counts
        assert w.controller.disk_signature == (), 'Background scan did not finish'
        print('QT_LOOP_OK', counts, flush=True)


class EventLoopRegression(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Windows Tk/Qt GIL regression')
    def test_timers_overlay_modal_dialog_and_scan_survive(self):
        result = subprocess.run([sys.executable, '-u', '-X', 'faulthandler', '-m',
                                 'tests.test_qt_event_loop', '--probe'],
                                cwd=Path(__file__).resolve().parents[1],
                                env=dict(os.environ, PYTHONIOENCODING='utf-8'),
                                capture_output=True, encoding='utf-8', errors='replace', timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('QT_LOOP_OK', result.stdout)


if __name__ == '__main__':
    if '--probe' in sys.argv:
        probe('--native-hotkey' in sys.argv)
    else:
        unittest.main()
