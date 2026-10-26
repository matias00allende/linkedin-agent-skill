#!/usr/bin/env python3
"""AgentIn: publica en LinkedIn con la API oficial, solo con aprobación explícita.

Es publicación asistida: una pieza a la vez, que la persona aprobó tras ver la vista previa y
que confirma escribiendo la huella en su propia terminal.
Solo biblioteca estándar. Habla únicamente con www.linkedin.com y api.linkedin.com.
No comenta, no reacciona, no envía mensajes ni invitaciones, no programa y no repite.

Subcomandos:

  auth-start   Imprime la dirección de autorización de LinkedIn.
  auth-finish  Recibe la dirección a la que LinkedIn redirigió y guarda la sesión.
  status       Muestra si hay sesión y cuándo vence (no usa la red).
  post         Vista previa de una publicación; publica solo con --confirm HUELLA.
  delete       Borra una publicación hecha con este programa (pide --yes).
  logout       Borra la sesión guardada.

Variables de entorno (nunca se guardan en archivos de este programa):
  LINKEDIN_CLIENT_ID       identificador de tu app de LinkedIn
  LINKEDIN_CLIENT_SECRET   secreto de tu app (solo auth-finish)
  LINKEDIN_REDIRECT_URI    dirección https registrada en tu app
  LINKEDIN_API_VERSION     versión de la API en formato AAAAMM (por defecto la de DEFAULT_API_VERSION)
  AGENTIN_HOME             carpeta de la sesión (por defecto ~/.agentin)

Códigos de salida: 0 correcto, 2 error de uso o de la API.

Ejemplos:
  python -I linkedin_publish.py auth-start
  python -I linkedin_publish.py auth-finish "https://tu-dominio/callback?code=...&state=..."
  python -I linkedin_publish.py post texto.txt --visibility CONNECTIONS
  python -I linkedin_publish.py post texto.txt --visibility CONNECTIONS --confirm 1a2b3c4d5e6f
  python -I linkedin_publish.py delete urn:li:share:123 --yes
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
import unicodedata
import urllib.parse
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

__version__ = "1.2.0"

HERE = os.path.dirname(os.path.abspath(__file__))
LIMITS_FILE = os.path.join(os.path.dirname(os.path.dirname(HERE)), "ag-voz", "data", "limits.json")

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
POSTS_URL = "https://api.linkedin.com/rest/posts"
UGC_URL = "https://api.linkedin.com/v2/ugcPosts"
FEED_URL = "https://www.linkedin.com/feed/update/"
ALLOWED_HOSTS = ("www.linkedin.com", "api.linkedin.com")
SCOPE = "openid profile w_member_social"

# LinkedIn mantiene cada versión al menos un año y exige indicarla en cada llamada.
# Revisar este valor una vez al año (o fijar LINKEDIN_API_VERSION).
DEFAULT_API_VERSION = "202610"

STATE_MAX_AGE = 30 * 60
PREVIEW_MAX_AGE = 24 * 3600
MAX_POSTS_PER_DAY = 3
DEFAULT_POST_MAX = 3000
# Caracteres que suelen delatar texto pegado sin limpiar: invisibles y rayas largas.
SUSPECT = {"\u200b": "espacio de ancho cero", "\u200c": "unión de ancho cero",
           "\u2060": "unión de palabras", "\ufeff": "marca de orden de bytes",
           "\u2014": "raya larga", "\u2013": "semiraya"}
# Caracteres reservados del formato de texto de la Posts API: se escapan con barra invertida.
LITTLE_RESERVED = set("|{}@[]()<>#\\*_~")
HASHTAG_RE = re.compile(r"(?<![\w#/])#([^\W\d_][\w]*)")
URN_RE = re.compile(r"urn:li:(share|ugcPost):\d+")
PERSON_RE = re.compile(r"urn:li:person:[A-Za-z0-9_-]{1,64}")
# Controles de terminal y de dirección del texto: pueden hacer que lo que se ve no sea lo que se envía.
BAD_CHARS = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]")
LOCK_STALE = 120


class UserError(Exception):
    """Error atribuible al uso o a la API; se informa sin traceback."""


class Rejected(UserError):
    """LinkedIn respondió con un error: la operación no se hizo."""


class Uncertain(UserError):
    """No se sabe si LinkedIn recibió la operación (corte de red, respuesta ilegible)."""


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
    if os.path.islink(path):
        raise UserError(f"{path} es un enlace simbólico; no se guarda la sesión ahí")
    os.makedirs(path, mode=0o700, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass  # en Windows los permisos dependen de la carpeta de usuario
    return path


def private_write(path: str, data: dict) -> None:
    """Escritura atómica: archivo temporal privado y reemplazo. No sigue enlaces simbólicos."""
    if os.path.islink(path):
        raise UserError(f"{path} es un enlace simbólico; bórralo y repite el paso")
    tmp = f"{path}.{os.getpid()}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp)
        raise


@contextlib.contextmanager
def locked():
    """Bloqueo entre procesos para leer, reservar y registrar sin que dos ejecuciones se pisen."""
    path = os.path.join(home_dir(), "lock")
    for _ in range(50):
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(path) > LOCK_STALE:
                    os.remove(path)
                    continue
            except OSError:
                pass
            time.sleep(0.1)
    else:
        raise UserError("otra ejecución está publicando; espera unos segundos y repite")
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            os.remove(path)


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


def api_version() -> str:
    version = os.environ.get("LINKEDIN_API_VERSION", "").strip() or DEFAULT_API_VERSION
    if not re.fullmatch(r"20\d{2}(0[1-9]|1[0-2])", version):
        raise UserError("LINKEDIN_API_VERSION debe tener el formato AAAAMM, por ejemplo 202610")
    return version


# ----------------------------------------------------------------------------
# Red
# ----------------------------------------------------------------------------

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise UserError(f"LinkedIn intentó redirigir la solicitud ({code}); no se sigue para no enviar credenciales a otro destino")


_OPENER = build_opener(_NoRedirect)


def urlopen(req, timeout=30):
    return _OPENER.open(req, timeout=timeout)


def clean(text, limit: int = 160) -> str:
    return BAD_CHARS.sub("?", str(text)).replace("\n", " ")[:limit]


def call(method: str, url: str, headers=None, body=None, form=None):
    """Una llamada HTTPS a LinkedIn. Devuelve (estado, cabeceras, json)."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS \
            or parts.username or parts.password or parts.port not in (None, 443):
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
        try:
            info = json.loads(exc.read().decode("utf-8", "replace"))
            detail = clean(info.get("message") or info.get("error_description") or "", 120) if isinstance(info, dict) else ""
        except ValueError:
            detail = ""
        raise Rejected(f"LinkedIn respondió {exc.code}" + (f": {detail}" if detail else ""))
    except URLError as exc:
        raise Uncertain(f"no se pudo conectar con LinkedIn: {clean(exc.reason)}")
    except (ValueError, OSError):
        raise Uncertain("la respuesta de LinkedIn no se pudo leer")


