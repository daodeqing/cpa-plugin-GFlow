import importlib.util
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".github/scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RepositoryTextTest(unittest.TestCase):
    def test_tracked_text_is_english(self):
        rows = list(load("check_english").findings())
        self.assertEqual(rows, [], "run python .github/scripts/check_english.py")

    def test_extension_archive_matches_source(self):
        pack = load("pack_extension")
        with zipfile.ZipFile(pack.ARCHIVE) as archive:
            packed = {name: archive.read(name) for name in archive.namelist()}
        self.assertEqual(packed, pack.extension_files(), "run python .github/scripts/pack_extension.py")


if __name__ == "__main__":
    unittest.main()
