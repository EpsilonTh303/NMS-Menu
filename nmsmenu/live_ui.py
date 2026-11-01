"""Live controls, independent of the offline fleet editor."""
import tkinter as tk
from tkinter import messagebox, ttk

from .live import CURRENCIES, SETTINGS, LiveBackend


class LivePanel:
    def __init__(self, parent, host, backend=None):
        self.host = host
        self.backend = backend or LiveBackend()
        self.state = None
        self.state_label = ttk.Label(parent, text='Bağlı değil. Oyunu açın; para kontrolleri için kaydınızı yükleyin.')
        self.state_label.pack(anchor='w')
        bar = ttk.Frame(parent)
        bar.pack(fill='x', pady=10)
        ttk.Button(bar, text='Açık oyuna bağlan', command=self.connect).pack(side='left')
        ttk.Button(bar, text='Canlı değerleri yenile', command=self.refresh).pack(side='left', padx=5)
        ttk.Button(bar, text='Ayarları geri al ve bağlantıyı kes', command=self.disconnect).pack(side='left')
        self.topmost = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text='Menü üstte kalsın', variable=self.topmost,
                        command=lambda: host.root.attributes('-topmost', self.topmost.get())).pack(side='right')
        ttk.Label(parent, text='Değişiklikler oyun açıkken uygulanır. Bu sekme kayıt dosyasına veya oyun koduna yazmaz.').pack(anchor='w')
        money = ttk.LabelFrame(parent, text='Canlı para miktarı', padding=10)
        money.pack(fill='x', pady=10)
        self.money_values = {}
        self.money_buttons = []
        for row, key in enumerate(CURRENCIES):
            ttk.Label(money, text=key, width=15).grid(row=row, column=0, sticky='w', pady=3)
            current = ttk.Label(money, text='—', width=18)
            current.grid(row=row, column=1)
            value = tk.StringVar(value='')
            ttk.Entry(money, textvariable=value, width=18).grid(row=row, column=2)
            button = ttk.Button(money, text='Miktarı ayarla', state='disabled',
                                 command=lambda k=key, v=value: self.set_currency(k, v))
            button.grid(row=row, column=3, padx=8)
            self.money_buttons.append(button)
            self.money_values[key] = (current, value)
        self.undo_button = ttk.Button(money, text='Son para işlemini geri al', state='disabled',
                                     command=lambda: self.host.run(self.backend.undo_currency, self.render))
        self.undo_button.grid(row=3, column=0, columnspan=2, sticky='w', pady=(7, 0))
        ttk.Label(money, text='Oyun kaydederse para kalıcı olur. Geri alma, değer hâlâ aynıysa çalışır.').grid(
            row=4, column=0, columnspan=4, sticky='w', pady=(5, 0))
        self.tree = ttk.Treeview(parent, columns=('setting', 'value', 'range'), show='headings', height=8,
                                 selectmode='browse')
        for key, title, width in [('setting', 'Canlı ayar', 410), ('value', 'Şu an', 150), ('range', 'İzinli aralık', 200)]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width)
        for key, field in SETTINGS.items():
            self.tree.insert('', 'end', iid=key, values=(field.title, '—', f'{field.minimum} – {field.maximum}'))
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', lambda _: self.selected())
        edit = ttk.Frame(parent)
        edit.pack(fill='x', pady=8)
        self.setting_value = tk.StringVar()
        ttk.Label(edit, text='Seçili ayarın yeni değeri: ').pack(side='left')
        ttk.Entry(edit, textvariable=self.setting_value, width=14).pack(side='left')
        self.setting_button = ttk.Button(edit, text='Oyunda hemen uygula', command=self.set_setting, state='disabled')
        self.setting_button.pack(side='left', padx=8)
        self.restore_button = ttk.Button(edit, text='Değiştirdiğim ayarları geri al', state='disabled',
                                         command=lambda: host.run(self.backend.restore_settings, self.render))
        self.restore_button.pack(side='left')
        self.note = ttk.Label(parent, text='Listeden ayar seçin. Geçici ayarlar bağlantı kesilirken geri alınır.', wraplength=1000)
        self.note.pack(anchor='w')
        ttk.Label(parent, text='Gemi ekleme/kaldırma ve yuva genişletme: Filo ve envanter sekmesi; oyun kapalı olmalı.').pack(anchor='w', pady=(6, 0))

    def connect(self):
        if self.host.busy:
            return
        self.host.run(self.backend.connect, self.render)

    def refresh(self):
        self.host.run(self.backend.snapshot, self.render)

    def render(self, state):
        self.state = state
        self.state_label.configure(text=f"Bağlı • PID {state['pid']} • " + (
            f"Kayıt yuvası {state['save_slot']} • Canlı oyuncu hazır" if state['loaded'] else 'Ana menü / yükleme • Para kontrolleri kilitli'))
        for key, value in state['settings'].items():
            self.tree.set(key, 'value', f'{value:.5g}')
        for key, (label, value) in self.money_values.items():
            label.configure(text=f"{state['currencies'][key]:,}" if state['loaded'] else 'Kayıt yüklenmeli')
            if not value.get() and state['loaded']:
                value.set(str(state['currencies'][key]))
        for button in self.money_buttons:
            button.configure(state='normal' if state['loaded'] else 'disabled')
        self.undo_button.configure(state='normal' if state['loaded'] and self.backend.currency_undo else 'disabled')
        self.setting_button.configure(state='normal')
        self.restore_button.configure(state='normal' if self.backend.originals else 'disabled')

    def selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        key = selected[0]
        field = SETTINGS[key]
        self.note.configure(text=field.note)
        self.setting_value.set(f"{self.state['settings'][key]:.5g}" if self.state else '')

    def set_setting(self):
        if self.host.busy:
            return
        try:
            selected = self.tree.selection()
            if not selected:
                raise ValueError('Önce listeden bir ayar seçin.')
            key, value = selected[0], float(self.setting_value.get().replace(',', '.'))
        except ValueError as exc:
            messagebox.showerror('Ayar', str(exc))
            return
        self.host.run(lambda: self.backend.set_setting(key, value), self.render)

    def set_currency(self, key, variable):
        if self.host.busy:
            return
        try:
            value = int(variable.get())
        except ValueError:
            messagebox.showerror('Para', 'Miktarı ayraçsız tam sayı olarak girin.')
            return
        self.host.run(lambda: self.backend.set_currency(key, value), self.render)

    def disconnect(self):
        def work():
            if self.backend.memory and not self.backend.memory.alive():
                self.backend.forget_closed_session()
            else:
                self.backend.disconnect()

        def done(_):
            self.state = None
            self.state_label.configure(text='Bağlantı kesildi. Geçici ayarlar geri alındı veya oyun oturumu kapandı.')
            for button in [*self.money_buttons, self.undo_button, self.setting_button, self.restore_button]:
                button.configure(state='disabled')
            for label, _ in self.money_values.values():
                label.configure(text='—')
            for key in SETTINGS:
                self.tree.set(key, 'value', '—')
        self.host.run(work, done)