# ----------------------------------------------------------------------------
# Autorización
# ----------------------------------------------------------------------------

def cmd_auth_start(args) -> int:
    client_id = env("LINKEDIN_CLIENT_ID")
    uri = redirect_uri()
    state = secrets.token_urlsafe(24)
    private_write(os.path.join(home_dir(), "auth_state.json"), {"state": state, "created": int(time.time()),
                                                                 "client_id": client_id, "redirect_uri": uri})
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
    if saved.get("client_id") != env("LINKEDIN_CLIENT_ID") or saved.get("redirect_uri") != redirect_uri():
        raise UserError("la app o la dirección de retorno cambiaron desde auth-start; repite auth-start")
    parts = urllib.parse.urlsplit(args.redirect_url)
    if args.redirect_url.split("?", 1)[0] != redirect_uri():
        raise UserError("la dirección recibida no corresponde a LINKEDIN_REDIRECT_URI")
    query = urllib.parse.parse_qs(parts.query)
    if any(len(v) > 1 for v in query.values()):
        raise UserError("la dirección trae parámetros repetidos; no se usa")
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
    if not isinstance(sub, str) or not PERSON_RE.fullmatch(f"urn:li:person:{sub}"):
        raise UserError("no se pudo obtener el identificador del miembro (¿falta el producto OpenID Connect?)")
    try:
        expires = int(time.time()) + int(tok.get("expires_in", 0))
    except (TypeError, ValueError):
        raise UserError("LinkedIn no informó cuánto dura la sesión")
    private_write(os.path.join(home_dir(), "token.json"), {
        "access_token": access, "expires_at": expires, "person_urn": f"urn:li:person:{sub}",
        "scope": tok.get("scope", "")})
    try:
        os.remove(os.path.join(home_dir(), "auth_state.json"))
    except OSError:
        pass
    print(f"Sesión guardada para {clean(info.get('name', 'la cuenta conectada'), 80)}.")
    print(f"Vence el {time.strftime('%Y-%m-%d', time.localtime(expires))}. Después hay que repetir la autorización.")
    return 0


