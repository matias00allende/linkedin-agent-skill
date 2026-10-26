"""Pruebas de ag-publish con la red simulada: ninguna prueba contacta a LinkedIn."""
import importlib.util
import io
import json
import os
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from helpers import ROOT

SCRIPT = os.path.join(ROOT, "skills", "ag-publish", "scripts", "linkedin_publish.py")
spec = importlib.util.spec_from_file_location("linkedin_publish", SCRIPT)
lp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lp)

TOKEN = "TOKEN-SECRETO-DE-PRUEBA"
OK_POST = lambda req, timeout=None: FakeResponse({}, 201, {"X-RestLi-Id": "urn:li:share:999"})  # noqa: E731


def read_file(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def read_json(path):
    return json.loads(read_file(path))


class FakeResponse:
    def __init__(self, payload=None, status=200, headers=None):
        self._raw = json.dumps(payload or {}).encode("utf-8")
        self.status = status
        self.headers = headers or {}

    def read(self, size=-1):
        return self._raw if size is None or size < 0 else self._raw[:size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        patcher = mock.patch.dict(os.environ, {
            "AGENTIN_HOME": self.home, "LINKEDIN_CLIENT_ID": "cid", "LINKEDIN_CLIENT_SECRET": "csecret",
            "LINKEDIN_REDIRECT_URI": "https://ejemplo.test/callback"})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("LINKEDIN_API_VERSION", None)
        self.addCleanup(self.tmp.cleanup)
        self.text_path = os.path.join(self.tmp.name, "texto.txt")
        self.write_text("Hoy cerramos el proyecto con 12 personas y un aprendizaje claro.")

    def write_text(self, text):
        with open(self.text_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    def write_session(self, expires_in=86400 * 30):
        os.makedirs(self.home, exist_ok=True)
        lp.private_write(os.path.join(self.home, "token.json"), {
            "access_token": TOKEN, "expires_at": int(time.time()) + expires_in,
            "person_urn": "urn:li:person:abc123", "scope": "w_member_social"})

    def run_cli(self, *argv, human=True):
        """Ejecuta el programa. human=True simula a la persona escribiendo la huella en su terminal."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), mock.patch.object(lp, "human_confirms", lambda d: human):
            code = lp.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def digest(self, link="", visibility="CONNECTIONS", title="", desc="", api="posts"):
        return lp.text_hash(read_file(self.text_path), link, visibility, title, desc, "urn:li:person:abc123", api)

    def preview(self, *extra, visibility="CONNECTIONS"):
        return self.run_cli("post", self.text_path, "--visibility", visibility, *extra)


class Huella(unittest.TestCase):
    def test_hash_depends_on_text_link_title_and_visibility(self):
        base = lp.text_hash("hola", "", "PUBLIC")
        self.assertEqual(base, lp.text_hash("hola\r\n", "", "PUBLIC"))
        self.assertNotEqual(base, lp.text_hash("hola!", "", "PUBLIC"))
        self.assertNotEqual(base, lp.text_hash("hola", "https://a.test", "PUBLIC"))
        self.assertNotEqual(base, lp.text_hash("hola", "", "CONNECTIONS"))
        with_link = lp.text_hash("hola", "https://a.test", "PUBLIC", "Titulo")
        self.assertNotEqual(with_link, lp.text_hash("hola", "https://a.test", "PUBLIC", "Otro titulo"))
        self.assertNotEqual(with_link, lp.text_hash("hola", "https://a.test", "PUBLIC", "Titulo", "Descripcion"))


    def test_hash_is_structural_and_bound_to_author_and_api(self):
        a = lp.text_hash("hola", "https://a.test", "PUBLIC", "Nota\nResumen", "")
        b = lp.text_hash("hola", "https://a.test", "PUBLIC", "Nota", "Resumen")
        self.assertNotEqual(a, b)
        base = lp.text_hash("hola", "", "PUBLIC", "", "", "urn:li:person:a", "posts")
        self.assertNotEqual(base, lp.text_hash("hola", "", "PUBLIC", "", "", "urn:li:person:b", "posts"))
        self.assertNotEqual(base, lp.text_hash("hola", "", "PUBLIC", "", "", "urn:li:person:a", "ugc"))


class FormatoDeTexto(unittest.TestCase):
    def test_reserved_characters_inside_a_hashtag_are_escaped(self):
        self.assertEqual(lp.to_little("Va #equipo_tecnico hoy"), "Va {hashtag|\\#|equipo\\_tecnico} hoy")

    def test_fragment_of_a_url_is_not_turned_into_a_hashtag(self):
        self.assertNotIn("{hashtag", lp.to_little("Ver https://a.test/#seccion"))

    def test_reserved_characters_are_escaped(self):
        self.assertEqual(lp.to_little("Costo (aprox.) [2026] * 3_5 ~ a|b {x} <y> @z \\ fin"),
                         "Costo \\(aprox.\\) \\[2026\\] \\* 3\\_5 \\~ a\\|b \\{x\\} \\<y\\> \\@z \\\\ fin")

    def test_hashtags_become_real_hashtag_templates(self):
        self.assertEqual(lp.to_little("Gracias #Ciberseguridad y #gestión"),
                         "Gracias {hashtag|\\#|Ciberseguridad} y {hashtag|\\#|gestión}")

    def test_hash_not_followed_by_a_word_is_plain_escaped_text(self):
        self.assertEqual(lp.to_little("Punto # 3 y #1 lugar"), "Punto \\# 3 y \\#1 lugar")

    def test_newlines_accents_and_plain_text_are_untouched(self):
        text = "Línea uno.\n\nLínea dos con ñ y tildes: él, más, año."
        self.assertEqual(lp.to_little(text), text)

    def test_url_with_special_characters_is_escaped_not_dropped(self):
        self.assertEqual(lp.to_little("Ver https://a.test/x_y?z=1#frag"), "Ver https://a.test/x\\_y?z=1\\#frag")


class VistaPrevia(Base):
    def test_preview_never_touches_the_network_and_shows_the_hash(self):
        self.write_session()
        with mock.patch.object(lp, "urlopen") as net:
            code, out, _ = self.preview()
        self.assertEqual(code, 0)
        net.assert_not_called()
        self.assertIn("No se publicó nada", out)
        self.assertIn("--confirm", out)
        self.assertNotIn(TOKEN, out)

    def test_visibility_is_required(self):
        self.write_session()
        code, _, err = self.run_cli("post", self.text_path)
        self.assertEqual(code, 2)
        self.assertIn("visibility", err)

    def test_suspicious_characters_are_warned(self):
        self.write_session()
        self.write_text("Texto con raya " + chr(0x2014) + " y salto" + chr(0x200b) + " invisible.")
        code, out, _ = self.preview(visibility="PUBLIC")
        self.assertEqual(code, 0)
        self.assertIn("raya larga", out)
        self.assertIn("espacio de ancho cero", out)

    def test_limits_and_empty_text_are_rejected(self):
        self.write_session()
        self.write_text("   \n")
        self.assertEqual(self.preview(visibility="PUBLIC")[0], 2)
        self.write_text("a" * 3001)
        code, _, err = self.preview(visibility="PUBLIC")
        self.assertEqual(code, 2)
        self.assertIn("3001", err)

    def test_link_rules(self):
        self.write_session()
        code, _, err = self.preview("--link", "http://a.test", "--link-title", "T")
        self.assertEqual((code, "https" in err), (2, True))
        code, _, err = self.preview("--link", "https://a.test")
        self.assertEqual((code, "--link-title" in err), (2, True))
        code, _, err = self.preview("--link-title", "Solo titulo")
        self.assertEqual((code, "junto con --link" in err), (2, True))
        self.assertEqual(self.preview("--link", "https://a.test", "--link-title", "Titulo")[0], 0)


class Publicar(Base):
    def publish(self, *extra, visibility="CONNECTIONS", link="", title="", desc="", api="posts", human=True):
        """Vista previa y luego publicación aprobada, como exige el flujo."""
        self.assertEqual(self.preview(*extra, visibility=visibility)[0], 0)
        return self.run_cli("post", self.text_path, "--visibility", visibility, *extra,
                            "--confirm", self.digest(link, visibility, title, desc, api), human=human)

    def test_confirmation_without_a_prior_preview_does_not_publish(self):
        self.write_session()
        with mock.patch.object(lp, "urlopen") as net:
            code, _, err = self.run_cli("post", self.text_path, "--visibility", "CONNECTIONS", "--confirm", self.digest())
        self.assertEqual(code, 2)
        net.assert_not_called()
        self.assertIn("vista previa", err)

    def test_wrong_confirmation_does_not_publish(self):
        self.write_session()
        self.preview()
        with mock.patch.object(lp, "urlopen") as net:
            code, _, err = self.run_cli("post", self.text_path, "--visibility", "CONNECTIONS", "--confirm", "000000000000")
        self.assertEqual(code, 2)
        net.assert_not_called()
        self.assertIn("no coincide", err)

    def test_changing_the_text_after_approval_invalidates_it(self):
        self.write_session()
        self.preview()
        approved = self.digest()
        self.write_text("Hoy cerramos el proyecto con 13 personas y un aprendizaje claro.")
        with mock.patch.object(lp, "urlopen") as net:
            code, _, _ = self.run_cli("post", self.text_path, "--visibility", "CONNECTIONS", "--confirm", approved)
        self.assertEqual(code, 2)
        net.assert_not_called()

    def test_confirmed_post_uses_the_versioned_posts_api(self):
        self.write_session()
        captured = {}

        def fake(req, timeout=None):
            captured["req"] = req
            return FakeResponse({}, 201, {"X-RestLi-Id": "urn:li:share:999"})

        with mock.patch.object(lp, "urlopen", fake):
            code, out, _ = self.publish()
        self.assertEqual(code, 0)
        self.assertIn("urn:li:share:999", out)
        self.assertIn("https://www.linkedin.com/feed/update/urn:li:share:999/", out)
        self.assertNotIn(TOKEN, out)
        req = captured["req"]
        self.assertEqual(req.full_url, "https://api.linkedin.com/rest/posts")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Authorization"), "Bearer " + TOKEN)
        self.assertEqual(req.get_header("X-restli-protocol-version"), "2.0.0")
        self.assertEqual(req.get_header("Linkedin-version"), lp.DEFAULT_API_VERSION)
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["author"], "urn:li:person:abc123")
        self.assertEqual(body["lifecycleState"], "PUBLISHED")
        self.assertEqual(body["visibility"], "CONNECTIONS")
        self.assertEqual(body["distribution"]["feedDistribution"], "MAIN_FEED")
        self.assertFalse(body["isReshareDisabledByAuthor"])
        self.assertIn("12 personas", body["commentary"])
        self.assertNotIn("content", body)
        log = read_json(os.path.join(self.home, "publicaciones.json"))
        self.assertEqual(log["items"][0]["id"], "urn:li:share:999")

    def test_commentary_is_sent_escaped_while_the_preview_shows_the_original(self):
        self.write_session()
        self.write_text("Costo (aprox.) y #Ciberseguridad")
        captured = {}

        def fake(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResponse({}, 201, {"X-RestLi-Id": "urn:li:share:1"})

        with mock.patch.object(lp, "urlopen", fake):
            code, out, _ = self.publish()
        self.assertEqual(code, 0)
        self.assertEqual(captured["body"]["commentary"], "Costo \\(aprox.\\) y {hashtag|\\#|Ciberseguridad}")
        self.assertIn("Costo (aprox.) y #Ciberseguridad", out)

    def test_api_version_can_be_set_and_is_validated(self):
        self.write_session()
        captured = {}

        def fake(req, timeout=None):
            captured["version"] = req.get_header("Linkedin-version")
            return FakeResponse({}, 201, {"X-RestLi-Id": "urn:li:share:1"})

        with mock.patch.dict(os.environ, {"LINKEDIN_API_VERSION": "202701"}), mock.patch.object(lp, "urlopen", fake):
            self.assertEqual(self.publish()[0], 0)
        self.assertEqual(captured["version"], "202701")
        with mock.patch.dict(os.environ, {"LINKEDIN_API_VERSION": "2026-10"}):
            code, _, err = self.preview()
        self.assertEqual(code, 2)
        self.assertIn("AAAAMM", err)

    def test_article_link_is_sent_with_title_and_description(self):
        self.write_session()
        link = "https://ejemplo.test/nota"
        captured = {}

        def fake(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResponse({}, 201, {"X-RestLi-Id": "urn:li:share:1"})

        with mock.patch.object(lp, "urlopen", fake):
            code, _, _ = self.publish("--link", link, "--link-title", "Nota", "--link-description", "Resumen",
                                      visibility="PUBLIC", link=link, title="Nota", desc="Resumen")
        self.assertEqual(code, 0)
        self.assertEqual(captured["body"]["content"]["article"],
                         {"source": link, "title": "Nota", "description": "Resumen"})

    def test_the_legacy_ugc_api_can_no_longer_publish(self):
        self.write_session()
        code, _, err = self.preview("--api", "ugc")
        self.assertEqual(code, 2)

    def test_same_text_is_not_published_twice(self):
        self.write_session()
        with mock.patch.object(lp, "urlopen", OK_POST):
            self.assertEqual(self.publish()[0], 0)
            code, _, err = self.preview()
        self.assertEqual(code, 2)
        self.assertIn("ya se publicó", err)

    def test_daily_cap_is_enforced(self):
        self.write_session()
        lp.private_write(os.path.join(self.home, "publicaciones.json"), {"items": [
            {"hash": "h%d" % i, "ts": int(time.time()) - 60, "id": str(i)} for i in range(lp.MAX_POSTS_PER_DAY)]})
        with mock.patch.object(lp, "urlopen") as net:
            code, _, err = self.preview()
        self.assertEqual(code, 2)
        net.assert_not_called()
        self.assertIn("tope", err)

    def test_api_error_is_reported_without_the_token(self):
        self.write_session()
        from urllib.error import HTTPError

        def boom(req, timeout=None):
            raise HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b'{"message":"not enough permissions"}'))

        with mock.patch.object(lp, "urlopen", boom):
            code, out, err = self.publish()
        self.assertEqual(code, 2)
        self.assertIn("403", err)
        self.assertNotIn(TOKEN, out + err)
        self.assertEqual(read_json(os.path.join(self.home, "publicaciones.json"))["items"], [])


class Garantias(Base):
    publish = Publicar.publish

    def test_agent_without_a_terminal_cannot_confirm(self):
        self.write_session()
        with mock.patch.object(lp.sys, "stdin", io.StringIO("")):
            with self.assertRaises(lp.UserError) as ctx:
                lp.human_confirms("abc")
        self.assertIn("terminal interactiva", str(ctx.exception))

    def test_a_terminal_with_the_wrong_digest_does_not_confirm(self):
        class Tty(io.StringIO):
            def isatty(self):
                return True
        with mock.patch.object(lp.sys, "stdin", Tty()), mock.patch("builtins.input", return_value="otra"):
            self.assertFalse(lp.human_confirms("abc"))
        with mock.patch.object(lp.sys, "stdin", Tty()), mock.patch("builtins.input", return_value="abc"):
            self.assertTrue(lp.human_confirms("abc"))

    def test_failed_human_confirmation_does_not_publish(self):
        self.write_session()
        with mock.patch.object(lp, "urlopen") as net:
            code, _, err = self.publish(human=False)
        self.assertEqual(code, 2)
        net.assert_not_called()
        self.assertIn("no coincide", err)

    def test_preview_shows_account_api_and_every_sent_field(self):
        self.write_session()
        _, out, _ = self.preview("--link", "https://a.test/x", "--link-title", "Titulo", "--link-description", "Descripcion larga")
        for expected in ("urn:li:person:abc123", "API: posts", "Título del enlace: Titulo", "Descripcion larga"):
            self.assertIn(expected, out)

    def test_terminal_and_direction_controls_are_rejected(self):
        self.write_session()
        for bad in ("Hola \x1b[2J oculto", "Hola \u202e invertido", "Hola \x07 timbre"):
            self.write_text(bad)
            code, _, err = self.preview()
            self.assertEqual(code, 2, bad)
            self.assertIn("carácter de control", err)

    def test_link_with_credentials_or_spaces_is_rejected(self):
        self.write_session()
        for bad in ("https://user:pass@a.test/x", "https://", "https://a.test/a b"):
            code, _, _ = self.preview("--link", bad, "--link-title", "T")
            self.assertEqual(code, 2, bad)

    def test_network_failure_after_sending_blocks_a_blind_retry(self):
        self.write_session()
        from urllib.error import URLError

        def cut(req, timeout=None):
            raise URLError("connection reset")

        with mock.patch.object(lp, "urlopen", cut):
            code, _, err = self.publish()
        self.assertEqual(code, 2)
        self.assertIn("No se sabe si se publicó", err)
        self.assertEqual(read_json(os.path.join(self.home, "publicaciones.json"))["items"][0]["status"], "incierto")
        with mock.patch.object(lp, "urlopen") as net:
            code, _, err = self.preview()
        net.assert_not_called()
        self.assertEqual(code, 2)
        self.assertIn("ya se publicó", err)

    def test_success_without_an_identifier_is_not_reported_as_published(self):
        self.write_session()
        with mock.patch.object(lp, "urlopen", lambda req, timeout=None: FakeResponse({}, 200, {})):
            code, out, err = self.publish()
        self.assertEqual(code, 2)
        self.assertNotIn("Publicado", out)
        self.assertIn("sin un identificador", err)
        self.assertEqual(read_json(os.path.join(self.home, "publicaciones.json"))["items"][0]["status"], "incierto")

    def test_same_text_with_other_visibility_is_still_a_duplicate(self):
        self.write_session()
        with mock.patch.object(lp, "urlopen", OK_POST):
            self.assertEqual(self.publish(visibility="CONNECTIONS")[0], 0)
            code, _, err = self.preview(visibility="PUBLIC")
        self.assertEqual(code, 2)
        self.assertIn("ya se publicó", err)

    def test_deleting_does_not_free_the_daily_cap(self):
        self.write_session()
        items = [{"hash": "h%d" % i, "text_id": "t%d" % i, "ts": int(time.time()) - 60, "id": "urn:li:share:%d" % i,
                  "status": "borrado"} for i in range(lp.MAX_POSTS_PER_DAY)]
        lp.private_write(os.path.join(self.home, "publicaciones.json"), {"items": items})
        code, _, err = self.preview()
        self.assertEqual(code, 2)
        self.assertIn("tope", err)

    def test_redirects_are_never_followed(self):
        handler = lp._NoRedirect()
        with self.assertRaises(lp.UserError) as ctx:
            handler.redirect_request(None, None, 302, "Found", {}, "https://evil.test/")
        self.assertIn("redirigir", str(ctx.exception))

    def test_urls_with_port_or_credentials_are_refused(self):
        for url in ("https://api.linkedin.com:8443/rest/posts", "https://u:p@api.linkedin.com/rest/posts"):
            with self.assertRaises(lp.UserError):
                lp.call("GET", url)

    def test_remote_error_text_is_sanitized_and_short(self):
        from urllib.error import HTTPError
        body = ('{"message":"' + "x" * 500 + '\\u001b[31m"}').encode()

        def boom(req, timeout=None):
            raise HTTPError(req.full_url, 400, "Bad", {}, io.BytesIO(body))

        with mock.patch.object(lp, "urlopen", boom):
            with self.assertRaises(lp.Rejected) as ctx:
                lp.call("GET", "https://api.linkedin.com/x")
        self.assertLess(len(str(ctx.exception)), 160)
        self.assertNotIn("\x1b", str(ctx.exception))

    def test_symlinked_home_and_files_are_refused(self):
        if os.name != "posix":
            self.skipTest("los enlaces simbólicos requieren POSIX")
        target = os.path.join(self.tmp.name, "otro")
        os.makedirs(target)
        link = os.path.join(self.tmp.name, "enlace")
        os.symlink(target, link)
        with mock.patch.dict(os.environ, {"AGENTIN_HOME": link}):
            with self.assertRaises(lp.UserError):
                lp.home_dir()
        os.makedirs(self.home)
        file_link = os.path.join(self.home, "token.json")
        os.symlink(os.path.join(target, "robado.json"), file_link)
        with self.assertRaises(lp.UserError):
            lp.private_write(file_link, {"a": 1})

    def test_atomic_write_leaves_no_temporary_files(self):
        os.makedirs(self.home)
        lp.private_write(os.path.join(self.home, "x.json"), {"a": 1})
        self.assertEqual(os.listdir(self.home), ["x.json"])

    def test_corrupt_session_is_rejected_cleanly(self):
        os.makedirs(self.home)
        lp.private_write(os.path.join(self.home, "token.json"),
                         {"access_token": TOKEN, "expires_at": "mañana", "person_urn": "urn:li:person:abc\nxyz"})
        code, _, err = self.preview(visibility="PUBLIC")
        self.assertEqual(code, 2)
        self.assertIn("sesión", err)

    def test_impossible_api_month_is_rejected(self):
        with mock.patch.dict(os.environ, {"LINKEDIN_API_VERSION": "202699"}):
            with self.assertRaises(lp.UserError):
                lp.api_version()

    def test_lock_serializes_and_recovers_from_a_stale_lock(self):
        os.makedirs(self.home)
        stale = os.path.join(self.home, "lock")
        open(stale, "w").close()
        old = time.time() - lp.LOCK_STALE - 10
        os.utime(stale, (old, old))
        with lp.locked():
            self.assertTrue(os.path.exists(stale))
        self.assertFalse(os.path.exists(stale))

    def test_auth_finish_requires_the_registered_callback_and_unique_params(self):
        self.run_cli("auth-start")
        state = read_json(os.path.join(self.home, "auth_state.json"))["state"]
        with mock.patch.object(lp, "urlopen") as net:
            code, _, err = self.run_cli("auth-finish", f"https://otro.test/callback?code=x&state={state}")
            code2, _, err2 = self.run_cli("auth-finish", f"https://ejemplo.test/callback?code=x&state={state}&state=otro")
        net.assert_not_called()
        self.assertEqual((code, code2), (2, 2))
        self.assertIn("LINKEDIN_REDIRECT_URI", err)
        self.assertIn("repetidos", err2)
        with mock.patch.dict(os.environ, {"LINKEDIN_CLIENT_ID": "otra-app"}):
            code3, _, err3 = self.run_cli("auth-finish", f"https://ejemplo.test/callback?code=x&state={state}")
        self.assertEqual(code3, 2)
        self.assertIn("cambiaron", err3)


class Endurecimiento(Base):
    publish = Publicar.publish

    def test_server_errors_on_a_write_stay_uncertain_and_block_a_retry(self):
        from urllib.error import HTTPError
        self.write_session()

        def boom(req, timeout=None):
            raise HTTPError(req.full_url, 502, "Bad Gateway", {}, io.BytesIO(b"{}"))

        with mock.patch.object(lp, "urlopen", boom):
            code, _, err = self.publish()
        self.assertEqual(code, 2)
        self.assertIn("No se sabe si se publicó", err)
        self.assertEqual(read_json(os.path.join(self.home, "publicaciones.json"))["items"][0]["status"], "incierto")

    def test_client_errors_release_the_reservation(self):
        from urllib.error import HTTPError
        self.write_session()

        def boom(req, timeout=None):
            raise HTTPError(req.full_url, 422, "Unprocessable", {}, io.BytesIO(b"{}"))

        with mock.patch.object(lp, "urlopen", boom):
            code, _, _ = self.publish()
        self.assertEqual(code, 2)
        self.assertEqual(read_json(os.path.join(self.home, "publicaciones.json"))["items"], [])

    def test_delete_only_counts_204_and_only_for_the_same_account(self):
        self.write_session()
        urn = "urn:li:share:9"
        log = os.path.join(self.home, "publicaciones.json")
        lp.private_write(log, {"items": [{"hash": "h", "ts": int(time.time()), "id": urn, "status": "publicado",
                                          "author": "urn:li:person:otra"}]})
        code, _, err = self.run_cli("delete", urn, "--yes")
        self.assertEqual(code, 2)
        self.assertIn("no figura", err)
        lp.private_write(log, {"items": [{"hash": "h", "ts": int(time.time()), "id": urn, "status": "publicado",
                                          "author": "urn:li:person:abc123"}]})
        with mock.patch.object(lp, "urlopen", lambda req, timeout=None: FakeResponse({}, 202)):
            code, out, err = self.run_cli("delete", urn, "--yes")
        self.assertEqual(code, 2)
        self.assertNotIn("Borrada", out)
        self.assertEqual(read_json(log)["items"][0]["status"], "publicado")

    def test_pending_markers_are_refused(self):
        self.write_session()
        self.write_text("Hola {{dato: cifra}} mundo")
        code, _, err = self.preview()
        self.assertEqual(code, 2)
        self.assertIn("marcador pendiente", err)

    def test_damaged_log_fails_closed(self):
        self.write_session()
        lp.private_write(os.path.join(self.home, "publicaciones.json"), {"items": "no soy una lista"})
        with mock.patch.object(lp, "urlopen") as net:
            code, _, err = self.preview()
        net.assert_not_called()
        self.assertEqual(code, 2)
        self.assertIn("dañado", err)

    def test_dedup_memory_outlives_200_attempts(self):
        self.write_session()
        old = {"hash": "x", "text_id": lp.text_hash(read_file(self.text_path)), "ts": int(time.time()) - 10 * 86400,
               "id": "urn:li:share:1", "status": "publicado", "author": "urn:li:person:abc123"}
        filler = [{"hash": "f%d" % i, "text_id": "t%d" % i, "ts": int(time.time()) - 10 * 86400, "id": "", "status": "borrado"}
                  for i in range(300)]
        lp.private_write(os.path.join(self.home, "publicaciones.json"), {"items": [old] + filler})
        code, _, err = self.preview()
        self.assertEqual(code, 2)
        self.assertIn("ya se publicó", err)

    def test_confirmation_happens_outside_the_lock_and_is_revalidated(self):
        self.write_session()
        self.assertEqual(self.preview()[0], 0)
        seen = {}

        def slow(digest):
            seen["lock_free"] = not os.path.exists(os.path.join(self.home, "lock"))
            # la vista previa vence mientras la persona decide
            lp.private_write(os.path.join(self.home, "previews.json"), {})
            return True

        with mock.patch.object(lp, "human_confirms", slow), mock.patch.object(lp, "urlopen") as net:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = lp.main(["post", self.text_path, "--visibility", "CONNECTIONS", "--confirm", self.digest()])
        net.assert_not_called()
        self.assertTrue(seen["lock_free"])
        self.assertEqual(code, 2)
        self.assertIn("venció mientras se confirmaba", err.getvalue())

    def test_a_lock_is_only_removed_by_its_owner(self):
        os.makedirs(self.home)
        path = os.path.join(self.home, "lock")
        with lp.locked():
            with open(path, "w") as fh:
                fh.write("otro-dueno")
        self.assertTrue(os.path.exists(path))

    def test_callback_error_is_shown_only_after_state_matches_and_is_sanitized(self):
        self.run_cli("auth-start")
        state = read_json(os.path.join(self.home, "auth_state.json"))["state"]
        _, _, err = self.run_cli("auth-finish", "https://ejemplo.test/callback?error=%1b%5b2Jx&state=falso")
        self.assertNotIn("\x1b", err)
        self.assertIn("state", err)
        _, _, err = self.run_cli("auth-finish", "https://ejemplo.test/callback?error=%1b%5b2Jx&state=" + state)
        self.assertNotIn("\x1b", err)

    def test_oauth_responses_of_the_wrong_type_are_rejected_cleanly(self):
        self.run_cli("auth-start")
        state = read_json(os.path.join(self.home, "auth_state.json"))["state"]
        with mock.patch.object(lp, "urlopen", lambda req, timeout=None: FakeResponse([1, 2], 200)):
            code, _, err = self.run_cli("auth-finish", f"https://ejemplo.test/callback?code=x&state={state}")
        self.assertEqual(code, 2)
        self.assertIn("access_token", err)

    def test_auth_finish_without_a_terminal_and_without_argument_is_refused(self):
        self.run_cli("auth-start")
        with mock.patch.object(lp.sys, "stdin", io.StringIO("")):
            code, _, err = self.run_cli("auth-finish")
        self.assertEqual(code, 2)
        self.assertIn("terminal interactiva", err)

    def test_logout_keeps_the_publication_log_and_says_so(self):
        self.write_session()
        lp.private_write(os.path.join(self.home, "publicaciones.json"), {"items": []})
        _, out, _ = self.run_cli("logout")
        self.assertTrue(os.path.exists(os.path.join(self.home, "publicaciones.json")))
        self.assertIn("publicaciones.json", out)


class Borrar(Base):
    def seed(self, urn="urn:li:share:555"):
        self.write_session()
        lp.private_write(os.path.join(self.home, "publicaciones.json"), {"items": [{"hash": "h", "ts": int(time.time()), "id": urn, "status": "publicado",
                                                                                     "author": "urn:li:person:abc123"}]})

    def test_delete_requires_yes_and_a_post_made_by_this_program(self):
        self.seed()
        with mock.patch.object(lp, "urlopen") as net:
            code, out, _ = self.run_cli("delete", "urn:li:share:555")
            self.assertIn("No se borró nada", out)
            code2, _, err = self.run_cli("delete", "urn:li:share:777", "--yes")
            code3, _, err3 = self.run_cli("delete", "no-es-un-urn", "--yes")
        net.assert_not_called()
        self.assertEqual((code, code2, code3), (0, 2, 2))
        self.assertIn("no figura", err)
        self.assertIn("urn:li:share", err3)

    def test_confirmed_delete_calls_the_versioned_endpoint_and_updates_the_log(self):
        self.seed()
        captured = {}

        def fake(req, timeout=None):
            captured["req"] = req
            return FakeResponse({}, 204)

        with mock.patch.object(lp, "urlopen", fake):
            code, out, _ = self.run_cli("delete", "urn:li:share:555", "--yes")
        self.assertEqual(code, 0)
        req = captured["req"]
        self.assertEqual(req.get_method(), "DELETE")
        self.assertEqual(req.full_url, "https://api.linkedin.com/rest/posts/urn%3Ali%3Ashare%3A555")
        self.assertEqual(req.get_header("Linkedin-version"), lp.DEFAULT_API_VERSION)
        item = read_json(os.path.join(self.home, "publicaciones.json"))["items"][0]
        self.assertEqual(item["status"], "borrado")  # sigue contando para el tope y los duplicados


class Sesion(Base):
    def test_no_session_and_expired_session_stop_before_anything(self):
        code, _, err = self.preview(visibility="PUBLIC")
        self.assertEqual(code, 2)
        self.assertIn("auth-start", err)
        self.write_session(expires_in=-10)
        code, _, err = self.preview(visibility="PUBLIC")
        self.assertEqual(code, 2)
        self.assertIn("venció", err)

    def test_status_and_logout(self):
        self.assertIn("Sin sesión", self.run_cli("status")[1])
        self.write_session()
        out = self.run_cli("status")[1]
        self.assertIn("Sesión activa", out)
        self.assertIn(lp.DEFAULT_API_VERSION, out)
        self.assertNotIn(TOKEN, out)
        self.run_cli("logout")
        self.assertFalse(os.path.exists(os.path.join(self.home, "token.json")))

    def test_auth_start_prints_the_official_url_with_minimal_scopes_and_state(self):
        code, out, _ = self.run_cli("auth-start")
        self.assertEqual(code, 0)
        self.assertIn("https://www.linkedin.com/oauth/v2/authorization?", out)
        self.assertIn("scope=openid%20profile%20w_member_social", out)
        self.assertNotIn("w_organization", out)
        self.assertNotIn("csecret", out)
        saved = read_json(os.path.join(self.home, "auth_state.json"))
        self.assertIn("state=" + saved["state"], out)

    def test_redirect_uri_must_be_https(self):
        with mock.patch.dict(os.environ, {"LINKEDIN_REDIRECT_URI": "http://localhost/cb"}):
            code, _, err = self.run_cli("auth-start")
        self.assertEqual(code, 2)
        self.assertIn("https", err)

    def test_auth_finish_rejects_a_foreign_state_without_using_the_code(self):
        self.run_cli("auth-start")
        with mock.patch.object(lp, "urlopen") as net:
            code, _, err = self.run_cli("auth-finish", "https://ejemplo.test/callback?code=abc&state=otro")
        self.assertEqual(code, 2)
        net.assert_not_called()
        self.assertIn("state", err)

    def test_auth_finish_without_start_is_rejected(self):
        code, _, err = self.run_cli("auth-finish", "https://ejemplo.test/callback?code=abc&state=x")
        self.assertEqual(code, 2)
        self.assertIn("auth-start", err)

    def test_auth_finish_stores_the_session_privately(self):
        self.run_cli("auth-start")
        state = read_json(os.path.join(self.home, "auth_state.json"))["state"]
        calls = []

        def fake(req, timeout=None):
            calls.append(req.full_url)
            if req.full_url.endswith("/accessToken"):
                self.assertIn(b"client_secret=csecret", req.data)
                self.assertIn(b"grant_type=authorization_code", req.data)
                return FakeResponse({"access_token": TOKEN, "expires_in": 5184000, "scope": "w_member_social"})
            return FakeResponse({"sub": "abc123", "name": "Persona de Prueba"})

        with mock.patch.object(lp, "urlopen", fake):
            code, out, _ = self.run_cli("auth-finish", f"https://ejemplo.test/callback?code=xyz&state={state}")
        self.assertEqual(code, 0)
        self.assertEqual(calls, ["https://www.linkedin.com/oauth/v2/accessToken", "https://api.linkedin.com/v2/userinfo"])
        self.assertNotIn(TOKEN, out)
        saved = read_json(os.path.join(self.home, "token.json"))
        self.assertEqual(saved["person_urn"], "urn:li:person:abc123")
        self.assertFalse(os.path.exists(os.path.join(self.home, "auth_state.json")))

    def test_auth_error_from_linkedin_is_reported(self):
        self.run_cli("auth-start")
        state = read_json(os.path.join(self.home, "auth_state.json"))["state"]
        code, _, err = self.run_cli("auth-finish", "https://ejemplo.test/callback?error=user_cancelled_authorize&state=" + state)
        self.assertEqual(code, 2)
        self.assertIn("user_cancelled_authorize", err)


class Red(unittest.TestCase):
    def test_only_linkedin_hosts_over_https_are_allowed(self):
        for url in ("https://evil.test/x", "http://api.linkedin.com/rest/posts", "https://api.linkedin.com.evil.test/"):
            with mock.patch.object(lp, "urlopen") as net:
                with self.assertRaises(lp.UserError):
                    lp.call("GET", url)
            net.assert_not_called()


class Contrato(unittest.TestCase):
    def test_script_has_no_comment_message_or_reaction_endpoints(self):
        src = read_file(SCRIPT)
        for banned in ("socialActions", "messages", "invitation", "playwright", "selenium", "w_organization", "while True",
                       "schedule"):
            self.assertNotIn(banned, src)

    def test_script_imports_are_limited_and_has_no_dynamic_execution(self):
        import ast
        tree = ast.parse(read_file(SCRIPT))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, ("exec", "eval", "compile", "__import__"))
        allowed = {"__future__", "argparse", "contextlib", "hashlib", "hmac", "json", "os", "re", "secrets", "sys", "time",
                   "unicodedata", "urllib"}
        self.assertLessEqual(imported, allowed)

    def test_only_linkedin_hosts_appear_in_the_script(self):
        import re
        hosts = set(re.findall(r"https://([a-z.]+)/", read_file(SCRIPT)))
        self.assertLessEqual(hosts, {"www.linkedin.com", "api.linkedin.com"})

    def test_state_files_are_not_world_readable_on_posix(self):
        if os.name != "posix":
            self.skipTest("los permisos en Windows dependen de la carpeta de usuario")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "t.json")
            lp.private_write(path, {"a": 1})
            self.assertEqual(os.stat(path).st_mode & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
