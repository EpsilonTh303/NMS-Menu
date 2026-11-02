"""Non-injected overlay using the existing guarded live controller/backend."""
import sys
import logging
from PySide6 import QtCore, QtGui, QtWidgets as Q
from .icons import icon
from .live import SETTINGS

LOG = logging.getLogger(__name__)
DEFAULT_HOTKEY = 'Ctrl+Alt+F9'


def hotkey_spec(sequence):
    """One modified letter, digit or function key, mapped to Win32 keys."""
    sequence = QtGui.QKeySequence(sequence)
    if sequence.count() != 1:
        raise ValueError('Panel kısayolu için Ctrl, Alt veya Shift ile bir harf, sayı ya da F1–F24 seçin.')
    combination = sequence[0]
    modifiers = combination.keyboardModifiers()
    key = combination.key().value
    mask = 0
    for qt, win in ((QtCore.Qt.KeyboardModifier.ControlModifier, 2),
                    (QtCore.Qt.KeyboardModifier.ShiftModifier, 4),
                    (QtCore.Qt.KeyboardModifier.AltModifier, 1)):
        if modifiers & qt:
            mask |= win
    allowed = (QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.ShiftModifier |
               QtCore.Qt.KeyboardModifier.AltModifier)
    if not mask or modifiers & ~allowed:
        raise ValueError('Panel kısayolu için Ctrl, Alt veya Shift ile bir harf, sayı ya da F1–F24 seçin.')
    if QtCore.Qt.Key.Key_F1.value <= key <= QtCore.Qt.Key.Key_F24.value:
        virtual_key = 0x70 + key - QtCore.Qt.Key.Key_F1.value
    elif ord('A') <= key <= ord('Z') or ord('0') <= key <= ord('9'):
        virtual_key = key
    else:
        raise ValueError('Panel kısayolu için Ctrl, Alt veya Shift ile bir harf, sayı ya da F1–F24 seçin.')
    return sequence.toString(QtGui.QKeySequence.SequenceFormat.PortableText), mask | 0x4000, virtual_key


def display_state(state, ships, translate):
    loaded = bool(state and state.get('loaded'))
    currencies = state.get('currencies', {}) if loaded else {}
    values = {key: f'{currencies[key]:,}' if type(currencies.get(key)) is int else '—'
              for key in ('Units', 'Nanit', 'Quicksilver')}
    return {'status': translate('Bağlı ve kayıt yüklü' if loaded else 'Canlı bağlantı / kayıt bekleniyor'),
            'values': values, 'ships': str(len(ships)) if loaded and ships else '—'}


class GlobalHotkey(QtCore.QAbstractNativeEventFilter):
    """Own one Windows hotkey. Never changes the CapsLock keyboard hook."""
    IDENTIFIER = 0x4E4D

    def __init__(self, callback, sequence=DEFAULT_HOTKEY, identifier=None, hwnd=None):
        super().__init__()
        self.callback = callback
        self.registered = False
        self.error_code = 0
        self.identifier = self.IDENTIFIER if identifier is None else identifier
        self.hwnd = hwnd
        self.sequence, modifiers, key = hotkey_spec(sequence)
        if sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            self.user32 = ctypes.WinDLL('user32', use_last_error=True)
            self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self.user32.RegisterHotKey.restype = wintypes.BOOL
            self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            self.user32.UnregisterHotKey.restype = wintypes.BOOL
            # Target the menu window so the message belongs to this UI and
            # passes through Qt's native window event filter.
            self.registered = bool(self.user32.RegisterHotKey(self.hwnd, self.identifier, modifiers, key))
            if not self.registered:
                self.error_code = ctypes.get_last_error()
                LOG.error('Overlay kısayolu kaydedilemedi: %s; Windows=%s (%s)',
                          self.sequence, self.error_code, ctypes.FormatError(self.error_code).strip())
        else:
            LOG.error('Global panel kısayolu yalnız Windows üzerinde destekleniyor.')
        if self.registered:
            Q.QApplication.instance().installNativeEventFilter(self)
            LOG.info('Overlay kısayolu hazır: %s', self.sequence)

    def nativeEventFilter(self, event_type, message):
        if self.registered and bytes(event_type) in (b'windows_generic_MSG', b'windows_dispatcher_MSG'):
            import ctypes
            from ctypes import wintypes
            event = wintypes.MSG.from_address(int(message))
            if event.message == 0x0312 and event.wParam == self.identifier:
                LOG.info('Overlay kısayoluna basıldı: %s', self.sequence)
                try:
                    self.callback()
                except Exception:
                    LOG.exception('Overlay açılamadı')
                return True, 0
        return False, 0

    def close(self):
        if self.registered:
            self.user32.UnregisterHotKey(self.hwnd, self.identifier)
            app = Q.QApplication.instance()
            if app:
                app.removeNativeEventFilter(self)
            self.registered = False


