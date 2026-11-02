"""Qt presentation adapter over the existing, independently validated controllers.

The hidden Tk widgets retain variable bindings, review invalidation and commands.
Qt never writes saves or memory: every action invokes the original controller.
"""
import sys
import html
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vendor'))
from PySide6 import QtCore, QtGui, QtWidgets as Q
from .ui import MenuApp
from .icons import icon, pixmap, for_text, resource_icon
from .i18n import Translator

STYLE = '''
QWidget { background:#0b202a; color:#dce9ed; font:12px "Segoe UI"; }
QMainWindow, #shell { background:#071720; }
QLabel { background:transparent; color:#adc1cb; }
QTabWidget::pane { border:1px solid #36515b; border-radius:13px; padding:8px; background:#0d242e; }
QTabBar::tab { background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1b3541,stop:1 #10232d); border:1px solid #344e59; padding:11px 16px; margin:1px; border-top-left-radius:10px; border-top-right-radius:10px; color:#b8cbd3; }
QTabBar::tab:selected { color:#fff0e8; border-color:#d17d71; background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #9d554e,stop:1 #482f31); }
QPushButton { border:1px solid #57717c; border-radius:7px; padding:8px 16px; background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #2a4653,stop:1 #18303b); }
QPushButton:hover { border-color:#e48b7d; background:#34525e; }
QPushButton:pressed { background:#75443f; }
QPushButton:disabled { color:#61747d; border-color:#243b46; }
QPushButton[accent="true"] { border:1px solid #e58a7a; background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #96554e,stop:1 #503135); }
QComboBox, QLineEdit, QTextEdit, QListWidget { border:1px solid #42606c; border-radius:5px; padding:5px 9px; background:#142d38; selection-background-color:#73504d; }
QComboBox::drop-down { border:0; width:25px; }
QComboBox::down-arrow, QSpinBox::down-arrow { image:url("__ICONS__/chevron-down.svg"); width:12px; height:8px; }
QSpinBox::up-arrow { image:url("__ICONS__/chevron-up.svg"); width:12px; height:8px; }
QSpinBox { border:1px solid #42606c; border-radius:5px; padding:5px 20px 5px 8px; background:#142d38; selection-background-color:#73504d; }
QSpinBox::up-button, QSpinBox::down-button { background:#213d49; border:1px solid #42606c; width:16px; }
QCheckBox { spacing:9px; padding:4px; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid #56717c; border-radius:5px; background:#102732; }
QCheckBox::indicator:checked { background:#ce7769; border-color:#f0a291; image:none; }
QTreeWidget { border:1px solid #3a5662; border-radius:6px; alternate-background-color:#132e3a; background:#0b202a; selection-background-color:#31515c; }
QTreeWidget::item { padding:4px; }
QHeaderView::section { background:#1a3440; color:#aec4cd; padding:5px; border:1px solid #304b57; }
QScrollBar:vertical { background:#0d222c; width:12px; }
QScrollBar::handle:vertical { background:#b46b62; border-radius:5px; min-height:25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
#stats { border:1px solid #385560; border-radius:8px; background:#142f39; padding:0; color:#dfedef; }
'''


class Toggle(Q.QCheckBox):
    """Actual checkbox behavior with the reference's pill-shaped switch."""
    def sizeHint(self):
        return QtCore.QSize(self.fontMetrics().horizontalAdvance(self.text()) + 64, 34)

    def hitButton(self, point):
        return self.rect().contains(point)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor('#8d5a56' if self.isChecked() else '#45616c')))
        painter.setBrush(QtGui.QColor('#98564f' if self.isChecked() else '#203c48'))
        y = (self.height() - 17) / 2
        painter.drawRoundedRect(QtCore.QRectF(8, y, 32, 17), 8.5, 8.5)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor('#fff0e8' if self.isEnabled() else '#627b85'))
        painter.drawEllipse(QtCore.QRectF(25 if self.isChecked() else 10, y+2, 13, 13))
        painter.setPen(QtGui.QColor('#dce9ed' if self.isEnabled() else '#61747d'))
        painter.drawText(QtCore.QRect(50, 0, self.width()-50, self.height()), QtCore.Qt.AlignmentFlag.AlignVCenter, self.text())
        if self.hasFocus():
            painter.setPen(QtGui.QPen(QtGui.QColor('#e38578'), 1, QtCore.Qt.PenStyle.DotLine))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)


