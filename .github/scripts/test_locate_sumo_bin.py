"""Synthetic wheel metadata and version fixtures; no actual engine execution."""
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from locate_sumo_bin import locate_native_bin, verify_version_banner


class LocateNativeBinTests(unittest.TestCase):
    def test_console_launcher_and_native_binary(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = [PurePosixPath('Scripts/sumo.exe'), PurePosixPath('sumo/bin/sumo.exe'), PurePosixPath('sumo/bin/netconvert.exe')]
            for file in files:
                path = root / file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            dist = SimpleNamespace(files=files, locate_file=lambda file: root / file)
            self.assertEqual(locate_native_bin(dist), (root / 'sumo/bin').resolve())
            (root / 'sumo/bin/netconvert.exe').unlink()
            with self.assertRaises(RuntimeError):
                locate_native_bin(dist)

    def test_launcher_only_is_rejected(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'sumo.exe').touch()
            (root / 'netconvert.exe').touch()
            dist = SimpleNamespace(files=[PurePosixPath('sumo.exe')], locate_file=lambda file: root / file)
            with self.assertRaises(RuntimeError):
                locate_native_bin(dist)

    def test_exact_native_version_banners(self):
        verify_version_banner('Eclipse SUMO sumo 1.28.0\r\n Build features: Windows', 'sumo')
        verify_version_banner('Eclipse SUMO netconvert 1.28.0\n', 'netconvert')
        verify_version_banner('Eclipse SUMO sumo Version 1.28.0\n', 'sumo')

    def test_wrong_versions_and_tools_are_rejected(self):
        for banner in ('Eclipse SUMO sumo 1.28.1', 'Eclipse SUMO sumo 1.28.01',
                       'Eclipse SUMO sumo 1.28.0-dev', 'Eclipse SUMO netconvert 1.28.0',
                       'Eclipse SUMO sumo 1.27.0\nEclipse SUMO sumo 1.28.0', ''):
            with self.subTest(banner=banner), self.assertRaises(RuntimeError):
                verify_version_banner(banner, 'sumo')


if __name__ == '__main__':
    unittest.main()
