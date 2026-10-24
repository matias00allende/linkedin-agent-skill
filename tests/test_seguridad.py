"""Pruebas de citas, direcciones, escritura exclusiva y carpetas temporales."""
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import SCRIPT, agentin, clean_text


class Citas(unittest.TestCase):
    def test_quotes_are_not_changed_by_lexical_replacements(self):
        text = 'El informe dice "utilizamos esto con el fin de crecer" y luego utilizamos otra cosa.'
        out, _ = clean_text(text)
        self.assertEqual(out, 'El informe dice "utilizamos esto con el fin de crecer" y luego usamos otra cosa.\n')

    def test_multiline_quotes_and_parentheses_are_protected(self):
        text = 'Cita:\n"Dicho esto, nos vamos.\nDicho esto, volvemos."\n(Dicho esto,\nse acordó.)'
        self.assertEqual(clean_text(text)[0], text + "\n")

    def test_spanish_angle_quotes_are_protected(self):
        text = "Dijo \u00abutilizamos esto\u00bb ayer."
        self.assertEqual(clean_text(text)[0], text + "\n")


class Direccion(unittest.TestCase):
    def test_override_controls_are_removed_even_when_the_text_has_rtl_letters(self):
        text = "مرحبا pago \u202etxt.exe\u202c hoy"
        out, _ = clean_text(text)
        self.assertNotIn("\u202e", out)
        self.assertNotIn("\u202c", out)
        self.assertIn("مرحبا", out)


class Emoji(unittest.TestCase):
    def test_any_emoji_is_flagged_but_not_removed(self):
        text = "Lanzamos hoy \U0001F389 el producto."
        out, rep = clean_text(text)
        self.assertIn("\U0001F389", out)
        self.assertIn("emoji", [s["id"] for s in rep["structures"]])


class EscrituraExclusiva(unittest.TestCase):
    def test_existing_file_is_not_overwritten_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.txt")
            agentin.write_text(path, "uno", force=False)
            with self.assertRaises(agentin.UserError):
                agentin.write_text(path, "dos", force=False)
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "uno")
            agentin.write_text(path, "dos", force=True)
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "dos")


class CarpetasTemporales(unittest.TestCase):
    def run_cli(self, home, *args):
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
        env["AGENTIN_HOME"] = home
        return subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, env=env, timeout=60)

    def test_new_creates_a_unique_folder_and_clean_removes_it(self):
        with tempfile.TemporaryDirectory() as home:
            a = self.run_cli(home, "tmp", "new").stdout.decode("utf-8").strip()
            b = self.run_cli(home, "tmp", "new").stdout.decode("utf-8").strip()
            self.assertNotEqual(a, b)
            self.assertTrue(os.path.isdir(a))
            with open(os.path.join(a, "borrador.txt"), "w", encoding="utf-8") as fh:
                fh.write("texto")
            os.makedirs(os.path.join(a, "sub"))
            r = self.run_cli(home, "tmp", "clean", a)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse(os.path.exists(a))
            self.assertTrue(os.path.isdir(b))

    def test_clean_refuses_foreign_folders(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as other:
            self.run_cli(home, "tmp", "new")
            r = self.run_cli(home, "tmp", "clean", other)
            self.assertEqual(r.returncode, 2)
            self.assertTrue(os.path.isdir(other))
            inside = os.path.join(home, "tmp", "sin-marca")
            os.makedirs(inside)
            r = self.run_cli(home, "tmp", "clean", inside)
            self.assertEqual(r.returncode, 2)
            self.assertTrue(os.path.isdir(inside))

    def test_clean_requires_a_path(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertEqual(self.run_cli(home, "tmp", "clean").returncode, 2)


if __name__ == "__main__":
    unittest.main()
