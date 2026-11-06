import ast
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]


class WorkerBundleTest(unittest.TestCase):
    def test_personal_browser_dependencies_reach_freezer_analysis(self):
        hooks = ModuleType("PyInstaller.utils.hooks")
        imports = {
            "deprecated": ["deprecated", "deprecated.sphinx"],
            "websockets": ["websockets", "websockets.asyncio", "websockets.asyncio.client"],
        }
        hooks.collect_all = Mock(side_effect=lambda package: ([], [], imports.get(package, [])))
        hooks.collect_submodules = Mock(return_value=[])
        analysis = Mock(return_value=SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[]))
        source = ROOT / ".github/scripts/worker.spec"
        namespace = {
            "SPECPATH": str(source.parent),
            "Analysis": analysis,
            "PYZ": Mock(),
            "EXE": Mock(),
        }
        with patch.dict(sys.modules, {"PyInstaller.utils.hooks": hooks}), \
                patch("importlib.metadata.distribution", return_value=SimpleNamespace(files=[])), \
                patch.object(sys, "path", sys.path.copy()):
            exec(compile(source.read_text(encoding="utf-8"), str(source), "exec"), namespace)
        hiddenimports = analysis.call_args.kwargs["hiddenimports"]
        self.assertIn("deprecated.sphinx", hiddenimports)
        self.assertIn("websockets.asyncio.client", hiddenimports)

    def test_personal_dependencies_are_installed_before_freezing(self):
        requirements = ROOT / "python/flow2api/requirements.txt"
        declarations = requirements.read_text(encoding="utf-8").lower().splitlines()
        self.assertIn("deprecated>=1.2.14", declarations)
        self.assertIn("websockets>=13.0", declarations)
        ast.parse((ROOT / ".github/scripts/worker.spec").read_text(encoding="utf-8"))

    def test_downloaded_extension_matches_sources(self):
        extension = ROOT / "browser-extension"
        sources = {path.relative_to(extension).as_posix(): path.read_bytes()
                   for path in extension.rglob("*") if path.is_file()}
        with zipfile.ZipFile(ROOT / "downloads/GFlow-browser-extension.zip") as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), set(sources))
            for name, content in sources.items():
                with self.subTest(name=name):
                    self.assertEqual(archive.read(name), content)

    def test_remote_host_access_remains_optional(self):
        manifest = json.loads((ROOT / "browser-extension/manifest.json").read_text(encoding="utf-8"))
        self.assertIn("https://*/*", manifest["optional_host_permissions"])
        self.assertNotIn("https://*/*", manifest["host_permissions"])
        self.assertNotIn("http://*/*", manifest["optional_host_permissions"])


if __name__ == "__main__":
    unittest.main()
