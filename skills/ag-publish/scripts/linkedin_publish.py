#!/usr/bin/env python3
"""AgentIn: publica en LinkedIn con la API oficial, solo con aprobación explícita.

Solo biblioteca estándar. Habla únicamente con www.linkedin.com y api.linkedin.com.
No comenta, no reacciona, no envía mensajes ni invitaciones, no programa y no repite.

Subcomandos:

  auth-start   Imprime la dirección de autorización de LinkedIn.
  auth-finish  Recibe la dirección a la que LinkedIn redirigió y guarda la sesión.
  status       Muestra si hay sesión y cuándo vence (no usa la red).
  post         Vista previa de una publicación; publica solo con --confirm HASH.
  logout       Borra la sesión guardada.

Variables de entorno (nunca se guardan en archivos de este programa):
  LINKEDIN_CLIENT_ID       identificador de tu app de LinkedIn
  LINKEDIN_CLIENT_SECRET   secreto de tu app (solo auth-finish)
  LINKEDIN_REDIRECT_URI    dirección https registrada en tu app
  AGENTIN_HOME             carpeta de la sesión (por defecto ~/.agentin)

Códigos de salida: 0 correcto, 2 error de uso o de la API.

Ejemplos:
  python -I linkedin_publish.py auth-start
  python -I linkedin_publish.py auth-finish "https://tu-dominio/callback?code=...&state=..."
  python -I linkedin_publish.py post texto.txt --visibility CONNECTIONS
  python -I linkedin_publish.py post texto.txt --visibility CONNECTIONS --confirm 1a2b3c4d5e6f
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import unicodedata
import urllib.parse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

__version__ = "1.0.0"

HERE = os.path.dirname(os.path.abspath(__file__))
LIMITS_FILE = os.path.join(os.path.dirname(os.path.dirname(HERE)), "ag-voz", "data", "limits.json")

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
POSTS_URL = "https://api.linkedin.com/v2/ugcPosts"
ALLOWED_HOSTS = ("www.linkedin.com", "api.linkedin.com")
SCOPE = "openid profile w_member_social"

STATE_MAX_AGE = 30 * 60
MAX_POSTS_PER_DAY = 3
DEFAULT_POST_MAX = 3000
# Caracteres que suelen delatar texto pegado sin limpiar: invisibles y rayas largas.
SUSPECT = {"\u200b": "espacio de ancho cero", "\u200c": "unión de ancho cero",
           "\u2060": "unión de palabras", "\ufeff": "marca de orden de bytes",
           "\u2014": "raya larga", "\u2013": "semiraya"}


class UserError(Exception):
    """Error atribuible al uso o a la API; se informa sin traceback."""


def setup_stdio() -> None:
    for stream, kwargs in ((sys.stdout, {"encoding": "utf-8", "newline": "\n"}),
                           (sys.stderr, {"encoding": "utf-8", "newline": "\n"})):
        try:
            stream.reconfigure(**kwargs)
        except (AttributeError, ValueError, OSError):
            pass


# ----------------------------------------------------------------------------
# Archivos de sesión (permisos restrictivos)
# ----------------------------------------------------------------------------

def home_dir() -> str:
    path = os.environ.get("AGENTIN_HOME") or os.path.join(os.path.expanduser("~"), ".agentin")
    os.makedirs(path, mode=0o700, exist_ok=True)
    return path


def private_write(path: str, data: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # en Windows los permisos dependen de la carpeta de usuario


def private_read(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        raise UserError(f"el archivo {path} está dañado; bórralo y repite el paso")
    return data if isinstance(data, dict) else None


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise UserError(f"falta la variable de entorno {name}")
    return value


def redirect_uri() -> str:
    uri = env("LINKEDIN_REDIRECT_URI")
    if not uri.startswith("https://"):
        raise UserError("LINKEDIN_REDIRECT_URI debe empezar con https://")
    return uri


# ----------------------------------------------------------------------------
# Red
# ----------------------------------------------------------------------------

def call(method: str, url: str, headers=None, body=None, form=None):
    """Una llamada HTTPS a LinkedIn. Devuelve (estado, cabeceras, json)."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise UserError(f"destino no permitido: {parts.hostname}")
    data = None
    hdrs = dict(headers or {})
    if form is not None:
        data = urllib.parse.urlencode(form).encode("ascii")
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=hdrs, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
            payload = json.loads(raw.decode("utf-8")) if raw.strip() else {}
            return resp.status, resp.headers, payload
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300].replace("\n", " ")
        raise UserError(f"LinkedIn respondió {exc.code}: {detail}")
    except URLError as exc:
        raise UserError(f"no se pudo conectar con LinkedIn: {exc.reason}")
    except ValueError:
        raise UserError("LinkedIn devolvió una respuesta que no es JSON")


