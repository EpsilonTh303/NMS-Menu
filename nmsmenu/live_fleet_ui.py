"""Review-first UI for live fleet inventory changes."""
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import json

from .live_fleet import LiveFleet


class LiveFleetPanel:
    def __init__(self, parent, host, live):
        self.host, self.live = host, live
        self.backend = LiveFleet(live)
        self.ships = []
        self.review = None
        self.last_applied = None
        ttk.Label(parent, text='Oyun açıkken mevcut gemileri onar / şarj et veya tüm gemilerin yuvalarını genişlet.',
                  font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(parent, text='Önce Canlı kontroller sekmesinden bağlanın. Oyunda Esc duraklatma menüsünü açın; hazırlama / uygulama / geri alma boyunca açık tutun.',
                  wraplength=1000).pack(anchor='w', pady=(5, 10))
        ttk.Button(parent, text='Oyuna bağlan / canlı filoyu yenile', command=self.refresh).pack(anchor='w')
        self.tree = ttk.Treeview(parent, columns=('slot', 'type', 'seed', 'cargo', 'tech', 'active'),
                                 show='headings', height=12, selectmode='browse')
        for key, title, width in [('slot', 'Yuva', 60), ('type', 'Tür', 140), ('seed', 'Tohum / kesin kimlik', 260),
                                  ('cargo', 'Kargo', 100), ('tech', 'Teknoloji', 100), ('active', 'Aktif', 70)]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width)
        self.tree.pack(fill='x', pady=10)
        bar = ttk.Frame(parent)
        bar.pack(fill='x')
        ttk.Button(bar, text='Seçili gemiyi onar / şarj et: plan hazırla',
                   command=lambda: self.prepare('repair_ship')).pack(side='left')
        ttk.Button(bar, text='Tüm gemilere maksimum yuva: plan hazırla',
                   command=lambda: self.prepare('max_slots')).pack(side='left', padx=8)
        self.report = ScrolledText(parent, height=13, state='disabled', font=('Consolas', 10))
        self.report.pack(fill='both', expand=True, pady=10)
        controls = ttk.Frame(parent)
        controls.pack(fill='x')
        self.apply_button = ttk.Button(controls, text='İncelediğim canlı filo planını uygula', state='disabled', command=self.apply)
        self.apply_button.pack(side='left')
        self.undo_button = ttk.Button(controls, text='Son canlı filo işlemini geri al', state='disabled', command=self.undo)
        self.undo_button.pack(side='left', padx=8)
        ttk.Label(parent, text='Aktif sınır 12 gemi. Canlı ekleme, silme, model / tohum değiştirme ve teknoloji ekleme henüz desteklenmiyor.',
                  wraplength=1000).pack(anchor='w', pady=(10, 0))

    def output(self, value):
        self.report.configure(state='normal')
        self.report.delete('1.0', 'end')
        self.report.insert('1.0', value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))
        self.report.configure(state='disabled')

    def refresh(self):
        def work():
            state = self.live.snapshot() if self.live.memory else self.live.connect()
            return self.backend.inspect(), state

        def loaded(result):
            ships, state = result
            self.host.live_panel.render(state)
            self.ships = ships
            self.tree.delete(*self.tree.get_children())
            for i, ship in enumerate(ships):
                self.tree.insert('', 'end', iid=str(i), values=(ship['slot'], ship['type'], ship['seed'],
                    ship['cargo'], ship['tech'], 'Evet' if ship['active'] else ''))
        self.host.run(work, loaded)

    def prepare(self, operation):
        if self.host.busy:
            return
        selected = self.tree.selection()
        ship = self.ships[int(selected[0])] if selected else None
        if operation == 'repair_ship' and ship is None:
            messagebox.showerror('Gemi seçimi', 'Canlı filoyu yenileyip tür / tohum / yuva ile gemi seçin.')
            return
        self.review = None
        self.apply_button.configure(state='disabled')
        self.output('Canlı envanter yakalanıyor; taze kayıt kopyasında FleetManager kuralları ve codec eşitliği doğrulanıyor.\n'
                    'Oyunda envanter veya gemi değişikliği yapmayın. Bu aşama belleğe / canlı kayda yazmaz.')

        def prepared(result):
            path, manifest, fingerprint = result
            self.review = (path, fingerprint)
            self.output({'transaction': str(path), 'plan': manifest['plan'], 'report': manifest['report'],
                         'codec_roundtrip': manifest['codec_roundtrip'], 'memory_fields': len(manifest['patches']),
                         'not': 'Raporu inceleyin. Kargo taşınmaz; teknoloji kimliği / konumu değiştirilmez.'})
            self.apply_button.configure(state='normal' if manifest['patches'] else 'disabled')
        self.host.run(lambda: self.backend.prepare(operation, ship), prepared)

    def apply(self):
        if self.host.busy or not self.review:
            return
        if not messagebox.askyesno('Canlı filo değişikliği',
            'Planı ve değişen yolları incelediniz mi?\n'
            'Gemi / envanter değişmediyse bu değişiklikler açık oyuna uygulanacak.\n'
            'Oyun kaydederse kalıcı olabilir. Uygulansın mı?'):
            return
        path, fingerprint = self.review
        self.review = None
        self.apply_button.configure(state='disabled')

        def done(output):
            self.last_applied = path
            self.undo_button.configure(state='normal')
            self.output(output)
        self.host.run(lambda: self.backend.apply(path, fingerprint), done)

    def undo(self):
        if self.host.busy or not self.last_applied:
            return
        path = self.last_applied

        def done(output):
            self.last_applied = None
            self.undo_button.configure(state='disabled')
            self.output(output)
        self.host.run(lambda: self.backend.undo(path), done)