def load_session() -> dict:
    tok = private_read(os.path.join(home_dir(), "token.json"))
    if not tok or not isinstance(tok.get("access_token"), str) or not PERSON_RE.fullmatch(str(tok.get("person_urn", ""))):
        raise UserError("no hay sesión de LinkedIn válida; ejecuta auth-start y auth-finish")
    if not isinstance(tok.get("expires_at"), int) or time.time() >= tok["expires_at"]:
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
        print(f"Sesión activa para {tok.get('person_urn')}. Quedan {left // 86400} días. Versión de la API: {api_version()}.")
    return 0


def cmd_logout(args) -> int:
    for name in ("token.json", "auth_state.json", "previews.json"):
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


def to_little(text: str) -> str:
    """Convierte texto plano al formato de la Posts API.

    Los caracteres reservados se escapan con barra invertida para que se lean como texto
    (sin esto, un paréntesis o un guion bajo puede cortar o deformar la publicación).
    Las palabras con # se envían como hashtag real. No se generan menciones.
    """
    out = []
    pos = 0
    for m in HASHTAG_RE.finditer(text):
        out.append(_escape(text[pos:m.start()]))
        out.append("{hashtag|\\#|" + _escape(m.group(1)) + "}")
        pos = m.end()
    out.append(_escape(text[pos:]))
    return "".join(out)


def _escape(chunk: str) -> str:
    return "".join("\\" + c if c in LITTLE_RESERVED else c for c in chunk)