# ----------------------------------------------------------------------------
# Autorización
# ----------------------------------------------------------------------------

def cmd_auth_start(args) -> int:
    client_id = env("LINKEDIN_CLIENT_ID")
    uri = redirect_uri()
    state = secrets.token_urlsafe(24)
    private_write(os.path.join(home_dir(), "auth_state.json"), {"state": state, "created": int(time.time())})
    query = urllib.parse.urlencode({"response_type": "code", "client_id": client_id, "redirect_uri": uri,
                                    "state": state, "scope": SCOPE}, quote_via=urllib.parse.quote)
    print("Abre esta dirección en tu navegador e inicia sesión en LinkedIn:")
    print()
    print(f"{AUTH_URL}?{query}")
    print()
    print("Al aceptar, LinkedIn te redirige a tu dirección de retorno. La página puede no cargar; no importa.")
    print("Copia la dirección completa de la barra del navegador y ejecuta auth-finish con ella entre comillas.")
    print("Tienes 30 minutos.")
    return 0


def cmd_auth_finish(args) -> int:
    saved = private_read(os.path.join(home_dir(), "auth_state.json"))
    if not saved or "state" not in saved:
        raise UserError("no hay una autorización en curso; ejecuta auth-start primero")
    if time.time() - int(saved.get("created", 0)) > STATE_MAX_AGE:
        raise UserError("la autorización venció; ejecuta auth-start otra vez")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(args.redirect_url).query)
    if "error" in query:
        raise UserError(f"LinkedIn informó: {query['error'][0]} ({query.get('error_description', [''])[0]})")
    got_state = (query.get("state") or [""])[0]
    if not hmac.compare_digest(got_state.encode("utf-8"), str(saved["state"]).encode("utf-8")):
        raise UserError("el valor state no coincide; no se usa el código (posible intento ajeno)")
    code = (query.get("code") or [""])[0]
    if not code:
        raise UserError("la dirección no trae el parámetro code")
    _, _, tok = call("POST", TOKEN_URL, form={
        "grant_type": "authorization_code", "code": code, "client_id": env("LINKEDIN_CLIENT_ID"),
        "client_secret": env("LINKEDIN_CLIENT_SECRET"), "redirect_uri": redirect_uri()})
    access = tok.get("access_token")
    if not access:
        raise UserError("LinkedIn no entregó access_token")
    _, _, info = call("GET", USERINFO_URL, headers={"Authorization": f"Bearer {access}"})
    sub = info.get("sub")
    if not sub:
        raise UserError("no se pudo obtener el identificador del miembro (¿falta el producto OpenID Connect?)")
    expires = int(time.time()) + int(tok.get("expires_in", 0))
    private_write(os.path.join(home_dir(), "token.json"), {
        "access_token": access, "expires_at": expires, "person_urn": f"urn:li:person:{sub}",
        "scope": tok.get("scope", "")})
    try:
        os.remove(os.path.join(home_dir(), "auth_state.json"))
    except OSError:
        pass
    print(f"Sesión guardada para {info.get('name', 'la cuenta conectada')}.")
    print(f"Vence el {time.strftime('%Y-%m-%d', time.localtime(expires))}. Después hay que repetir la autorización.")
    return 0


def load_session() -> dict:
    tok = private_read(os.path.join(home_dir(), "token.json"))
    if not tok or "access_token" not in tok:
        raise UserError("no hay sesión de LinkedIn; ejecuta auth-start y auth-finish")
    if time.time() >= int(tok.get("expires_at", 0)):
        raise UserError("la sesión de LinkedIn venció; repite auth-start y auth-finish")
    return tok


def cmd_status(args) -> int:
    tok = private_read(os.path.join(home_dir(), "token.json"))
    if not tok:
        print("Sin sesión.")
        return 0
    left = int(tok.get("expires_at", 0)) - int(time.time())
    if left <= 0:
        print("Sesión vencida.")
    else:
        print(f"Sesión activa para {tok.get('person_urn')}. Quedan {left // 86400} días.")
    return 0


def cmd_logout(args) -> int:
    for name in ("token.json", "auth_state.json"):
        try:
            os.remove(os.path.join(home_dir(), name))
        except FileNotFoundError:
            pass
    print("Sesión borrada de este equipo. Para revocar el acceso también en LinkedIn, hazlo en su configuración de permisos.")
    return 0