class DragHandle(Q.QLabel):
    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self.offset = None
        self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - self.panel.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.offset is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.panel.move(event.globalPosition().toPoint() - self.offset)

    def mouseReleaseEvent(self, event):
        self.offset = None


class GameOverlay(Q.QDialog):
    def __init__(self, owner):
        super().__init__(None, QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.owner = owner
        # This is an interactive menu: Windows must transfer focus away from
        # the game so its cursor capture cannot consume our clicks.
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.return_window = None
        self.setWindowTitle('NMS Menu Overlay')
        self.setObjectName('overlayCard')
        self.setStyleSheet(owner.styleSheet() + '\n#overlayCard { border:1px solid #a56d65; border-radius:12px; background:#0b202a; }')
        self.setWindowOpacity(.96)
        layout = Q.QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        row = Q.QHBoxLayout()
        self.handle = DragHandle(self)
        row.addWidget(self.handle, 1)
        close = Q.QPushButton('×')
        close.setFixedSize(30, 28)
        close.setStyleSheet('padding:0; font-size:20px;')
        close.clicked.connect(self.close)
        row.addWidget(close)
        layout.addLayout(row)
        self.status = Q.QLabel()
        layout.addWidget(self.status)
        self.values = {}
        grid = Q.QGridLayout()
        for index, key in enumerate(('Units', 'Nanit', 'Quicksilver')):
            label, value = Q.QLabel(), Q.QLabel('—')
            value.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            value.setStyleSheet('font-size:16px; color:#eff4f6;')
            self.values[key] = (label, value)
            grid.addWidget(label, index, 0)
            grid.addWidget(value, index, 1)
        layout.addLayout(grid)
        self.fleet = Q.QLabel()
        layout.addWidget(self.fleet)
        self.controls = Q.QGroupBox()
        controls = Q.QGridLayout(self.controls)
        self.currency = Q.QComboBox()
        self.currency.setMinimumWidth(0)
        self.currency.setSizePolicy(Q.QSizePolicy.Policy.Ignored, Q.QSizePolicy.Policy.Fixed)
        for key in ('Units', 'Nanit', 'Quicksilver'):
            self.currency.addItem(key, key)
        self.amount = Q.QSpinBox()
        self.amount.setRange(0, 2_000_000_000)
        self.amount.setGroupSeparatorShown(True)
        self.amount.setFixedWidth(125)
        self.money_apply = Q.QPushButton()
        self.money_apply.clicked.connect(self.apply_currency)
        controls.addWidget(self.currency, 0, 0)
        controls.addWidget(self.amount, 0, 1)
        controls.addWidget(self.money_apply, 0, 2)
        self.setting = Q.QComboBox()
        self.setting.setMinimumWidth(0)
        self.setting.setSizePolicy(Q.QSizePolicy.Policy.Ignored, Q.QSizePolicy.Policy.Fixed)
        for key, field in SETTINGS.items():
            self.setting.addItem(field.title, key)
        self.setting_amount = Q.QDoubleSpinBox()
        self.setting_amount.setDecimals(2)
        self.setting_amount.setFixedWidth(125)
        self.setting.currentIndexChanged.connect(self.select_setting)
        self.setting_apply = Q.QPushButton()
        self.setting_apply.clicked.connect(self.apply_setting)
        controls.addWidget(self.setting, 1, 0)
        controls.addWidget(self.setting_amount, 1, 1)
        controls.addWidget(self.setting_apply, 1, 2)
        self.undo = Q.QPushButton()
        self.undo.clicked.connect(lambda: self.dispatch('undo'))
        self.restore = Q.QPushButton()
        self.restore.clicked.connect(lambda: self.dispatch('restore'))
        controls.addWidget(self.undo, 2, 0, 1, 3)
        controls.addWidget(self.restore, 3, 0, 1, 3)
        layout.addWidget(self.controls)
        controls.setColumnStretch(0, 1)
        self.note = Q.QLabel()
        self.note.setWordWrap(True)
        self.note.setMaximumWidth(410)
        layout.addWidget(self.note)
        self.input_hint = Q.QLabel()
        self.input_hint.setWordWrap(True)
        layout.addWidget(self.input_hint)
        self.back_button = Q.QPushButton()
        self.back_button.clicked.connect(self.close)
        layout.addWidget(self.back_button)
        self.select_setting()
        row = Q.QHBoxLayout()
        self.live_button = Q.QPushButton()
        self.live_button.setIcon(icon('signal'))
        self.live_button.clicked.connect(lambda: self.open_menu(0))
        row.addWidget(self.live_button)
        self.capital_button = Q.QPushButton()
        self.capital_button.setIcon(icon('ship'))
        self.capital_button.clicked.connect(lambda: self.open_menu(7))
        row.addWidget(self.capital_button)
        layout.addLayout(row)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)
        self.setFixedWidth(440)
        self.refresh()
        self.adjustSize()
        screen = Q.QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 18, screen.top() + 35)

    def refresh(self):
        t = self.owner.t
        host = self.owner.controller
        state = display_state(host.live_panel.state, host.live_fleet_panel.ships, t)
        hotkey = self.owner.overlay_hotkey
        self.handle.setText('NMS Menu • ' + hotkey.sequence if hotkey and hotkey.registered else 'NMS Menu')
        self.status.setText(state['status'])
        for key, (label, value) in self.values.items():
            label.setText(t(key))
            value.setText(state['values'][key])
        self.fleet.setText(t('Aktif gemi sayısı: {v0}').replace('{v0}', state['ships']))
        self.controls.setTitle(t('Canlı kontroller'))
        self.money_apply.setText(t('Değiştir'))
        self.money_apply.setToolTip(t('Miktarı ayarla'))
        self.setting_apply.setText(t('Uygula'))
        self.setting_apply.setToolTip(t('Oyunda hemen uygula'))
        self.undo.setText(t('Son para işlemini geri al'))
        self.restore.setText(t('Değiştirdiğim ayarları geri al'))
        for index, key in enumerate(SETTINGS):
            self.setting.setItemText(index, t(SETTINGS[key].title))
        for index, key in enumerate(('Units', 'Nanit', 'Quicksilver')):
            self.currency.setItemText(index, t(key))
        ready = bool(host.live_panel.state and host.live_panel.state.get('loaded') and not host.busy)
        self.money_apply.setEnabled(ready)
        self.setting_apply.setEnabled(ready)
        self.undo.setEnabled(ready and bool(host.live_panel.backend.currency_undo))
        self.restore.setEnabled(ready and bool(host.live_panel.backend.originals))
        self.note.setText(t('Oyun kaydederse para kalıcı olur. Geri alma, değer hâlâ aynıysa çalışır.'))
        self.input_hint.setText(t('Panel açıkken fare ve klavye panelde çalışır. Kısayolla oyuna dön.'))
        self.back_button.setText(t('Oyun ekranına dön'))
        self.live_button.setText(t('Canlı kontroller'))
        self.capital_button.setText(t('Yük gemisi / fırkateyn'))
        self.adjustSize()

    def show_interactive(self):
        if sys.platform == 'win32':
            user32 = self.window_api()
            previous = user32.GetForegroundWindow()
            if previous and previous != int(self.winId()):
                self.return_window = previous
        self.show()
        self.raise_()
        self.activateWindow()
        self.currency.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)
        if sys.platform == 'win32':
            hwnd = int(self.winId())
            focused = bool(user32.SetForegroundWindow(hwnd))
            if user32.GetForegroundWindow() == hwnd:
                # NMS clips its mouse to the game window. Unclip only after
                # this menu actually owns foreground input.
                user32.ClipCursor(None)
                LOG.info('Overlay giriş odağını aldı; fare serbest')
            else:
                LOG.warning('Overlay odağı alınamadı: SetForegroundWindow=%s', focused)

    @staticmethod
    def window_api():
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.IsWindow.restype = wintypes.BOOL
        user32.ClipCursor.argtypes = [ctypes.c_void_p]
        user32.ClipCursor.restype = wintypes.BOOL
        return user32

    def return_input(self):
        if sys.platform == 'win32' and self.return_window:
            user32 = self.window_api()
            if user32.GetForegroundWindow() == int(self.winId()) and user32.IsWindow(self.return_window):
                LOG.info('Overlay giriş odağını önceki pencereye bırakıyor')
                user32.SetForegroundWindow(self.return_window)
        self.return_window = None

    def select_setting(self):
        key = self.setting.currentData()
        field = SETTINGS[key]
        self.setting_amount.setRange(field.minimum, field.maximum)
        state = self.owner.controller.live_panel.state or {}
        self.setting_amount.setValue(state.get('settings', {}).get(key, field.minimum))

    def apply_currency(self):
        self.dispatch('currency', self.currency.currentData(), self.amount.value())

    def apply_setting(self):
        self.dispatch('setting', self.setting.currentData(), self.setting_amount.value())

    def dispatch(self, operation, key=None, value=None):
        host = self.owner.controller
        panel = host.live_panel
        if host.busy or not panel.state or not panel.state.get('loaded'):
            return
        backend = panel.backend
        actions = {'currency': lambda: backend.set_currency(key, value),
                   'setting': lambda: backend.set_setting(key, value),
                   'undo': backend.undo_currency, 'restore': backend.restore_settings}
        host.run(actions[operation], panel.render)
        self.refresh()

    def open_menu(self, index):
        self.owner.overlay_toggle.setChecked(False)
        self.owner.controller.book.select(index)
        self.owner.tick()
        self.owner.showNormal()
        self.owner.raise_()
        self.owner.activateWindow()

    def reject(self):
        # QDialog's default Escape path merely hides the window, leaving the
        # toggle checked and preventing the next shortcut from reopening it.
        self.close()

    def closeEvent(self, event):
        self.return_input()
        self.timer.stop()
        self.owner.overlay_toggle.setChecked(False)
        event.accept()
