import json
from pathlib import Path
import tempfile
import unittest
from nmsmenu.i18n import Translator, LOCALES, ROOT, audit, atomic_json


class Languages(unittest.TestCase):
    def setUp(self):
        (ROOT / 'runtime').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'runtime')
        self.root = Path(self.temp.name)
        self.locales = self.root / 'locales'
        self.locales.mkdir()
        self.settings = self.root / 'settings.json'
        self.source = {'Ayarlar': 'Ayarlar', 'Dil': 'Dil', '{v0} sonuç': '{v0} sonuç', 'Eksik': 'Eksik'}
        atomic_json(self.locales / 'tr.json', self.source)
        atomic_json(self.locales / 'en.json', {'Ayarlar': 'Settings', 'Dil': 'Language', '{v0} sonuç': '{v0} results'})
        self.translator = Translator(self.locales, self.settings)

    def tearDown(self):
        self.temp.cleanup()

    def test_switch_persist_and_missing_fallback(self):
        self.translator.select('en')
        self.assertEqual(self.translator.text('Ayarlar'), 'Settings')
        self.assertEqual(self.translator.text('Eksik'), 'Eksik')
        restored = Translator(self.locales, self.settings)
        self.assertEqual(restored.language, 'en')
        self.assertEqual(json.loads(self.settings.read_text())['language'], 'en')

    def test_live_value_and_procedural_name_preserved(self):
        self.translator.select('en')
        self.assertEqual(self.translator.text('1272 sonuç'), '1272 results')
        self.assertEqual(self.translator.text('My Starship — 0x1234'), 'My Starship — 0x1234')

    def test_new_language_discovered_and_reloaded(self):
        atomic_json(self.locales / 'fr.json', {'_meta': {'name': 'Français'}, 'Ayarlar': 'Réglages'})
        self.assertEqual(self.translator.available()['fr'], 'Français')
        self.translator.select('fr')
        self.assertEqual(self.translator.text('Ayarlar'), 'Réglages')
        atomic_json(self.locales / 'fr.json', {'Ayarlar': 'Paramètres'})
        self.translator.reload()
        self.assertEqual(self.translator.text('Ayarlar'), 'Paramètres')

    def test_invalid_placeholder_falls_back_and_is_reported(self):
        atomic_json(self.locales / 'en.json', {'{v0} sonuç': '{v1} results'})
        self.translator.select('en')
        self.assertEqual(self.translator.text('27 sonuç'), '27 sonuç')
        self.assertTrue(any('placeholders' in item for item in audit(self.locales)))

    def test_corrupt_settings_and_catalog_are_tolerated(self):
        self.settings.write_text('broken')
        (self.locales / 'bad.json').write_text('not json')
        translator = Translator(self.locales, self.settings)
        self.assertEqual(translator.language, 'tr')
        self.assertNotIn('bad', translator.available())
        translator.select('../../outside', persist=False)
        self.assertEqual(translator.language, 'tr')

    def test_unrelated_preferences_preserved(self):
        atomic_json(self.settings, {'other': {'x': 2}})
        self.translator.select('en')
        self.assertEqual(json.loads(self.settings.read_text())['other'], {'x': 2})

    def test_language_catalogs_complete(self):
        self.assertEqual(audit(LOCALES), [])


if __name__ == '__main__':
    unittest.main()
