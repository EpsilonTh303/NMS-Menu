import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.install_codec import ROOT, install


class CodecInstaller(unittest.TestCase):
    def setUp(self):
        (ROOT / 'runtime').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'runtime')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.payload = b'official codec test fixture'
        self.target = self.directory / 'libNOM.io.cli.exe'
        manifest = {'filename': self.target.name, 'size': len(self.payload),
                    'sha256': hashlib.sha256(self.payload).hexdigest(),
                    'url': 'https://github.com/zencq/libNOM.io/releases/download/0.14.2/test.exe'}
        (self.directory / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')

    def test_verified_existing_binary_skips_network(self):
        self.target.write_bytes(self.payload)
        with patch('tools.install_codec.urlopen') as download:
            self.assertEqual(install(self.directory), self.target)
            download.assert_not_called()

    def test_download_is_verified_before_install(self):
        with patch('tools.install_codec.urlopen', return_value=io.BytesIO(self.payload)):
            install(self.directory)
        self.assertEqual(self.target.read_bytes(), self.payload)

    def test_bad_download_preserves_existing_file_and_cleans_partial(self):
        self.target.write_bytes(b'keep existing codec')
        bad = b'x' * len(self.payload)
        with patch('tools.install_codec.urlopen', return_value=io.BytesIO(bad)):
            with self.assertRaisesRegex(ValueError, 'checksum'):
                install(self.directory)
        self.assertEqual(self.target.read_bytes(), b'keep existing codec')
        self.assertEqual(list(self.directory.glob('*.part')), [])

    def test_check_never_downloads(self):
        with patch('tools.install_codec.urlopen') as download:
            with self.assertRaisesRegex(ValueError, 'missing'):
                install(self.directory, check=True)
            download.assert_not_called()