def text_hash(text: str, link: str = "", visibility: str = "", link_title: str = "", link_desc: str = "",
              author: str = "", api: str = "posts") -> str:
    """Huella de lo que se aprueba: texto, enlace (título y descripción), visibilidad, autor y API.

    Se calcula sobre una estructura canónica (JSON), no sobre texto unido con saltos de línea,
    para que dos operaciones distintas no puedan dar la misma huella.
    """
    blob = json.dumps({"text": normalize(text), "link": link, "visibility": visibility, "title": link_title,
                       "description": link_desc, "author": author, "api": api},
                      ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(blob).hexdigest()[:16]


def human_confirms(digest: str) -> bool:
    """La publicación exige que una persona escriba la huella en una terminal interactiva.

    Un agente que ejecuta comandos sin terminal no puede cumplirlo: la persona debe correr el
    comando ella misma. No es una garantía absoluta (quien controle el equipo puede saltarse el
    programa), pero evita que un agente encadene vista previa y publicación sin que la persona lo vea.
    """
    if not (sys.stdin and sys.stdin.isatty()):
        raise UserError("la publicación se confirma en una terminal interactiva: ejecuta este mismo comando tú, "
                        "en tu propia terminal, y escribe la huella cuando se te pida")
    try:
        typed = input(f"Para publicar escribe la huella ({digest}): ").strip()
    except EOFError:
        return False
    return hmac.compare_digest(typed.encode("utf-8"), digest.encode("utf-8"))


def check_clean(label: str, value: str) -> None:
    bad = BAD_CHARS.search(value.replace("\n", "").replace("\t", ""))
    if bad:
        raise UserError(f"{label} trae un carácter de control o de dirección (U+{ord(bad.group()):04X}); límpialo con ag-voz")


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


def build_body(session: dict, text: str, visibility: str, link: str, link_title: str, link_desc: str, api: str) -> dict:
    if api == "ugc":
        content = {"shareCommentary": {"text": text}, "shareMediaCategory": "NONE"}
        if link:
            media = {"status": "READY", "originalUrl": link}
            if link_title:
                media["title"] = {"text": link_title}
            if link_desc:
                media["description"] = {"text": link_desc}
            content["shareMediaCategory"] = "ARTICLE"
            content["media"] = [media]
        return {"author": session["person_urn"], "lifecycleState": "PUBLISHED",
                "specificContent": {"com.linkedin.ugc.ShareContent": content},
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility}}
    body = {"author": session["person_urn"], "commentary": to_little(text), "visibility": visibility,
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
    if link:
        article = {"source": link, "title": link_title}
        if link_desc:
            article["description"] = link_desc
        body["content"] = {"article": article}
    return body


def cmd_post(args) -> int:
    session = load_session()
    version = api_version()
    text = normalize(read_post(args.file))
    if not text:
        raise UserError("el texto está vacío")
    limit = post_limit()
    if len(text) > limit:
        raise UserError(f"el texto tiene {len(text)} caracteres y el límite configurado es {limit}")
    link = args.link or ""
    link_title = (args.link_title or "").strip()
    link_desc = (args.link_description or "").strip()
    for label, value in (("el texto", text), ("el título", link_title), ("la descripción", link_desc), ("el enlace", link)):
        check_clean(label, value)
    if link:
        lp = urllib.parse.urlsplit(link)
        if lp.scheme != "https" or not lp.hostname or lp.username or lp.password or re.search(r"\s", link):
            raise UserError("--link debe ser una dirección https válida, sin usuario ni espacios")
    if (link_title or link_desc) and not link:
        raise UserError("--link-title y --link-description solo se usan junto con --link")
    if link and not link_title and args.api == "posts":
        raise UserError("con --link hay que dar --link-title: la API no lee el título de la página por su cuenta")
    digest = text_hash(text, link, args.visibility, link_title, link_desc, session["person_urn"], args.api)
    text_id = text_hash(text)

    print(f"Cuenta: {session['person_urn']}. API: {args.api}. Visibilidad: {args.visibility}.")
    print(f"Caracteres: {len(text)} de {limit}.")
    if link:
        print(f"Enlace: {link}")
        print(f"Título del enlace: {link_title or 'sin título'}")
        print(f"Descripción del enlace: {link_desc or 'sin descripción'}")
    found = [f"{n} ({SUSPECT[c]})" for c, n in ((c, text.count(c)) for c in SUSPECT) if n]
    if found:
        print("Aviso: el texto trae " + ", ".join(found) + ". Conviene pasarlo por ag-voz antes de publicar.")
    print("Texto exacto que se publicaría:")
    print()
    print(text)
    print()

    now = int(time.time())
    previews_path = os.path.join(home_dir(), "previews.json")
    log_path = os.path.join(home_dir(), "publicaciones.json")
    with locked():
        log = load_log()
        if any(i.get("text_id") == text_id or i.get("hash") == digest for i in log):
            raise UserError("este mismo texto ya se publicó (o quedó en duda) con este programa; no se publica dos veces")
        recent = [i for i in log if now - int(i.get("ts", 0)) < 86400]
        if len(recent) >= MAX_POSTS_PER_DAY:
            raise UserError(f"ya hay {len(recent)} publicaciones en las últimas 24 horas; el tope local es {MAX_POSTS_PER_DAY}")
        previews = {k: v for k, v in (private_read(previews_path) or {}).items() if now - int(v) < PREVIEW_MAX_AGE}
        if not args.confirm:
            previews[digest] = now
            private_write(previews_path, previews)
            print(f"Vista previa. No se publicó nada. Huella de aprobación: {digest}")
            print("Para publicar, la persona ejecuta en su terminal el mismo comando con --confirm " + digest)
            return 0
        if not hmac.compare_digest(args.confirm.encode("utf-8"), digest.encode("utf-8")):
            raise UserError("la aprobación no coincide con el texto, el enlace, la visibilidad o la cuenta actuales; no se publicó")
        if digest not in previews:
            raise UserError("no hay una vista previa reciente de este texto; ejecuta primero post sin --confirm y muéstrasela a la persona")
        if not human_confirms(digest):
            raise UserError("la huella escrita no coincide; no se publicó")
        previews.pop(digest, None)
        private_write(previews_path, previews)
        # Se reserva antes de enviar: si el resultado queda en duda, no se puede repetir a ciegas.
        entry = {"hash": digest, "text_id": text_id, "ts": now, "id": "", "status": "pendiente"}
        log.append(entry)
        private_write(log_path, {"items": log[-200:]})

        body = build_body(session, text, args.visibility, link, link_title, link_desc, args.api)
        headers = {"Authorization": f"Bearer {session['access_token']}", "X-Restli-Protocol-Version": "2.0.0"}
        if args.api == "posts":
            headers["Linkedin-Version"] = version
            url = POSTS_URL
        else:
            url = UGC_URL
        try:
            status, resp_headers, _ = call("POST", url, body=body, headers=headers)
        except Rejected:
            log.remove(entry)
            private_write(log_path, {"items": log[-200:]})
            raise
        except UserError as exc:
            entry["status"] = "incierto"
            private_write(log_path, {"items": log[-200:]})
            raise UserError(f"{exc}. No se sabe si se publicó: mira tu perfil de LinkedIn antes de intentar otra vez. "
                            "Este texto queda bloqueado en el registro local.")
        post_id = resp_headers.get("X-RestLi-Id", "") if resp_headers is not None else ""
        if status != 201 or not URN_RE.fullmatch(post_id or ""):
            entry["status"] = "incierto"
            private_write(log_path, {"items": log[-200:]})
            raise UserError(f"LinkedIn respondió {status} sin un identificador reconocible. Mira tu perfil antes de intentar otra vez. "
                            "Este texto queda bloqueado en el registro local.")
        entry.update({"id": post_id, "status": "publicado"})
        private_write(log_path, {"items": log[-200:]})
    print(f"Publicado (estado {status}). Identificador: {post_id}")
    print(f"Para verlo: {FEED_URL}{post_id}/")
    return 0


def cmd_delete(args) -> int:
    session = load_session()
    if not URN_RE.fullmatch(args.urn):
        raise UserError("el identificador debe verse como urn:li:share:123 o urn:li:ugcPost:123")
    if not any(i.get("id") == args.urn and i.get("status") == "publicado" for i in load_log()):
        raise UserError("ese identificador no figura entre las publicaciones hechas con este programa; no se borra")
    if not args.yes:
        print(f"Se borraría {args.urn}. No se borró nada; agrega --yes para confirmar.")
        return 0
    url = POSTS_URL + "/" + urllib.parse.quote(args.urn, safe="")
    status, _, _ = call("DELETE", url, headers={
        "Authorization": f"Bearer {session['access_token']}", "X-Restli-Protocol-Version": "2.0.0",
        "Linkedin-Version": api_version(), "X-RestLi-Method": "DELETE"})
    with locked():
        log = load_log()
        for i in log:
            if i.get("id") == args.urn:
                i["status"] = "borrado"  # se conserva para el tope y para no repetir el texto
        private_write(os.path.join(home_dir(), "publicaciones.json"), {"items": log})
    print(f"Borrada (estado {status}): {args.urn}")
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
    q.add_argument("--link-title")
    q.add_argument("--link-description")
    q.add_argument("--api", choices=("posts", "ugc"), default="posts")
    q.add_argument("--confirm")
    q.set_defaults(func=cmd_post)
    d = sub.add_parser("delete")
    d.add_argument("urn")
    d.add_argument("--yes", action="store_true")
    d.set_defaults(func=cmd_delete)
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
