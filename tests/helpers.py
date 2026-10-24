"""Utilidades comunes de las pruebas: carga agentin.py por ruta y define rutas del repo."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "skills", "ag-voz", "scripts", "agentin.py")
DATA = os.path.join(ROOT, "skills", "ag-voz", "data")


def load_agentin():
    spec = importlib.util.spec_from_file_location("agentin", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agentin = load_agentin()
LEX = {"en": agentin.load_lexicon("en"), "es": agentin.load_lexicon("es")}


def clean_text(text, lang=None, **kwargs):
    lang = lang or agentin.detect_language(text)
    return agentin.clean(text, lang, LEX[lang], **kwargs)
