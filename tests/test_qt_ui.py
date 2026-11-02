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

    def test_hidden_tree_selection_dispatches_once_through_adapter(self):
        source = ttk.Treeview(self.window.legacy)
        source.insert('', 'end', iid='one')
        calls = []
        source.bind('<<TreeviewSelect>>', lambda _: calls.append(source.selection()))
        self.window.build(source)
        source.selection_set('one')
        self.window.controller_events.refresh_selections()
        self.window.controller_events.refresh_selections()
        self.assertEqual(calls, [('one',)])
        self.assertEqual(source.bind('<<TreeviewSelect>>'), '')

    def test_controller_timer_cancel_survives_modal_dialog(self):
        from nmsmenu.qt_ui import QtCore
        calls = []
        identifier = self.window.legacy.after(0, lambda: calls.append('cancelled'))
        self.window.legacy.after_cancel(identifier)
        self.window.legacy.after(0, lambda: calls.append('ran'))
        dialog = Q.QDialog(self.window)
        QtCore.QTimer.singleShot(25, dialog.accept)
        dialog.exec()
        self.assertEqual(calls, ['ran'])

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
        with patch.object(window.overlay_hotkey, 'close') as close:
            window.overlay_toggle.setChecked(True)
            self.assertIsNotNone(window.overlay_panel)
            self.assertTrue(window.overlay_panel.windowFlags() & __import__('PySide6.QtCore', fromlist=['Qt']).Qt.WindowType.WindowStaysOnTopHint)
            self.assertIn('disabled', source.state())
            window.overlay_panel.close()
            self.assertFalse(window.overlay_toggle.isChecked())
            self.assertFalse(window.overlay_panel.timer.isActive())
            # Closing the panel keeps the global shortcut ready to reopen it.
            close.assert_not_called()
            window.shortcut_overlay()
            self.assertTrue(window.overlay_toggle.isChecked())
            self.assertTrue(window.overlay_panel.isVisible())
            window.shortcut_overlay()
            self.assertFalse(window.overlay_panel.isVisible())

    def test_overlay_escape_keeps_shortcut_reopenable(self):
        window = self.window
        window.overlay_toggle.setChecked(True)
        self.assertFalse(window.overlay_panel.testAttribute(__import__('PySide6.QtCore', fromlist=['Qt']).Qt.WidgetAttribute.WA_ShowWithoutActivating))
        window.overlay_panel.reject()
        self.assertFalse(window.overlay_toggle.isChecked())
        window.shortcut_overlay()
        self.assertTrue(window.overlay_panel.isVisible())
        window.shortcut_overlay()

    def test_hotkey_change_persists_and_conflict_keeps_working_key(self):
        import json
        from unittest.mock import patch, Mock
        from nmsmenu.overlay import GlobalHotkey
        from nmsmenu.qt_ui import QtGui
        window = self.window
        old = window.overlay_hotkey
        original_sequence = window.overlay_sequence
        candidate = Mock(registered=True, sequence='Ctrl+Shift+F10', identifier=GlobalHotkey.IDENTIFIER + 1)
        window.translator.select('tr')
        try:
            with patch('nmsmenu.overlay.GlobalHotkey') as factory:
                factory.IDENTIFIER = GlobalHotkey.IDENTIFIER
                factory.return_value = candidate
                window.hotkey_edit.setKeySequence(QtGui.QKeySequence(candidate.sequence))
                window.save_overlay_hotkey()
                self.assertIs(window.overlay_hotkey, candidate)
                saved = json.loads(window.translator.settings.read_text(encoding='utf-8'))
                self.assertEqual(saved['overlay_hotkey'], candidate.sequence)
                self.assertEqual(saved['language'], window.translator.language)
                factory.return_value = Mock(registered=False, sequence='Ctrl+Alt+K', error_code=1409)
                window.hotkey_edit.setKeySequence(QtGui.QKeySequence('Ctrl+Alt+K'))
                with self.assertLogs('nmsmenu.qt_ui', level='ERROR'):
                    window.save_overlay_hotkey()
                self.assertIs(window.overlay_hotkey, candidate)
                self.assertIn('1409', window.hotkey_status.text())
                candidate.close.assert_not_called()
                self.assertEqual(json.loads(window.translator.settings.read_text())['overlay_hotkey'], candidate.sequence)
        finally:
            candidate.close()
            window.overlay_hotkey = old
            window.overlay_sequence = original_sequence
            window.update_hotkey_status()

    def test_spinbox_updates_original_variable_with_limits(self):
        value = tk.StringVar(self.window.legacy, '1')
        source = ttk.Spinbox(self.window.legacy, from_=1, to=16, textvariable=value)
        target = self.window.build(source)
        target.setValue(25)
        self.assertEqual(value.get(), '16')
        self.assertEqual(target.maximum(), 16)

    def test_catalog_typed_amount_reaches_plan_and_edit_invalidates_review(self):
        from PySide6 import QtCore, QtTest
        from unittest.mock import patch
        window = self.window
        panel, view = window.controller.catalog_panel, window.catalog_workspace
        old_saves, old_kind = panel.saves, panel.kind.get()
        try:
            panel.load_snapshot([{'file': 'save.hg', 'mtime_ns': 0, 'fleet': [], 'multitools': []}], [])
            panel.kind.set('Eşya / malzeme')
            panel.change_kind()
            key = panel.products.get_children()[0]
            panel.products.selection_set(key)
            window.controller.book.select(6)
            panel.book.select(0)
            window.show()
            window.tick()
            self.assertTrue(view.quantity.isEnabled())
            view.quantity.lineEdit().selectAll()
            QtTest.QTest.keyClicks(view.quantity.lineEdit(), '12345')
            with patch.object(panel.service, 'remember'):
                QtTest.QTest.mouseClick(view.add, QtCore.Qt.MouseButton.LeftButton)
            self.assertEqual(panel.cart.plan()['actions'][-1]['amount'], 12345)
            self.assertIn('12,345', view.pending.item(view.pending.count() - 1).text())
            self.assertNotIn('{', view.pending.item(view.pending.count() - 1).text())
            panel.review = ('prepared-path', 'hash', panel.cart.revision)
            panel.apply_button.configure(state='normal')
            view.pending.setCurrentRow(view.pending.count() - 1)
            window.tick()
            view.pending_quantity.lineEdit().selectAll()
            QtTest.QTest.keyClicks(view.pending_quantity.lineEdit(), '6789')
            view.change_pending_amount()
            self.assertEqual(panel.cart.plan()['actions'][-1]['amount'], 6789)
            self.assertIsNone(panel.review)
            self.assertIn('disabled', panel.apply_button.state())
            self.assertTrue(view.prepare.isVisible())
            self.assertTrue(view.apply.isVisible())
            self.assertFalse(view.apply.isEnabled())
            panel.products.selection_set('')
            window.tick()
            self.assertFalse(view.quantity.isEnabled())
        finally:
            panel.cart.clear()
            panel.changed()
            panel.load_snapshot(old_saves, [])
            panel.kind.set(old_kind)
            panel.change_kind()

    def test_sidebar_navigation_preserves_controller_tabs(self):
        window = self.window
        window.navigation.setCurrentRow(7)
        self.assertEqual(window.controller.book.index(window.controller.book.select()), 7)
        window.controller.book.select(6)
        window.tick()
        self.assertEqual(window.navigation.currentRow(), 6)
        self.assertTrue(window.main_book.tabBar().isHidden())

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
