import time
import unittest

from helpers import LEX, agentin, clean_text

EM = "\u2014"
EN = "\u2013"
ZWSP = "\u200b"
ZWJ = "\u200d"
ZWNJ = "\u200c"
RLM = "\u200f"
NBSP = "\u00a0"
VS16 = "\ufe0f"


class Hygiene(unittest.TestCase):
    def test_zero_width_and_bom_and_soft_hyphen_removed(self):
        out, rep = clean_text("a" + ZWSP + "b\ufeffc\u00add\u2060e")
        self.assertEqual(out, "abcde\n")
        self.assertEqual(sum(h["count"] for h in rep["invisible"]), 4)

    def test_hard_spaces_become_plain_spaces(self):
        out, _ = clean_text("uno" + NBSP + "dos tres cuatro")
        self.assertEqual(out, "uno dos tres cuatro\n")

    def test_zero_width_inside_url_is_removed(self):
        out, _ = clean_text("mira https://exa" + ZWSP + "mple.com/ruta ahora")
        self.assertIn("https://example.com/ruta", out)

    def test_emoji_zwj_sequences_survive(self):
        family = "\U0001F468" + ZWJ + "\U0001F469" + ZWJ + "\U0001F467"
        rainbow = "\U0001F3F3" + VS16 + ZWJ + "\U0001F308"
        out, rep = clean_text(f"familia {family} y bandera {rainbow}")
        self.assertIn(family, out)
        self.assertIn(rainbow, out)
        self.assertEqual(rep["invisible"], [])

    def test_subregion_flag_tag_sequence_survives_but_stray_tags_do_not(self):
        scotland = "\U0001F3F4" + "".join(chr(0xE0000 + ord(c)) for c in "gbsct") + "\U000E007F"
        hidden = "".join(chr(0xE0000 + ord(c)) for c in "ignore")
        out, rep = clean_text(f"hola {scotland} chao{hidden}")
        self.assertIn(scotland, out)
        self.assertNotIn(hidden, out)
        self.assertEqual(sum(h["count"] for h in rep["invisible"]), len(hidden))

    def test_zwj_between_latin_letters_is_removed(self):
        out, _ = clean_text("a" + ZWJ + "b")
        self.assertEqual(out, "ab\n")

    def test_zwnj_between_persian_letters_survives(self):
        word = "می" + ZWNJ + "خواهم"
        out, _ = clean_text(word)
        self.assertIn(ZWNJ, out)

    def test_direction_marks_kept_in_rtl_text_removed_in_latin(self):
        arabic = RLM + "مرحبا" + RLM
        self.assertIn(RLM, clean_text(arabic)[0])
        self.assertNotIn(RLM, clean_text("hello" + RLM + " world")[0])

    def test_nfc_normalization(self):
        out, rep = clean_text("Mari\u0301a")
        self.assertEqual(out, "María\n")
        self.assertTrue(rep["normalized_nfc"])

    def test_empty_and_whitespace(self):
        self.assertEqual(clean_text("")[0], "")
        self.assertEqual(clean_text("  \n \t ")[0], "")


class Typography(unittest.TestCase):
    def test_em_dash_mid_line_becomes_comma(self):
        self.assertEqual(clean_text(f"uno {EM} dos")[0], "uno, dos\n")
        self.assertEqual(clean_text(f"uno{EM}dos")[0], "uno, dos\n")

    def test_em_dash_does_not_swallow_paragraph_break(self):
        out, _ = clean_text(f"Intro line {EM}\n\nNext paragraph")
        self.assertEqual(out, "Intro line,\n\nNext paragraph\n")

    def test_em_dash_at_line_start_becomes_list_marker(self):
        out, _ = clean_text(f"{EM} one\n{EM} two")
        self.assertEqual(out, "- one\n- two\n")

    def test_em_dash_before_punctuation_is_dropped(self):
        self.assertEqual(clean_text(f"se fue{EM}.")[0], "se fue.\n")

    def test_numeric_ranges(self):
        self.assertEqual(clean_text(f"2020{EN}2022 y 5 {EN} 10")[0], "2020-2022 y 5-10\n")

    def test_curly_quotes_ellipsis_arrows_bullets(self):
        out, _ = clean_text("\u201chola\u201d \u2018x\u2019\u2026 a \u2192 b\n\u2022 item")
        self.assertEqual(out, "\"hola\" 'x'... a -> b\n- item\n")

    def test_commas_and_paragraph_breaks_are_preserved(self):
        text = "Hi Sarah,\n\nI saw your post.\n\nThanks,\nJake"
        self.assertEqual(clean_text(text)[0], text + "\n")

    def test_technical_text_is_not_mangled(self):
        text = "Stack:\n.NET 8 and .env files\nx = a ? b : c\n5 : 30"
        self.assertEqual(clean_text(text)[0], text + "\n")

    def test_protected_segments_are_untouched(self):
        text = "usa `utilize` y #utilize con @utilize y https://x.io/a" + EN + "b y a@b.com"
        out, _ = clean_text(text)
        self.assertEqual(out, text + "\n")


