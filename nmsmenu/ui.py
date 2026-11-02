"""Tk desktop shell; workers never access Tk widgets."""
from concurrent.futures import ThreadPoolExecutor
import time
import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .backend import FleetBackend
from .modules import MODULES, OPERATIONS, build_plan
from .live_ui import LivePanel
from .live_fleet_ui import LiveFleetPanel
from .weapon_ui import WeaponPanel
from .shared_scan import SharedScan
from .catalog_ui import CatalogPanel


def formatted(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


class MenuApp:
    def __init__(self, root, backend=None):
        self.root = root
        self.backend = backend or FleetBackend()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.scan_pool = ThreadPoolExecutor(max_workers=1)
        self.action_generation = 0
        self.shared_started = False
        self.live_future = None
        self.disk_future = None
        self.disk_signature = None
        self.next_live = 0
        self.next_disk = 0
        self.force_disk = True
        self.disk_error = ''
        self.busy = False
        self.review = None
        self.saves = []
        self.ships = []
        self.garage_entries = []
        self.transactions = []
        self.catalog = self.backend.catalog()
        self.loadouts = self.backend.loadouts()
        root.title("No Man's Sky • Menu 0.7 • Ekleme Kataloğu")
        root.geometry('1160x810')
        root.minsize(920, 680)
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TButton', padding=7)
        style.configure('TNotebook.Tab', padding=(18, 9))
        shell = ttk.Frame(root, padding=18)
        shell.pack(fill='both', expand=True)
        ttk.Label(shell, text='NO MAN’S SKY  /  KONTROL MERKEZİ', font=('Segoe UI', 19, 'bold')).pack(anchor='w')
        ttk.Label(shell, text='Offline GOG • Canlı filo: Esc duraklatma menüsünde • Kayıt dosyası düzenleme: oyun kapalıyken.').pack(anchor='w', pady=(4, 12))
        self.status = tk.StringVar(value='Otomatik bağlantı başlatılıyor; ortak listeler arka planda dolduruluyor.')
        controls = ttk.Frame(shell)
        controls.pack(fill='x', pady=(0, 6))
        self.scan_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text='Otomatik bağlantı ve ortak yenileme', variable=self.scan_enabled).pack(side='left')
        ttk.Button(controls, text='Tümünü yenile', command=self.refresh_all).pack(side='left', padx=10)
        self.scan_status = tk.StringVar(value='Açılışta otomatik bağlanır • Canlı veriler ~2 sn • Disk listeleri autosave değişince yenilenir')
        ttk.Label(shell, textvariable=self.scan_status, wraplength=1050).pack(anchor='w', pady=(0, 6))
        book = ttk.Notebook(shell)
        self.book = book
        book.pack(fill='both', expand=True)
        live = ttk.Frame(book, padding=12)
        live_fleet = ttk.Frame(book, padding=12)
        fleet = ttk.Frame(book, padding=12)
        weapons = ttk.Frame(book, padding=12)
        history = ttk.Frame(book, padding=12)
        roadmap = ttk.Frame(book, padding=12)
        catalog = ttk.Frame(book, padding=12)
        book.add(live, text='Canlı kontroller')
        book.add(live_fleet, text='Canlı filo')
        book.add(fleet, text='Filo ve envanter')
        book.add(weapons, text='Silah koleksiyonu')
        book.add(history, text='Yedek / geri alma')
        book.add(roadmap, text='Özellikler ve yol haritası')
        book.add(catalog, text='Katalog / toplu ekle')
        self.make_fleet(fleet)
        self.live_panel = LivePanel(live, self)
        self.live_fleet_panel = LiveFleetPanel(live_fleet, self, self.live_panel.backend)
        self.weapon_panel = WeaponPanel(weapons, self)
        self.catalog_panel = CatalogPanel(catalog, self)
        self.shared = SharedScan(self.live_panel.backend, self.live_fleet_panel.backend)
        self.make_history(history)
        self.make_roadmap(roadmap)
        ttk.Label(shell, textvariable=self.status, wraplength=1060).pack(anchor='w', pady=(10, 0))
        root.protocol('WM_DELETE_WINDOW', self.close)

    def close(self):
        if self.busy:
            messagebox.showinfo('İşlem sürüyor', 'Kayıt işlemi tamamlanınca pencereyi kapatın.')
            return
        self.scan_enabled.set(False)
        backend = self.live_panel.backend
        if backend.memory:
            def disconnect():
                if backend.memory.alive():
                    backend.disconnect()
                else:
                    backend.forget_closed_session()
            self.run(disconnect, lambda _: self.close())
            return
        self.pool.shutdown(wait=False)
        self.scan_pool.shutdown(wait=False, cancel_futures=True)
        self.root.destroy()

    def start_shared_scan(self):
        if not self.shared_started:
            self.shared_started = True
            self.root.after(0, self.shared_tick)

    def refresh_all(self):
        self.scan_enabled.set(True)
        self.next_live = 0
        self.next_disk = 0
        self.force_disk = True
        self.start_shared_scan()

    def shared_tick(self):
        if not self.busy:
            if self.live_future and self.live_future.done():
                future, self.live_future = self.live_future, None
                try:
                    result = future.result()
                    if self.live_scan_generation == self.action_generation:
                        if result['live']:
                            self.live_panel.render(result['live'])
                        else:
                            self.live_panel.render_disconnected()
                        self.live_fleet_panel.load_ships(result['fleet'])
                        self.scan_status.set('Canlı: ' + (result['error'] or 'bağlı ve güncel') +
                            ' • ' + (self.disk_error or 'Ortak disk listesi autosave değişince yenilenir'))
                except Exception as exc:
                    self.scan_status.set('Ortak canlı tarama: ' + str(exc))
            if self.disk_future and self.disk_future.done():
                future, self.disk_future = self.disk_future, None
                try:
                    result = future.result()
                    self.loaded(result['saves'])
                    self.weapon_panel.load_saves(result['saves'])
                    self.catalog_panel.load_snapshot(result['saves'], result['garage'])
                    self.load_garage(result['garage'])
                    self.load_history(result['history'])
                    self.disk_signature = self.requested_disk_signature
                    self.disk_error = '; '.join(result['errors'])
                    if self.action_generation == 0:
                        self.status.set(f"Ortak listeler hazır: {len(result['saves'])} kayıt, {len(result['garage'])} garaj gemisi, {len(result['history'])} işlem.")
                    if result['errors']:
                        self.disk_signature = None
                        self.next_disk = time.monotonic() + 5
                        self.scan_status.set('Disk kaydı: ' + '; '.join(result['errors']))
                except Exception as exc:
                    self.next_disk = time.monotonic() + 5
                    self.scan_status.set('Ortak kayıt taraması: ' + str(exc))
            if self.scan_enabled.get():
                now = time.monotonic()
                if self.live_future is None and now >= self.next_live:
                    self.live_scan_generation = self.action_generation
                    self.live_future = self.pool.submit(self.shared.fast)
                    self.next_live = now + 2
                if self.disk_future is None and now >= self.next_disk:
                    try:
                        signature = self.shared.disk.signature()
                        if self.force_disk or signature != self.disk_signature:
                            force, self.force_disk = self.force_disk, False
                            self.requested_disk_signature = signature
                            self.disk_future = self.scan_pool.submit(self.shared.disk.scan, force)
                    except Exception as exc:
                        self.next_disk = now + 5
                        self.scan_status.set('Kayıt konumu: ' + str(exc))
        self.root.after(200, self.shared_tick)

    def run(self, work, success):
        if self.busy:
            return
        self.busy = True
        self.action_generation += 1
        self.status.set('İşlem sürüyor…')
        future = self.pool.submit(work)

        def poll():
            if not future.done():
                self.root.after(100, poll)
                return
            self.busy = False
            try:
                result = future.result()
                success(result)
                self.status.set('İşlem tamamlandı. Ayrıntılar ilgili panelde.')
            except Exception as exc:
                self.status.set(str(exc))
                messagebox.showerror('İşlem durduruldu', str(exc))
        self.root.after(100, poll)

    def output(self, widget, value):
        if widget is getattr(self, 'report', None):
            self.review = None
            self.apply_button.configure(state='disabled')
        widget.configure(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', value if isinstance(value, str) else formatted(value))
        widget.configure(state='disabled')

    def make_fleet(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill='x')
        ttk.Label(bar, text='Ortak disk kayıt listesi').pack(side='left')
        ttk.Label(bar, text='   Kayıt yuvası:').pack(side='left')
        self.slot = tk.StringVar(value='1')
        self.slot_box = ttk.Combobox(bar, textvariable=self.slot, state='readonly', width=5,
                                     values=list(range(1, 16)))
        self.slot_box.pack(side='left')
        self.slot_box.bind('<<ComboboxSelected>>', lambda _: self.populate_ships())
        self.save_info = ttk.Label(bar, text='Henüz okunmadı')
        self.save_info.pack(side='left', padx=12)
        self.tree = ttk.Treeview(parent, columns=('slot', 'name', 'type', 'seed', 'cargo', 'tech'),
                                 show='headings', height=6, selectmode='browse')
        for key, label, width in [('slot', 'Gemi yuvası', 80), ('name', 'Kayıttaki ad', 210),
                                  ('type', 'Tür', 100), ('seed', 'Tohum / kimlik', 190),
                                  ('cargo', 'Kargo yuvası', 100), ('tech', 'Teknoloji', 90)]:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width)
        self.tree.pack(fill='x', pady=12)
        ttk.Label(parent, text='Boş prosedürel adlarda tür + tohum + yuva kimliğini kontrol edin. Aktif gemi sınırı: 12.').pack(anchor='w')
        controls = ttk.Frame(parent)
        controls.pack(fill='x', pady=10)
        self.operation = tk.StringVar(value=next(iter(OPERATIONS)))
        op_box = ttk.Combobox(controls, textvariable=self.operation, values=list(OPERATIONS), state='readonly', width=43)
        op_box.grid(row=0, column=0, sticky='w')
        op_box.bind('<<ComboboxSelected>>', lambda _: self.update_profiles())
        self.profile = tk.StringVar()
        self.profile_box = ttk.Combobox(controls, textvariable=self.profile, state='readonly', width=25)
        self.profile_box.grid(row=0, column=1, padx=10)
        ttk.Button(controls, text='1. Planı hazırla', command=self.prepare).grid(row=0, column=2)
        ttk.Label(controls, text='Garaj kaydı:').grid(row=1, column=0, sticky='w', pady=(8, 0))
        self.garage_choice = tk.StringVar()
        self.garage_box = ttk.Combobox(controls, textvariable=self.garage_choice, state='readonly', width=48)
        self.garage_box.grid(row=2, column=0, columnspan=2, sticky='w')
        ttk.Label(controls, text='Garaj otomatik listelenir').grid(row=1, column=2)
        ttk.Button(controls, text='Filoyu garaja arşivle', command=self.snapshot).grid(row=2, column=2)
        self.update_profiles()
        ttk.Label(parent, text='Hazırlanan işlem: eylemler, değişen JSON yolları ve sonuç filosu. Uygulamadan önce inceleyin.').pack(anchor='w')
        self.report = ScrolledText(parent, height=13, font=('Consolas', 10), state='disabled')
        self.report.pack(fill='both', expand=True, pady=5)
        self.apply_button = ttk.Button(parent, text='2. İncelediğim işlemi uygula', command=self.apply, state='disabled')
        self.apply_button.pack(anchor='e')

    def update_profiles(self):
        operation = OPERATIONS[self.operation.get()]
        values = list(self.loadouts) if operation == 'equip' else list(self.catalog) if operation == 'add' else []
        self.profile_box.configure(values=values, state='readonly' if values else 'disabled')
        preferred = 'utopia_speeder' if 'utopia_speeder' in values else values[0] if values else ''
        self.profile.set(preferred)

    def refresh(self):
        self.refresh_all()

    def loaded(self, saves):
        self.saves = saves
        self.populate_ships()
        if not saves:
            self.status.set('DefaultUser altında kayıt bulunamadı.')

    def populate_ships(self):
        previous = self.selected_ship()
        self.tree.delete(*self.tree.get_children())
        slot = int(self.slot.get())
        stems = {'save' if n == 1 else f'save{n}' for n in (2 * slot - 1, 2 * slot)}
        candidates = [s for s in self.saves if Path(s['file']).stem in stems]
        # Display newest of auto/manual; engine still edits each independently.
        chosen = max(candidates, key=lambda s: s.get('mtime_ns', 0), default=None)
        self.ships = chosen['fleet'] if chosen else []
        self.save_info.configure(text=f"Görünüm: {chosen['file']} • {len(self.ships)}/12 gemi" if chosen else 'Bu yuvada kayıt yok')
        for i, ship in enumerate(self.ships):
            self.tree.insert('', 'end', iid=str(i), values=(ship['slot'], ship['name'], ship['type'],
                             ship['seed'], ship['cargo_slots'], ship['tech_slots']))
            if previous and (ship['slot'], ship['seed']) == (previous['slot'], previous['seed']):
                self.tree.selection_set(str(i))

    def selected_ship(self):
        selected = self.tree.selection()
        return self.ships[int(selected[0])] if selected else None

    def closed_confirmation(self):
        return messagebox.askokcancel('Oyunu kapatın',
            'Önce oyunda kaydedip No Man’s Sky’ı tamamen kapatın.\n'
            'Oyun kapalıysa Tamam’a basın. Program oyunu zorla kapatmaz.')

    def prepare(self):
        if self.busy:
            return
        try:
            index = self.garage_box.current()
            garage_id = self.garage_entries[index]['id'] if index >= 0 else ''
            plan = build_plan(OPERATIONS[self.operation.get()], int(self.slot.get()),
                              self.selected_ship(), self.profile.get(), garage_id)
        except Exception as exc:
            messagebox.showerror('Plan oluşturulamadı', str(exc))
            return
        if not self.closed_confirmation():
            return
        self.review = None
        self.apply_button.configure(state='disabled')
        self.output(self.report, {'istenen_plan': plan, 'durum': 'Hazırlanıyor; canlı kayda yazılmadı.'})

        def prepared(result):
            path, manifest, fingerprint = result
            self.review = (path, fingerprint)
            self.output(self.report, {'transaction': str(path), 'plan': manifest['plan'],
                        'state': manifest['state'], 'report': manifest['report'],
                        'not': 'Auto/manual bağımsız işlendi. Codec yeniden okuma eşitliği doğrulandı.'})
            self.apply_button.configure(state='normal')
        self.run(lambda: self.backend.prepare(plan), prepared)

    def apply(self):
        if self.busy or not self.review:
            return
        if not messagebox.askyesno('İncelenen değişiklikleri uygula',
            'Rapordaki eylemleri ve değişen yolları incelediniz mi?\n'
            'Oyun tamamen kapalı olmalı. Bu işlem canlı kayıtlara yazacak.\n'
            'Kaynak değişmişse işlem reddedilir. Devam edilsin mi?'):
            return
        path, fingerprint = self.review
        self.review = None
        self.apply_button.configure(state='disabled')
        self.run(lambda: self.backend.apply(path, fingerprint),
                 lambda output: self.output(self.report, output + '\nYedek: ' + str(path / 'before')))

    def refresh_garage(self):
        self.refresh_all()

    def load_garage(self, entries):
        index = self.garage_box.current()
        previous = self.garage_entries[index]['id'] if index >= 0 else None
        self.garage_entries = entries
        values = [f"{e['name'] or '(prosedürel)'} | {e['type']} | {e['seed']} | {e['id']}" for e in entries]
        self.garage_box.configure(values=values)
        chosen = next((i for i, e in enumerate(entries) if e['id'] == previous), None)
        if chosen is not None:
            self.garage_box.current(chosen)
        else:
            self.garage_choice.set('')

    def snapshot(self):
        if self.busy or not self.closed_confirmation():
            return
        slot = int(self.slot.get())
        self.run(lambda: self.backend.snapshot(slot), lambda out: self.output(self.report, out))

    def make_history(self, parent):
        ttk.Label(parent, text='Tam kayıt geri alma, seçilen işlemin zamanına döner. Sonraki ilerleme bu eski kayıtta bulunmaz.',
                  wraplength=1000).pack(anchor='w')
        ttk.Label(parent, text='Güncel durum geri almadan önce ayrıca yedeklenir. Yalnız uygulanmış işlemler geri alınabilir.').pack(anchor='w', pady=6)
        ttk.Label(parent, text='İşlem geçmişi ortak taramadan otomatik güncellenir.').pack(anchor='w')
        self.history_list = tk.Listbox(parent, height=13, exportselection=False, font=('Consolas', 11))
        self.history_list.pack(fill='both', expand=True, pady=10)
        ttk.Button(parent, text='Seçili işlemin raporunu göster', command=self.show_history).pack(anchor='w')
        self.history_report = ScrolledText(parent, height=10, state='disabled')
        self.history_report.pack(fill='both', expand=True, pady=8)
        ttk.Button(parent, text='Seçili işlemi tam geri al', command=self.restore).pack(anchor='e')

    def refresh_history(self):
        self.refresh_all()

    def load_history(self, entries):
        selected = self.history_list.curselection()
        previous = self.transactions[selected[0]][0] if selected else None
        self.transactions = entries
        self.history_list.delete(0, 'end')
        for i, (path, state) in enumerate(entries):
            self.history_list.insert('end', f'{path.name}   [{state}]')
            if path == previous:
                self.history_list.selection_set(i)

    def selected_transaction(self):
        selected = self.history_list.curselection()
        if not selected:
            raise ValueError('Geçmişten bir işlem seçin.')
        return self.transactions[selected[0]]

    def show_history(self):
        from .backend import read_json
        try:
            path, _ = self.selected_transaction()
            self.output(self.history_report, read_json(path / 'manifest.json'))
        except Exception as exc:
            messagebox.showerror('Rapor açılamadı', str(exc))

    def restore(self):
        if self.busy:
            return
        try:
            path, state = self.selected_transaction()
            if state != 'applied':
                raise ValueError('Yalnız applied durumundaki işlem geri alınabilir.')
        except Exception as exc:
            messagebox.showerror('Geri alma', str(exc))
            return
        if not self.closed_confirmation():
            return
        if not messagebox.askyesno('Tam kayıt geri alma',
            f'{path.name} öncesindeki kayda dönülecek.\n'
            'Bu işlemden sonraki ilerleme eski kayıtta yoktur.\n'
            'Şimdiki kayıt ayrıca yedeklenecek. Geri alınsın mı?'):
            return
        self.run(lambda: self.backend.restore(path), lambda out: self.output(self.history_report, out))

    def make_roadmap(self, parent):
        text = ScrolledText(parent, wrap='word', font=('Segoe UI', 11))
        text.pack(fill='both', expand=True)
        for module in MODULES:
            text.insert('end', f'{module.title}  —  {module.status}\n{module.features}\n\n')
        text.insert('end', 'AKIŞ\nOyunu kaydet ve kapat → kayıtları yenile → yeni plan hazırla → raporu incele → uygula.\n\n'
                    'Canlı para ve yapılandırma kontrolleri ilk sekmededir. Eşya / görev / overlay kontrolleri uygulanmadı. '
                    'Oyunda yapılabilen her eylemin kayıt dosyasından kontrolü garanti edilmez.\n'
                    'Kalkış otomatik şarjı normal oyun teknolojisidir; anlık sınırsız yakıt değildir.\n'
                    'Harici garaj arşivdir; aktif gemi sınırını artırmaz.')
        text.configure(state='disabled')


def main(connect=False, fleet=False, weapons=False, catalog=False):
    root = tk.Tk()
    try:
        app = MenuApp(root)
        if fleet:
            app.book.select(1)
        if weapons:
            app.book.select(3)
        if catalog:
            app.book.select(6)
        app.start_shared_scan()
    except Exception as exc:
        messagebox.showerror('Menu başlatılamadı', str(exc))
        root.destroy()
        raise
    root.mainloop()
