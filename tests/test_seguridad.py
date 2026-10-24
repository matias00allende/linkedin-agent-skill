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


class CitasLargas(unittest.TestCase):
    def test_very_long_quotes_and_parentheses_are_protected(self):
        long_quote = "\"" + "Dicho esto, utilizamos esto. " * 80 + "\""
        long_paren = "(" + "Dicho esto, utilizamos esto. " * 60 + ")"
        text = f"Cita: {long_quote}\n{long_paren}"
        self.assertEqual(clean_text(text)[0], text + "\n")

    def test_unclosed_quote_does_not_hide_the_rest_of_the_text(self):
        out, _ = clean_text('Abrió una comilla " y luego utilizamos esto.')
        self.assertIn("usamos esto", out)

    def test_views_column_is_not_taken_as_impressions(self):
        with self.assertRaises(agentin.UserError) as ctx:
            agentin.parse_analytics("Fecha,Visualizaciones,Reacciones\n2026-01-01,100,5\n")
        self.assertIn("puede medir otra cosa", str(ctx.exception))


class CasosDeSeleccion(unittest.TestCase):
    def test_selection_cases_cover_every_skill_and_negatives(self):
        import json
        from helpers import ROOT
        with open(os.path.join(ROOT, "tests", "seleccion.json"), encoding="utf-8") as fh:
            cases = json.load(fh)
        expected = {x for c in cases for x in c["esperada"]}
        skills = {d for d in os.listdir(os.path.join(ROOT, "skills")) if d.startswith("ag-")}
        self.assertTrue(skills <= expected, skills - expected)
        for kind in ("ninguna", "pregunta", "rechazo"):
            self.assertIn(kind, expected)
        self.assertGreaterEqual(len(cases), 30)


class RondaSeis(unittest.TestCase):
    def test_nested_quote_inside_parentheses_is_restored(self):
        text = 'Mira (la nota dice "utilizar" aquí) y luego utilizar otra cosa.'
        out, _ = clean_text(text)
        self.assertEqual(out, 'Mira (la nota dice "utilizar" aquí) y luego usar otra cosa.\n')
        self.assertFalse([c for c in out if 0xE000 <= ord(c) <= 0xF8FF])

    def test_parentheses_around_a_quote_are_restored(self):
        text = '("utilizar")'
        self.assertEqual(clean_text(text)[0], text + "\n")

    def test_negative_arguments_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.csv")
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write("Impresiones,Reacciones\n1000,10\n")
            self.assertEqual(agentin.main(["stats", path, "--followers", "-10"]), 2)
            self.assertEqual(agentin.main(["stats", path, "--top", "0"]), 2)

    def test_malformed_limits_file_is_a_controlled_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "limits.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write('{"kinds": {"post": {"max": "mucho"}}}')
            txt = os.path.join(tmp, "a.txt")
            with open(txt, "w", encoding="utf-8") as fh:
                fh.write("hola")
            self.assertEqual(agentin.main(["limits", "--kind", "post", txt, "--limits-file", bad]), 2)

    def test_lexicon_without_find_is_a_controlled_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "lex.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write('{"entries": [{"action": "flag"}], "structures": []}')
            txt = os.path.join(tmp, "a.txt")
            with open(txt, "w", encoding="utf-8") as fh:
                fh.write("hola")
            self.assertEqual(agentin.main(["clean", txt, "--lexicon", bad]), 2)


class RondaSiete(unittest.TestCase):
    def test_single_quoted_citations_are_protected_but_apostrophes_are_not(self):
        text = "Dijo 'utilizamos esto' y luego utilizamos otra cosa."
        self.assertEqual(clean_text(text)[0], "Dijo 'utilizamos esto' y luego usamos otra cosa.\n")

    def test_csv_rows_with_wrong_width_are_skipped_with_a_warning(self):
        rows, warnings = agentin.parse_analytics("Impresiones,Reacciones\n1000,10\n2000,20,99\n")
        self.assertEqual(len(rows), 1)
        self.assertIn("ambigua", " ".join(warnings))

    def test_duplicate_equivalent_headers_are_an_error(self):
        with self.assertRaises(agentin.UserError):
            agentin.parse_analytics("Impresiones,Reacciones,Reacciones totales\n1000,10,12\n")

    def test_json_root_must_be_an_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "l.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write("[]")
            txt = os.path.join(tmp, "a.txt")
            with open(txt, "w", encoding="utf-8") as fh:
                fh.write("hola")
            self.assertEqual(agentin.main(["limits", "--kind", "post", txt, "--limits-file", bad]), 2)

    def test_tmp_clean_rejects_a_forged_marker(self):
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
        with tempfile.TemporaryDirectory() as home:
            env["AGENTIN_HOME"] = home
            fake = os.path.join(home, "tmp", "falsa")
            os.makedirs(fake)
            with open(os.path.join(fake, ".agentin-tmp"), "w", encoding="utf-8") as fh:
                fh.write("otra cosa")
            r = subprocess.run([sys.executable, "-I", SCRIPT, "tmp", "clean", fake], capture_output=True, env=env, timeout=60)
            self.assertEqual(r.returncode, 2)
            self.assertTrue(os.path.isdir(fake))
