import copy
import unittest
from unittest.mock import patch
from nmsmenu.qt_ui import Q
from nmsmenu.overlay import display_state, GlobalHotkey


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
        with patch('ctypes.windll.user32') as user32:
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
        with patch('ctypes.windll.user32') as user32:
            user32.RegisterHotKey.return_value = 1
            hotkey = GlobalHotkey(lambda: calls.append('toggle'))
            message = wintypes.MSG()
            message.message, message.wParam = 0x0312, hotkey.IDENTIFIER
            self.assertEqual(hotkey.nativeEventFilter(b'windows_generic_MSG', ctypes.addressof(message)), (True, 0))
            self.assertEqual(calls, ['toggle'])
            message.wParam += 1
            self.assertEqual(hotkey.nativeEventFilter(b'windows_generic_MSG', ctypes.addressof(message)), (False, 0))
            hotkey.close()