# ----------------------------------------------------------------------------
# Publicación
# ----------------------------------------------------------------------------

def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


def text_hash(text: str, link: str = "", visibility: str = "") -> str:
    """Huella de lo que se aprueba: texto, enlace y visibilidad."""
    blob = "\n".join((normalize(text), link, visibility)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


def post_limit() -> int:
    try:
        with open(LIMITS_FILE, encoding="utf-8") as fh:
            return int(json.load(fh)["kinds"]["post"]["max"])
    except (OSError, ValueError, KeyError, TypeError):
        return DEFAULT_POST_MAX


def read_post(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise UserError(f"no se pudo leer {path}: {exc.strerror or exc}")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UserError(f"{path} no está en UTF-8")


def load_log() -> list:
    data = private_read(os.path.join(home_dir(), "publicaciones.json")) or {}
    items = data.get("items", [])
    return items if isinstance(items, list) else []


def cmd_post(args) -> int:
    session = load_session()
    text = normalize(read_post(args.file))
    if not text:
        raise UserError("el texto está vacío")
    limit = post_limit()
    if len(text) > limit:
        raise UserError(f"el texto tiene {len(text)} caracteres y el límite configurado es {limit}")
    link = args.link or ""
    if link and not link.startswith("https://"):
        raise UserError("--link debe empezar con https://")
    digest = text_hash(text, link, args.visibility)

    log = load_log()
    now = int(time.time())
    if any(i.get("hash") == digest for i in log):
        raise UserError("este mismo texto ya se publicó con este programa; no se publica dos veces")
    recent = [i for i in log if now - int(i.get("ts", 0)) < 86400]
    if len(recent) >= MAX_POSTS_PER_DAY:
        raise UserError(f"ya hay {len(recent)} publicaciones en las últimas 24 horas; el tope es {MAX_POSTS_PER_DAY}")

    print(f"Caracteres: {len(text)} de {limit}. Visibilidad: {args.visibility}." + (f" Enlace: {link}" if link else ""))
    found = [f"{n} ({SUSPECT[c]})" for c, n in ((c, text.count(c)) for c in SUSPECT) if n]
    if found:
        print("Aviso: el texto trae " + ", ".join(found) + ". Conviene pasarlo por ag-voz antes de publicar.")
    print("Texto exacto que se publicaría:")
    print()
    print(text)
    print()
    if not args.confirm:
        print(f"Vista previa. No se publicó nada. Huella de aprobación: {digest}")
        print("Para publicar este texto, la persona debe aprobarlo y se ejecuta de nuevo con --confirm " + digest)
        return 0
    if not hmac.compare_digest(args.confirm.encode("utf-8"), digest.encode("utf-8")):
        raise UserError("la aprobación no coincide con el texto, el enlace o la visibilidad actuales; no se publicó")

    content = {"shareCommentary": {"text": text}, "shareMediaCategory": "NONE"}
    if link:
        content["shareMediaCategory"] = "ARTICLE"
        content["media"] = [{"status": "READY", "originalUrl": link}]
    body = {"author": session["person_urn"], "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": content},
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": args.visibility}}
    status, headers, _ = call("POST", POSTS_URL, body=body, headers={
        "Authorization": f"Bearer {session['access_token']}", "X-Restli-Protocol-Version": "2.0.0"})
    post_id = headers.get("X-RestLi-Id", "") if headers is not None else ""
    log.append({"hash": digest, "ts": now, "id": post_id})
    private_write(os.path.join(home_dir(), "publicaciones.json"), {"items": log[-200:]})
    print(f"Publicado (estado {status}). Identificador: {post_id or 'no informado'}")
    return 0


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

class EsParser(argparse.ArgumentParser):
    def error(self, message):
        raise UserError(message)


def build_parser() -> argparse.ArgumentParser:
    p = EsParser(prog="linkedin_publish.py", add_help=True, description="Publica en LinkedIn con aprobación explícita.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth-start").set_defaults(func=cmd_auth_start)
    f = sub.add_parser("auth-finish")
    f.add_argument("redirect_url")
    f.set_defaults(func=cmd_auth_finish)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("logout").set_defaults(func=cmd_logout)
    q = sub.add_parser("post")
    q.add_argument("file")
    q.add_argument("--visibility", required=True, choices=("PUBLIC", "CONNECTIONS"))
    q.add_argument("--link")
    q.add_argument("--confirm")
    q.set_defaults(func=cmd_post)
    return p


def main(argv=None) -> int:
    setup_stdio()
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except UserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
