import copy
import unittest
from unittest.mock import patch
from nmsmenu.qt_ui import Q
from nmsmenu.overlay import display_state, GlobalHotkey, hotkey_spec


class OverlayState(unittest.TestCase):
    def test_disconnected_state_hides_stale_numbers_and_ship_count(self):
        state = {'loaded': False, 'currencies': {'Units': 9999}}
        result = display_state(state, [{'slot': 1}], lambda text: text)
        self.assertEqual(result['values']['Units'], '—')
        self.assertEqual(result['ships'], '—')

    def test_snapshot_is_displayed_without_mutating_game_state(self):
        state = {'loaded': True, 'currencies': {'Units': 12345, 'Nanit': 200, 'Quicksilver': 5}}
        before = copy.deepcopy(state)
        result = display_state(state, [{'slot': 1}], lambda text: 'translated:' + text)
        self.assertEqual(result['values']['Units'], '12,345')
        self.assertEqual(result['ships'], '1')
        self.assertTrue(result['status'].startswith('translated:'))
        self.assertEqual(state, before)

    def test_unknown_currencies_are_not_fabricated(self):
        result = display_state({'loaded': True, 'currencies': {}}, [], str)
        self.assertEqual(result['values']['Nanit'], '—')

    def test_hotkey_unregisters_its_own_registration(self):
        import ctypes
        app = Q.QApplication.instance() or Q.QApplication([])
        with patch('ctypes.WinDLL') as dll:
            user32 = dll.return_value
            user32.RegisterHotKey.return_value = 1
            hotkey = GlobalHotkey(lambda: None)
            self.assertTrue(hotkey.registered)
            hotkey.close()
            user32.UnregisterHotKey.assert_called_once_with(None, hotkey.IDENTIFIER)
            self.assertFalse(hotkey.registered)

    def test_native_hotkey_message_dispatches_only_registered_identifier(self):
        import ctypes
        from ctypes import wintypes
        app = Q.QApplication.instance() or Q.QApplication([])
        calls = []
        with patch('ctypes.WinDLL') as dll:
            user32 = dll.return_value
            user32.RegisterHotKey.return_value = 1
            hotkey = GlobalHotkey(lambda: calls.append('toggle'))
            message = wintypes.MSG()
            message.message, message.wParam = 0x0312, hotkey.IDENTIFIER
            self.assertEqual(hotkey.nativeEventFilter(b'windows_generic_MSG', ctypes.addressof(message)), (True, 0))
            self.assertEqual(calls, ['toggle'])
            message.wParam += 1
            self.assertEqual(hotkey.nativeEventFilter(b'windows_generic_MSG', ctypes.addressof(message)), (False, 0))
            hotkey.close()

    def test_shortcut_mapping_and_invalid_shortcuts(self):
        self.assertEqual(hotkey_spec('Ctrl+Alt+F9'), ('Ctrl+Alt+F9', 0x4003, 0x78))
        self.assertEqual(hotkey_spec('Ctrl+Shift+K'), ('Ctrl+Shift+K', 0x4006, ord('K')))
        for invalid in ('', 'F9', 'Ctrl+F9, Ctrl+F8', 'Alt+Left', 'Meta+K'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                hotkey_spec(invalid)

    def test_registration_failure_reports_windows_error(self):
        app = Q.QApplication.instance() or Q.QApplication([])
        with patch('ctypes.WinDLL') as dll, patch('ctypes.get_last_error', return_value=1409):
            dll.return_value.RegisterHotKey.return_value = 0
            with self.assertLogs('nmsmenu.overlay', level='ERROR') as log:
                hotkey = GlobalHotkey(lambda: None)
            self.assertFalse(hotkey.registered)
            self.assertEqual(hotkey.error_code, 1409)
            self.assertIn('1409', log.output[0])
            hotkey.close()
            dll.return_value.UnregisterHotKey.assert_not_called()
