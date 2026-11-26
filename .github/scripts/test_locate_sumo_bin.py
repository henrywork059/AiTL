"""Synthetic wheel metadata fixture; no actual engine execution."""
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from locate_sumo_bin import locate_native_bin


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


if __name__ == '__main__':
    unittest.main()
