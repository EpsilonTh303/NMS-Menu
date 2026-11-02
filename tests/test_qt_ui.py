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

    def test_spinbox_updates_original_variable_with_limits(self):
        value = tk.StringVar(self.window.legacy, '1')
        source = ttk.Spinbox(self.window.legacy, from_=1, to=16, textvariable=value)
        target = self.window.build(source)
        target.setValue(25)
        self.assertEqual(value.get(), '16')
        self.assertEqual(target.maximum(), 16)

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
