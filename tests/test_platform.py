import pathlib
import tempfile
import unittest

from tests import helpers  # noqa: F401
import platform_utils as pu


class VenvPathTests(unittest.TestCase):
    def test_windows_and_linux_paths(self):
        win = pu.venv_python("/proj", windows=True)
        lin = pu.venv_python("/proj", windows=False)
        self.assertEqual(win.parts[-3:], (".venv", "Scripts", "python.exe"))
        self.assertEqual(lin.parts[-3:], (".venv", "bin", "python"))
        self.assertEqual(pu.venv_py_rel(True), ".venv\\Scripts\\python.exe")
        self.assertEqual(pu.venv_py_rel(False), ".venv/bin/python")

    def make(self, root, *relative):
        for rel in relative:
            p = pathlib.Path(root, ".venv", *rel.split("/"))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("")
        return pathlib.Path(root, ".venv")

    def test_diagnose_venv(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(pu.diagnose_venv(pathlib.Path(d, ".venv"), windows=False), "missing")
            venv = self.make(d, "Scripts/python.exe")
            self.assertEqual(pu.diagnose_venv(venv, windows=True), "ok")
            self.assertEqual(pu.diagnose_venv(venv, windows=False), "foreign")  # Windows venv on Linux
        with tempfile.TemporaryDirectory() as d:
            venv = self.make(d, "bin/python")
            self.assertEqual(pu.diagnose_venv(venv, windows=False), "ok")
            self.assertEqual(pu.diagnose_venv(venv, windows=True), "foreign")  # Linux venv on Windows
        with tempfile.TemporaryDirectory() as d:
            venv = self.make(d, "pyvenv.cfg")
            self.assertEqual(pu.diagnose_venv(venv, windows=False), "broken")

    def test_hints_and_console(self):
        self.assertIn("ollama", pu.ollama_install_hint().lower())
        pu.make_console_utf8()  # must never raise


if __name__ == "__main__":
    unittest.main()
