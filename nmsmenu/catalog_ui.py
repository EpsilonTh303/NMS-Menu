"""Temporary Tk presentation; all catalog / cart rules live in services."""
import json
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .catalog_backend import CatalogBackend
from .catalog_service import CatalogCart, CatalogService


KINDS = {'Hepsi': '', 'Gemi profilleri': 'ship', 'Çok amaçlı alet': 'multitool', 'Teknoloji': 'technology', 'Eşya / malzeme': 'item', 'Garaj': 'garage', 'Tür rehberi': 'reference'}
KIND_LABELS = {v: k for k, v in KINDS.items()}
TARGETS = {'Ekzosuit': 'exosuit', 'Gemi': 'ship', 'Çok amaçlı alet': 'multitool'}


class CatalogPanel:
    def __init__(self, parent, host):
        self.host, self.service, self.cart, self.backend = host, CatalogService(), CatalogCart(), CatalogBackend()
        self.saves, self.targets = [], []
        self.review, self.last_applied = None, None
        ttk.Label(parent, text='Katalog • eşya, envanter, donanım ve koleksiyon', font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        ttk.Label(parent, text='Liste ortak taramadan gelir. Sepet uygulaması için oyunu kaydedip tamamen kapatın.').pack(anchor='w', pady=5)
        self.overview = ttk.Label(parent, text='', wraplength=1080)
        self.overview.pack(anchor='w')
        self.book = ttk.Notebook(parent)
        self.book.pack(fill='both', expand=True)
        browse, review = ttk.Frame(self.book, padding=8), ttk.Frame(self.book, padding=8)
        self.book.add(browse, text='Ara ve seç')
        self.book.add(review, text='Sepet ve işlem raporu')
        row = ttk.Frame(browse)
        row.pack(fill='x', pady=4)
        ttk.Label(row, text='Disk kaydı: ').pack(side='left')
        self.save_choice = ttk.Combobox(row, state='readonly', width=13)
        self.save_choice.pack(side='left')
        self.save_choice.bind('<<ComboboxSelected>>', lambda _: self.update_targets())
        self.kind = ttk.Combobox(row, state='readonly', values=list(KINDS), width=22)
        self.kind.set('Hepsi')
        self.kind.pack(side='left', padx=8)
        self.kind.bind('<<ComboboxSelected>>', lambda _: self.change_kind())
        self.query = tk.StringVar()
        ttk.Entry(row, textvariable=self.query, width=28).pack(side='left')
        self.query.trace_add('write', lambda *_: self.filter())
        self.family = ttk.Combobox(row, state='readonly', width=19)
        self.family.set('Tüm aileler')
        self.family.pack(side='left', padx=8)
        self.family.bind('<<ComboboxSelected>>', lambda _: self.filter())
        row = ttk.Frame(browse)
        row.pack(fill='x', pady=5)
        ttk.Label(row, text='Eşya / teknoloji hedefi: ').pack(side='left')
        self.target_kind = ttk.Combobox(row, state='readonly', values=list(TARGETS), width=17)
        self.target_kind.set('Ekzosuit')
        self.target_kind.pack(side='left')
        self.target_kind.bind('<<ComboboxSelected>>', lambda _: self.update_targets())
        self.target_choice = ttk.Combobox(row, state='readonly', width=53)
        self.target_choice.pack(side='left', padx=8)
        self.target_choice.bind('<<ComboboxSelected>>', lambda _: self.filter())
        self.show_all = tk.BooleanVar(value=False)
        self.fit = tk.BooleanVar(value=True)
        self.new_ship_seed = tk.BooleanVar(value=False)
        self.random_tool_seed = tk.BooleanVar(value=False)
        self.favorites_only = tk.BooleanVar(value=False)
        self.recent_only = tk.BooleanVar(value=False)
        row = ttk.Frame(browse)
        row.pack(fill='x')
        ttk.Checkbutton(row, text='Yalnız uygun teknolojiler', variable=self.fit, command=self.filter).pack(side='left')
        ttk.Checkbutton(row, text='Beğenilmeyen gemi profillerini de göster', variable=self.show_all, command=self.filter).pack(side='left', padx=8)
        ttk.Checkbutton(row, text='Favoriler', variable=self.favorites_only, command=self.filter).pack(side='left')
        ttk.Checkbutton(row, text='Son kullanılan', variable=self.recent_only, command=self.filter).pack(side='left', padx=6)
        ttk.Checkbutton(browse, text='Gemi profillerini yeni tohumla ekle (aynı modelden kopya; görünüm değişimi garanti değil)',
                        variable=self.new_ship_seed).pack(anchor='w')
        ttk.Checkbutton(browse, text='Alet ödül tohumunu rastgele değiştir (kapalıyken hazır referans kullanılır)',
                        variable=self.random_tool_seed).pack(anchor='w')
        self.count = ttk.Label(row, text='')
        self.count.pack(side='right')
        self.products = ttk.Treeview(browse, columns=('title', 'kind', 'detail'), show='headings', selectmode='extended', height=7)
        for key, title, width in [('title', 'İçerik', 340), ('kind', 'Tür / durum', 155), ('detail', 'Aile / profil', 400)]:
            self.products.heading(key, text=title)
            self.products.column(key, width=width)
        product_row = ttk.Frame(browse)
        product_row.pack(fill='both', expand=True, pady=6)
        # Keep scrollbars with the list, including when a smaller window is used.
        self.products.pack(in_=product_row, side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(product_row, orient='vertical', command=self.products.yview)
        scrollbar.pack(side='right', fill='y')
        self.products.configure(yscrollcommand=scrollbar.set)
        self.products.bind('<<TreeviewSelect>>', lambda _: self.show_detail())
        self.details = ScrolledText(browse, height=4, wrap='word', font=('Segoe UI', 10), state='disabled')
        self.details.pack(fill='x', pady=(0, 4))
        row = ttk.Frame(browse)
        row.pack(fill='x')
        ttk.Label(row, text='Yeni alet adı: ').pack(side='left')
        self.new_name = tk.StringVar(value='Yeni Alet')
        ttk.Entry(row, textvariable=self.new_name, width=18).pack(side='left')
        ttk.Label(row, text='Eşya miktarı: ').pack(side='left', padx=(8, 0))
        self.quantity = tk.StringVar(value='1')
        ttk.Spinbox(row, from_=1, to=10000000, textvariable=self.quantity, width=8).pack(side='left')
        ttk.Button(row, text='Seçilenleri sepete ekle', command=self.add).pack(side='left', padx=8)
        ttk.Button(row, text='Sepete git', command=lambda: self.book.select(1)).pack(side='left')
        ttk.Button(row, text='★ Favori', command=self.favorite).pack(side='left', padx=4)
        ttk.Button(row, text='Tarifi öğren', command=self.learn_recipe).pack(side='left')
        ttk.Label(browse, text='Alet modelleri/tohumları kaynak aletin sınıfını ve donanımını kullanır. Rehber kayıtları sepete eklenmez.\n'
                  'Aktif sınırlar: 12 gemi, 6 alet. Gemi profilleri boş yuva ister; garajda tam kopyalar saklanır.', wraplength=1050).pack(anchor='w', pady=6)
        self.cart_label = ttk.Label(review, text='Sepet boş')
        self.cart_label.pack(anchor='w')
        self.cart_list = tk.Listbox(review, height=6, font=('Consolas', 10), exportselection=False)
        self.cart_list.pack(fill='x', pady=6)
        row = ttk.Frame(review)
        row.pack(fill='x')
        ttk.Button(row, text='Seçileni çıkar', command=self.remove).pack(side='left')
        ttk.Button(row, text='Sepeti temizle', command=self.clear).pack(side='left', padx=6)
        ttk.Button(row, text='Yeni planı hazırla', command=self.prepare).pack(side='left')
        self.report = ScrolledText(review, state='disabled', height=14, font=('Consolas', 10))
        self.report.pack(fill='both', expand=True, pady=8)
        row = ttk.Frame(review)
        row.pack(fill='x')
        self.apply_button = ttk.Button(row, text='İncelediğim sepeti uygula', command=self.apply, state='disabled')
        self.apply_button.pack(side='left')
        self.restore_button = ttk.Button(row, text='Son katalog işlemi öncesine tam kayıt geri al', command=self.restore, state='disabled')
        self.restore_button.pack(side='left', padx=8)
        from .inventory_ui import WorkbenchPanel, fit_grid
        workspace = ttk.Frame(self.book, padding=8)
        self.book.add(workspace, text='Envanter / donanım / arşiv')
        self.workbench = WorkbenchPanel(workspace, self)
        fit_grid(browse, 5)
        self.change_kind()

    def favorite(self):
        for key in self.products.selection():
            self.service.toggle_favorite(key)
        self.filter()

    def learn_recipe(self):
        try:
            keys = self.products.selection()
            if not keys:
                raise ValueError('Katalogdan bir teknoloji veya üretilebilir ürün seçin.')
            actions = []
            for key in keys:
                prefix, ident = key.split(':', 1)
                entry = self.service.detail(key)
                if prefix != 'tech' and not (prefix == 'item' and entry['kind'] == 'Product' and entry['craftable']):
                    raise ValueError('Seçimin içinde öğrenilebilir tarifi olmayan içerik var.')
                actions.append({'op': 'learn_recipe', 'kind': 'technology' if prefix == 'tech' else 'product', 'id': ident})
            self.queue(self.selected_save()['file'], actions)
        except Exception as exc:
            messagebox.showerror('Tarif', str(exc))

    def queue(self, filename, commands):
        number = 1 if filename == 'save.hg' else int(filename[4:-3])
        slot = (number + 1) // 2
        if self.cart.commands and self.cart.save_slot != slot:
            raise ValueError('Farklı oyun yuvaları tek sepete konulamaz.')
        if len(self.cart.commands) + len(commands) > 256:
            raise ValueError('Tek sepet en fazla 256 işlem alabilir.')
        for command in commands:
            self.cart.add(slot, command)
        self.changed()

    def change_kind(self):
        self.family.configure(values=['Tüm aileler'] + sorted({p.family for p in self.service.items(
            kind=KINDS[self.kind.get()], include_hidden=True) if p.family}))
        self.family.set('Tüm aileler')
        self.filter()

    def show_detail(self):
        keys = self.products.selection()
        if not keys:
            if hasattr(self, 'details'):
                self.details.configure(state='normal')
                self.details.delete('1.0', 'end')
                self.details.configure(state='disabled')
            return
        key = keys[0]
        data = self.service.detail(key)
        title = data.get('title', data.get('name', data.get('id', key)))
        lines = [title]
        lines += [str(data[k]) for k in ('description', 'summary', 'status', 'note') if data.get(k)]
        if 'model' in data:
            lines.append('Model: ' + data['model'])
        if 'seed' in data:
            lines.append('Referans tohum: ' + data['seed'])
        if data.get('category'):
            lines.append('Kategori: ' + data['category'] + ' • ID: ' + data['id'])
        lines += ['Kaynak: ' + p for p in data.get('sources', [])]
        self.details.configure(state='normal')
        self.details.delete('1.0', 'end')
        self.details.insert('1.0', '\n'.join(lines))
        self.details.configure(state='disabled')

    def selected_save(self):
        index = self.save_choice.current()
        if index < 0:
            raise ValueError('Ortak kayıt listesinin dolmasını bekleyin.')
        return self.saves[index]

    def selected_target(self):
        index = self.target_choice.current()
        return self.targets[index] if index >= 0 else None

    def load_snapshot(self, saves, garage):
        previous = self.save_choice.get()
        self.saves, self.service.garage = saves, garage
        names = [s['file'] for s in saves]
        self.save_choice.configure(values=names)
        if names:
            self.save_choice.current(names.index(previous) if previous in names else max(range(len(saves)), key=lambda i: saves[i].get('mtime_ns', 0)))
        else:
            self.save_choice.set('')
        self.update_targets()
        self.workbench.load_snapshot(saves)

    def update_targets(self):
        previous = self.selected_target()
        index = self.save_choice.current()
        save = self.saves[index] if index >= 0 else {}
        kind = TARGETS[self.target_kind.get()]
        self.targets = save.get('fleet' if kind == 'ship' else 'multitools', []) if kind != 'exosuit' else []
        self.target_choice.configure(values=[f"{p['slot']} • {p['name']} • {p['seed']}" for p in self.targets])
        if self.targets:
            chosen = next((i for i, t in enumerate(self.targets) if previous and (t['slot'], t['seed']) == (previous['slot'], previous['seed'])), 0)
            self.target_choice.current(chosen)
        else:
            self.target_choice.set('')
        self.filter()

    def filter(self):
        if not hasattr(self, 'products'):
            return
        selected = set(self.products.selection())
        target = self.selected_target()
        items = self.service.items(self.query.get(), KINDS[self.kind.get()],
            TARGETS[self.target_kind.get()] if self.fit.get() else '', (target or {}).get('type'), self.show_all.get(),
            '' if self.family.get() == 'Tüm aileler' else self.family.get(), self.favorites_only.get(), self.recent_only.get())
        self.products.delete(*self.products.get_children())
        for item in items:
            self.products.insert('', 'end', iid=item.key, values=(('★ ' if item.preferred else '') + item.title,
                KIND_LABELS[item.kind], item.family + ' • ' + item.detail))
            if item.key in selected:
                self.products.selection_add(item.key)
        self.count.configure(text=f'{len(items)} sonuç')
        c = self.service.counts()
        self.overview.configure(text=f"{c['ships']} gemi profili / tohum varyantı • {c['tools']} alet modeli / tohum varyantı • "
            f"{c['technologies']} teknoloji • {c['items']} eşya • {c['garage']} garaj kaydı | Seçenek sayıları oyundaki toplam tür sayısı değildir.")

    def add(self):
        try:
            save = self.selected_save()
            number = 1 if save['file'] == 'save.hg' else int(save['file'][4:-3])
            keys = self.products.selection()
            if not keys:
                raise ValueError('Listeden bir veya birden çok içerik seçin.')
            pending = []
            for key in keys:
                target_kind = TARGETS[self.target_kind.get()]
                target = self.selected_target()
                if key.startswith('tool:'):
                    target = target if target_kind == 'multitool' else next((t for t in save['multitools'] if t['active']), None)
                    selector = {k: target[k] for k in ('slot', 'seed', 'filename')} if target else None
                elif key.startswith(('tech:', 'item:')) and target_kind != 'exosuit':
                    fields = ('slot', 'seed', 'type') if target_kind == 'ship' else ('slot', 'seed', 'filename')
                    selector = {k: target[k] for k in fields} if target else None
                else:
                    selector = None
                pending.append(self.service.command(key, target_kind, selector, self.new_name.get(), self.new_ship_seed.get(), self.random_tool_seed.get(), int(self.quantity.get())))
            if self.cart.commands and self.cart.save_slot != (number + 1) // 2:
                raise ValueError('Farklı oyun yuvaları tek sepete konulamaz.')
            if len(self.cart.commands) + len(pending) > 256:
                raise ValueError('Tek sepet en fazla 256 işlem alabilir.')
            for command in pending:
                self.cart.add((number + 1) // 2, command)
            self.changed()
            self.service.remember(keys)
        except Exception as exc:
            messagebox.showerror('Katalog', str(exc))

    def changed(self):
        self.review = None
        self.apply_button.configure(state='disabled')
        self.cart_list.delete(0, 'end')
        for command in self.cart.commands:
            self.cart_list.insert('end', json.dumps(command, ensure_ascii=False))
        self.cart_label.configure(text=f'Kayıt yuvası {self.cart.save_slot} • {len(self.cart.commands)} işlem')

    def remove(self):
        selected = self.cart_list.curselection()
        if selected:
            self.cart.remove(selected[0])
            self.changed()

    def clear(self):
        self.cart.clear()
        self.changed()

    def output(self, value):
        self.report.configure(state='normal')
        self.report.delete('1.0', 'end')
        self.report.insert('1.0', value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))
        self.report.configure(state='disabled')

    def prepare(self):
        if self.host.busy:
            return
        try:
            plan = self.cart.plan()
        except ValueError as exc:
            messagebox.showerror('Sepet', str(exc))
            return
        if not self.host.closed_confirmation():
            return
        self.review = None
        self.apply_button.configure(state='disabled')
        self.output({'plan': plan, 'durum': 'Taze kayıt, yedek ve codec doğrulanıyor.'})
        revision = self.cart.revision
        def prepared(result):
            path, manifest, fingerprint = result
            if revision != self.cart.revision:
                self.output('Hazırlama sırasında sepet değişti. Güncel sepet için yeni plan hazırlayın.')
                return
            self.review = (path, fingerprint, revision)
            self.output({'transaction': str(path), 'plan': manifest['plan'], 'report': manifest['report']})
            changed = any(report['changed_paths'] for report in manifest['report'].values())
            self.apply_button.configure(state='normal' if changed else 'disabled')
        self.host.run(lambda: self.backend.prepare(plan), prepared)

    def apply(self):
        if self.host.busy or not self.review:
            return
        if not messagebox.askyesno('Katalog sepeti', 'Raporu incelediniz mi? Oyun tamamen kapalı olmalı.\nSepet canlı kayıt dosyalarına uygulansın mı?'):
            return
        path, fingerprint, revision = self.review
        if revision != self.cart.revision:
            self.review = None
            self.apply_button.configure(state='disabled')
            return
        self.review = None
        self.apply_button.configure(state='disabled')
        def done(output):
            self.last_applied = path
            self.restore_button.configure(state='normal')
            self.output(output + '\nYedek: ' + str(path / 'before'))
        self.host.run(lambda: self.backend.apply(path, fingerprint), done)

    def restore(self):
        if self.host.busy or not self.last_applied or not self.host.closed_confirmation():
            return
        if not messagebox.askyesno('Tam kayıt geri alma', 'Bu sepet işleminden önceki TAM kayda dönülecek.\nSonraki ilerleme eski kayıtta yoktur; güncel durum ayrıca yedeklenir. Devam edilsin mi?'):
            return
        path = self.last_applied
        def done(output):
            self.last_applied = None
            self.restore_button.configure(state='disabled')
            self.output(output)
        self.host.run(lambda: self.backend.restore(path), done)
