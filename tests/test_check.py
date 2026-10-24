import io
import unittest
from contextlib import redirect_stdout

from helpers import LEX, agentin

HUMAN_EN = ("I lost a $4,200 client last March because I never wrote a contract. It stung more than the money. "
            "Now everything gets signed before work starts, no exceptions, not even for friends. "
            "Dan from Acme still laughs about it. I don't blame him.")
HUMAN_ES = ("Ayer perdí un cliente de $4.200 por no tener contrato. Me dolió más el orgullo que la plata, "
            "y eso que Marcela me avisó dos veces. Aprendí rápido: ahora todo se firma antes de empezar. "
            "No hay excepciones. Ni con amigos, ni con los que pagan puntual. Se acabó.")
LLM_EN = ("In today's fast-paced world, it is crucial to leverage robust solutions. Moreover, a comprehensive "
          "approach fosters seamless collaboration. Furthermore, organizations must cultivate innovative "
          "strategies. Ultimately, success is a journey, not a destination.")


def run(text, lang):
    return agentin.run_checks(text, LEX[lang], lang)


class Language(unittest.TestCase):
    def test_detects_spanish_and_english(self):
        self.assertEqual(agentin.detect_language(HUMAN_ES), "es")
        self.assertEqual(agentin.detect_language(HUMAN_EN), "en")
        self.assertEqual(agentin.detect_language("Gracias por la invitación"), "es")

    def test_words_keep_accents_and_enye(self):
        self.assertEqual(agentin.words_of("información gestión año"), ["información", "gestión", "año"])


class Sentences(unittest.TestCase):
    def test_decimals_and_abbreviations_do_not_split(self):
        parts = agentin.split_sentences("Cost was $4.5 million, e.g. big. Next one is here ok.")
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(agentin.split_sentences("Pagué $4.200 ayer. Fue un buen trato para todos.")), 2)

    def test_bullets_count_as_sentences(self):
        self.assertEqual(len(agentin.split_sentences("- uno dos tres\n- cuatro cinco seis")), 2)


class Scoring(unittest.TestCase):
    def test_empty_text_has_no_verdict(self):
        res = run("", "en")
        self.assertEqual(res["verdict"], "SIN DATOS")
        self.assertIsNone(res["score"])

    def test_short_clean_comment_can_reach_bien_with_low_confidence(self):
        res = run("Gracias por el dato, lo probé ayer y funcionó.", "es")
        self.assertEqual(res["verdict"], "BIEN")
        self.assertEqual(res["confidence"], "baja")
        self.assertIsNone(res["checks"]["rhythm"][0])

    def test_canned_ai_text_scores_worse_than_human_text(self):
        bad = run(LLM_EN, "en")
        good = run(HUMAN_EN, "en")
        self.assertEqual(bad["verdict"], "CORREGIR")
        self.assertGreater(good["score"], bad["score"] + 20)
        self.assertLess(bad["checks"]["filler"][0], 10)

    def test_spanish_human_text_is_not_penalised_for_being_spanish(self):
        res = run(HUMAN_ES, "es")
        self.assertGreater(res["checks"]["filler"][0], 90)
        self.assertGreater(res["checks"]["voice"][0], 60)
        self.assertGreater(res["checks"]["specificity"][0], 40)

    def test_hygiene_penalises_invisible_characters(self):
        dirty = "uno\u200b dos\u200b tres\u2014cuatro " * 10
        self.assertLess(run(dirty, "es")["checks"]["hygiene"][0], 5)

    def test_output_never_claims_detector_results(self):
        buf = io.StringIO()
        agentin.render_check(run(LLM_EN, "en"), None, buf)
        out = buf.getvalue()
        self.assertIn("No mide autoría", out)
        for banned in ("GPTZero", "Originality", "undetectable", "indetectable", "PASS"):
            self.assertNotIn(banned, out)

    def test_main_fail_under_exit_codes(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(LLM_EN)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(agentin.main(["check", path, "--fail-under", "60"]), 1)
                self.assertEqual(agentin.main(["check", path]), 0)
                self.assertEqual(agentin.main(["check", path, "--json"]), 0)


if __name__ == "__main__":
    unittest.main()
