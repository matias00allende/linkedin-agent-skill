"""Pruebas de robustez: controles de dirección, analítica estricta, cobertura y salida en español."""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from helpers import SCRIPT, agentin, clean_text


def call(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = agentin.main(argv)
    return code, out.getvalue(), err.getvalue()


class Direccion(unittest.TestCase):
    def test_bidi_override_controls_are_removed_from_latin_text(self):
        spoof = "pago a \u202etxt.exe\u202c hoy \u2066x\u2069"
        out, rep = clean_text(spoof)
        self.assertEqual(out, "pago a txt.exe hoy x\n")
        self.assertGreaterEqual(sum(h["count"] for h in rep["invisible"]), 4)

    def test_invisible_report_names_are_in_spanish(self):
        _, rep = clean_text("a\u200bb")
        self.assertIn("espacio de ancho cero", rep["invisible"][0]["name"])


class AnaliticaEstricta(unittest.TestCase):
    def parse(self, csv_text):
        return agentin.parse_analytics(csv_text)

    def test_invalid_numbers_are_reported_and_not_invented(self):
        rows, warnings = self.parse("Impresiones,Reacciones,Comentarios\n1000,-12,1,2 mil\n2000,12.5,3\n")
        by_imp = {r["impressions"]: r for r in rows}
        self.assertIsNone(by_imp[2000]["reactions"])
        text = " ".join(warnings)
        self.assertIn("valor no válido '12.5'", text)
        self.assertIn("fila 3", text)

    def test_thousand_separators_are_accepted_only_in_groups_of_three(self):
        rows, _ = self.parse("Impresiones,Reacciones\n1.940,12\n\"11,400\",7\n12.5,3\n")
        self.assertEqual(sorted(r["impressions"] for r in rows), [1940, 11400])

    def test_absent_is_not_zero(self):
        rows, _ = self.parse("Impresiones,Reacciones,Comentarios\n1000,50,10\n")
        self.assertIsNone(rows[0]["reposts"])
        stats = agentin.compute_stats(rows, None, 5)
        self.assertEqual(stats["coverage"], ["reacciones", "comentarios"])
        self.assertFalse(stats["complete_rate"])
        self.assertAlmostEqual(stats["top"][0]["engagement_rate"], 60 / 1000)

    def test_rows_with_different_coverage_are_not_compared(self):
        csv_text = ("Impresiones,Reacciones,Comentarios,Compartidos\n"
                    "1000,50,10,5\n2000,20,4,2\n3000,30,6,\n")
        rows, _ = self.parse(csv_text)
        stats = agentin.compute_stats(rows, None, 5)
        self.assertEqual(stats["n"], 2)
        self.assertEqual(stats["excluded_rows"], 1)

    def test_cli_output_uses_spanish_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.csv")
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write("Impresiones,Reacciones,Comentarios,Reposts\n1000,50,10,5\n")
            code, out, _ = call(["stats", path, "--followers", "500"])
        self.assertEqual(code, 0)
        self.assertIn("republicaciones", out)
        self.assertNotIn("reposts", out.lower())
        self.assertIn("impresiones por seguidor", out)


class SalidaEnEspanol(unittest.TestCase):
    def run_cli(self, *args):
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
        return subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, env=env, timeout=60)

    def test_help_is_spanish(self):
        r = self.run_cli("--help")
        out = r.stdout.decode("utf-8")
        self.assertEqual(r.returncode, 0)
        self.assertIn("utilidades locales de texto", out)
        for english in ("usage:", "options:", "positional arguments", "show this help"):
            self.assertNotIn(english, out)

    def test_usage_errors_are_spanish(self):
        r = self.run_cli("limits")
        err = r.stderr.decode("utf-8")
        self.assertEqual(r.returncode, 2)
        self.assertIn("uso incorrecto", err)
        for english in ("usage:", "required", "error: the"):
            self.assertNotIn(english, err)

    def test_all_error_messages_are_spanish(self):
        r = self.run_cli("clean", os.path.join(tempfile.gettempdir(), "no-existe-agentin.txt"))
        self.assertIn("no existe el archivo", r.stderr.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
