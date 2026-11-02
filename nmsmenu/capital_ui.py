"""Capital fleet panel. Commands enter the existing reviewed catalog basket."""
import secrets
import tkinter as tk
from tkinter import ttk, messagebox

from . import capital
from .inventory import fingerprint


class CapitalPanel:
    def __init__(self, parent, host):
        self.host, self.saves, self.view, self.signature = host, [], {}, None
        ttk.Label(parent, text='Yük gemisi ve fırkateyn yönetimi', font=('Segoe UI', 15, 'bold')).pack(anchor='w')
        ttk.Label(parent, text='Oyun kapalıyken çalışır. İşlemler ortak sepete eklenir; yeni plan ve rapor incelemesi gerekir.', wraplength=1050).pack(anchor='w', pady=5)
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=5)
        ttk.Label(row, text='Disk kaydı: ').pack(side='left')
        self.save_choice = ttk.Combobox(row, state='readonly', width=15)
        self.save_choice.pack(side='left')
        self.save_choice.bind('<<ComboboxSelected>>', lambda _: self.load_save())
        self.info = ttk.Label(row, text='Ortak kayıt taraması bekleniyor.')
        self.info.pack(side='left', padx=12)
        group = ttk.LabelFrame(parent, text='Yük gemisi', padding=10)
        group.pack(fill='x', pady=5)
        self.freighter_info = ttk.Label(group, text='Sahip olunan yük gemisi bulunamadı.')
        self.freighter_info.pack(anchor='w')
        row = ttk.Frame(group)
        row.pack(fill='x', pady=5)
        self.freighter_name = tk.StringVar()
        ttk.Entry(row, textvariable=self.freighter_name, width=28).pack(side='left')
        self.freighter_class = ttk.Combobox(row, values=['C', 'B', 'A', 'S'], state='readonly', width=5)
        self.freighter_class.pack(side='left', padx=5)
        self.freighter_buttons = []
        for title, fn in [('Adı sepete ekle', lambda: self.freighter('freighter_edit', {'name': capital.name(self.freighter_name.get())})),
                          ('Sınıfı sepete ekle', lambda: self.freighter('freighter_edit', {'class': self.freighter_class.get()})),
                          ('Onar / şarj et', lambda: self.freighter('freighter_repair')),
                          ('S sınıfı 120/60 yuva', lambda: self.freighter('freighter_expand'))]:
            button = ttk.Button(row, text=title, state='disabled', command=lambda fn=fn: self.perform(fn))
            button.pack(side='left', padx=3)
            self.freighter_buttons.append(button)
        group = ttk.LabelFrame(parent, text='Fırkateyn filosu', padding=10)
        group.pack(fill='both', expand=True, pady=5)
        self.fleet_info = ttk.Label(group, text='')
        self.fleet_info.pack(anchor='w')
        self.tree = ttk.Treeview(group, columns=('slot', 'name', 'type', 'class', 'seed', 'damage', 'mission'), show='headings', selectmode='browse', height=6)
        for key, title, width in [('slot', 'Yuva', 45), ('name', 'Ad', 170), ('type', 'Tür', 110),
                                  ('class', 'Sınıf', 50), ('seed', 'Tohum / kimlik', 180), ('damage', 'Hasar', 55), ('mission', 'Sefer', 100)]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width)
        self.tree.pack(fill='both', expand=True, pady=5)
        self.tree.bind('<<TreeviewSelect>>', lambda _: self.selected())
        row = ttk.Frame(group)
        row.pack(fill='x')
        ttk.Label(row, text='Ad: ').pack(side='left')
        self.frigate_name = tk.StringVar()
        ttk.Entry(row, textvariable=self.frigate_name, width=24).pack(side='left')
        self.stats = [tk.StringVar(value='0') for _ in range(4)]
        for title, value in zip(('Savaş', 'Keşif', 'Sanayi', 'Ticaret'), self.stats):
            ttk.Label(row, text=title).pack(side='left', padx=(8, 2))
            ttk.Spinbox(row, from_=0, to=100, textvariable=value, width=5).pack(side='left')
        row = ttk.Frame(group)
        row.pack(fill='x', pady=5)
        self.frigate_buttons = []
        for title, fn in [('Adı değiştir', lambda: self.frigate('frigate_edit', {'name': capital.name(self.frigate_name.get())})),
                          ('Becerileri ayarla', lambda: self.frigate('frigate_edit', {'stats': [int(v.get()) for v in self.stats]})),
                          ('Fırkateyni onar', lambda: self.frigate('frigate_repair')),
                          ('Yeni tohumla kopyala', self.clone), ('Fırkateyni kaldır', lambda: self.frigate('frigate_remove'))]:
            button = ttk.Button(row, text=title, state='disabled', command=lambda fn=fn: self.perform(fn))
            button.pack(side='left', padx=(0, 6))
            self.frigate_buttons.append(button)
        ttk.Label(group, text='Seferdeki veya rapor bekleyen fırkateyn değiştirilemez. Kaldırma için tüm sefer raporlarını alın. Normal türler kopyalanır; sınır 30.', wraplength=1050).pack(anchor='w')
        ttk.Button(parent, text='Sepet ve işlem raporuna git', command=self.open_basket).pack(anchor='e', pady=5)

    def perform(self, fn):
        try:
            fn()
        except (ValueError, KeyError, IndexError) as exc:
            messagebox.showerror('Yük gemisi / fırkateyn', str(exc))

    def open_basket(self):
        self.host.book.select(6)
        self.host.catalog_panel.book.select(1)

    def load_saves(self, saves):
        previous = self.save_choice.get()
        self.saves = saves
        names = [s['file'] for s in saves]
        self.save_choice.configure(values=names)
        if names:
            self.save_choice.current(names.index(previous) if previous in names else max(range(len(saves)), key=lambda i: saves[i].get('mtime_ns', 0)))
        else:
            self.save_choice.set('')
        self.load_save()

    def save(self):
        index = self.save_choice.current()
        if not 0 <= index < len(self.saves):
            raise ValueError('Ortak kayıt listesinin dolmasını bekleyin.')
        return self.saves[index]

    def load_save(self):
        current = self.saves[self.save_choice.current()] if self.save_choice.current() >= 0 else {}
        view = current.get('capital', {'freighter': None, 'frigates': [], 'missions': 0})
        signature = fingerprint([current.get('file'), view, current.get('capital_error')])
        if signature == self.signature:
            return
        self.signature, self.view = signature, view
        self.info.configure(text=current.get('capital_error', current.get('read_at', '')))
        freighter = view['freighter']
        self.freighter_info.configure(text=(freighter['name'] or freighter['filename']) + f" • {freighter['class']} • {freighter['cargo']} / {freighter['tech']}" if freighter else 'Sahip olunan yük gemisi bulunamadı.')
        self.freighter_name.set(freighter['name'] if freighter else '')
        self.freighter_class.set(freighter['class'] if freighter else '')
        for button in self.freighter_buttons:
            button.configure(state='normal' if freighter and not current.get('capital_error') else 'disabled')
        self.tree.delete(*self.tree.get_children())
        for i, frigate in enumerate(view['frigates']):
            self.tree.insert('', 'end', iid=str(i), values=(frigate['slot'], frigate['name'], frigate['type'], frigate['class'], frigate['seed'], frigate['damage'], 'Sefer / rapor' if frigate['busy'] else 'Boşta'))
        self.fleet_info.configure(text=f"{len(view['frigates'])} / 30 fırkateyn • {view['missions']} sefer")
        self.selected()

    def chosen(self):
        selected = self.tree.selection()
        if not selected:
            raise ValueError('Taze listeden bir fırkateyn seçin.')
        frigate = self.view['frigates'][int(selected[0])]
        if frigate['busy']:
            raise ValueError('Seferdeki veya rapor bekleyen fırkateyn düzenlenemez.')
        return frigate

    def selected(self):
        selected = self.tree.selection()
        frigate = self.view.get('frigates', [])[int(selected[0])] if selected else None
        for button in self.frigate_buttons:
            button.configure(state='normal' if frigate and not frigate['busy'] else 'disabled')
        if frigate:
            self.frigate_name.set(frigate['name'])
            for variable, value in zip(self.stats, frigate['stats']):
                variable.set(str(value))

    def queue(self, action):
        self.host.catalog_panel.queue(self.save()['file'], [action])
        self.info.configure(text='İşlem sepete eklendi; henüz uygulanmadı.')

    def freighter(self, operation, fields=None):
        freighter = self.view.get('freighter')
        if not freighter:
            raise ValueError('Sahip olunan yük gemisi bulunamadı.')
        action = {'op': operation, 'selector': {key: freighter[key] for key in ('filename', 'seed')}}
        if fields is not None:
            action['fields'] = fields
        self.queue(action)

    def frigate(self, operation, fields=None):
        frigate = self.chosen()
        action = {'op': operation, 'selector': {key: frigate[key] for key in ('slot', 'seed', 'type')}}
        if fields is not None:
            action['fields'] = fields
        self.queue(action)

    def clone(self):
        frigate = self.chosen()
        self.queue({'op': 'frigate_clone', 'selector': {key: frigate[key] for key in ('slot', 'seed', 'type')},
                    'name': capital.name(self.frigate_name.get()), 'seed': f'0x{secrets.randbits(64) or 1:016X}'})
