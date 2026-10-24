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
        out, rep = clean_text("a" + ZWSP + "b\ufeffc\u00add\u2060e", "en")
        self.assertEqual(out, "abcde\n")
        self.assertEqual(sum(h["count"] for h in rep["invisible"]), 4)

    def test_hard_spaces_become_plain_spaces(self):
        out, _ = clean_text("uno" + NBSP + "dos tres cuatro", "es")
        self.assertEqual(out, "uno dos tres cuatro\n")

    def test_zero_width_inside_url_is_removed(self):
        out, _ = clean_text("mira https://exa" + ZWSP + "mple.com/ruta ahora", "es")
        self.assertIn("https://example.com/ruta", out)

    def test_emoji_zwj_sequences_survive(self):
        family = "\U0001F468" + ZWJ + "\U0001F469" + ZWJ + "\U0001F467"
        rainbow = "\U0001F3F3" + VS16 + ZWJ + "\U0001F308"
        out, rep = clean_text(f"familia {family} y bandera {rainbow}", "es")
        self.assertIn(family, out)
        self.assertIn(rainbow, out)
        self.assertEqual(rep["invisible"], [])

    def test_subregion_flag_tag_sequence_survives_but_stray_tags_do_not(self):
        scotland = "\U0001F3F4" + "".join(chr(0xE0000 + ord(c)) for c in "gbsct") + "\U000E007F"
        hidden = "".join(chr(0xE0000 + ord(c)) for c in "ignore")
        out, rep = clean_text(f"hola {scotland} chao{hidden}", "es")
        self.assertIn(scotland, out)
        self.assertNotIn(hidden, out)
        self.assertEqual(sum(h["count"] for h in rep["invisible"]), len(hidden))

    def test_zwj_between_latin_letters_is_removed(self):
        out, _ = clean_text("a" + ZWJ + "b", "en")
        self.assertEqual(out, "ab\n")

    def test_zwnj_between_persian_letters_survives(self):
        word = "می" + ZWNJ + "خواهم"
        out, _ = clean_text(word, "en")
        self.assertIn(ZWNJ, out)

    def test_direction_marks_kept_in_rtl_text_removed_in_latin(self):
        arabic = RLM + "مرحبا" + RLM
        self.assertIn(RLM, clean_text(arabic, "en")[0])
        self.assertNotIn(RLM, clean_text("hello" + RLM + " world", "en")[0])

    def test_nfc_normalization(self):
        out, rep = clean_text("Mari\u0301a", "es")
        self.assertEqual(out, "María\n")
        self.assertTrue(rep["normalized_nfc"])

    def test_empty_and_whitespace(self):
        self.assertEqual(clean_text("", "en")[0], "")
        self.assertEqual(clean_text("  \n \t ", "en")[0], "")


class Typography(unittest.TestCase):
    def test_em_dash_mid_line_becomes_comma(self):
        self.assertEqual(clean_text(f"uno {EM} dos", "es")[0], "uno, dos\n")
        self.assertEqual(clean_text(f"uno{EM}dos", "es")[0], "uno, dos\n")

    def test_em_dash_does_not_swallow_paragraph_break(self):
        out, _ = clean_text(f"Intro line {EM}\n\nNext paragraph", "en")
        self.assertEqual(out, "Intro line,\n\nNext paragraph\n")

    def test_em_dash_at_line_start_becomes_list_marker(self):
        out, _ = clean_text(f"{EM} one\n{EM} two", "en")
        self.assertEqual(out, "- one\n- two\n")

    def test_em_dash_before_punctuation_is_dropped(self):
        self.assertEqual(clean_text(f"se fue{EM}.", "es")[0], "se fue.\n")

    def test_numeric_ranges(self):
        self.assertEqual(clean_text(f"2020{EN}2022 y 5 {EN} 10", "es")[0], "2020-2022 y 5-10\n")

    def test_curly_quotes_ellipsis_arrows_bullets(self):
        out, _ = clean_text("\u201chola\u201d \u2018x\u2019\u2026 a \u2192 b\n\u2022 item", "es")
        self.assertEqual(out, "\"hola\" 'x'... a -> b\n- item\n")

    def test_commas_and_paragraph_breaks_are_preserved(self):
        text = "Hi Sarah,\n\nI saw your post.\n\nThanks,\nJake"
        self.assertEqual(clean_text(text, "en")[0], text + "\n")

    def test_technical_text_is_not_mangled(self):
        text = "Stack:\n.NET 8 and .env files\nx = a ? b : c\n5 : 30"
        self.assertEqual(clean_text(text, "en")[0], text + "\n")

    def test_protected_segments_are_untouched(self):
        text = "usa `utilize` y #utilize con @utilize y https://x.io/a" + EN + "b y a@b.com"
        out, _ = clean_text(text, "es")
        self.assertEqual(out, text + "\n")


