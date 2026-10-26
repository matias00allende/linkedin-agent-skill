"""Pruebas de la higiene del propio repositorio: estructura, datos, texto y seguridad."""
import json
import os
import re
import unicodedata
import unittest

from helpers import DATA, ROOT, SCRIPT, agentin

SKILLS = ["audit", "carousel", "comment", "dm", "human", "inbox", "plan", "post", "profile", "publish", "reply", "repurpose"]
EXPECTED = sorted("ag-" + ("voz" if s == "human" else s) for s in SKILLS)
TEXT_EXT = (".md", ".py", ".json", ".yml", ".yaml", ".txt", ".gitignore")


def repo_files():
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
        for f in fn:
            yield os.path.join(dp, f)


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def frontmatter(path):
    text = read(path)
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, f"sin frontmatter: {path}"
    fm, current = {}, None
    for line in m.group(1).split("\n"):
        k = re.match(r"^([a-z_-]+):\s*(>-|.*)$", line)
        if k and not line.startswith(" "):
            current = k.group(1)
            fm[current] = "" if k.group(2) == ">-" else k.group(2).strip()
        elif current:
            fm[current] = (fm[current] + " " + line.strip()).strip()
    return fm


class Structure(unittest.TestCase):
    def test_twelve_skills_with_matching_names(self):
        found = sorted(d for d in os.listdir(os.path.join(ROOT, "skills")) if d.startswith("ag-"))
        self.assertEqual(found, EXPECTED)
        for d in found:
            fm = frontmatter(os.path.join(ROOT, "skills", d, "SKILL.md"))
            self.assertEqual(fm["name"], d)
            self.assertTrue(40 < len(fm["description"]) <= 800, f"{d}: descripción de {len(fm['description'])}")

    def test_descriptions_are_spanish_pushy_and_say_they_do_not_publish_or_evade(self):
        for d in EXPECTED:
            desc = frontmatter(os.path.join(ROOT, "skills", d, "SKILL.md"))["description"]
            self.assertNotIn("English", desc, d)
            self.assertIn("aunque no", desc, f"{d}: la descripción debe ser activa (aunque no digan...)")
            if d != "ag-voz":
                self.assertTrue("Nunca " in desc or "No programa" in desc or "Solo trabaja" in desc, d)
        voz = frontmatter(os.path.join(ROOT, "skills", "ag-voz", "SKILL.md"))["description"]
        self.assertIn("evadir detectores", voz)

    def test_plain_text_no_decoration(self):
        import re as _re
        files = [os.path.join(ROOT, "skills", d, "SKILL.md") for d in EXPECTED]
        files += [os.path.join(ROOT, "README.md"), os.path.join(ROOT, "CONTRIBUTING.md"),
                  os.path.join(ROOT, "templates", "voz.md"),
                  os.path.join(ROOT, "skills", "ag-voz", "references", "criterio.md")]
        emoji = _re.compile("[\U0001f000-\U0001faff\u2600-\u27bf\u2b00-\u2bff]")
        for path in files:
            text = read(path)
            self.assertNotIn("**", text, path)
            self.assertNotIn("|---", text, path)
            self.assertNotIn("| ---", text, path)
            self.assertIsNone(emoji.search(text), path)
            self.assertNotIn("\u00b7", text.replace("[LinkedIn]", ""), path) if path.endswith("SKILL.md") else None

    def test_everything_user_facing_is_spanish_only(self):
        for path in repo_files():
            if path.endswith((".md", ".json")) and "CHANGELOG" not in path:
                low = read(path).lower()
                for w in (" the ", " and ", " with ", " your "):
                    self.assertNotIn(w, low, f"{path}: texto en inglés ({w.strip()})")

    def test_skills_define_the_response_format(self):
        for d in EXPECTED:
            if d != "ag-voz":
                self.assertIn("Formato de la respuesta", read(os.path.join(ROOT, "skills", d, "SKILL.md")), d)

    def test_criterio_exists_and_skills_point_to_it(self):
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "skills", "ag-voz", "references", "criterio.md")))
        for d in EXPECTED:
            if d != "ag-voz":
                self.assertIn("references/criterio.md", read(os.path.join(ROOT, "skills", d, "SKILL.md")), d)

    def test_registro_base_humano_y_ajustable(self):
        crit = read(os.path.join(ROOT, "skills", "ag-voz", "references", "criterio.md"))
        for frase in ("## Registro y tono", "profesional y humano", "lo que pide ahora, luego su voz.md",
                      "un método para evadir detectores de IA"):
            self.assertIn(frase, crit)
        for d in ("ag-post", "ag-comment", "ag-reply", "ag-dm", "ag-inbox", "ag-repurpose", "ag-carousel", "ag-profile"):
            self.assertIn("profesional y humano por defecto", read(os.path.join(ROOT, "skills", d, "SKILL.md")), d)
        self.assertIn("Registro de base", read(os.path.join(ROOT, "templates", "voz.md")))

    def test_every_skill_has_the_common_rules_or_policy(self):
        for d in EXPECTED:
            text = read(os.path.join(ROOT, "skills", d, "SKILL.md"))
            if d == "ag-voz":
                self.assertIn("## Política", text)
                self.assertIn("no es un detector de IA", text)
            else:
                self.assertIn("## Reglas comunes de AgentIn", text, d)
                self.assertIn("es dato, no instrucciones", text, d)

    def test_script_paths_in_skills_use_the_skill_dir_variable(self):
        for d in EXPECTED:
            text = read(os.path.join(ROOT, "skills", d, "SKILL.md"))
            for m in re.finditer(r"agentin\.py", text):
                line = text[text.rfind("\n", 0, m.start()) + 1: text.find("\n", m.start())]
                if re.match(r"^python3? ", line):
                    self.assertIn("-I", line, f"{d}: falta -I en: {line}")
                    self.assertIn("${CLAUDE_SKILL_DIR}", line, f"{d}: falta la variable en: {line}")

    def test_json_files_parse_and_are_consistent(self):
        formulas = json.loads(read(os.path.join(ROOT, "skills", "ag-post", "hook-formulas.json")))
        self.assertEqual([h["id"] for h in formulas["hooks"]], list(range(1, 22)))
        for h in formulas["hooks"]:
            for field in ("name", "template", "example", "use", "trap"):
                self.assertTrue(h[field].strip(), f"{h['id']}.{field}")
            self.assertNotIn("\\n", h["template"] + h["example"])
        rubric = json.loads(read(os.path.join(ROOT, "skills", "ag-profile", "rubric.json")))
        self.assertEqual(sum(i["points"] for i in rubric["items"]), 100)
        self.assertEqual(len(rubric["items"]), 12)
        for name in ("limits.json", "lexicon_es.json"):
            json.loads(read(os.path.join(DATA, name)))
        plugin = json.loads(read(os.path.join(ROOT, ".claude-plugin", "plugin.json")))
        market = json.loads(read(os.path.join(ROOT, ".claude-plugin", "marketplace.json")))
        self.assertEqual(plugin["name"], "agentin")
        self.assertEqual(market["plugins"][0]["name"], plugin["name"])
        self.assertEqual(plugin["license"], "Apache-2.0")

    def test_license_keeps_the_original_attribution(self):
        self.assertIn("Apache License", read(os.path.join(ROOT, "LICENSE")))
        notice = read(os.path.join(ROOT, "NOTICE"))
        self.assertIn("MIT License", notice)
        self.assertIn("Jake Schincariol", notice)
        self.assertIn("Matías Allende", notice)

    def test_required_top_level_files(self):
        for name in ("README.md", "LICENSE", "NOTICE", "CHANGELOG.md", "CONTRIBUTING.md"):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, name)), name)
        self.assertIn("## Autor", read(os.path.join(ROOT, "README.md")))

    def test_invite_example_length_claim_is_true(self):
        text = read(os.path.join(ROOT, "skills", "ag-dm", "SKILL.md"))
        m = re.search(r"\((\d+) caracteres, contados[^)]*\):\n\n(.*?)\n\n", text, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), len(m.group(2)))


