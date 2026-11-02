"""Exercise adapter bindings without reading or writing a game process/save."""
import unittest
import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from nmsmenu.qt_ui import Q, Window
from nmsmenu.i18n import Translator, ROOT


class QtBindings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Q.QApplication.instance() or Q.QApplication([])
        (ROOT / 'runtime').mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=ROOT / 'runtime')
        cls.window = Window(start_scan=False, translator=Translator(settings=Path(cls.temp.name) / 'settings.json'))
        cls.window.timer.stop()

    @classmethod
    def tearDownClass(cls):
        cls.window.controller.close()
        cls.temp.cleanup()

    def test_button_invokes_original_command(self):
        calls = []
        source = ttk.Button(self.window.legacy, command=lambda: calls.append('original'))
        self.window.build(source).click()
        self.assertEqual(calls, ['original'])

    def test_capital_panel_queues_only_and_missing_freighter_stays_disabled(self):
        from nmsmenu import capital
        from test_capital import source
        panel = self.window.controller.capital_panel
        data = source()
        p = data['BaseContext']['PlayerStateData']
        record = {'file': 'save.hg', 'capital': capital.snapshot(p)}
        panel.load_saves([record])
        panel.tree.selection_set('0')
        self.window.legacy.update()
        panel.frigate('frigate_repair')
        cart = self.window.controller.catalog_panel.cart
        self.assertEqual(cart.plan()['actions'][-1]['op'], 'frigate_repair')
        self.assertEqual(p['FleetFrigates'][0]['DamageTaken'], 2)
        cart.clear()
        self.window.controller.catalog_panel.changed()
        p['CurrentFreighter']['Filename'] = ''
        record['capital'] = capital.snapshot(p)
        panel.load_saves([record])
        self.assertTrue(all('disabled' in button.state() for button in panel.freighter_buttons))
        self.assertEqual(len(panel.tree.get_children()), 2)

    def test_entry_updates_original_variable(self):
        value = tk.StringVar(self.window.legacy, '1')
        source = ttk.Entry(self.window.legacy, textvariable=value)
        target = self.window.build(source)
        target.textEdited.emit('25')
        self.assertEqual(value.get(), '25')

    def test_combo_dispatches_selection_event(self):
        source = ttk.Combobox(self.window.legacy, values=['one', 'two'])
        events = []
        source.bind('<<ComboboxSelected>>', lambda _: events.append(source.get()))
        target = self.window.build(source)
        self.window.sync(source, target)
        target.activated.emit(1)
        self.assertEqual(source.get(), 'two')
        self.assertEqual(events, ['two'])

    def test_review_button_disabled_state_is_preserved(self):
        source = self.window.controller.catalog_panel.apply_button
        target = next(q for t, q in self.window.bindings if t is source)
        self.window.sync(source, target)
        self.assertFalse(target.isEnabled())

    def test_overlay_toggle_closes_and_preserves_menu_review(self):
        from unittest.mock import patch
        window = self.window
        source = window.controller.catalog_panel.apply_button
        with patch('nmsmenu.overlay.GlobalHotkey') as hotkey:
            hotkey.return_value.registered = True
            window.overlay_toggle.setChecked(True)
            self.assertIsNotNone(window.overlay_panel)
            self.assertTrue(window.overlay_panel.windowFlags() & __import__('PySide6.QtCore', fromlist=['Qt']).Qt.WindowType.WindowStaysOnTopHint)
            self.assertIn('disabled', source.state())
            window.overlay_panel.close()
            self.assertFalse(window.overlay_toggle.isChecked())
            self.assertFalse(window.overlay_panel.timer.isActive())
            hotkey.return_value.close.assert_called_once()

    def test_spinbox_updates_original_variable_with_limits(self):
        value = tk.StringVar(self.window.legacy, '1')
        source = ttk.Spinbox(self.window.legacy, from_=1, to=16, textvariable=value)
        target = self.window.build(source)
        target.setValue(25)
        self.assertEqual(value.get(), '16')
        self.assertEqual(target.maximum(), 16)

    def test_overlay_controls_use_guarded_backend_and_block_unloaded_or_busy(self):
        from unittest.mock import patch
        from nmsmenu.overlay import GameOverlay
        window = self.window
        panel = window.controller.live_panel
        old = panel.state
        overlay = GameOverlay(window)
        try:
            with patch.object(window.controller, 'run') as run, patch.object(panel.backend, 'set_currency') as currency:
                panel.state = {'loaded': False}
                overlay.dispatch('currency', 'Units', 123)
                run.assert_not_called()
                panel.state = {'loaded': True, 'settings': {'run': 8}}
                window.controller.busy = True
                overlay.dispatch('currency', 'Units', 123)
                run.assert_not_called()
                window.controller.busy = False
                overlay.dispatch('currency', 'Units', 123)
                work, callback = run.call_args.args
                work()
                currency.assert_called_once_with('Units', 123)
                self.assertEqual(callback, panel.render)
                overlay.setting.setCurrentIndex(overlay.setting.findData('run'))
                self.assertEqual(overlay.setting_amount.value(), 8)
                self.assertEqual(overlay.setting_amount.maximum(), 40)
        finally:
            panel.state = old
            window.controller.busy = False
            overlay.timer.stop()
            overlay.deleteLater()

    def test_toggle_uses_original_checkbox_command(self):
        calls = []
        value = tk.BooleanVar(self.window.legacy, True)
        source = ttk.Checkbutton(self.window.legacy, text='Otomatik bağlantı ve ortak yenileme',
                                 variable=value, command=lambda: calls.append(value.get()))
        target = self.window.build(source)
        self.window.sync(source, target)
        target.click()
        self.assertFalse(value.get())
        self.assertEqual(calls, [False])

    def test_language_switch_keeps_settings_open_and_controller_values_intact(self):
        window = self.window
        source = window.controller.catalog_panel.kind
        target = next(q for t, q in window.bindings if t is source)
        original = source.get()
        window.main_book.setCurrentIndex(window.settings_index)
        window.language_choice.setCurrentIndex(window.language_choice.findData('en'))
        window.tick()
        self.assertEqual(window.main_book.currentIndex(), window.settings_index)
        self.assertEqual(window.main_book.tabText(window.settings_index), 'Settings')
        self.assertEqual(source.get(), original)
        self.assertNotEqual(target.currentText(), source.get())
        self.assertEqual(window.translator.language, 'en')
        # Switching the translated choice still selects the original Turkish key.
        index = 1
        target.activated.emit(index)
        self.assertEqual(source.current(), index)
        window.language_choice.setCurrentIndex(window.language_choice.findData('tr'))


if __name__ == '__main__':
    unittest.main()
