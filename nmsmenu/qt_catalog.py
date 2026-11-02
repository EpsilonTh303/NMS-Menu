"""Compact catalog presentation; all mutations still use CatalogPanel's review flow."""
from PySide6 import QtCore, QtWidgets as Q


def action_text(command, service, translate):
    operation = command.get('op', '')
    prefix = {'add': 'ship:', 'add_item': 'item:', 'install_technology': 'tech:'}.get(operation)
    identity = command.get('profile') if operation == 'add' else command.get('id')
    if operation == 'install_technology':
        identity = command.get('technology', command.get('id'))
    title = command.get('name') or identity or ''
    if prefix and identity:
        try:
            entry = service.detail(prefix + identity)
            title = entry.get('title') or entry.get('name') or title
        except ValueError:
            pass
    verbs = {'add': 'Ekle', 'add_item': 'Ekle', 'install_technology': 'Ekle',
             'tool_add': 'Ekle', 'garage_import': 'Ekle', 'remove': 'Kaldır', 'tool_remove': 'Kaldır',
             'repair_ship': 'Onar', 'max_slots': 'Yuvaları genişlet',
             'auto_recharge': 'Otomatik şarj', 'learn_recipe': 'Tarifi öğren',
             'freighter_edit': 'Değiştir', 'frigate_edit': 'Değiştir',
             'freighter_create': 'Ekle', 'frigate_clone': 'Ekle', 'frigate_remove': 'Kaldır',
             'freighter_repair': 'Onar', 'frigate_repair': 'Onar', 'freighter_expand': 'Yuvaları genişlet'}
    verb = translate(verbs.get(operation, 'Değiştir'))
    if operation == 'add_item':
        title = f"{title} × {command['amount']:,}"
    if not title:
        selector = command.get('selector', {})
        title = selector.get('name') or selector.get('seed') or translate('Envanter')
    return f'{verb} · {title}'


