"""Non-injected overlay using the existing guarded live controller/backend."""
import sys
from PySide6 import QtCore, QtWidgets as Q
from .icons import icon
from .live import SETTINGS


def display_state(state, ships, translate):
    loaded = bool(state and state.get('loaded'))
    currencies = state.get('currencies', {}) if loaded else {}
    values = {key: f'{currencies[key]:,}' if type(currencies.get(key)) is int else '—'
              for key in ('Units', 'Nanit', 'Quicksilver')}
    return {'status': translate('Bağlı ve kayıt yüklü' if loaded else 'Canlı bağlantı / kayıt bekleniyor'),
            'values': values, 'ships': str(len(ships)) if loaded and ships else '—'}


class GlobalHotkey(QtCore.QAbstractNativeEventFilter):
    """Own a single thread hotkey. Never changes the CapsLock keyboard hook."""
    IDENTIFIER = 0x4E4D

    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.registered = False
        if sys.platform == 'win32':
            import ctypes
            self.user32 = ctypes.windll.user32
            # Ctrl + Shift + F8, with repeat suppression.
            self.registered = bool(self.user32.RegisterHotKey(None, self.IDENTIFIER, 0x4000 | 0x0002 | 0x0004, 0x77))
        if self.registered:
            Q.QApplication.instance().installNativeEventFilter(self)

    def nativeEventFilter(self, event_type, message):
        if self.registered and bytes(event_type) in (b'windows_generic_MSG', b'windows_dispatcher_MSG'):
            import ctypes
            from ctypes import wintypes
            event = wintypes.MSG.from_address(int(message))
            if event.message == 0x0312 and event.wParam == self.IDENTIFIER:
                self.callback()
                return True, 0
        return False, 0

    def close(self):
        if self.registered:
            self.user32.UnregisterHotKey(None, self.IDENTIFIER)
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
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
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
        self.handle.setText('NMS Menu • Ctrl+Shift+F8' if hotkey and hotkey.registered else 'NMS Menu')
        self.status.setText(state['status'])
        for key, (label, value) in self.values.items():
            label.setText(t(key))
            value.setText(state['values'][key])
        self.fleet.setText(t('Aktif gemi sayısı: {v0}').replace('{v0}', state['ships']))
        self.controls.setTitle(t('Canlı kontroller'))
        self.money_apply.setText(t('Tamam'))
        self.money_apply.setToolTip(t('Miktarı ayarla'))
        self.setting_apply.setText(t('Tamam'))
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
        self.live_button.setText(t('Canlı kontroller'))
        self.capital_button.setText(t('Yük gemisi / fırkateyn'))
        self.adjustSize()

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
        self.owner.controller.book.select(index)
        self.owner.tick()
        self.owner.showNormal()
        self.owner.raise_()
        self.owner.activateWindow()

    def closeEvent(self, event):
        self.timer.stop()
        self.owner.overlay_toggle.setChecked(False)
        event.accept()