class StatsBar(Q.QFrame):
    def __init__(self, translator):
        super().__init__()
        self.translator = translator
        self.setObjectName('stats')
        layout = Q.QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        self.counters = {}
        for key, title, symbol in [('ships', 'Gemi profili', 'ship'), ('tools', 'Alet / tohum varyantı', 'leaf'),
                                   ('technologies', 'Teknoloji', 'chip'), ('items', 'Eşya', 'box'),
                                   ('garage', 'Garaj kaydı', 'garage')]:
            if self.counters:
                divider = Q.QFrame()
                divider.setFrameShape(Q.QFrame.Shape.VLine)
                divider.setStyleSheet('color:#385560; background:#385560;')
                divider.setFixedSize(1, 30)
                layout.addWidget(divider)
            image = Q.QLabel()
            image.setPixmap(pixmap(symbol, 27))
            layout.addWidget(image)
            value = Q.QLabel()
            value.setStyleSheet('background:transparent; padding:0; border:0;')
            self.counters[key] = (value, title)
            layout.addWidget(value, 1)
        info = Q.QLabel()
        info.setPixmap(pixmap('info', 18))
        info.setToolTip('Seçenek sayıları oyundaki toplam tür sayısı değildir.')
        self.setToolTip(info.toolTip())
        layout.addWidget(info)

    def refresh(self, counts):
        self.setToolTip(self.translator.text('Seçenek sayıları oyundaki toplam tür sayısı değildir.'))
        for key, (label, title) in self.counters.items():
            label.setText(f'<b style="font-size:15px;color:#e1edef">{counts[key]}</b><br>{html.escape(self.translator.text(title))}')


class Header(Q.QFrame):
    """Keep artwork as artwork; all header text remains live and translatable."""
    def __init__(self, translator):
        super().__init__()
        self.translator = translator
        self.art = QtGui.QPixmap(str(Path(__file__).resolve().parents[1] / 'assets/reference-banner.png'))
        self.setFixedHeight(122)
        layout = Q.QGridLayout(self)
        layout.setContentsMargins(12, 8, 12, 3)
        logo = Q.QLabel()
        logo.setPixmap(self.art.copy(25, 5, 54, 75))
        layout.addWidget(logo, 0, 0, 2, 1)
        brand = Q.QLabel("NO MAN'S SKY")
        brand.setStyleSheet('font-size:26px; letter-spacing:4px; color:#edf3f5;')
        layout.addWidget(brand, 0, 1)
        self.brand_sub = Q.QLabel()
        self.brand_sub.setStyleSheet('color:#e99c90; letter-spacing:5px; font-weight:600;')
        layout.addWidget(self.brand_sub, 1, 1)
        self.subtitle = Q.QLabel()
        self.subtitle.setWordWrap(True)
        self.subtitle.setMaximumWidth(335)
        layout.addWidget(self.subtitle, 0, 2, 2, 1)
        layout.setColumnStretch(3, 1)
        self.note = Q.QLabel()
        layout.addWidget(self.note, 2, 0, 1, 4)
        self.refresh()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor('#081c26'))
        art = self.art.copy(700, 0, 580, 122)
        painter.drawPixmap(QtCore.QRect(max(540, self.width()-640), 0, 640, 122), art)
        fade = QtGui.QLinearGradient(480, 0, 800, 0)
        fade.setColorAt(0, QtGui.QColor('#081c26'))
        fade.setColorAt(1, QtGui.QColor(8, 28, 38, 0))
        painter.fillRect(QtCore.QRect(480, 0, 320, 122), fade)

    def refresh(self):
        t = self.translator.text
        self.brand_sub.setText(t('Mod Merkezi').upper())
        self.subtitle.setText('<b>' + html.escape(t('Envanter ve Koleksiyon')) + '</b><br>' + html.escape(t('Modüler envanter, eşya ve koleksiyon yöneticisi')))
        self.note.setText('<span style="color:#52bd82">●</span> &nbsp;Offline GOG &nbsp; | &nbsp;' + html.escape(t('Canlı filo: Esc')) + ' &nbsp; | &nbsp;' + html.escape(t('Kayıt dosyası düzenleme: oyun kapalıyken')))


