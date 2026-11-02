"""The controller and CLI must use the same, bundled transaction engine."""
from pathlib import Path
import unittest
from nmsmenu.backend import FLEET, ROOT, FleetBackend
from nmsmenu.live_fleet import engine


class IntegratedEngine(unittest.TestCase):
    def test_engine_and_controllers_share_repository_root(self):
        self.assertEqual(FLEET, ROOT)
        self.assertEqual(engine().ROOT, ROOT)
        self.assertEqual(FleetBackend().fleet, ROOT)

    def test_catalog_dependencies_resolve_inside_repository(self):
        native = engine()
        for profile in native.load(ROOT / 'catalog.json').values():
            if 'customisation_file' in profile:
                path = (ROOT / profile['customisation_file']).resolve()
                self.assertTrue(path.is_relative_to(ROOT / 'ship-references'))
                self.assertTrue(path.is_file())
        self.assertTrue((ROOT / 'loadouts.json').is_file())
        self.assertTrue((ROOT / 'preferences.json').is_file())

    def test_codec_and_live_save_locations_are_preserved(self):
        native = engine()
        self.assertEqual(native.TOOL, ROOT.parent / 'SolarShipFix' / 'libNOM.io.cli.exe')
        self.assertEqual(native.LIVE.parts[-3:], ('HelloGames', 'NMS', 'DefaultUser'))
        self.assertEqual(native.GARAGE, ROOT / 'garage')


if __name__ == '__main__':
    unittest.main()
