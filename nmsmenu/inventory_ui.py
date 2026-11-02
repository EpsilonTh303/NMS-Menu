"""Tk adapter for shared inventory snapshots, loadouts and native archives."""
import copy
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

from . import loadouts
from .catalog_data import technologies
from .inventory import fingerprint


def fit_grid(parent, *stretch_rows):
    """Keep action rows visible while list/canvas rows absorb smaller windows."""
    widgets = parent.pack_slaves()
    for widget in widgets:
        widget.pack_forget()
    for row, widget in enumerate(widgets):
        widget.grid(row=row, column=0, sticky='nsew' if row in stretch_rows else 'ew', pady=1)
    parent.columnconfigure(0, weight=1)
    for row in stretch_rows:
        parent.rowconfigure(row, weight=1)


class WorkbenchPanel:
    def __init__(self, parent, catalog):
        self.catalog = catalog
        self.saves, self.nodes, self.active_entries, self.archived_entries = [], [], [], []
        self.store = loadouts.LoadoutStore()
        row = ttk.Frame(parent)
        row.pack(fill='x')
        ttk.Label(row, text='Disk kaydı: ').pack(side='left')
        self.save_choice = ttk.Combobox(row, state='readonly', width=15)
        self.save_choice.pack(side='left')
        self.save_choice.bind('<<ComboboxSelected>>', lambda _: self.load_save())
        self.info = ttk.Label(row, text='Ortak kayıt taraması bekleniyor.')
        self.info.pack(side='left', padx=10)
        book = ttk.Notebook(parent)
        book.pack(fill='both', expand=True, pady=6)
        inventory, presets, archive = [ttk.Frame(book, padding=6) for _ in range(3)]
        for frame, title in [(inventory, 'Envanter'), (presets, 'Donanım setleri'), (archive, 'Yerleşik arşiv')]:
            book.add(frame, text=title)
        self.make_inventory(inventory)
        self.make_presets(presets)
        self.make_archive(archive)
        ttk.Label(parent, text='Değişiklikler ortak sepete gider. Sepet ve işlem raporu bölümünden hazırlayın / inceleyin / uygulayın.', wraplength=1020).pack(anchor='w')
        ttk.Button(parent, text='Sepet ve işlem raporuna git', command=lambda: catalog.book.select(1)).pack(anchor='w', pady=3)
        fit_grid(parent, 1)

    def perform(self, fn):
        try:
            fn()
        except Exception as exc:
            messagebox.showerror('Envanter / koleksiyon', str(exc))

    def save(self):
        i = self.save_choice.current()
        if i < 0:
            raise ValueError('Ortak kayıt listesinin dolmasını bekleyin.')
        return self.saves[i]

    def node(self, destination=False):
        choice = self.destination if destination else self.inventory_choice
        i = choice.current()
        if i < 0 or i >= len(self.nodes):
            raise ValueError('Envanter seçin.')
        return self.nodes[i]

    def queue(self, commands):
        self.catalog.queue(self.save()['file'], commands)
        self.info.configure(text=f'{len(commands)} işlem sepete gönderildi; henüz uygulanmadı.')

    def load_snapshot(self, saves):
        previous = self.save_choice.get()
        self.saves = saves
        names = [s['file'] for s in saves]
        self.save_choice.configure(values=names)
        if names:
            self.save_choice.current(names.index(previous) if previous in names else max(range(len(saves)), key=lambda i: saves[i].get('mtime_ns', 0)))
        else:
            self.save_choice.set('')
        self.load_save()

    def load_save(self):
        old_source = fingerprint(self.node()['spec']) if self.nodes and self.inventory_choice.current() >= 0 else None
        old_dest = fingerprint(self.node(True)['spec']) if self.nodes and self.destination.current() >= 0 else None
        save = self.saves[self.save_choice.current()] if self.save_choice.current() >= 0 else {}
        self.nodes = save.get('inventories', [])
        labels = [n['label'] for n in self.nodes]
        for choice, old in [(self.inventory_choice, old_source), (self.destination, old_dest)]:
            choice.configure(values=labels)
            if labels:
                choice.current(next((i for i, n in enumerate(self.nodes) if fingerprint(n['spec']) == old), 0))
            else:
                choice.set('')
        self.render_inventory()
        self.render_archive(save)
        self.info.configure(text=save.get('inventory_error') or f"{len(self.nodes)} envanter • Disk verisi: {save.get('read_at', 'bekleniyor')}")

    def make_inventory(self, parent):
        self.inventory_choice = ttk.Combobox(parent, state='readonly', width=90)
        self.inventory_choice.pack(fill='x')
        self.inventory_choice.bind('<<ComboboxSelected>>', lambda _: self.render_inventory())
        self.capacity = ttk.Label(parent, text='')
        self.capacity.pack(anchor='w', pady=3)
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(frame, height=90, background='#161e29', highlightthickness=0)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.contents = ttk.Treeview(parent, columns=('title', 'id', 'amount', 'pos'), show='headings', height=3, selectmode='browse')
        for key, title, width in [('title', 'İçerik', 350), ('id', 'ID', 180), ('amount', 'Miktar / yığın', 140), ('pos', 'X / Y', 90)]:
            self.contents.heading(key, text=title)
            self.contents.column(key, width=width)
        self.contents.pack(fill='x', pady=4)
        row = ttk.Frame(parent)
        row.pack(fill='x')
        ttk.Label(row, text='Hedef: ').pack(side='left')
        self.destination = ttk.Combobox(row, state='readonly', width=59)
        self.destination.pack(side='left')
        self.x, self.y, self.quantity = tk.StringVar(value='1'), tk.StringVar(value='1'), tk.StringVar(value='1')
        for title, var, limit in [('X:', self.x, 16), ('Y:', self.y, 16), ('Miktar:', self.quantity, 10000000)]:
            ttk.Label(row, text=title).pack(side='left', padx=(8, 1))
            ttk.Spinbox(row, from_=1, to=limit, textvariable=var, width=6).pack(side='left')
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=4)
        for title, fn in [('Taşı', lambda: self.move(False)), ('Yığını böl', lambda: self.move(True)),
                          ('Miktarı ayarla', self.set_amount), ('Yığınları birleştir', self.merge)]:
            ttk.Button(row, text=title, command=lambda fn=fn: self.perform(fn)).pack(side='left', padx=(0, 6))
        ttk.Label(parent, text='Koordinatlar 1’den başlar. Izgarada boş yuvaya tıklamak hedef koordinatını seçer; altın kenar süperşarjlı yuvadır.', wraplength=1020).pack(anchor='w')
        fit_grid(parent, 2)

    def render_inventory(self):
        previous = self.contents.selection()
        self.contents.delete(*self.contents.get_children())
        self.canvas.delete('all')
        if not self.nodes or self.inventory_choice.current() < 0:
            self.capacity.configure(text='Envanter bekleniyor.')
            return
        node = self.node()
        self.capacity.configure(text=f"{len(node['items'])} dolu / {len(node['valid'])} açık yuva • {len(node['valid']) - len(node['items'])} boş")
        from .catalog_data import technologies
        for item in node['items']:
            title = technologies().get(item['id'].lstrip('^'), {}).get('title', item['title'])
            self.contents.insert('', 'end', iid=item['identity'], values=(title, item['id'], f"{item['amount']} / {item['max']}", f"{item['position']['X'] + 1} / {item['position']['Y'] + 1}"))
        if previous and self.contents.exists(previous[0]):
            self.contents.selection_set(previous[0])
        valid = {(p['X'], p['Y']) for p in node['valid']}
        special = {(p['Index']['X'], p['Index']['Y']) for p in node['special']}
        occupied = {(p['position']['X'], p['position']['Y']): p for p in node['items']}
        for y in range(node['height']):
            for x in range(node['width']):
                item = occupied.get((x, y))
                tag = f'cell:{x}:{y}'
                colour = '#263549' if (x, y) in valid else '#101720'
                if item:
                    colour = '#21465b' if item['kind'] == 'Technology' else '#354d42'
                self.canvas.create_rectangle(x * 86 + 2, y * 42 + 2, x * 86 + 84, y * 42 + 40,
                    fill=colour, outline='#dfb64b' if (x, y) in special else '#45566c', width=2, tags=tag)
                if item:
                    title = technologies().get(item['id'].lstrip('^'), {}).get('title', item['title'])
                    self.canvas.create_text(x * 86 + 43, y * 42 + 21, text=title[:12] + '\n' + str(item['amount']), fill='#e6edf6', font=('Segoe UI', 8), tags=tag)
                if (x, y) in valid:
                    self.canvas.tag_bind(tag, '<Button-1>', lambda _, x=x, y=y, item=item: self.cell(x, y, item))
        self.canvas.configure(scrollregion=(0, 0, node['width'] * 86, node['height'] * 42))

    def cell(self, x, y, item):
        self.x.set(str(x + 1))
        self.y.set(str(y + 1))
        if item:
            self.contents.selection_set(item['identity'])
            self.contents.see(item['identity'])

    def selected_item(self):
        keys = self.contents.selection()
        if not keys:
            raise ValueError('Önce envanterden bir eşya seçin.')
        return keys[0]

    def move(self, split):
        command = {'op': 'split_item' if split else 'move_item', 'inventory': copy.deepcopy(self.node()['spec']),
            'item': self.selected_item(), 'destination': copy.deepcopy(self.node(True)['spec']),
            'position': {'X': int(self.x.get()) - 1, 'Y': int(self.y.get()) - 1}}
        if split:
            command['amount'] = int(self.quantity.get())
        self.queue([command])

    def set_amount(self):
        self.queue([{'op': 'set_item_amount', 'inventory': self.node()['spec'], 'item': self.selected_item(), 'amount': int(self.quantity.get())}])

    def merge(self):
        self.queue([{'op': 'merge_stacks', 'inventory': self.node()['spec']}])

    def make_presets(self, parent):
        ttk.Label(parent, text='Envanter bölümünden uygun teknoloji envanterini seçin. Set mevcut teknolojileri sökmeden yalnız eksikleri ekler.', wraplength=1020).pack(anchor='w')
        self.preset = ttk.Combobox(parent, state='readonly', width=65)
        self.preset.pack(anchor='w', pady=8)
        self.preset.bind('<<ComboboxSelected>>', lambda _: self.show_preset())
        self.preset_details = ScrolledText(parent, height=10, state='disabled', wrap='word')
        self.preset_details.pack(fill='both', expand=True)
        ttk.Button(parent, text='Seçili seti hedefe kurmak için sepete ekle', command=lambda: self.perform(self.apply_preset)).pack(anchor='w', pady=6)
        row = ttk.Frame(parent)
        row.pack(fill='x')
        self.preset_name = tk.StringVar(value='Benim donanım setim')
        ttk.Entry(row, textvariable=self.preset_name, width=35).pack(side='left')
        ttk.Button(row, text='Seçili envanterin sabit teknolojilerini set olarak kaydet', command=lambda: self.perform(self.capture_preset)).pack(side='left', padx=8)
        ttk.Label(parent, text='Kişisel set yalnız yerel menüye kaydedilir. Prosedürel S/X modülleri ve hedefe özel olmayan kayıtlar kopyalanmaz.', wraplength=1020).pack(anchor='w', pady=6)
        self.reload_presets()
        fit_grid(parent, 2)

    def reload_presets(self):
        self.profiles = self.store.all()
        self.profile_keys = list(self.profiles)
        self.preset.configure(values=[self.profiles[k]['title'] for k in self.profile_keys])
        self.preset.current(0)
        self.show_preset()

    def show_preset(self):
        if self.preset.current() < 0:
            return
        profile = self.profiles[self.profile_keys[self.preset.current()]]
        text = profile['title'] + '\nHedef: ' + profile['target'] + '\n\n' + '\n'.join(
            technologies().get(i, {}).get('title', i) + ' • ' + i for i in profile['ids'])
        self.preset_details.configure(state='normal')
        self.preset_details.delete('1.0', 'end')
        self.preset_details.insert('1.0', text)
        self.preset_details.configure(state='disabled')

    def apply_preset(self):
        self.queue(loadouts.commands(self.profiles[self.profile_keys[self.preset.current()]], self.node()['spec']))

    def capture_preset(self):
        node = self.node()
        if node['spec']['section'] != 'tech':
            raise ValueError('Önce teknoloji envanteri seçin.')
        ids = [p['id'].lstrip('^') for p in node['items'] if p['kind'] == 'Technology' and p['id'].lstrip('^') in technologies()]
        key = self.store.save(self.preset_name.get(), node['spec']['kind'], ids)
        self.reload_presets()
        self.preset.current(self.profile_keys.index(key))
        self.show_preset()
        self.info.configure(text='Kişisel donanım seti kaydedildi; oyun kaydına dokunulmadı.')

    def make_archive(self, parent):
        ttk.Label(parent, text='Aktif koleksiyon', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        self.active = ttk.Treeview(parent, columns=('kind', 'name', 'identity'), show='headings', height=5, selectmode='browse')
        self.archived = ttk.Treeview(parent, columns=('kind', 'name', 'identity'), show='headings', height=5, selectmode='browse')
        for tree in (self.active, self.archived):
            for key, title, width in [('kind', 'Tür', 100), ('name', 'Ad / sınıf', 370), ('identity', 'Yuva / tohum', 350)]:
                tree.heading(key, text=title)
                tree.column(key, width=width)
        self.active.pack(fill='both', expand=True)
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=5)
        ttk.Button(row, text='Seçili gemiyi / aleti arşivleme sepetine ekle', command=lambda: self.perform(self.archive)).pack(side='left')
        ttk.Label(row, text='Ortak alet modeli için aile: ').pack(side='left', padx=8)
        self.weapon_family = ttk.Combobox(row, state='readonly', values=['Otomatik', 'Pistol', 'Rifle', 'Alien', 'Pristine'], width=12)
        self.weapon_family.set('Otomatik')
        self.weapon_family.pack(side='left')
        self.archive_capacity = ttk.Label(parent, text='Yerleşik arşiv • 18 gemi / 18 alet')
        self.archive_capacity.pack(anchor='w')
        self.archived.pack(fill='both', expand=True)
        ttk.Button(parent, text='Arşivde seçileni boş aktif yuvaya geri alma sepetine ekle', command=lambda: self.perform(self.restore_archive)).pack(anchor='w', pady=5)
        ttk.Label(parent, text='Gemi kargosu önce ekzosuite taşınır; yer yoksa işlem durur. Tam gemi ayrıca harici garaja aktarılır.\n'
                  'Aktif gemi için istasyonda kayıt gerekir. Son gemi / son alet arşivlenmez. Sabit diziler büyütülmez.', wraplength=1020).pack(anchor='w')
        fit_grid(parent, 1, 4)

    def render_archive(self, save):
        old_active, old_archive = self.active.selection(), self.archived.selection()
        self.active.delete(*self.active.get_children())
        self.archived.delete(*self.archived.get_children())
        self.active_entries = []
        for kind, field in [('ship', 'fleet'), ('multitool', 'multitools')]:
            for item in save.get(field, []):
                self.active_entries.append((kind, item))
                key = kind + ':' + str(item['slot'])
                self.active.insert('', 'end', iid=key, values=('Gemi' if kind == 'ship' else 'Alet', f"{item['name']} • {item['class']}", f"{item['slot']} • {item['seed']}"))
        self.archived_entries = save.get('archives', [])
        for item in self.archived_entries:
            selector = item['selector']
            key = item['kind'] + ':' + str(selector['slot'])
            self.archived.insert('', 'end', iid=key, values=('Gemi' if item['kind'] == 'ship' else 'Alet', f"{item['name']} • {item['class']}", f"{selector['slot']} • {selector['seed']}"))
        for tree, old in [(self.active, old_active), (self.archived, old_archive)]:
            if old and tree.exists(old[0]):
                tree.selection_set(old[0])
        ships = sum(p['kind'] == 'ship' for p in self.archived_entries)
        self.archive_capacity.configure(text=f'Yerleşik arşiv: {ships}/18 gemi • {len(self.archived_entries) - ships}/18 alet')

    def archive(self):
        selection = self.active.selection()
        if not selection:
            raise ValueError('Aktif koleksiyondan kesin bir gemi veya alet seçin.')
        kind, item = next((kind, item) for kind, item in self.active_entries if kind + ':' + str(item['slot']) == selection[0])
        fields = ('slot', 'seed', 'type') if kind == 'ship' else ('slot', 'seed', 'filename')
        action = {'op': 'archive_ship' if kind == 'ship' else 'archive_tool', 'selector': {k: item[k] for k in fields}}
        if kind != 'ship' and self.weapon_family.get() != 'Otomatik':
            action['weapon_class'] = self.weapon_family.get()
        self.queue([action])

    def restore_archive(self):
        selection = self.archived.selection()
        if not selection:
            raise ValueError('Arşivden bir kayıt seçin.')
        item = next(p for p in self.archived_entries if p['kind'] + ':' + str(p['selector']['slot']) == selection[0])
        self.queue([{'op': 'restore_archived_ship' if item['kind'] == 'ship' else 'restore_archived_tool', 'selector': item['selector']}])
