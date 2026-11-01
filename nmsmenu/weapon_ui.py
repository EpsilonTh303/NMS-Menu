import json
import secrets
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .weapon_backend import WeaponBackend


class WeaponPanel:
    def __init__(self, parent, host):
        self.host, self.backend = host, WeaponBackend()
        self.saves, self.tools = [], []
        self.review, self.last_applied = None, None
        ttk.Label(parent, text='Çok amaçlı alet koleksiyonu', font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        ttk.Label(parent, text='Ekleme / silme için oyunu kaydedip tamamen kapatın. Liste oyun açıkken de okunabilir.').pack(anchor='w', pady=5)
        bar = ttk.Frame(parent)
        bar.pack(fill='x', pady=6)
        ttk.Button(bar, text='Taze silah listesini oku', command=self.refresh).pack(side='left')
        self.save_choice = ttk.Combobox(bar, state='readonly', width=16)
        self.save_choice.pack(side='left', padx=8)
        self.save_choice.bind('<<ComboboxSelected>>', lambda _: self.populate())
        self.tree = ttk.Treeview(parent, columns=('slot', 'name', 'seed', 'class', 'slots', 'active'),
                                 show='headings', height=7, selectmode='browse')
        for key, title, width in [('slot', 'Yuva', 55), ('name', 'Kayıttaki ad', 240), ('seed', 'Tohum / kimlik', 240),
                                  ('class', 'Sınıf', 70), ('slots', 'Yuva', 70), ('active', 'Aktif', 70)]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width)
        self.tree.pack(fill='x', pady=8)
        row = ttk.Frame(parent)
        row.pack(fill='x')
        ttk.Label(row, text='Yeni alet adı: ').pack(side='left')
        self.name = tk.StringVar(value='Yeni Alet')
        ttk.Entry(row, textvariable=self.name, width=20).pack(side='left')
        ttk.Button(row, text='Seçili aletin donanımıyla yeni alet: plan hazırla',
                   command=lambda: self.prepare('tool_add')).pack(side='left', padx=8)
        ttk.Button(row, text='Seçili aleti kaldır: plan hazırla',
                   command=lambda: self.prepare('tool_remove')).pack(side='left')
        ttk.Label(parent, text='Yeni alet, seçili aletin model ailesini, sınıfını ve donanımını kopyalar; farklı görünüm tohumu üretir. Sınır: 6 aktif alet.',
                  wraplength=1030).pack(anchor='w', pady=6)
        self.report = ScrolledText(parent, height=12, state='disabled', font=('Consolas', 10))
        self.report.pack(fill='both', expand=True)
        buttons = ttk.Frame(parent)
        buttons.pack(fill='x', pady=8)
        self.apply_button = ttk.Button(buttons, text='İncelediğim silah planını uygula', state='disabled', command=self.apply)
        self.apply_button.pack(side='left')
        self.restore_button = ttk.Button(buttons, text='Son silah işlemi öncesine tam kayıt geri al', state='disabled', command=self.restore)
        self.restore_button.pack(side='left', padx=8)
        station = ttk.LabelFrame(parent, text='Uzay istasyonu silah / hasar seçenekleri', padding=7)
        station.pack(fill='x')
        ttk.Checkbutton(station, text='İstasyonda silahı çıkar / kullan', state='disabled').pack(side='left')
        ttk.Checkbutton(station, text='İstasyon NPC’lerine hasar', state='disabled').pack(side='left', padx=12)
        ttk.Label(parent, text='İstasyon seçenekleri henüz bu sürümde doğrulanmadı; çalıştırılamaz. Çok amaçlı alet ekleme / silme canlı değildir.',
                  wraplength=1030).pack(anchor='w', pady=(5, 0))

    def output(self, value):
        self.report.configure(state='normal')
        self.report.delete('1.0', 'end')
        self.report.insert('1.0', value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))
        self.report.configure(state='disabled')

    def refresh(self):
        def loaded(saves):
            self.saves = saves
            self.save_choice.configure(values=[s['file'] for s in saves])
            if saves:
                self.save_choice.current(0)
            self.populate()
        self.host.run(self.backend.inspect, loaded)

    def populate(self):
        self.tree.delete(*self.tree.get_children())
        index = self.save_choice.current()
        self.tools = self.saves[index]['multitools'] if index >= 0 else []
        for i, tool in enumerate(self.tools):
            self.tree.insert('', 'end', iid=str(i), values=(tool['slot'], tool['name'], tool['seed'],
                tool['class'], tool['slots'], 'Evet' if tool['active'] else ''))

    def prepare(self, operation):
        if self.host.busy:
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror('Alet seçimi', 'Taze listeden tohum / yuva ile bir alet seçin.')
            return
        tool = self.tools[int(selected[0])]
        stem = self.saves[self.save_choice.current()]['file'].split('.')[0]
        number = 1 if stem == 'save' else int(stem[4:])
        action = {'op': operation, 'selector': {key: tool[key] for key in ('slot', 'seed', 'filename')}}
        if operation == 'tool_add':
            action.update(name=self.name.get(), seed=f'0x{secrets.randbits(64) or 1:016X}')
        plan = {'save_slot': (number + 1) // 2, 'actions': [action]}
        if not self.host.closed_confirmation():
            return
        self.review = None
        self.apply_button.configure(state='disabled')
        self.output({'plan': plan, 'durum': 'Taze kayıtlar, yedek ve codec eşitliği doğrulanıyor.'})

        def prepared(result):
            path, manifest, fingerprint = result
            self.review = (path, fingerprint)
            self.output({'transaction': str(path), 'plan': manifest['plan'], 'report': manifest['report'],
                         'not': 'Silinen alet donanımıyla dışa aktarılır. Auto/manual ayrı işlenir. Raporu inceleyin.'})
            self.apply_button.configure(state='normal')
        self.host.run(lambda: self.backend.prepare(plan), prepared)

    def apply(self):
        if self.host.busy or not self.review:
            return
        if not messagebox.askyesno('Silah planını uygula', 'Raporu incelediniz mi? Oyun tamamen kapalı olmalı.\n'
                                  'Değişiklikler canlı kayıt dosyalarına uygulanacak. Devam edilsin mi?'):
            return
        path, fingerprint = self.review
        self.review = None
        self.apply_button.configure(state='disabled')

        def done(output):
            self.last_applied = path
            self.restore_button.configure(state='normal')
            self.output(output + '\nYedek ve tam alet dışa aktarımları: ' + str(path))
        self.host.run(lambda: self.backend.apply(path, fingerprint), done)

    def restore(self):
        if self.host.busy or not self.last_applied:
            return
        if not self.host.closed_confirmation():
            return
        if not messagebox.askyesno('Tam kayıt geri alma', 'Seçili silah işleminden önceki tam oyun kaydına dönülecek.\n'
            'Sonraki ilerleme eski kayıtta yoktur. Güncel kayıt ayrıca yedeklenecek. Geri alınsın mı?'):
            return
        path = self.last_applied

        def done(output):
            self.last_applied = None
            self.restore_button.configure(state='disabled')
            self.output(output)
        self.host.run(lambda: self.backend.restore(path), done)
