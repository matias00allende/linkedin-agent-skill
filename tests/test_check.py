import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from helpers import LEX, agentin

HUMAN_ES = ("Ayer perdí un cliente de $4.200 por no tener contrato. Me dolió más el orgullo que la plata, "
            "y eso que Marcela me avisó dos veces. Aprendí rápido: ahora todo se firma antes de empezar. "
            "No hay excepciones. Ni con amigos, ni con los que pagan puntual. Se acabó.")
LLM_ES = ("En el mundo actual, es crucial utilizar soluciones robustas. Cabe destacar que un enfoque integral "
          "potencia sinergias innovadoras. Además, las organizaciones deben fomentar estrategias disruptivas. "
          "En definitiva, el éxito es un viaje hacia un panorama transformador.")


def run(text):
    return agentin.run_checks(text, LEX["es"], "es")


class Words(unittest.TestCase):
    def test_words_keep_accents_and_enye(self):
        self.assertEqual(agentin.words_of("información gestión año"), ["información", "gestión", "año"])


class Sentences(unittest.TestCase):
    def test_decimals_and_abbreviations_do_not_split(self):
        parts = agentin.split_sentences("El costo fue $4.5 millones, p. ej. alto. La siguiente cifra es menor.")
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(agentin.split_sentences("Pagué $4.200 ayer. Fue un buen trato para todos.")), 2)

    def test_bullets_count_as_sentences(self):
        self.assertEqual(len(agentin.split_sentences("- uno dos tres\n- cuatro cinco seis")), 2)


class Scoring(unittest.TestCase):
    def test_empty_text_has_no_verdict(self):
        res = run("")
        self.assertEqual(res["verdict"], "SIN DATOS")
        self.assertIsNone(res["score"])

    def test_very_short_text_gets_partial_results_and_no_global_verdict(self):
        res = run("Gracias por el dato, lo probé ayer y funcionó.")
        self.assertEqual(res["verdict"], "PARCIAL")
        self.assertIsNone(res["score"])
        self.assertEqual(res["evaluable"], 2)
        self.assertIsNone(res["checks"]["rhythm"][0])

    def test_omit_excludes_checks_that_do_not_apply(self):
        res = agentin.run_checks(HUMAN_ES, LEX["es"], "es", ("voice", "specificity"))
        self.assertIsNone(res["checks"]["voice"][0])
        self.assertIsNone(res["checks"]["specificity"][0])
        self.assertEqual(res["evaluable"], 3)

    def test_template_text_scores_worse_than_human_text(self):
        bad = run(LLM_ES)
        good = run(HUMAN_ES)
        self.assertEqual(bad["verdict"], "CORREGIR")
        self.assertGreater(good["score"], bad["score"] + 20)
        self.assertLess(bad["checks"]["filler"][0], 10)

    def test_human_spanish_text_gets_credit(self):
        res = run(HUMAN_ES)
        self.assertGreater(res["checks"]["filler"][0], 90)
        self.assertGreater(res["checks"]["voice"][0], 60)
        self.assertGreater(res["checks"]["specificity"][0], 40)

    def test_hygiene_penalises_invisible_characters(self):
        dirty = "uno\u200b dos\u200b tres\u2014cuatro " * 10
        self.assertLess(run(dirty)["checks"]["hygiene"][0], 5)

    def test_output_is_plain_text_and_never_claims_detector_results(self):
        buf = io.StringIO()
        agentin.render_check(run(LLM_ES), None, buf)
        out = buf.getvalue()
        self.assertIn("No mide autoría", out)
        for banned in ("GPTZero", "Originality", "undetectable", "indetectable", "PASS", "####", "====", "----"):
            self.assertNotIn(banned, out)

    def test_main_fail_under_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(LLM_ES)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(agentin.main(["check", path, "--fail-under", "60"]), 1)
                self.assertEqual(agentin.main(["check", path]), 0)
                self.assertEqual(agentin.main(["check", path, "--json"]), 0)


if __name__ == "__main__":
    unittest.main()