class Lexicon(unittest.TestCase):
    def test_deleted_fillers_leave_clean_sentences(self):
        text = "Importantly, we shipped. Notably, it works. Let's face it, it failed."
        self.assertEqual(clean_text(text, "en")[0], "We shipped. It works. It failed.\n")

    def test_standalone_closers_drop_the_whole_sentence(self):
        out, _ = clean_text("We won. Let that sink in. Then we left.", "en")
        self.assertEqual(out, "We won. Then we left.\n")

    def test_phrase_ending_in_question_mark_matches(self):
        out, _ = clean_text("We shipped it. What are your thoughts? Tell me.", "en")
        self.assertEqual(out, "We shipped it. Tell me.\n")

    def test_replacements_keep_case(self):
        out, _ = clean_text("We utilize it. UTILIZE it. Moreover, it works.", "en")
        self.assertEqual(out, "We use it. USE it. Also, it works.\n")

    def test_ambiguous_words_are_flagged_not_changed(self):
        text = "A landscape photo of vital signs, and we leveraged the journey."
        out, rep = clean_text(text, "en")
        self.assertEqual(out, text + "\n")
        flagged = {f["find"] for f in rep["lexical"]["flagged"]}
        self.assertTrue({"landscape", "vital", "leveraged", "journey"} <= flagged)

    def test_announcement_openers_are_flagged_not_cut(self):
        text = "I am excited to announce that we launched."
        out, rep = clean_text(text, "en")
        self.assertEqual(out, text + "\n")
        self.assertEqual(rep["lexical"]["flagged"][0]["find"], "i am excited to announce")

    def test_spanish_lexicon(self):
        text = "Cabe destacar que el equipo trabajó. Utilizamos robustas soluciones con el fin de crecer."
        out, _ = clean_text(text, "es")
        self.assertEqual(out, "El equipo trabajó. Usamos sólidas soluciones para crecer.\n")

    def test_hygiene_only_skips_lexicon(self):
        text = "Moreover, we utilize it."
        out, _ = clean_text(text, "en", hygiene_only=True)
        self.assertEqual(out, text + "\n")

    def test_idempotent(self):
        sample = f"Importantly, {EM} we utilize it.\n\nHi Ana,\n\n\u201cLet that sink in.\u201d \U0001F680 #tag"
        once, _ = clean_text(sample, "en")
        twice, _ = clean_text(once, "en")
        self.assertEqual(once, twice)

    def test_every_delete_entry_leaves_grammatical_text(self):
        for lang, lex in LEX.items():
            for e in lex["entries"]:
                if e["action"] != "delete":
                    continue
                find = e["find"]
                with self.subTest(lang=lang, find=find):
                    out, _ = agentin.clean(f"{find[0].upper() + find[1:]}, we shipped.", lang, lex)
                    self.assertEqual(out, "We shipped.\n")

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
        big = ("We utilize a robust approach " + EM + " it was crucial. ") * 5000
        start = time.time()
        clean_text(big, "en")
        self.assertLess(time.time() - start, 30)


if __name__ == "__main__":
    unittest.main()
