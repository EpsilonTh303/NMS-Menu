"""Temporary Tk presentation; all catalog / cart rules live in services."""
import json
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .catalog_backend import CatalogBackend
from .catalog_service import CatalogCart, CatalogService


KINDS = {'Hepsi': '', 'Gemi profilleri': 'ship', 'Çok amaçlı alet': 'multitool', 'Teknoloji': 'technology', 'Garaj': 'garage'}
TARGETS = {'Ekzosuit': 'exosuit', 'Gemi': 'ship', 'Çok amaçlı alet': 'multitool'}


class CatalogPanel:
    def __init__(self, parent, host):
        self.host, self.service, self.cart, self.backend = host, CatalogService(), CatalogCart(), CatalogBackend()
        self.saves, self.targets = [], []
        self.review, self.last_applied = None, None
        ttk.Label(parent, text='Ekleme kataloğu • gemi, alet ve teknoloji', font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        ttk.Label(parent, text='Liste ortak taramadan gelir. Sepet uygulaması için oyunu kaydedip tamamen kapatın.').pack(anchor='w', pady=5)
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
        self.kind.bind('<<ComboboxSelected>>', lambda _: self.filter())
        self.query = tk.StringVar()
        ttk.Entry(row, textvariable=self.query, width=28).pack(side='left')
        self.query.trace_add('write', lambda *_: self.filter())
        row = ttk.Frame(browse)
        row.pack(fill='x', pady=5)
        ttk.Label(row, text='Teknoloji hedefi: ').pack(side='left')
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
        row = ttk.Frame(browse)
        row.pack(fill='x')
        ttk.Checkbutton(row, text='Yalnız uygun teknolojiler', variable=self.fit, command=self.filter).pack(side='left')
        ttk.Checkbutton(row, text='Beğenilmeyen gemi profillerini de göster', variable=self.show_all, command=self.filter).pack(side='left', padx=8)
        ttk.Checkbutton(browse, text='Gemi profillerini yeni tohumla ekle (aynı modelden kopya; görünüm değişimi garanti değil)',
                        variable=self.new_ship_seed).pack(anchor='w')
        self.count = ttk.Label(row, text='')
        self.count.pack(side='right')
        self.products = ttk.Treeview(browse, columns=('title', 'kind', 'detail'), show='headings', selectmode='extended', height=10)
        for key, title, width in [('title', 'İçerik', 370), ('kind', 'Tür', 110), ('detail', 'Profil / teknoloji ID', 400)]:
            self.products.heading(key, text=title)
            self.products.column(key, width=width)
        self.products.pack(fill='both', expand=True, pady=8)
        row = ttk.Frame(browse)
        row.pack(fill='x')
        ttk.Label(row, text='Yeni alet adı: ').pack(side='left')
        self.new_name = tk.StringVar(value='Yeni Alet')
        ttk.Entry(row, textvariable=self.new_name, width=18).pack(side='left')
        ttk.Button(row, text='Seçilenleri sepete ekle', command=self.add).pack(side='left', padx=8)
        ttk.Button(row, text='Sepete git', command=lambda: self.book.select(1)).pack(side='left')
        ttk.Label(browse, text='Yeni alet, aktif aletin (alet hedefi seçiliyse o aletin) sınıfını/donanımını korur. Model ve görünüm tohumu değişir.\n'
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
        self.filter()

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
            TARGETS[self.target_kind.get()] if self.fit.get() else '', (target or {}).get('type'), self.show_all.get())
        self.products.delete(*self.products.get_children())
        for item in items:
            self.products.insert('', 'end', iid=item.key, values=(('★ ' if item.preferred else '') + item.title, item.kind, item.detail))
            if item.key in selected:
                self.products.selection_add(item.key)
        self.count.configure(text=f'{len(items)} içerik')

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
                elif key.startswith('tech:') and target_kind != 'exosuit':
                    fields = ('slot', 'seed', 'type') if target_kind == 'ship' else ('slot', 'seed', 'filename')
                    selector = {k: target[k] for k in fields} if target else None
                else:
                    selector = None
                pending.append(self.service.command(key, target_kind, selector, self.new_name.get(), self.new_ship_seed.get()))
            if self.cart.commands and self.cart.save_slot != (number + 1) // 2:
                raise ValueError('Farklı oyun yuvaları tek sepete konulamaz.')
            for command in pending:
                self.cart.add((number + 1) // 2, command)
            self.changed()
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