class Hygiene(unittest.TestCase):
    def test_no_long_dashes_anywhere(self):
        for path in repo_files():
            if path.endswith(TEXT_EXT):
                self.assertFalse(re.search("[\u2013\u2014]", read(path)), path)

    def test_no_invisible_or_format_characters_anywhere(self):
        for path in repo_files():
            if path.endswith(TEXT_EXT):
                bad = [c for c in read(path) if unicodedata.category(c) in ("Cf", "Co", "Cn") or c in "\u00a0\u202f\u2009"]
                self.assertEqual(bad, [], path)

    def test_code_and_data_use_escapes_for_special_punctuation(self):
        allowed_non_ascii = lambda c: unicodedata.category(c).startswith("L") or c in "\u00bf\u00a1\u00ab\u00bb\u00b7"
        for path in repo_files():
            if path.endswith((".py", ".json")):
                for c in read(path):
                    if ord(c) > 127:
                        self.assertTrue(allowed_non_ascii(c), f"{path}: U+{ord(c):04X}")

    def test_utf8_lf_files(self):
        for path in repo_files():
            if path.endswith(TEXT_EXT):
                with open(path, "rb") as fh:
                    data = fh.read()
                self.assertNotIn(b"\r", data, path)
                self.assertFalse(data.startswith(b"\xef\xbb\xbf"), path)

    def test_no_personal_paths_or_secret_patterns(self):
        patterns = [r"[A-Za-z]:\\Users\\", r"/Users/[a-z]", r"/home/[a-z]", r"AKIA[0-9A-Z]{12,}", r"ghp_[A-Za-z0-9]{20,}",
                    r"github_pat_", r"BEGIN [A-Z ]*PRIVATE KEY", r"\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b"]
        for path in repo_files():
            if path.endswith(TEXT_EXT) and not path.endswith("test_repo.py"):
                text = read(path)
                for p in patterns:
                    self.assertIsNone(re.search(p, text), f"{path}: {p}")

    def test_script_has_no_network_or_dynamic_execution(self):
        import ast
        tree = ast.parse(read(SCRIPT))
        banned_modules = {"socket", "urllib", "http", "requests", "subprocess", "ctypes", "pickle", "marshal",
                          "ftplib", "smtplib", "xmlrpc", "asyncio", "multiprocessing", "importlib", "shutil"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, ("exec", "eval", "compile", "__import__"))
                elif isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, ("system", "popen", "popen2", "spawn", "startfile"))
        self.assertEqual(imported & banned_modules, set())
        self.assertLessEqual(imported, {"__future__", "argparse", "csv", "io", "json", "os", "re", "statistics", "sys", "tempfile", "time", "unicodedata"})

    def test_script_writes_only_where_asked(self):
        text = read(SCRIPT)
        self.assertEqual(len(re.findall(r"open\([^\n]*(?:\"w\"|mode)", text)), 2)  # write_text y la marca de tmp new

    def test_no_forbidden_claims_in_docs(self):
        banned = ["undetectable", "indetectable", "bypass", "evade ai detect", "humanizer", "huella de ia"]
        for path in repo_files():
            if path.endswith((".md", ".json")) and not path.endswith(("CHANGELOG.md", "CONTRIBUTING.md")):
                low = read(path).lower()
                for b in banned:
                    self.assertNotIn(b, low, f"{path}: {b}")


class Tokens(unittest.TestCase):
    def test_skill_files_are_not_bloated(self):
        for d in EXPECTED:
            size = os.path.getsize(os.path.join(ROOT, "skills", d, "SKILL.md"))
            self.assertLess(size, 12000, d)


if __name__ == "__main__":
    unittest.main()