class Window(Q.QMainWindow):
    def __init__(self, inventory=True, fleet=False, weapons=False, catalog=False, start_scan=True, translator=None):
        super().__init__()
        self.translator = translator or Translator()
        self.t = self.translator.text
        self.localized_widgets = []
        self.overlay_panel = None
        self.overlay_hotkey = None
        self.legacy = tk.Tk()
        self.legacy.withdraw()
        self.controller = MenuApp(self.legacy)
        self.legacy.withdraw()
        self.bindings = []
        self.cache = {}
        self.setWindowTitle("No Man's Sky • Mod Merkezi • Qt")
        self.setWindowIcon(icon('ship'))
        available = Q.QApplication.primaryScreen().availableGeometry()
        self.resize(min(1280, available.width()-24), min(920, available.height()-32))
        self.setMinimumSize(1000, 680)
        self.setStyleSheet(STYLE.replace('__ICONS__', (Path(__file__).resolve().parents[1] / 'assets/icons').as_posix()))
        self.patch_dialogs()
        shell = Q.QWidget(objectName='shell')
        outer = Q.QVBoxLayout(shell)
        outer.setContentsMargins(16, 0, 16, 10)
        outer.setSpacing(7)
        self.setCentralWidget(shell)
        header = Header(self.translator)
        outer.addWidget(header)
        self.header = header
        legacy_shell = self.legacy.winfo_children()[0]
        # Original heading/subheading are represented by the supplied masthead.
        for child in legacy_shell.pack_slaves()[2:]:
            widget = self.build(child)
            outer.addWidget(widget, 1 if isinstance(child, ttk.Notebook) else 0)
        self.main_book = next(q for source, q in self.bindings if source is self.controller.book)
        self.add_settings()
        if inventory:
            self.controller.book.select(6)
            self.controller.catalog_panel.book.select(2)
        elif fleet:
            self.controller.book.select(1)
        elif weapons:
            self.controller.book.select(3)
        elif catalog:
            self.controller.book.select(6)
        if start_scan:
            self.controller.start_shared_scan()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(120)
        self.tick()

    def patch_dialogs(self):
        for name, icon in [('showinfo', Q.QMessageBox.Icon.Information), ('showerror', Q.QMessageBox.Icon.Critical), ('showwarning', Q.QMessageBox.Icon.Warning)]:
            def show(title, message, _icon=icon, **kwargs):
                dialog = Q.QMessageBox(_icon, self.t(str(title)), self.t(str(message)), parent=self)
                dialog.setStandardButtons(Q.QMessageBox.StandardButton.Ok)
                dialog.button(Q.QMessageBox.StandardButton.Ok).setText(self.t('Tamam'))
                dialog.exec()
                return 'ok'
            setattr(messagebox, name, show)
        def ask(title, message, **kwargs):
            dialog = Q.QMessageBox(Q.QMessageBox.Icon.Question, self.t(str(title)), self.t(str(message)), parent=self)
            dialog.setStandardButtons(Q.QMessageBox.StandardButton.Yes | Q.QMessageBox.StandardButton.No)
            dialog.setDefaultButton(Q.QMessageBox.StandardButton.No)
            dialog.button(Q.QMessageBox.StandardButton.Yes).setText(self.t('Evet'))
            dialog.button(Q.QMessageBox.StandardButton.No).setText(self.t('Hayır'))
            return dialog.exec() == Q.QMessageBox.StandardButton.Yes
        messagebox.askyesno = ask
        messagebox.askokcancel = ask

    def add_settings(self):
        page = Q.QWidget()
        layout = Q.QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        title = Q.QLabel()
        title.setStyleSheet('font-size:23px; font-weight:600; color:#e1edef;')
        layout.addWidget(title)
        self.localized_widgets.append((title, 'Ayarlar'))
        row = Q.QHBoxLayout()
        language_label = Q.QLabel()
        row.addWidget(language_label)
        self.localized_widgets.append((language_label, 'Arayüz dili'))
        self.language_choice = Q.QComboBox()
        self.language_choice.setMinimumWidth(240)
        row.addWidget(self.language_choice)
        row.addStretch()
        layout.addLayout(row)
        for text in ('Dil değişikliği hemen uygulanır ve bu bilgisayarda saklanır.',
                     'Yeni bir dil eklemek için locales klasörüne bir JSON dosyası ekleyin.',
                     'Eksik çeviriler Türkçe gösterilir.'):
            label = Q.QLabel()
            label.setWordWrap(True)
            layout.addWidget(label)
            self.localized_widgets.append((label, text))
        self.coverage = Q.QLabel()
        layout.addWidget(self.coverage)
        reload_button = Q.QPushButton()
        reload_button.setIcon(icon('refresh'))
        reload_button.clicked.connect(self.reload_languages)
        self.localized_widgets.append((reload_button, 'Dil dosyalarını yenile'))
        layout.addWidget(reload_button, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.overlay_toggle = Q.QCheckBox()
        self.localized_widgets.append((self.overlay_toggle, 'Oyun üstü paneli etkinleştir'))
        self.overlay_toggle.toggled.connect(self.toggle_overlay)
        layout.addWidget(self.overlay_toggle)
        self.overlay_hint = Q.QLabel()
        self.overlay_hint.setWordWrap(True)
        self.localized_widgets.append((self.overlay_hint, 'Ctrl+Shift+F8 ile gizle/göster. Pencere veya kenarlıksız mod gerekir.'))
        layout.addWidget(self.overlay_hint)
        layout.addStretch()
        self.settings_index = self.main_book.addTab(page, icon('settings'), self.t('Ayarlar'))
        self.language_choice.currentIndexChanged.connect(self.change_language)
        self.main_book.currentChanged.connect(lambda index: self.refresh_language_choices() if index == self.settings_index else None)
        self.refresh_language_choices()
        self.retranslate()

    def toggle_overlay(self, enabled):
        from .overlay import GameOverlay, GlobalHotkey
        if enabled:
            if self.overlay_panel is None:
                self.overlay_panel = GameOverlay(self)
            self.overlay_panel.timer.start(500)
            self.overlay_panel.show()
            if self.overlay_hotkey is None:
                self.overlay_hotkey = GlobalHotkey(lambda: self.overlay_panel.setVisible(not self.overlay_panel.isVisible()))
            if not self.overlay_hotkey.registered:
                self.overlay_hint.setText(self.t('Kısayol kullanımda veya desteklenmiyor; panel ayarlardan açılabilir.'))
            self.overlay_panel.refresh()
        else:
            if self.overlay_panel is not None:
                self.overlay_panel.hide()
                self.overlay_panel.timer.stop()
            if self.overlay_hotkey is not None:
                self.overlay_hotkey.close()
                self.overlay_hotkey = None

    def refresh_language_choices(self):
        self.language_choice.blockSignals(True)
        self.language_choice.clear()
        for code, name in self.translator.available().items():
            self.language_choice.addItem(name, code)
        self.language_choice.setCurrentIndex(self.language_choice.findData(self.translator.language))
        self.language_choice.blockSignals(False)

    def reload_languages(self):
        try:
            self.translator.reload()
        except (OSError, ValueError) as exc:
            messagebox.showerror('Dil', str(exc))
            return
        self.refresh_language_choices()
        self.cache.clear()
        self.retranslate()
        self.tick()

    def change_language(self, index):
        code = self.language_choice.itemData(index)
        if not code:
            return
        try:
            self.translator.select(code)
        except (OSError, ValueError) as exc:
            messagebox.showerror('Dil', self.t('Dil tercihi kaydedilemedi: {v0}').replace('{v0}', str(exc)))
            self.refresh_language_choices()
            return
        self.cache.clear()
        self.retranslate()
        self.tick()

    def retranslate(self):
        self.setWindowTitle("No Man's Sky • " + self.t('Mod Merkezi'))
        self.header.refresh()
        for widget, text in self.localized_widgets:
            widget.setText(self.t(text))
        self.main_book.setTabText(self.settings_index, self.t('Ayarlar'))
        total = len([key for key in self.translator.source if key != '_meta'])
        done = sum(bool(self.translator.catalog.get(key)) for key in self.translator.source if key != '_meta')
        self.coverage.setText(self.t('Çeviri kapsamı: {v0}/{v1}').replace('{v0}', str(done)).replace('{v1}', str(total)))

    def dispatch(self, source, event):
        source.event_generate(event)
        self.legacy.update()

    def build(self, source):
        if isinstance(source, ttk.Notebook):
            target = Q.QTabWidget()
            target.setIconSize(QtCore.QSize(23, 23))
            target.setUsesScrollButtons(True)
            for name in source.tabs():
                child = source.nametowidget(name)
                page = self.build(child)
                if source == self.controller.book:
                    scroll = Q.QScrollArea()
                    scroll.setWidgetResizable(True)
                    scroll.setFrameShape(Q.QFrame.Shape.NoFrame)
                    scroll.setWidget(page)
                    page = scroll
                title = source.tab(name, 'text')
                target.addTab(page, icon(for_text(title)), self.t(title))
            target.currentChanged.connect(lambda index: source.select(index) if index < len(source.tabs()) else None)
        elif isinstance(source, ttk.Button):
            target = Q.QPushButton(str(source.cget('text')))
            target.setIcon(icon(for_text(target.text())))
            target.setIconSize(QtCore.QSize(21, 21))
            target.clicked.connect(lambda checked=False: source.invoke())
            if any(s in target.text().lower() for s in ('raporuna git', 'incelediğim')):
                target.setProperty('accent', True)
        elif isinstance(source, ttk.Checkbutton):
            text = str(source.cget('text'))
            target = Toggle(text) if text == 'Otomatik bağlantı ve ortak yenileme' else Q.QCheckBox(text)
            target.clicked.connect(lambda checked=False: source.invoke())
        elif isinstance(source, ttk.Combobox):
            target = Q.QComboBox()
            target.setMinimumWidth(95)
            width = int(source.cget('width'))
            if width < 40:
                target.setMaximumWidth(max(110, width * 8 + 35))
            def select(index):
                source.current(index)
                self.dispatch(source, '<<ComboboxSelected>>')
            target.activated.connect(select)
        elif isinstance(source, ttk.Spinbox):
            target = Q.QSpinBox()
            target.setRange(int(float(source.cget('from'))), int(float(source.cget('to'))))
            target.setSingleStep(int(float(source.cget('increment'))))
            target.setMaximumWidth(110)
            target.setKeyboardTracking(True)
            target.valueChanged.connect(lambda value: source.setvar(str(source.cget('textvariable')), str(value)))
        elif isinstance(source, (ttk.Entry, tk.Entry)):
            target = Q.QLineEdit()
            target.setMinimumWidth(45)
            target.setMaximumWidth(90 if isinstance(source, ttk.Spinbox) else 500)
            def edit(value):
                variable = str(source.cget('textvariable'))
                if variable:
                    source.setvar(variable, value)
                else:
                    source.delete(0, 'end')
                    source.insert(0, value)
            target.textEdited.connect(edit)
        elif isinstance(source, ttk.Treeview):
            target = Q.QTreeWidget()
            target.setRootIsDecorated(False)
            target.setAlternatingRowColors(True)
            columns = source.cget('columns')
            target.setHeaderLabels([source.heading(c, 'text') for c in columns])
            target.setSelectionMode(Q.QAbstractItemView.SelectionMode.ExtendedSelection if source.cget('selectmode') == 'extended' else Q.QAbstractItemView.SelectionMode.SingleSelection)
            target.setMinimumHeight(85)
            target.setMaximumHeight(150 if int(source.cget('height')) <= 3 else 16777215)
            if source is self.controller.capital_panel.tree:
                target.setFixedHeight(150)
            def select_tree():
                source.selection_set([item.data(0, QtCore.Qt.ItemDataRole.UserRole) for item in target.selectedItems()])
                self.dispatch(source, '<<TreeviewSelect>>')
            target.itemSelectionChanged.connect(select_tree)
        elif isinstance(source, tk.Listbox):
            target = Q.QListWidget()
            def select_list():
                source.selection_clear(0, 'end')
                for item in target.selectedIndexes():
                    source.selection_set(item.row())
                self.dispatch(source, '<<ListboxSelect>>')
            target.itemSelectionChanged.connect(select_list)
        elif isinstance(source, tk.Text):
            target = Q.QTextEdit()
            target.setMinimumHeight(75)
            target.setMaximumHeight(max(90, min(300, int(source.cget('height')) * 17)))
            def text_edit():
                if str(source.cget('state')) != 'disabled':
                    source.delete('1.0', 'end')
                    source.insert('1.0', target.toPlainText())
            target.textChanged.connect(text_edit)
        elif isinstance(source, tk.Canvas):
            target = InventoryCanvas(source, self.controller.catalog_panel.workbench)
        elif isinstance(source, (ttk.Label, tk.Label)):
            if source == self.controller.catalog_panel.overview:
                target = StatsBar(self.translator)
                self.bindings.append((source, target))
                return target
            target = Q.QLabel(str(source.cget('text')))
            target.setWordWrap(int(source.cget('wraplength') or 0) > 0)
            if source == self.controller.catalog_panel.overview:
                target.setObjectName('stats')
            font = str(source.cget('font'))
            if 'bold' in font:
                target.setStyleSheet('font-size:19px; font-weight:600; color:#e3edef; padding:3px 0;')
        elif isinstance(source, (ttk.Scrollbar, tk.Scrollbar)):
            target = Q.QWidget()
            target.setFixedSize(0, 0)
        elif isinstance(source, ttk.LabelFrame):
            target = Q.QGroupBox(self.t(str(source.cget('text'))))
            self.layout_children(source, target)
        else:
            target = Q.QWidget()
            self.layout_children(source, target)
        self.bindings.append((source, target))
        return target

    def layout_children(self, source, target):
        if source.grid_slaves():
            layout = Q.QGridLayout(target)
            for child in reversed(source.grid_slaves()):
                info = child.grid_info()
                row, col = int(info['row']), int(info['column'])
                layout.addWidget(self.build(child), row, col, int(info['rowspan']), int(info['columnspan']))
                layout.setRowStretch(row, int(source.grid_rowconfigure(row, 'weight')))
                layout.setColumnStretch(col, int(source.grid_columnconfigure(col, 'weight')))
        else:
            layout = Q.QVBoxLayout(target)
            row = None
            for child in source.pack_slaves():
                info = tk._splitdict(source.tk, source.tk.call('pack', 'info', child._w))
                if str(info['side']) in ('left', 'right'):
                    if row is None:
                        row = Q.QHBoxLayout()
                        layout.addLayout(row)
                    row.addWidget(self.build(child))
                    row.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
                else:
                    row = None
                    layout.addWidget(self.build(child), 1 if info['expand'] else 0)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(5)

    def tick(self):
        try:
            self.legacy.update()
            for source, target in self.bindings:
                target.blockSignals(True)
                try:
                    self.sync(source, target)
                finally:
                    target.blockSignals(False)
        except tk.TclError:
            self.timer.stop()
            self.close()

    def sync(self, source, target):
        if isinstance(target, Q.QTabWidget):
            for index, name in enumerate(source.tabs()):
                target.setTabText(index, self.t(source.tab(name, 'text')))
            if target.currentIndex() < len(source.tabs()):
                target.setCurrentIndex(source.index(source.select()))
        elif isinstance(target, Q.QCheckBox):
            target.setText(self.t(str(source.cget('text'))))
            target.setChecked('selected' in source.state())
            target.setEnabled('disabled' not in source.state())
        elif isinstance(target, Q.QPushButton):
            target.setText(self.t(str(source.cget('text'))))
            target.setEnabled('disabled' not in source.state())
        elif isinstance(target, Q.QComboBox):
            values = list(source.cget('values'))
            display = [self.t(str(v)) for v in values]
            if display != [target.itemText(i) for i in range(target.count())]:
                target.clear()
                target.addItems(display)
            target.setCurrentIndex(source.current())
            target.setEnabled('disabled' not in source.state())
        elif isinstance(target, Q.QSpinBox):
            if not target.hasFocus() and not target.lineEdit().hasFocus():
                try:
                    target.setValue(int(source.get()))
                except ValueError:
                    pass
            target.setEnabled('disabled' not in source.state())
        elif isinstance(target, Q.QLineEdit):
            if not target.hasFocus():
                target.setText(source.get())
            target.setEnabled(str(source.cget('state')) != 'disabled')
        elif isinstance(target, Q.QTreeWidget):
            columns = source.cget('columns')
            target.setHeaderLabels([self.t(source.heading(c, 'text')) for c in columns])
            rows = [(i, tuple(source.item(i, 'values'))) for i in source.get_children()]
            if self.cache.get(source) != rows:
                self.cache[source] = rows
                target.clear()
                for identity, values in rows:
                    # Never translate player-chosen names, seeds, paths or item IDs.
                    item = Q.QTreeWidgetItem([str(v) if columns[index] in ('name', 'title', 'seed', 'id', 'identity') else self.t(str(v)) for index, v in enumerate(values)])
                    if source is self.controller.catalog_panel.workbench.contents:
                        item.setIcon(0, resource_icon(str(values[1])))
                    item.setData(0, QtCore.Qt.ItemDataRole.UserRole, identity)
                    target.addTopLevelItem(item)
                for i in range(target.columnCount()):
                    target.header().setSectionResizeMode(i, Q.QHeaderView.ResizeMode.Stretch)
            selected = source.selection()
            for i in range(target.topLevelItemCount()):
                item = target.topLevelItem(i)
                item.setSelected(item.data(0, QtCore.Qt.ItemDataRole.UserRole) in selected)
        elif isinstance(target, Q.QListWidget):
            values = source.get(0, 'end')
            if self.cache.get(source) != values:
                self.cache[source] = values
                target.clear()
                target.addItems([self.t(value) for value in values])
        elif isinstance(target, Q.QTextEdit):
            target.setReadOnly(str(source.cget('state')) == 'disabled')
            value = source.get('1.0', 'end-1c')
            if not value.lstrip().startswith(('{', '[')):
                value = self.t(value)
            if value != target.toPlainText() and not target.hasFocus():
                target.setPlainText(value)
        elif isinstance(target, InventoryCanvas):
            target.refresh()
        elif isinstance(target, StatsBar):
            target.refresh(self.controller.catalog_panel.service.counts())
        elif isinstance(target, Q.QGroupBox):
            target.setTitle(self.t(str(source.cget('text'))))
        elif isinstance(target, Q.QLabel):
            value = str(source.cget('text'))
            if source is self.controller.capital_panel.freighter_info and self.controller.capital_panel.view.get('freighter'):
                target.setText(value)
            elif str(source.cget('textvariable')) == str(self.controller.scan_status):
                # The dot conveys actual connection state, not a decorative "connected" claim.
                color = '#51b77f' if value.startswith('Canlı: bağlı ve güncel') else '#e5a16d'
                target.setText(f'<span style="color:{color}">●</span> &nbsp;{html.escape(self.t(value))}')
            elif value.startswith('Katalog •'):
                target.setText('<span style="color:#e38578">❯❯</span> &nbsp;' + html.escape(self.t(value)))
            elif value.startswith(('Koordinatlar ', 'Değişiklikler ortak sepete')):
                target.setText('<span style="color:#9fbcc8">ⓘ</span> &nbsp;' + html.escape(self.t(value)))
            else:
                target.setText(self.t(value))

    def closeEvent(self, event):
        try:
            exists = self.legacy.winfo_exists()
        except tk.TclError:
            exists = False
        if exists:
            if not self.controller.busy:
                for timer_id in self.legacy.tk.call('after', 'info'):
                    self.legacy.after_cancel(timer_id)
            self.controller.close()
            try:
                alive = self.legacy.winfo_exists()
            except tk.TclError:
                alive = False
            if alive:
                event.ignore()
                return
        self.toggle_overlay(False)
        event.accept()


class InventoryCanvas(Q.QGraphicsView):
    def __init__(self, source, workbench):
        super().__init__()
        self.source, self.workbench = source, workbench
        self.setScene(Q.QGraphicsScene(self))
        self.setMinimumHeight(90)
        self.setMaximumHeight(180)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet('border:0; background:#0a202a;')
        self.signature = None

    def refresh(self):
        data = [(self.source.type(i), self.source.coords(i), self.source.itemcget(i, 'fill'), self.source.itemcget(i, 'text') if self.source.type(i) == 'text' else '', self.source.itemcget(i, 'outline') if self.source.type(i) == 'rectangle' else '') for i in self.source.find_all()]
        signature = repr(data)
        if signature == self.signature:
            return
        self.signature = signature
        scene = self.scene()
        scene.clear()
        for kind, coords, fill, text, outline in data:
            if kind == 'rectangle':
                x1, y1, x2, y2 = coords
                gradient = QtGui.QLinearGradient(x1, y1, x1, y2)
                gradient.setColorAt(0, QtGui.QColor('#20564f' if fill == '#354d42' else '#193440'))
                gradient.setColorAt(1, QtGui.QColor('#10352f' if fill == '#354d42' else '#0b202a'))
                pen = QtGui.QPen(QtGui.QColor('#d8b458' if outline == '#dfb64b' else '#38756a' if fill == '#354d42' else '#2c4854'))
                path = QtGui.QPainterPath()
                path.addRoundedRect(x1, y1, x2-x1, y2-y1, 5, 5)
                scene.addPath(path, pen, QtGui.QBrush(gradient))
                if fill == '#263549':
                    cx, cy = (x1+x2)/2, (y1+y2)/2
                    plus_pen = QtGui.QPen(QtGui.QColor('#365461'), 1)
                    scene.addLine(cx-5, cy, cx+5, cy, plus_pen)
                    scene.addLine(cx, cy-5, cx, cy+5, plus_pen)
            elif kind == 'text':
                item = scene.addText(text, QtGui.QFont('Segoe UI', 8))
                item.setDefaultTextColor(QtGui.QColor('#e1edef'))
                rect = item.boundingRect()
                item.setPos(coords[0]-rect.width()/2, coords[1]-rect.height()/2)
        scene.setSceneRect(scene.itemsBoundingRect())

    def mousePressEvent(self, event):
        point = self.mapToScene(event.position().toPoint())
        x, y = int(point.x() // 86), int(point.y() // 42)
        if self.workbench.nodes:
            node = self.workbench.node()
            if any(p['X'] == x and p['Y'] == y for p in node['valid']):
                item = next((p for p in node['items'] if p['position']['X'] == x and p['position']['Y'] == y), None)
                self.workbench.cell(x, y, item)
        super().mousePressEvent(event)


def main(inventory=True, fleet=False, weapons=False, catalog=False, settings=False, capital=False):
    app = Q.QApplication(sys.argv)
    app.setStyle('Fusion')
    window = Window(inventory, fleet, weapons, catalog)
    if capital:
        window.controller.book.select(7)
        window.tick()
    if settings:
        window.main_book.setCurrentIndex(window.settings_index)
    window.show()
    return app.exec()
