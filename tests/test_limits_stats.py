import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from helpers import agentin

NOTE = ("Saw your post on killing the discovery call - we did the same thing in March and it worked. "
        "I run ops at a 12-person studio. Would like to follow along.")


def write(tmp, name, text):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return path


def call(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = agentin.main(argv)
    return code, out.getvalue(), err.getvalue()


class Limits(unittest.TestCase):
    def test_sample_invite_note_has_152_characters(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = call(["limits", "--kind", "invite", write(tmp, "n.txt", NOTE + "\n")])
        self.assertEqual(code, 0)
        self.assertIn(f"{len(NOTE)}/200", out)
        self.assertEqual(len(NOTE), 152)

    def test_over_limit_returns_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = call(["limits", "--kind", "invite", write(tmp, "n.txt", "x" * 201)])
        self.assertEqual(code, 1)
        self.assertIn("fuera del límite", out)

    def test_premium_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "n.txt", "x" * 250)
            self.assertEqual(call(["limits", "--kind", "invite", path])[0], 1)
            self.assertEqual(call(["limits", "--kind", "invite", path, "--premium"])[0], 0)

    def test_emoji_count_as_two_units_and_the_larger_count_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "n.txt", "\U0001F680" * 101)
            code, out, _ = call(["limits", "--kind", "invite", path, "--json"])
        self.assertEqual(code, 1)
        self.assertIn('"characters": 101', out)
        self.assertIn('"utf16_units": 202', out)

    def test_unknown_kind_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _, err = call(["limits", "--kind", "nope", write(tmp, "n.txt", "x")])
        self.assertEqual(code, 2)
        self.assertIn("tipo desconocido", err)

    def test_limits_are_marked_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, out, _ = call(["limits", "--kind", "post", write(tmp, "n.txt", "hola")])
        self.assertIn("no verificado", out)


CSV_ES = ("Fecha;Texto;Impresiones;Reacciones;Comentarios;Compartidos;Gancho\n"
          "2026-08-01;Perdí un cliente;1.940;120;38;4;3\n"
          "2026-08-04;7 herramientas;11.400;80;6;2;5\n"
          "2026-08-08;Cobré más;2.210;95;30;7;20\n"
          "2026-08-09;Sin datos;0;1;1;1;1\n")
CSV_EN = ("Date,Post,Impressions,Reactions,Comments,Reposts\n"
          "2026-08-01,One,1000,50,10,0\n"
          "2026-08-02,Two,2000,10,0,0\n")


class Stats(unittest.TestCase):
    def test_semicolon_csv_with_spanish_headers_and_thousand_dots(self):
        rows, warnings = agentin.parse_analytics(CSV_ES)
        self.assertEqual([r["impressions"] for r in rows], [1940, 11400, 2210])
        self.assertEqual(len(warnings), 1)
        stats = agentin.compute_stats(rows, 4200, 2)
        first = stats["top"][0]
        self.assertAlmostEqual(first["engagement_rate"], (120 + 38 + 4) / 1940)
        self.assertAlmostEqual(first["comment_ratio"], 38 / 120)
        self.assertAlmostEqual(first["reach_multiple"], 1940 / 4200)
        self.assertEqual(stats["top"][0]["impressions"], 1940)
        self.assertEqual(stats["bottom"][0]["impressions"], 11400)

    def test_comma_csv_and_small_sample_note(self):
        rows, _ = agentin.parse_analytics(CSV_EN)
        stats = agentin.compute_stats(rows, None, 5)
        self.assertEqual(stats["n"], 2)
        self.assertIn("no hay muestra", stats["sample_note"])
        self.assertIsNone(stats["top"][0]["reach_multiple"])

    def test_hook_groups(self):
        rows, _ = agentin.parse_analytics(CSV_ES)
        stats = agentin.compute_stats(rows, None, 5)
        self.assertEqual({g["hook"] for g in stats["by_hook"]}, {"3", "5", "20"})

    def test_missing_columns_report_what_was_found(self):
        with self.assertRaises(agentin.UserError) as ctx:
            agentin.parse_analytics("a,b\n1,2\n")
        self.assertIn("Columnas encontradas: a, b", str(ctx.exception))

    def test_cli_text_and_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(tmp, "a.csv", CSV_ES)
            code, out, _ = call(["stats", path, "--followers", "4200"])
            self.assertEqual(code, 0)
            self.assertIn("Mejores por tasa de interacción", out)
            code, out, _ = call(["stats", path, "--json"])
            self.assertEqual(code, 0)
            self.assertIn('"n": 3', out)


if __name__ == "__main__":
    unittest.main()
