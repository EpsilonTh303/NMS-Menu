"""Explicit, optional native reward requests; no automatic injection."""
import tkinter as tk
from tkinter import ttk, messagebox
from .runtime_ship import RuntimeShipClient, rewards


class RuntimeShipPanel:
    def __init__(self, parent, host):
        self.host = host
        self.client = RuntimeShipClient()
        self.profiles = rewards()
        group = ttk.LabelFrame(parent, text='Deneysel oyun içi gemi ödülü', padding=8)
        group.pack(fill='x', pady=8)
        ttk.Label(group, text='Ayrı runtime köprüsü gerekir. İstek sonraki doğal ödül çağrısında çalışır; teslim ekranı açılabilir. Oyun içi test yapılmadı.', wraplength=1050).pack(anchor='w')
        ttk.Label(group, text='Önce CapsLockFix ile oyunu açın; sonra Menu/native-bridge.cmd çalıştırın. Köprü otomatik yüklenmez.', wraplength=1050).pack(anchor='w')
        row = ttk.Frame(group)
        row.pack(fill='x', pady=4)
        self.choice = ttk.Combobox(row, values=[p['title'] for p in self.profiles.values()], state='readonly', width=28)
        self.choice.current(0)
        self.choice.pack(side='left')
        self.ack = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text='Test edilmemiş runtime desteğini kabul ediyorum', variable=self.ack).pack(side='left', padx=5)
        self.submit = ttk.Button(row, text='Gemi ödülünü sıraya al', command=self.enqueue, state='disabled')
        self.submit.pack(side='left')
        ttk.Button(row, text='Bekleyen isteği iptal et', command=self.cancel).pack(side='left', padx=5)
        self.status = ttk.Label(group, text='Runtime köprüsü bağlı değil.')
        self.status.pack(anchor='w')
        self.refresh()

    def refresh(self):
        state = self.client.status()
        ready = state.get('loaded') and state.get('offline') and state.get('accepting') and not self.host.busy
        self.submit.configure(state='normal' if ready and self.ack.get() else 'disabled')
        if state:
            result = state.get('last_result')
            if result and result.get('state') == 'dispatched':
                text = 'Ödül çağrısı gönderildi; oyundaki teslim ekranını kontrol edin.'
            elif result:
                text = f"İstek reddedildi: {result.get('error', '')}"
            elif (self.client.directory / 'request.json').exists():
                text = 'İstek bekliyor; oyunda doğal bir ödül alın.'
            else:
                text = 'Runtime köprüsü bağlı.' if state.get('loaded') else 'Runtime köprüsü bağlı; kayıt bekleniyor.'
            self.status.configure(text=text)
        else:
            self.status.configure(text='Runtime köprüsü bağlı değil.')
        self.host.root.after(1000, self.refresh)

    def enqueue(self):
        try:
            if self.host.busy:
                return
            reward = list(self.profiles)[self.choice.current()]
            ident = self.client.enqueue(reward, self.ack.get(), self.host.live_panel.backend)
            self.status.configure(text=f'İstek sıraya alındı: {ident}')
        except Exception as exc:
            messagebox.showerror('Runtime', str(exc))

    def cancel(self):
        try:
            self.client.cancel()
        except OSError as exc:
            messagebox.showerror('Runtime', str(exc))
