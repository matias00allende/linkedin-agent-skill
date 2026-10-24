"""Pruebas de extremo a extremo por subproceso, con la codificación local forzada a la de Windows/POSIX sin UTF-8."""
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import SCRIPT


def env_without_utf8():
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING", "PYTHONSTARTUP")}
    env["PYTHONUTF8"] = "0"
    return env


def run(args, data=None):
    return subprocess.run([sys.executable, "-I", SCRIPT] + args, input=data, capture_output=True,
                          env=env_without_utf8(), timeout=60)


SAMPLE = "Hola María \u2014 mañana lanzamos \U0001F680 el producto. Gracias\u2026\n".encode("utf-8")


class Cli(unittest.TestCase):
    def test_isolated_mode_runs_without_sibling_imports(self):
        r = run(["--version"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(b"agentin", r.stdout)

    def test_stdin_stdout_roundtrip_is_utf8_with_emoji_and_accents(self):
        r = run(["clean", "-"], SAMPLE)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        self.assertEqual(r.stdout.decode("utf-8"), "Hola María, mañana lanzamos \U0001F680 el producto. Gracias...\n")
        self.assertNotIn(b"\r\n", r.stdout)

    def test_json_output_with_emoji(self):
        r = run(["clean", "-", "--json"], SAMPLE)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        self.assertIn("\U0001F680", r.stdout.decode("utf-8"))

    def test_out_file_is_utf8_lf_and_not_overwritten_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "o.txt")
            self.assertEqual(run(["clean", "-", "-o", out], SAMPLE).returncode, 0)
            with open(out, "rb") as fh:
                data = fh.read()
            self.assertNotIn(b"\r", data)
            self.assertIn("María".encode("utf-8"), data)
            r = run(["clean", "-", "-o", out], SAMPLE)
            self.assertEqual(r.returncode, 2)
            self.assertIn(b"--force", r.stderr)
            self.assertEqual(run(["clean", "-", "-o", out, "--force"], SAMPLE).returncode, 0)

    def test_missing_file_is_a_clean_error_not_a_traceback(self):
        r = run(["clean", os.path.join(tempfile.gettempdir(), "no-existe-agentin.txt")])
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stderr.startswith(b"error:"))
        self.assertNotIn(b"Traceback", r.stderr)

    def test_non_utf8_input_is_reported(self):
        r = run(["clean", "-"], "mañana".encode("cp1252"))
        self.assertEqual(r.returncode, 2)
        self.assertIn(b"UTF-8", r.stderr)

    def test_bom_and_crlf_input(self):
        r = run(["clean", "-"], b"\xef\xbb\xbfuno\r\ndos\r\n")
        self.assertEqual(r.stdout, b"uno\ndos\n")

    def test_check_compare_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = os.path.join(tmp, "a.txt"), os.path.join(tmp, "b.txt")
            with open(a, "w", encoding="utf-8") as fh:
                fh.write("Moreover, it is crucial to leverage robust solutions. " * 5)
            with open(b, "w", encoding="utf-8") as fh:
                fh.write("I fixed the login bug on Tuesday. It took 3 hours. Dan helped.\n" * 3)
            r = run(["check", a, b])
        self.assertEqual(r.returncode, 0)
        self.assertIn("->", r.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