class Lexicon(unittest.TestCase):
    def test_deleted_fillers_leave_clean_sentences(self):
        text = "Dicho esto, lanzamos. Seamos honestos, funcionó. No es ningún secreto que costó."
        self.assertEqual(clean_text(text)[0], "Lanzamos. Funcionó. Costó.\n")

    def test_standalone_closers_drop_the_whole_sentence(self):
        out, _ = clean_text("Ganamos. Léelo de nuevo. Después nos fuimos.")
        self.assertEqual(out, "Ganamos. Después nos fuimos.\n")

    def test_phrase_pattern_matches_phrases_ending_in_a_question_mark(self):
        import re
        self.assertIsNotNone(re.search(agentin.phrase_pattern("qué opinas?"), "dime qué opinas? ahora"))

    def test_replacements_keep_case(self):
        out, _ = clean_text("Utilizamos esto. UTILIZAMOS eso. Con el fin de crecer.")
        self.assertEqual(out, "Usamos esto. USAMOS eso. Para crecer.\n")

    def test_ambiguous_words_are_flagged_not_changed(self):
        text = "Una foto del panorama, un enfoque innovador y el ecosistema."
        out, rep = clean_text(text)
        self.assertEqual(out, text + "\n")
        flagged = {f["find"] for f in rep["lexical"]["flagged"]}
        self.assertTrue({"panorama", "innovador", "ecosistema"} <= flagged)

    def test_announcement_openers_are_flagged_not_cut(self):
        text = "Me emociona anunciar que lanzamos."
        out, rep = clean_text(text)
        self.assertEqual(out, text + "\n")
        self.assertEqual(rep["lexical"]["flagged"][0]["find"], "me emociona anunciar")

    def test_spanish_lexicon(self):
        text = "Cabe destacar que el equipo trabajó. Utilizamos robustas soluciones con el fin de crecer."
        out, _ = clean_text(text)
        self.assertEqual(out, "El equipo trabajó. Usamos sólidas soluciones para crecer.\n")

    def test_hygiene_only_skips_lexicon(self):
        text = "Dicho esto, utilizamos esto."
        out, _ = clean_text(text, hygiene_only=True)
        self.assertEqual(out, text + "\n")

    def test_idempotent(self):
        sample = f"Dicho esto, {EM} utilizamos esto.\n\nHola Ana,\n\n\u201cLéelo de nuevo.\u201d \U0001F680 #tag"
        once, _ = clean_text(sample)
        twice, _ = clean_text(once)
        self.assertEqual(once, twice)

    def test_every_delete_entry_leaves_grammatical_text(self):
        for lang, lex in LEX.items():
            for e in lex["entries"]:
                if e["action"] != "delete":
                    continue
                find = e["find"]
                with self.subTest(lang=lang, find=find):
                    sep = "." if e.get("standalone") else ","
                    out, _ = agentin.clean(f"{find[0].upper() + find[1:]}{sep} lanzamos.", lang, lex)
                    self.assertEqual(out, "Lanzamos.\n")

    def test_deletions_only_happen_at_the_start_of_a_sentence(self):
        for text in ("Si ya lo sabes, avisa.", "Dime qué pasó, dicho esto, avisa.",
                     "Escribió \"dicho esto, nos vamos\" en el acta.", "Quedó claro que no es ningún secreto que hubo cambios."):
            self.assertEqual(clean_text(text)[0], text + "\n", text)

    def test_closer_inside_a_sentence_is_kept(self):
        text = "Si quieres, léelo de nuevo, y me cuentas."
        self.assertEqual(clean_text(text)[0], text + "\n")

    def test_every_replace_entry_applies(self):
        for lang, lex in LEX.items():
            for e in lex["entries"]:
                if e["action"] != "replace":
                    continue
                with self.subTest(lang=lang, find=e["find"]):
                    out, _ = agentin.clean(f"x {e['find']} y", lang, lex)
                    self.assertIn(e["replace"], out)

    def test_lexicon_integrity(self):
        for lang, lex in LEX.items():
            seen = set()
            for e in lex["entries"]:
                self.assertIn(e["action"], ("replace", "delete", "flag"))
                self.assertNotIn(e["find"], seen, f"duplicado en {lang}: {e['find']}")
                seen.add(e["find"])
                if e["action"] == "replace":
                    self.assertTrue(e["replace"], e["find"])


class Performance(unittest.TestCase):
    def test_large_input_is_fast(self):
        big = ("Utilizamos un enfoque robusto " + EM + " fue crucial. ") * 5000
        start = time.time()
        clean_text(big)
        self.assertLess(time.time() - start, 30)


if __name__ == "__main__":
    unittest.main()