class CatalogWorkspace(Q.QWidget):
    def __init__(self, owner):
        super().__init__()
        self.owner, self.panel = owner, owner.controller.catalog_panel
        self.localized = []
        self.checks = []
        self.last_revision = None
        self.last_review = None
        layout = Q.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        self.pages = Q.QTabWidget()
        browse = Q.QWidget()
        scroll = Q.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(Q.QFrame.Shape.NoFrame)
        scroll.setWidget(browse)
        self.pages.addTab(scroll, '')
        self.pages.addTab(Q.QWidget(), '')  # Legacy review navigation maps to the fixed side panel.
        self.pages.setTabVisible(1, False)
        workspace = self.panel.book.nametowidget(self.panel.book.tabs()[2])
        self.pages.addTab(owner.build(workspace), '')
        self.pages.currentChanged.connect(lambda index: self.panel.book.select(index))
        owner.bindings.append((self.panel.book, self.pages))
        layout.addWidget(self.pages, 1)
        self.build_browse(browse)
        self.side = Q.QFrame(objectName='changesPanel')
        self.side.setMinimumWidth(300)
        self.side.setMaximumWidth(370)
        right = Q.QVBoxLayout(self.side)
        right.setContentsMargins(14, 14, 14, 14)
        title = self.label('Bekleyen değişiklikler')
        title.setSizePolicy(Q.QSizePolicy.Policy.Preferred, Q.QSizePolicy.Policy.Fixed)
        title.setStyleSheet('font-size:17px; font-weight:600; color:#eff5f7;')
        right.addWidget(title)
        self.summary = Q.QLabel()
        self.summary.setSizePolicy(Q.QSizePolicy.Policy.Preferred, Q.QSizePolicy.Policy.Fixed)
        right.addWidget(self.summary)
        self.pending = owner.build(self.panel.cart_list)
        self.pending.setMinimumHeight(100)
        self.pending.setMaximumHeight(190)
        self.pending.setWordWrap(True)
        right.addWidget(self.pending)
        self.edit_row = Q.QWidget()
        edit = Q.QHBoxLayout(self.edit_row)
        edit.setContentsMargins(0, 0, 0, 0)
        edit.addWidget(self.label('Adet'))
        self.pending_quantity = Q.QSpinBox()
        self.pending_quantity.setRange(1, 10_000_000)
        self.pending_quantity.setMinimumWidth(130)
        self.pending_quantity.setKeyboardTracking(False)
        edit.addWidget(self.pending_quantity)
        edit.addWidget(self.button('Değiştir', self.change_pending_amount))
        self.edit_row.hide()
        self.edit_signature = None
        right.addWidget(self.edit_row)
        row = Q.QHBoxLayout()
        row.addWidget(self.button('Kaldır', self.panel.remove))
        row.addWidget(self.button('Değişiklikleri temizle', self.panel.clear))
        right.addLayout(row)
        note = self.label('Oyunu kaydet ve kapat; ardından kontrol et ve uygula.')
        note.setWordWrap(True)
        right.addWidget(note)
        self.prepare = self.button('Değişiklikleri kontrol et', self.panel.prepare)
        right.addWidget(self.prepare)
        self.panel.apply_button.configure(text='Uygula')
        self.apply = owner.build(self.panel.apply_button)
        self.apply.setProperty('accent', True)
        right.addWidget(self.apply)
        self.review_toggle = self.button('Ayrıntıları göster', lambda: None)
        self.review_toggle.setCheckable(True)
        right.addWidget(self.review_toggle)
        self.report = owner.build(self.panel.report)
        self.report.setMinimumHeight(110)
        self.report.setMaximumHeight(16777215)
        self.report.hide()
        self.review_toggle.toggled.connect(self.report.setVisible)
        right.addWidget(self.report, 1)
        self.restore = owner.build(self.panel.restore_button)
        self.restore.setVisible(False)
        self.review_toggle.toggled.connect(self.restore.setVisible)
        right.addWidget(self.restore)
        # Keep review/apply beside the heading, above the pending list.
        # Hidden details must never spread the action buttons down the page.
        for widget in (self.prepare, self.apply, note):
            right.removeWidget(widget)
        right.insertWidget(2, self.prepare)
        right.insertWidget(3, self.apply)
        right.insertWidget(4, note)
        right.addStretch(1)
        layout.addWidget(self.side)
        self.refresh()

    def label(self, text):
        widget = Q.QLabel()
        self.localized.append((widget, text))
        return widget

    def button(self, text, callback):
        button = Q.QPushButton()
        self.localized.append((button, text))
        button.clicked.connect(callback)
        return button

    def checkbox(self, text, variable, callback=None):
        check = Q.QCheckBox()
        self.localized.append((check, text))
        check.setChecked(variable.get())
        def changed(checked):
            variable.set(checked)
            if callback:
                callback()
        check.toggled.connect(changed)
        self.checks.append((check, variable))
        return check

    def variable_widget(self, variable):
        def visit(widget):
            for option in ('textvariable', 'variable'):
                if option in widget.keys() and str(widget.cget(option)) == str(variable):
                    return widget
            for child in widget.winfo_children():
                found = visit(child)
                if found is not None:
                    return found
        return visit(self.panel.book)

    def build_browse(self, page):
        panel, owner = self.panel, self.owner
        layout = Q.QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        first = Q.QHBoxLayout()
        first.addWidget(self.label('Kayıt seç'))
        first.addWidget(owner.build(panel.save_choice))
        first.addWidget(self.label('Tür'))
        first.addWidget(owner.build(panel.kind), 1)
        layout.addLayout(first)
        self.search = owner.build(self.variable_widget(panel.query))
        self.search.setMaximumWidth(16777215)
        layout.addWidget(self.search)
        target = Q.QHBoxLayout()
        target.addWidget(self.label('Hedef'))
        target.addWidget(owner.build(panel.target_kind))
        self.target_choice = owner.build(panel.target_choice)
        self.target_choice.setMinimumWidth(0)
        self.target_choice.setSizePolicy(Q.QSizePolicy.Policy.Ignored, Q.QSizePolicy.Policy.Fixed)
        target.addWidget(self.target_choice, 1)
        layout.addLayout(target)
        products = owner.build(panel.products)
        products.setMinimumHeight(160)
        layout.addWidget(products, 1)
        # The main action row stays directly beside the selected content.
        action = Q.QHBoxLayout()
        action.addWidget(self.label('Adet'))
        self.quantity = owner.build(self.variable_widget(panel.quantity))
        self.quantity.setMinimumWidth(165)
        self.quantity.setMaximumWidth(200)
        action.addWidget(self.quantity)
        self.add = self.button('Ekle', self.add_selected)
        self.add.setProperty('accent', True)
        action.addWidget(self.add, 1)
        action.addWidget(self.button('★ Favori', panel.favorite))
        layout.addLayout(action)
        self.quantity_note = Q.QLabel()
        self.quantity_note.setWordWrap(True)
        layout.addWidget(self.quantity_note)
        details = owner.build(panel.details)
        details.setFixedHeight(72)
        layout.addWidget(details)
        self.advanced_toggle = self.button('Gelişmiş seçenekler', lambda: None)
        self.advanced_toggle.setCheckable(True)
        layout.addWidget(self.advanced_toggle)
        advanced = Q.QWidget()
        grid = Q.QGridLayout(advanced)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(owner.build(panel.family), 0, 0)
        grid.addWidget(self.button('Tarifi öğren', panel.learn_recipe), 0, 1)
        for row, (text, var) in enumerate((('Yalnız uygun teknolojiler', panel.fit),
                                         ('Favoriler', panel.favorites_only),
                                         ('Son kullanılan', panel.recent_only),
                                         ('Beğenilmeyen gemi profillerini de göster', panel.show_all)), 1):
            grid.addWidget(self.checkbox(text, var, panel.filter), row, 0, 1, 2)
        grid.addWidget(self.checkbox('Rastgele gemi tohumu', panel.new_ship_seed), 5, 0)
        grid.addWidget(self.checkbox('Rastgele alet tohumu', panel.random_tool_seed), 5, 1)
        grid.addWidget(self.label('Yeni alet adı'), 6, 0)
        grid.addWidget(owner.build(self.variable_widget(panel.new_name)), 6, 1)
        advanced.setVisible(False)
        self.advanced_toggle.toggled.connect(advanced.setVisible)
        layout.addWidget(advanced)

    def add_selected(self):
        self.quantity.interpretText()
        self.panel.quantity.set(str(self.quantity.value()))
        self.panel.add()
        self.owner.tick()

    def change_pending_amount(self):
        index = self.pending.currentRow()
        if 0 <= index < len(self.panel.cart.commands) and self.panel.cart.commands[index].get('op') == 'add_item':
            self.pending_quantity.interpretText()
            self.panel.cart.set_item_amount(index, self.pending_quantity.value())
            self.panel.changed()
            self.owner.tick()

    def refresh(self):
        t, panel = self.owner.t, self.panel
        if self.last_revision is not None and self.last_revision != panel.cart.revision and panel.review is None:
            panel.output('Kontrol edildiğinde uygula açılır.')
            self.review_toggle.setChecked(False)
        self.last_revision = panel.cart.revision
        for widget, text in self.localized:
            widget.setText(t(text))
        self.search.setPlaceholderText(t('Ara…'))
        self.pages.setTabText(0, t('İçerik ekle'))
        self.pages.setTabText(2, t('Envanter / donanım / arşiv'))
        if panel.book.index(panel.book.select()) == 1:
            panel.book.select(0)
            self.pages.setCurrentIndex(0)
            self.review_toggle.setChecked(True)
        for check, variable in self.checks:
            with QtCore.QSignalBlocker(check):
                check.setChecked(variable.get())
        keys = panel.products.selection()
        has_items = any(key.startswith('item:') for key in keys)
        self.quantity.setEnabled(has_items)
        self.quantity.setToolTip(t('Her seçili eşyadan eklenecek miktar.'))
        self.quantity_note.setText(t('Her seçili eşyadan eklenecek miktar.' if has_items else
                                    'Adet yalnız eşya ve malzemeler için kullanılır.'))
        self.add.setEnabled(bool(keys) and panel.save_choice.current() >= 0 and not self.owner.controller.busy)
        self.prepare.setEnabled(bool(panel.cart.commands) and not self.owner.controller.busy)
        count = len(panel.cart.commands)
        self.summary.setText(t('Henüz değişiklik eklenmedi.') if not count else
                             t('Kayıt yuvası {v0} • {v1} işlem').replace('{v0}', str(panel.cart.save_slot)).replace('{v1}', str(count)))
        if panel.review is not None and panel.review != self.last_review:
            self.review_toggle.setChecked(True)
        self.last_review = panel.review
        index = self.pending.currentRow()
        commands = panel.cart.commands
        editable = 0 <= index < len(commands) and commands[index].get('op') == 'add_item'
        self.edit_row.setVisible(editable)
        signature = (index, panel.cart.revision)
        if editable and signature != self.edit_signature:
            self.pending_quantity.setValue(commands[index]['amount'])
        self.edit_signature = signature
