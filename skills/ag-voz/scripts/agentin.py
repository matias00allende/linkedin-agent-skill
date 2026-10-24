#!/usr/bin/env python3
"""AgentIn: utilidades locales de texto para las skills ag-*.

Subcomandos (solo biblioteca estándar, sin red, nada se sube a ningún servicio):

  clean   Higiene de un borrador: caracteres invisibles, tipografía y muletillas.
  check   Índice de estilo con cinco chequeos. Es una heuristica de estilo: no mide
          autoría y no predice el veredicto de ningún detector externo.
  limits  Cuenta caracteres contra los límites de LinkedIn (data/limits.json).
  stats   Métricas de interacción desde un CSV de analítica (ag-audit).

Códigos de salida: 0 correcto, 1 resultado negativo pedido (limits fuera de rango,
check bajo --fail-under), 2 error de uso o de entrada.

Ejemplos:
  python -I agentin.py clean borrador.txt --report
  python -I agentin.py check borrador.txt
  python -I agentin.py check antes.txt despues.txt
  python -I agentin.py limits --kind invite nota.txt
  python -I agentin.py stats analítica.csv --followers 4200

"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import statistics
import sys
import tempfile
import time
import unicodedata

__version__ = "1.4.0"

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


class UserError(Exception):
    """Error atribuible al uso o a la entrada; se informa sin traceback."""


# ----------------------------------------------------------------------------
# Entrada y salida
# ----------------------------------------------------------------------------

def setup_stdio() -> None:
    """Fuerza UTF-8 y saltos de linea LF en los flujos estándar (Windows usa cp1252)."""
    for stream, kwargs in ((sys.stdin, {"encoding": "utf-8"}),
                           (sys.stdout, {"encoding": "utf-8", "newline": "\n"}),
                           (sys.stderr, {"encoding": "utf-8", "newline": "\n"})):
        try:
            stream.reconfigure(**kwargs)
        except (AttributeError, ValueError, OSError):
            pass


def read_text(path: str) -> str:
    """Lee un archivo (o stdin con '-') como UTF-8 y normaliza los saltos de linea."""
    if path == "-":
        raw = sys.stdin.buffer.read()
    else:
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except FileNotFoundError:
            raise UserError(f"no existe el archivo: {path}")
        except IsADirectoryError:
            raise UserError(f"es una carpeta, no un archivo: {path}")
        except OSError as exc:
            raise UserError(f"no se pudo leer {path}: {exc.strerror or exc}")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UserError(f"{path if path != '-' else 'la entrada'} no esta en UTF-8; guardelo como UTF-8 e intente de nuevo")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def write_text(path: str, text: str, force: bool) -> None:
    mode = "w" if force else "x"
    try:
        with open(path, mode, encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except FileExistsError:
        raise UserError(f"{path} ya existe; use --force para sobrescribirlo")
    except OSError as exc:
        raise UserError(f"no se pudo escribir {path}: {exc.strerror or exc}")


def load_json(name: str, path: str | None = None) -> dict:
    target = path or os.path.join(DATA, name)
    try:
        with open(target, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise UserError(f"falta el archivo de datos: {target}")
    except json.JSONDecodeError as exc:
        raise UserError(f"JSON inválido en {target}: {exc}")


def pick_marker(text: str, start: int = 0xE000) -> str:
    """Devuelve un caracter de uso privado que no aparece en el texto."""
    for cp in range(start, start + 0x100):
        if chr(cp) not in text:
            return chr(cp)
    raise UserError("el texto usa todos los caracteres de marcado internos")


# ----------------------------------------------------------------------------
# Idioma
# ----------------------------------------------------------------------------

def resolve_lang(requested: str, text: str) -> str:
    """AgentIn trabaja solo en español; el parámetro se conserva para el léxico alternativo."""
    return "es"


# ----------------------------------------------------------------------------
# Lexico
# ----------------------------------------------------------------------------

def phrase_pattern(find: str) -> str:
    """Patron para una frase: sin letras pegadas, espacios flexibles, apostrofe recto o curvo."""
    parts = [re.escape(p) for p in find.split()]
    body = r"(?:[ \t]+|[ \t]*\n[ \t]*)".join(parts)
    body = body.replace("'", "['\u2019]")
    return r"(?<!\w)" + body + r"(?!\w)"


def load_lexicon(lang: str, path: str | None = None) -> dict:
    lex = load_json(f"lexicon_{lang}.json", path)
    for key in ("entries", "structures"):
        if not isinstance(lex.get(key), list):
            raise UserError(f"el léxico no tiene la lista '{key}'")
    entries = sorted(lex["entries"], key=lambda e: len(e["find"]), reverse=True)
    for e in entries:
        if e.get("action") not in ("replace", "delete", "flag"):
            raise UserError(f"entrada de léxico con acción inválida: {e.get('find')!r}")
        e["_rx"] = re.compile(phrase_pattern(e["find"]), re.IGNORECASE)
    lex["entries"] = entries
    for s in lex["structures"]:
        try:
            s["_rx"] = re.compile(s["regex"], re.MULTILINE)
        except re.error as exc:
            raise UserError(f"regex inválida en la estructura {s.get('id')!r}: {exc}")
    return lex


def match_case(src: str, repl: str) -> str:
    if not repl:
        return repl
    letters = [c for c in src if c.isalpha()]
    if len(letters) > 1 and all(c.isupper() for c in letters):
        return repl.upper()
    if src[:1].isupper():
        return repl[0].upper() + repl[1:]
    return repl


# ----------------------------------------------------------------------------
# Segmentacion de oraciones
# ----------------------------------------------------------------------------

_ABBREV = re.compile(
    r"\b(?:e\.g|i\.e|vs|etc|sr|sra|srta|dr|dra|ud|uds|p\. ?ej|a\.m|p\.m|n[o\u00ba\u00b0]|inc|ltd|u\.s|"
    r"aprox|av|dpto|pag|art)\.", re.IGNORECASE)


def split_sentences(text: str, min_words: int = 3) -> list[str]:
    """Divide en oraciones sin partir decimales, abreviaturas ni puntos suspensivos."""
    dot = pick_marker(text, 0xE100)
    # Decimales y separadores de miles: se protege el punto entre dígitos.
    s = re.sub(r"(?<=\d)\.(?=\d)", dot, text)
    s = _ABBREV.sub(lambda m: m.group(0)[:-1] + dot, s)
    parts = re.split(r"(?<=[.!?\u2026])\s+|\n+", s)
    out = []
    for p in parts:
        p = p.replace(dot, ".").strip()
        p = re.sub(r"^(?:[-*\u2022]|\d+[.)])\s+", "", p)
        if len(re.findall(r"\w+", p)) >= min_words:
            out.append(p)
    return out


def words_of(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+(?:['\u2019][^\W\d_]+)?", text)


# ----------------------------------------------------------------------------
# clean: higiene
# ----------------------------------------------------------------------------

HAS_RTL = re.compile(r"[\u0590-\u08ff\ufb1d-\ufdff\ufe70-\ufeff]")
EMOJI_TAG_SEQ = "\U0001F3F4[\U000E0020-\U000E007E]+\U000E007F"
INVIS_RE = re.compile(
    "(" + EMOJI_TAG_SEQ + ")"
    "|([\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\u206a-\u206f\ufeff\u00ad\u180e\u061c\u034f\ufff9-\ufffb\U000E0000-\U000E007F])"
    "|([\u00a0\u202f\u2000-\u200a\u205f\u1680])")

_INVIS_NAMES = {
    0x200B: "espacio de ancho cero", 0x200C: "separador de ancho cero", 0x200D: "unión de ancho cero",
    0x200E: "marca de izquierda a derecha", 0x200F: "marca de derecha a izquierda", 0x2060: "unión de palabras",
    0xFEFF: "marca de orden de bytes", 0x00AD: "guion blando", 0x180E: "separador vocálico mongol",
    0x061C: "marca de letra árabe", 0x034F: "unión de grafemas",
    0x00A0: "espacio duro", 0x202F: "espacio duro angosto", 0x2009: "espacio fino",
    0x2007: "espacio de cifra", 0x2003: "espacio largo", 0x2002: "espacio medio",
    0x202A: "control de dirección", 0x202B: "control de dirección", 0x202C: "control de dirección",
    0x202D: "control de dirección", 0x202E: "control de dirección (puede invertir el texto a la vista)",
    0x2066: "aislamiento de dirección", 0x2067: "aislamiento de dirección", 0x2068: "aislamiento de dirección",
    0x2069: "aislamiento de dirección",
}


def _invisible_name(ch: str) -> str:
    cp = ord(ch)
    if 0xE0000 <= cp <= 0xE007F:
        return "caracteres tag (pueden esconder texto)"
    return f"U+{cp:04X} " + _INVIS_NAMES.get(cp, "carácter de formato")


def is_emoji_like(ch: str) -> bool:
    o = ord(ch)
    return (0x1F000 <= o <= 0x1FAFF or 0x2190 <= o <= 0x21FF or 0x2300 <= o <= 0x23FF
            or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF or o == 0xFE0F or o == 0x20E3)


def pass_invisible(text: str) -> tuple[str, list[dict]]:
    """Quita caracteres invisibles. Conserva ZWJ entre emoji, ZWNJ entre letras no latinas,
    marcas de direccion en texto de derecha a izquierda y banderas de subregion (tag sequences)."""
    has_rtl = bool(HAS_RTL.search(text))
    hits: dict[str, dict] = {}

    def note(ch: str, action: str) -> None:
        key = _invisible_name(ch)
        rec = hits.setdefault(key, {"name": key, "count": 0, "action": action})
        rec["count"] += 1

    def repl(m: re.Match) -> str:
        if m.group(1):
            return m.group(1)
        ch = m.group(2) or m.group(3)
        cp = ord(ch)
        prev = m.string[m.start() - 1] if m.start() > 0 else ""
        nxt = m.string[m.end()] if m.end() < len(m.string) else ""
        if m.group(3):
            note(ch, "espacio")
            return " "
        if cp == 0x200D and prev and nxt and is_emoji_like(prev) and is_emoji_like(nxt):
            return ch
        if cp == 0x200C and prev.isalpha() and nxt.isalpha() and ord(prev) > 0x24F and ord(nxt) > 0x24F:
            return ch
        if cp in (0x200E, 0x200F, 0x061C) and has_rtl:
            return ch
        note(ch, "borrado")
        return ""

    return INVIS_RE.sub(repl, text), sorted(hits.values(), key=lambda h: -h["count"])


_PROTECT = [
    re.compile(r"```.*?```", re.DOTALL),
    re.compile(r"`[^`\n]+`"),
    re.compile(r"https?://[^\s<>]*[^\s<>.,;:!?)\]\"']|www\.[^\s<>]*[^\s<>.,;:!?)\]\"']"),
    re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    re.compile(r"(?<!\w)#\w+"),
    re.compile(r"(?<!\w)@\w[\w.]*"),
]


def protect(text: str) -> tuple[str, list[str], str]:
    marker = pick_marker(text)
    found: list[str] = []

    def stash(m: re.Match) -> str:
        found.append(m.group(0))
        return f"{marker}{len(found) - 1}{marker}"

    for rx in _PROTECT:
        text = rx.sub(stash, text)
    return text, found, marker


def restore(text: str, found: list[str], marker: str) -> str:
    return re.sub(re.escape(marker) + r"(\d+)" + re.escape(marker), lambda m: found[int(m.group(1))], text)


_QUOTES = [re.compile(r'"[^"]*"'), re.compile(r"\u00ab[^\u00bb]*\u00bb"), re.compile(r"\([^)]*\)")]


def protect_quotes(text: str) -> tuple[str, list[str], str]:
    """Aparta citas textuales y paréntesis (también de varias líneas) para que la pasada léxica no los toque."""
    marker = pick_marker(text, 0xE300)
    found: list[str] = []

    def stash(m: re.Match) -> str:
        found.append(m.group(0))
        return f"{marker}{len(found) - 1}{marker}"

    for rx in _QUOTES:
        text = rx.sub(stash, text)
    return text, found, marker


def pass_typography(text: str) -> tuple[str, list[dict]]:
    hits: list[dict] = []

    def count(name: str, n: int, to: str) -> None:
        if n:
            hits.append({"name": name, "count": n, "to": to})

    n_em = text.count("\u2014")
    if n_em:
        text = re.sub(r"(?<=\d)\u2014(?=\d)", "-", text)
        text = re.sub(r"(?m)^([ \t]*)\u2014[ \t]*", r"\1- ", text)
        text = re.sub(r"[ \t]*\u2014[ \t]*(?=[,.;:!?)\]\"'])", "", text)
        text = re.sub(r"(?m)[ \t]*\u2014[ \t]*$", ",", text)
        text = re.sub(r"[ \t]*\u2014[ \t]*", ", ", text)
        count("U+2014 raya (em dash)", n_em, "coma")
    n_en = text.count("\u2013")
    if n_en:
        text = re.sub(r"(?<=\d)[ \t]*\u2013[ \t]*(?=\d)", "-", text)
        text = re.sub(r"[ \t]+\u2013[ \t]+", ", ", text)
        text = text.replace("\u2013", "-")
        count("U+2013 semiraya (en dash)", n_en, "guion o coma")
    text = re.sub(r"(?m)^([ \t]*)\u2022[ \t]*", r"\1- ", text)
    simple = [("\u2018", "'", "comilla simple izquierda"), ("\u2019", "'", "comilla simple derecha / apostrofe"),
              ("\u201c", '"', "comilla doble izquierda"),
              ("\u201d", '"', "comilla doble derecha"), ("\u2026", "...", "puntos suspensivos (un caracter)"),
              ("\u2192", "->", "flecha"), ("\u2022", "-", "viñeta")]
    for ch, to, name in simple:
        n = text.count(ch)
        if n:
            text = text.replace(ch, to)
            count(f"U+{ord(ch):04X} {name}", n, to)
    n_dot = len(re.findall(r"(?<= )\u00b7(?= )", text))
    if n_dot:
        text = re.sub(r"(?<= )\u00b7(?= )", "-", text)
        count("U+00B7 punto medio entre espacios", n_dot, "-")
    return text, hits


def at_sentence_start(before: str) -> bool:
    b = before.rstrip(" \t")
    b = re.sub(r"[\"'(\[\u00bf\u00a1]+$", "", b)
    if not b or b[-1] in ".!?\n":
        return True
    return bool(re.search(r"(?:^|\n)[ \t]*(?:[-*]|\d+[.)])$", b))


def pass_lexical(text: str, lex: dict) -> tuple[str, dict]:
    report = {"replaced": [], "deleted": [], "flagged": []}
    mark = pick_marker(text, 0xE200)
    for e in lex["entries"]:
        action = e["action"]
        if action == "flag":
            continue
        core = phrase_pattern(e["find"])
        if action == "replace":
            n = 0

            def sub_replace(m: re.Match, e=e) -> str:
                nonlocal n
                n += 1
                return match_case(m.group(0), e["replace"])

            text = e["_rx"].sub(sub_replace, text)
            if n:
                report["replaced"].append({"find": e["find"], "replace": e["replace"], "count": n})
            continue
        post = r"(?P<post>[ \t]*[,:;]|[ \t]*[.!?]+)?" if e.get("standalone") else r"(?P<post>[ \t]*[,:;])?"
        rx = re.compile(r"(?P<pre>,[ \t]*)?" + core + post + r"(?P<tail>[ \t]*)(?P<nxt>\w)?", re.IGNORECASE)
        n = 0

        def sub_delete(m: re.Match, e=e) -> str:
            nonlocal n
            pre, post_g = m.group("pre"), m.group("post")
            tail, nxt = m.group("tail") or "", m.group("nxt") or ""
            phrase_start = m.end("pre") if pre else m.start()
            before = m.string[:phrase_start]
            # Solo se borra al comienzo de una oración, fuera de citas y paréntesis, y si el resto queda correcto.
            if pre or not at_sentence_start(before) or before.rstrip(" \t")[-1:] in ("\"", "\u201c", "\u00ab", "'", "("):
                return m.group(0)
            if e.get("standalone"):
                terminal = bool(post_g and re.search(r"[.!?]$", post_g.strip())) or e["find"].endswith("?")
                if not (terminal or (not post_g and not nxt)):
                    return m.group(0)
            elif not (post_g or e["find"].endswith(" que")):
                return m.group(0)
            n += 1
            return nxt.upper()

        text = rx.sub(sub_delete, text)
        if n:
            report["deleted"].append({"find": e["find"], "count": n})
    text = re.sub(r"[ \t]*" + re.escape(mark) + r"(?=[,.;:!?])", "", text)
    text = text.replace(mark, "")
    return text, report


def find_flags(text: str, lex: dict) -> list[dict]:
    flags = []
    for e in lex["entries"]:
        if e["action"] != "flag":
            continue
        lines = [text.count("\n", 0, m.start()) + 1 for m in e["_rx"].finditer(text)]
        if lines:
            flags.append({"find": e["find"], "count": len(lines), "lines": sorted(set(lines)),
                          "note": e.get("note", ""), "family": e.get("family", "")})
    return flags


def scan_structures(text: str, lex: dict) -> list[dict]:
    flags = []
    for s in lex["structures"]:
        lines = [text.count("\n", 0, m.start()) + 1 for m in s["_rx"].finditer(text)]
        if lines:
            flags.append({"id": s["id"], "name": s["name"], "count": len(lines),
                          "lines": sorted(set(lines)), "fix": s["fix"]})
    lens = [len(words_of(x)) for x in split_sentences(text)]
    if len(lens) >= 4:
        mean = statistics.mean(lens)
        cv = statistics.pstdev(lens) / mean if mean else 0
        if cv < 0.35:
            flags.append({"id": "uniform-length", "name": f"Oraciones de largo uniforme (variación {cv:.2f})",
                          "count": len(lens), "lines": [],
                          "fix": "Si el ritmo suena monótono, parte una oración a la mitad y deja otra más larga."})
    return flags


def clean(text: str, lang: str, lex: dict | None = None, hygiene_only: bool = False) -> tuple[str, dict]:
    """Higiene completa. Devuelve (texto, informe)."""
    text, invisible = pass_invisible(text)
    nfc = unicodedata.normalize("NFC", text)
    normalized = nfc != text
    text = nfc
    shielded, found, marker = protect(text)
    shielded, typography = pass_typography(shielded)
    lexical = {"replaced": [], "deleted": [], "flagged": []}
    if lex is not None and not hygiene_only:
        q_shield, q_found, q_marker = protect_quotes(shielded)
        q_shield, lexical = pass_lexical(q_shield, lex)
        shielded = restore(q_shield, q_found, q_marker)
    shielded = re.sub(r"[ \t]+(?=\n|$)", "", shielded)
    shielded = re.sub(r"(?<=\S)[ \t]{2,}(?=\S)", " ", shielded)
    shielded = re.sub(r"\n{3,}", "\n\n", shielded)
    text = restore(shielded, found, marker).strip()
    text = text + "\n" if text else ""
    structures: list[dict] = []
    if lex is not None:
        lexical["flagged"] = find_flags(text, lex)
        structures = scan_structures(text, lex)
    return text, {"language": lang, "invisible": invisible, "typography": typography,
                  "normalized_nfc": normalized, "lexical": lexical, "structures": structures}


def render_clean_report(report: dict, out) -> None:
    lx = report["lexical"]
    total = (sum(h["count"] for h in report["invisible"]) + sum(h["count"] for h in report["typography"])
             + sum(h["count"] for h in lx["replaced"]) + sum(h["count"] for h in lx["deleted"]))
    print(f"Cambios aplicados: {total}. Términos señalados: {len(lx['flagged'])}. "
          f"Estructuras para reescribir a mano: {len(report['structures'])}.", file=out)
    if report["invisible"]:
        print("Caracteres invisibles:", file=out)
        for h in report["invisible"]:
            print(f"  {h['count']} x {h['name']}: {h['action']}", file=out)
    if report["normalized_nfc"]:
        print("Se normalizaron tildes descompuestas.", file=out)
    if report["typography"]:
        print("Tipografía:", file=out)
        for h in report["typography"]:
            print(f"  {h['count']} x {h['name']}: {h['to']}", file=out)
    if lx["replaced"] or lx["deleted"]:
        print("Muletillas cambiadas:", file=out)
        for h in lx["replaced"]:
            print(f"  {h['count']} x {h['find']}: {h['replace']}", file=out)
        for h in lx["deleted"]:
            print(f"  {h['count']} x {h['find']}: borrada", file=out)
    if lx["flagged"]:
        print("Términos señalados (dependen del contexto, no se cambian solos):", file=out)
        for h in lx["flagged"]:
            extra = f" ({h['note']})" if h["note"] else ""
            print(f"  {h['count']} x {h['find']}, líneas {h['lines']}{extra}", file=out)
    if report["structures"]:
        print("Estructuras para reescribir a mano:", file=out)
        for h in report["structures"]:
            where = f", líneas {h['lines']}" if h["lines"] else ""
            print(f"  {h['count']} x {h['name']}{where}. {h['fix']}", file=out)
    if not (total or lx["flagged"] or report["structures"]):
        print("No había nada que cambiar.", file=out)


def cmd_clean(args: argparse.Namespace) -> int:
    text = read_text(args.input)
    lang = "es"
    lex = load_lexicon(lang, args.lexicon)
    cleaned, report = clean(text, lang, lex, hygiene_only=args.hygiene_only)
    if args.json:
        print(json.dumps({"text": cleaned, "report": report}, indent=2, ensure_ascii=False))
        return 0
    if args.out:
        write_text(args.out, cleaned, args.force)
        print(f"escrito: {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(cleaned)
    if args.report:
        render_clean_report(report, sys.stderr)
    return 0


# ----------------------------------------------------------------------------
# check: índice de estilo
# ----------------------------------------------------------------------------

CHECK_KEYS = ["rhythm", "specificity", "filler", "hygiene", "voice"]
CHECK_LABELS = {"rhythm": "Ritmo", "specificity": "Marcadores numéricos y nombres", "filler": "Muletillas",
                "hygiene": "Higiene", "voice": "Marcas de persona"}
MIN_SENTENCES, MIN_WORDS = 4, 25


def clamp(n: float) -> float:
    return max(0.0, min(100.0, n))


def scale(value: float, good: float, bad: float) -> float:
    if good == bad:
        return 50.0
    return clamp((value - bad) / (good - bad) * 100)


def check_rhythm(text: str):
    lens = [len(words_of(s)) for s in split_sentences(text)]
    if len(lens) < MIN_SENTENCES:
        return None, f"no evaluable: se necesitan {MIN_SENTENCES}+ oraciones (hay {len(lens)})"
    mean = statistics.mean(lens)
    cv = statistics.pstdev(lens) / mean if mean else 0.0
    return scale(cv, 0.70, 0.22), f"variación {cv:.2f} en {len(lens)} oraciones (referencia: más variación suele sonar menos monótono)"


def check_specificity(text: str):
    w = words_of(text)
    if len(w) < MIN_WORDS:
        return None, f"no evaluable: se necesitan {MIN_WORDS}+ palabras (hay {len(w)})"
    numbers = len(re.findall(r"\d[\d.,]*%?", text))
    proper = set()
    for s in split_sentences(text, min_words=1):
        toks = words_of(s)[1:]
        proper.update(t for t in toks if len(t) >= 3 and t[0].isupper() and t[1:].islower())
        proper.update(t for t in toks if len(t) >= 2 and t.isupper())
    hits = numbers + len(proper)
    density = hits * 100 / len(w)
    return scale(density, 6.0, 0.5), f"marcadores concretos: {hits} ({density:.1f} por 100 palabras)"


def check_filler(text: str, lex: dict):
    w = words_of(text)
    if not w:
        return None, "no evaluable: texto vacío"
    hits, found = 0, []
    for e in lex["entries"]:
        n = len(e["_rx"].findall(text))
        if n:
            hits += n
            found.append(e["find"])
    density = hits * 100 / len(w)
    detail = f"muletillas: {hits} ({density:.1f} por 100 palabras)"
    if found:
        detail += " (" + ", ".join(sorted(found)[:4]) + (", ..." if len(found) > 4 else "") + ")"
    return scale(density, 0.0, 4.0), detail


def check_hygiene(text: str):
    if not text.strip():
        return None, "no evaluable: texto vacío"
    invisible = sum(1 for m in INVIS_RE.finditer(text) if m.group(2))
    spaces = sum(1 for m in INVIS_RE.finditer(text) if m.group(3))
    em = text.count("\u2014")
    curly = sum(text.count(c) for c in "\u2018\u2019\u201c\u201d")
    ellipsis = text.count("\u2026")
    total = invisible * 4 + em * 2 + curly + ellipsis + spaces
    per1k = total * 1000 / max(len(text), 1)
    detail = (f"{invisible} invisibles, {em} rayas, {curly} comillas curvas, "
              f"{ellipsis} puntos suspensivos, {spaces} espacios duros")
    return scale(per1k, 0.0, 12.0), detail


def check_voice(text: str, lex: dict, lang: str):
    w = words_of(text)
    if len(w) < MIN_WORDS:
        return None, f"no evaluable: se necesitan {MIN_WORDS}+ palabras (hay {len(w)})"
    per100 = 100 / len(w)
    persons = set(lex.get("person_words", []))
    person_n = sum(1 for t in w if t.lower() in persons)
    for rx in lex.get("person_verb_regexes", []):
        person_n += len(re.findall(rx, text, re.IGNORECASE))
    person = person_n * per100
    tells, names = 0, []
    for s in lex["structures"]:
        n = len(s["_rx"].findall(text))
        if n:
            tells += n
            names.append(s["id"])
    bullets = [len(words_of(b)) for b in re.findall(r"(?m)^\s*[-*]\s+(.+)$", text)]
    uniform = len(bullets) >= 3 and statistics.pstdev(bullets) < 1.6
    tell_score = clamp(100 - tells * 22)
    if lex.get("contraction_regex"):
        contractions = len(re.findall(lex["contraction_regex"], text, re.IGNORECASE)) * per100
        score = (scale(contractions, 3.0, 0.0) * 0.35 + scale(person, 8.0, 1.0) * 0.35 + tell_score * 0.30)
        detail = (f"contracciones: {contractions:.1f} y marcas de persona: {person:.1f} por 100 palabras; "
                  f"estructuras señaladas: {tells}")
    else:
        score = scale(person, 8.0, 1.0) * 0.55 + tell_score * 0.45
        detail = f"marcas de persona: {person:.1f} por 100 palabras; estructuras señaladas: {tells}"
    if uniform:
        score -= 12
        names.append("viñetas-uniformes")
    if names:
        detail += " [" + ", ".join(names[:4]) + "]"
    return clamp(score), detail


def run_checks(text: str, lex: dict, lang: str) -> dict:
    results = {
        "rhythm": check_rhythm(text),
        "specificity": check_specificity(text),
        "filler": check_filler(text, lex),
        "hygiene": check_hygiene(text),
        "voice": check_voice(text, lex, lang),
    }
    scored = [v[0] for v in results.values() if v[0] is not None]
    if not scored:
        return {"checks": results, "score": None, "verdict": "SIN DATOS", "evaluable": 0}
    overall = statistics.mean(scored) * 0.6 + min(scored) * 0.4
    if overall >= 70 and min(scored) >= 55:
        verdict = "BIEN"
    elif overall >= 50:
        verdict = "REVISAR"
    else:
        verdict = "CORREGIR"
    return {"checks": results, "score": overall, "verdict": verdict, "evaluable": len(scored)}


def fmt1(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def render_check(res: dict, label: str | None, out) -> None:
    print("Índice de estilo (heurístico)" + (f": {label}" if label else ""), file=out)
    for key in CHECK_KEYS:
        score, detail = res["checks"][key]
        shown = "no evaluable" if score is None else f"{fmt1(score)} de 100"
        print(f"{CHECK_LABELS[key]}: {shown}. {detail}", file=out)
    if res["score"] is None:
        print("Índice: sin datos suficientes.", file=out)
    else:
        print(f"Índice: {fmt1(res['score'])} de 100. Veredicto: {res['verdict'].lower()}. "
              f"Cobertura: {res['evaluable']} de 5 chequeos calculables.", file=out)
        if res["verdict"] != "BIEN":
            weakest = min((k for k in CHECK_KEYS if res["checks"][k][0] is not None),
                          key=lambda k: res["checks"][k][0])
            print(f"Chequeo con menor puntaje: {CHECK_LABELS[weakest].lower()}. Es una heurística: puede reflejar el tipo de texto.", file=out)
    print("Esto mide muletillas, ritmo e higiene tipográfica. No mide autoría y no predice el "
          "veredicto de ningún detector externo. No agregues cifras ni nombres solo para subir el índice. La revisión final es suya.\n", file=out)


def cmd_check(args: argparse.Namespace) -> int:
    texts = [(p, read_text(p)) for p in [args.input] + ([args.compare] if args.compare else [])]
    payload, results = [], []
    for name, text in texts:
        lang = "es"
        lex = load_lexicon(lang, args.lexicon)
        res = run_checks(text, lex, lang)
        results.append((name, res))
        payload.append({
            "source": name, "language": lang,
            "checks": {k: {"score": None if v[0] is None else round(v[0], 1), "detail": v[1]}
                       for k, v in res["checks"].items()},
            "score": None if res["score"] is None else round(res["score"], 1),
            "verdict": res["verdict"], "evaluable": res["evaluable"],
        })
    if args.json:
        print(json.dumps(payload if args.compare else payload[0], indent=2, ensure_ascii=False))
    else:
        for name, res in results:
            render_check(res, os.path.basename(name) if args.compare else None, sys.stdout)
        if args.compare and payload[0]["score"] is not None and payload[1]["score"] is not None:
            a, b = payload
            print(f"Antes {fmt1(a['score'])} ({a['verdict'].lower()}), después {fmt1(b['score'])} "
                  f"({b['verdict'].lower()}), diferencia {fmt1(b['score'] - a['score'])}.")
    last = payload[-1]["score"]
    if args.fail_under is not None and (last is None or last < args.fail_under):
        return 1
    return 0


# ----------------------------------------------------------------------------
# limits
# ----------------------------------------------------------------------------

def utf16_len(s: str) -> int:
    return sum(2 if ord(c) > 0xFFFF else 1 for c in s)


def cmd_limits(args: argparse.Namespace) -> int:
    data = load_json("limits.json", args.limits_file)
    kinds = data["kinds"]
    if args.kind not in kinds:
        raise UserError(f"tipo desconocido {args.kind!r}; opciones: {', '.join(sorted(kinds))}")
    spec = kinds[args.kind]
    limit = spec.get("max_premium", spec["max"]) if args.premium else spec["max"]
    text = read_text(args.input)
    if text.endswith("\n"):
        text = text[:-1]
    text = unicodedata.normalize("NFC", text)
    chars, units = len(text), utf16_len(text)
    over = max(chars, units) > limit
    res = {"kind": args.kind, "label": spec["label"], "limit": limit, "characters": chars,
           "utf16_units": units, "remaining": limit - max(chars, units), "within_limit": not over,
           "limit_verified": bool(spec.get("verified", False))}
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        state = "fuera del límite" if over else "dentro del límite"
        print(f"{spec['label']}: {chars}/{limit} caracteres ({state}; quedan {res['remaining']})")
        if units != chars:
            print(f"  Contando emoji como 2 unidades: {units}/{limit}. Se usa el mayor de los dos.")
        if not res["limit_verified"]:
            print("  Límite reportado, no verificado contra LinkedIn: confírmelo en la interfaz.")
    return 1 if over else 0


# ----------------------------------------------------------------------------
# stats
# ----------------------------------------------------------------------------

_ALIASES = {
    "impressions": {"impressions", "impresiones", "impresionesdelpost"},
    "reactions": {"reactions", "reacciones", "likes", "megusta", "reaccionestotales"},
    "comments": {"comments", "comentarios"},
    "reposts": {"reposts", "shares", "compartidos", "republicaciones", "recompartidos", "veces compartido"},
    "saves": {"saves", "guardados", "guardadas"},
    "sends": {"sends", "envios", "enviados"},
    "date": {"date", "fecha", "fechadepublicacion", "publishdate", "createdat", "fechapublicacion"},
    "text": {"text", "texto", "post", "title", "titulo", "content", "contenido", "publicación"},
    "hook": {"hook", "fórmula", "gancho", "formulagancho"},
}


def _norm_header(h: str) -> str:
    h = unicodedata.normalize("NFD", h.lower())
    h = "".join(c for c in h if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", h)


COMPONENT_NAMES = {"reactions": "reacciones", "comments": "comentarios", "reposts": "republicaciones"}


def parse_count(value: str, column: str, row: int, problems: list) -> int | None:
    """Entero no negativo. Vacío es dato ausente; todo lo ambiguo se informa y se trata como ausente."""
    v = (value or "").strip()
    if v == "":
        return None
    if re.fullmatch(r"\d+", v):
        return int(v)
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", v):
        return int(re.sub(r"[.,]", "", v))
    problems.append(f"fila {row}, columna {column}: valor no válido {v!r}; se trata como dato ausente")
    return None


def parse_analytics(text: str) -> tuple[list[dict], list[str]]:
    if not text.strip():
        raise UserError("el CSV esta vacío")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    header = rows[0]
    index: dict[str, int] = {}
    for i, h in enumerate(header):
        norm = _norm_header(h)
        for key, names in _ALIASES.items():
            if norm in {_norm_header(n) for n in names} and key not in index:
                index[key] = i
    ambiguous = [h for h in header if _norm_header(h) in ("views", "vistas", "visualizaciones")]
    if "impressions" not in index and ambiguous:
        raise UserError(f"la columna {ambiguous[0]!r} puede medir otra cosa (por ejemplo reproducciones de video). "
                        "Confirme que mide impresiones y renómbrela a 'impresiones' antes de calcular.")
    if "impressions" not in index or not ({"reactions", "comments"} & set(index)):
        raise UserError("el CSV necesita al menos una columna de impresiones y otra de reacciones o comentarios. "
                        f"Columnas encontradas: {', '.join(header)}")
    out, warnings = [], []
    for n, row in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in row):
            continue

        def get(key: str) -> str:
            i = index.get(key)
            return row[i].strip() if i is not None and i < len(row) else ""

        imp = parse_count(get("impressions"), "impresiones", n, warnings)
        if not imp:
            warnings.append(f"fila {n}: sin impresiones válidas; omitida")
            continue
        rec = {"row": n, "impressions": imp, "text": get("text")[:80], "date": get("date"), "hook": get("hook")}
        for key in ("reactions", "comments", "reposts", "saves", "sends"):
            rec[key] = parse_count(get(key), key, n, warnings) if key in index else None
        out.append(rec)
    if not out:
        raise UserError("ninguna fila tenía impresiones válidas")
    return out, warnings


def compute_stats(rows: list[dict], followers: int | None, top: int) -> dict:
    for r in rows:
        known = tuple(k for k in ("reactions", "comments", "reposts") if r.get(k) is not None)
        r["coverage"] = known
        r["engagement_rate"] = (sum(r[k] for k in known) / r["impressions"]) if known else None
        r["comment_ratio"] = (r["comments"] / r["reactions"]) if (r.get("reactions") and r.get("comments") is not None) else None
        sv = [r[k] for k in ("saves", "sends") if r.get(k) is not None]
        r["save_send_rate"] = (sum(sv) / r["impressions"]) if sv else None
        r["reach_multiple"] = (r["impressions"] / followers) if followers else None
    counts: dict[tuple, int] = {}
    for r in rows:
        if r["coverage"]:
            counts[r["coverage"]] = counts.get(r["coverage"], 0) + 1
    if not counts:
        raise UserError("ninguna fila tiene reacciones, comentarios ni republicaciones conocidas")
    main_cov = max(counts, key=lambda c: (counts[c], len(c)))
    comparable = [r for r in rows if r["coverage"] == main_cov]
    excluded = len(rows) - len(comparable)
    ranked = sorted(comparable, key=lambda r: r["engagement_rate"], reverse=True)
    groups: dict[str, list[float]] = {}
    for r in comparable:
        if r["hook"]:
            groups.setdefault(r["hook"], []).append(r["engagement_rate"])
    by_hook = sorted(({"hook": k, "n": len(v), "mean_engagement_rate": statistics.mean(v)} for k, v in groups.items()),
                     key=lambda g: g["mean_engagement_rate"], reverse=True)
    n = len(comparable)
    note = None
    if n < 10:
        note = f"Con {n} publicaciones comparables no hay muestra para concluir patrones; trate lo siguiente como descripción, no como hallazgo."
    return {"n": n, "followers": followers, "coverage": [COMPONENT_NAMES[k] for k in main_cov],
            "complete_rate": len(main_cov) == 3, "excluded_rows": excluded,
            "mean_engagement_rate": statistics.mean(r["engagement_rate"] for r in comparable),
            "median_engagement_rate": statistics.median(r["engagement_rate"] for r in comparable),
            "top": ranked[:top], "bottom": ranked[-top:][::-1] if n > top else [], "by_hook": by_hook,
            "sample_note": note}


def cmd_stats(args: argparse.Namespace) -> int:
    rows, warnings = parse_analytics(read_text(args.input))
    stats = compute_stats(rows, args.followers, args.top)
    stats["warnings"] = warnings
    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return 0

    def pct(x: float) -> str:
        return f"{x * 100:.1f}".replace(".", ",") + " %"

    def line(r: dict) -> str:
        reach = f", {r['reach_multiple']:.2f}".replace(".", ",") + " impresiones por seguidor" if r["reach_multiple"] is not None else ""
        cr = f"{r['comment_ratio']:.2f}".replace(".", ",") if r["comment_ratio"] is not None else "no calculable"
        imp = f"{r['impressions']:,}".replace(",", ".")
        return (f"  {pct(r['engagement_rate'])}, {imp} impresiones, comentarios por reacción {cr}{reach}. "
                f"{r['date']} {r['text']}".rstrip())

    cov = ", ".join(stats["coverage"])
    label = "Tasa de interacción" if stats["complete_rate"] else "Tasa parcial de interacción (falta algún componente)"
    print(f"{label}, calculada con: {cov}.")
    if stats["excluded_rows"]:
        print(f"Aviso: {stats['excluded_rows']} publicaciones tienen otra cobertura de datos y no se comparan con las demás.")
    print(f"Publicaciones: {stats['n']}. Interacción media {pct(stats['mean_engagement_rate'])}, "
          f"mediana {pct(stats['median_engagement_rate'])}.")
    if stats["sample_note"]:
        print(f"Aviso: {stats['sample_note']}")
    print("Mejores por tasa de interacción (componentes conocidos, sobre impresiones):")
    for r in stats["top"]:
        print(line(r))
    if stats["bottom"]:
        print("Más bajas:")
        for r in stats["bottom"]:
            print(line(r))
    if stats["by_hook"]:
        print("Por fórmula de gancho:")
        for g in stats["by_hook"]:
            print(f"  {pct(g['mean_engagement_rate'])}, {g['n']} publicaciones, fórmula {g['hook']}")
    for w in warnings:
        print(f"Aviso: {w}", file=sys.stderr)
    return 0


# ----------------------------------------------------------------------------
# tmp: carpetas temporales únicas y borrado comprobado
# ----------------------------------------------------------------------------

TMP_MARKER = ".agentin-tmp"


def tmp_root() -> str:
    base = os.environ.get("AGENTIN_HOME") or os.path.join(os.path.expanduser("~"), ".claude", "agentin")
    return os.path.join(base, "tmp")


def remove_tree(path: str) -> None:
    for dp, dn, fn in os.walk(path, topdown=False, followlinks=False):
        for f in fn:
            try:
                os.remove(os.path.join(dp, f))
            except OSError:
                pass
        for d in dn:
            full = os.path.join(dp, d)
            try:
                os.remove(full) if os.path.islink(full) else os.rmdir(full)
            except OSError:
                pass
    try:
        os.rmdir(path)
    except OSError:
        pass


def cmd_tmp(args: argparse.Namespace) -> int:
    root = tmp_root()
    if args.action == "new":
        os.makedirs(root, exist_ok=True)
        path = tempfile.mkdtemp(prefix=time.strftime("%Y%m%d-%H%M%S-"), dir=root)
        with open(os.path.join(path, TMP_MARKER), "w", encoding="utf-8") as fh:
            fh.write("agentin\n")
        print(path)
        return 0
    if not args.path:
        raise UserError("falta la ruta de la carpeta temporal que se debe borrar")
    real = os.path.realpath(args.path)
    if os.path.dirname(real) != os.path.realpath(root):
        raise UserError(f"solo se borran carpetas creadas con 'tmp new' directamente dentro de {root}")
    if not os.path.isfile(os.path.join(real, TMP_MARKER)):
        raise UserError("esa carpeta no tiene la marca de tmp new; no se borra")
    remove_tree(real)
    if os.path.exists(real):
        print(f"no se pudo borrar completamente: {real}. Puede eliminar a mano solo esa carpeta.", file=sys.stderr)
        return 1
    print("carpeta temporal borrada y comprobada")
    return 0


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

HELP_ES = """AgentIn: utilidades locales de texto. Uso:
  python -I agentin.py clean [ARCHIVO] [-o SALIDA] [--force] [--report] [--json] [--hygiene-only] [--lexicon RUTA]
      Limpia un borrador: caracteres invisibles, tipografía y muletillas. Sin ARCHIVO o con - lee la entrada estándar.
  python -I agentin.py check [ARCHIVO] [SEGUNDO_ARCHIVO] [--json] [--lexicon RUTA] [--fail-under N]
      Índice de estilo heurístico. Con dos archivos muestra antes y después. No es un detector de IA.
  python -I agentin.py limits --kind TIPO [ARCHIVO] [--premium] [--json] [--limits-file RUTA]
      Cuenta caracteres contra los límites de LinkedIn. TIPO: invite, post, headline, about o comment.
  python -I agentin.py stats ARCHIVO.csv [--followers N] [--top N] [--json]
      Métricas de interacción desde un CSV de analítica.
  python -I agentin.py tmp new
      Crea una carpeta temporal única y la imprime. Con "tmp clean RUTA" borra una carpeta marcada por tmp new dentro de la raíz temporal y comprueba que ya no existe.
Códigos de salida: 0 correcto, 1 resultado negativo pedido, 2 error de uso o de entrada.
Opciones generales: -h o --help muestra esta ayuda; --version muestra la versión."""


class EsParser(argparse.ArgumentParser):
    def error(self, message):
        raise UserError("uso incorrecto de los argumentos. Use -h para ver la ayuda.")


def build_parser() -> argparse.ArgumentParser:
    ap = EsParser(prog="agentin.py", add_help=False)
    ap.add_argument("--version", action="version", version=f"agentin {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("clean", add_help=False)
    c.add_argument("input", nargs="?", default="-")
    c.add_argument("-o", "--out")
    c.add_argument("--force", action="store_true")
    c.add_argument("--report", action="store_true")
    c.add_argument("--json", action="store_true")
    c.add_argument("--hygiene-only", action="store_true")
    c.add_argument("--lexicon")
    c.set_defaults(fn=cmd_clean)

    k = sub.add_parser("check", add_help=False)
    k.add_argument("input", nargs="?", default="-")
    k.add_argument("compare", nargs="?")
    k.add_argument("--json", action="store_true")
    k.add_argument("--lexicon")
    k.add_argument("--fail-under", type=float)
    k.set_defaults(fn=cmd_check)

    li = sub.add_parser("limits", add_help=False)
    li.add_argument("--kind", required=True)
    li.add_argument("input", nargs="?", default="-")
    li.add_argument("--premium", action="store_true")
    li.add_argument("--json", action="store_true")
    li.add_argument("--limits-file")
    li.set_defaults(fn=cmd_limits)

    tm = sub.add_parser("tmp", add_help=False)
    tm.add_argument("action", choices=["new", "clean"])
    tm.add_argument("path", nargs="?")
    tm.set_defaults(fn=cmd_tmp)

    st = sub.add_parser("stats", add_help=False)
    st.add_argument("input")
    st.add_argument("--followers", type=int)
    st.add_argument("--top", type=int, default=5)
    st.add_argument("--json", action="store_true")
    st.set_defaults(fn=cmd_stats)
    return ap


def main(argv: list[str] | None = None) -> int:
    setup_stdio()
    argv = sys.argv[1:] if argv is None else argv
    if any(a in ("-h", "--help") for a in argv):
        print(HELP_ES)
        return 0
    try:
        args = build_parser().parse_args(argv)
        return args.fn(args)
    except UserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
