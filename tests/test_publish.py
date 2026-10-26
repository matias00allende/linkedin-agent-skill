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

    def read(self):
        return self._raw

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

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = lp.main(list(argv))
        return code, out.getvalue(), err.getvalue()


class Huella(unittest.TestCase):
    def test_hash_depends_on_text_link_and_visibility(self):
        base = lp.text_hash("hola", "", "PUBLIC")
        self.assertEqual(base, lp.text_hash("hola\r\n", "", "PUBLIC"))
        self.assertNotEqual(base, lp.text_hash("hola!", "", "PUBLIC"))
        self.assertNotEqual(base, lp.text_hash("hola", "https://a.test", "PUBLIC"))
        self.assertNotEqual(base, lp.text_hash("hola", "", "CONNECTIONS"))


class VistaPrevia(Base):
    def test_preview_never_touches_the_network_and_shows_the_hash(self):
        self.write_session()
        with mock.patch.object(lp, "urlopen") as net:
            code, out, _ = self.run_cli("post", self.text_path, "--visibility", "CONNECTIONS")
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
        code, out, _ = self.run_cli("post", self.text_path, "--visibility", "PUBLIC")
        self.assertEqual(code, 0)
        self.assertIn("raya larga", out)
        self.assertIn("espacio de ancho cero", out)

    def test_limits_and_empty_text_are_rejected(self):
        self.write_session()
        self.write_text("   \n")
        self.assertEqual(self.run_cli("post", self.text_path, "--visibility", "PUBLIC")[0], 2)
        self.write_text("a" * 3001)
        code, _, err = self.run_cli("post", self.text_path, "--visibility", "PUBLIC")
        self.assertEqual(code, 2)
        self.assertIn("3001", err)

    def test_link_must_be_https(self):
        self.write_session()
        code, _, err = self.run_cli("post", self.text_path, "--visibility", "PUBLIC", "--link", "http://a.test")
        self.assertEqual(code, 2)
        self.assertIn("https", err)


class Publicar(Base):
    def digest(self, link="", visibility="CONNECTIONS"):
        return lp.text_hash(read_file(self.text_path), link, visibility)

    def test_wrong_confirmation_does_not_publish(self):
        self.write_session()
        with mock.patch.object(lp, "urlopen") as net:
            code, _, err = self.run_cli("post", self.text_path, "--visibility", "CONNECTIONS", "--confirm", "000000000000")
        self.assertEqual(code, 2)
        net.assert_not_called()
        self.assertIn("no coincide", err)

    def test_changing_the_text_after_approval_invalidates_it(self):
        self.write_session()
        approved = self.digest()
        self.write_text("Hoy cerramos el proyecto con 13 personas y un aprendizaje claro.")
        with mock.patch.object(lp, "urlopen") as net:
            code, _, _ = self.run_cli("post", self.text_path, "--visibility", "CONNECTIONS", "--confirm", approved)
        self.assertEqual(code, 2)
        net.assert_not_called()

    def test_confirmed_post_sends_the_documented_request_and_logs_it(self):
        self.write_session()
        captured = {}

        def fake(req, timeout=None):
            captured["req"] = req
            return FakeResponse({}, 201, {"X-RestLi-Id": "urn:li:share:999"})

        with mock.patch.object(lp, "urlopen", fake):
            code, out, _ = self.run_cli("post", self.text_path, "--visibility", "CONNECTIONS", "--confirm", self.digest())
        self.assertEqual(code, 0)
        self.assertIn("urn:li:share:999", out)
        self.assertNotIn(TOKEN, out)
        req = captured["req"]
        self.assertEqual(req.full_url, "https://api.linkedin.com/v2/ugcPosts")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Authorization"), "Bearer " + TOKEN)
        self.assertEqual(req.get_header("X-restli-protocol-version"), "2.0.0")
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["author"], "urn:li:person:abc123")
        self.assertEqual(body["lifecycleState"], "PUBLISHED")
        content = body["specificContent"]["com.linkedin.ugc.ShareContent"]
        self.assertEqual(content["shareMediaCategory"], "NONE")
        self.assertIn("12 personas", content["shareCommentary"]["text"])
        self.assertEqual(body["visibility"]["com.linkedin.ugc.MemberNetworkVisibility"], "CONNECTIONS")
        log = read_json(os.path.join(self.home, "publicaciones.json"))
        self.assertEqual(len(log["items"]), 1)

    def test_article_link_changes_the_media_category(self):
        self.write_session()
        link = "https://ejemplo.test/nota"
        captured = {}

        def fake(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return FakeResponse({}, 201, {"X-RestLi-Id": "urn:li:share:1"})

        with mock.patch.object(lp, "urlopen", fake):
            code, _, _ = self.run_cli("post", self.text_path, "--visibility", "PUBLIC", "--link", link,
                                      "--confirm", self.digest(link, "PUBLIC"))
        self.assertEqual(code, 0)
        content = captured["body"]["specificContent"]["com.linkedin.ugc.ShareContent"]
        self.assertEqual(content["shareMediaCategory"], "ARTICLE")
        self.assertEqual(content["media"][0]["originalUrl"], link)

    def test_same_text_is_not_published_twice(self):
        self.write_session()
        with mock.patch.object(lp, "urlopen", lambda req, timeout=None: FakeResponse({}, 201, {"X-RestLi-Id": "1"})):
            self.assertEqual(self.run_cli("post", self.text_path, "--visibility", "CONNECTIONS", "--confirm", self.digest())[0], 0)
            code, _, err = self.run_cli("post", self.text_path, "--visibility", "CONNECTIONS", "--confirm", self.digest())
        self.assertEqual(code, 2)
        self.assertIn("ya se publicó", err)

    def test_daily_cap_is_enforced(self):
        self.write_session()
        lp.private_write(os.path.join(self.home, "publicaciones.json"), {"items": [
            {"hash": "h%d" % i, "ts": int(time.time()) - 60, "id": str(i)} for i in range(lp.MAX_POSTS_PER_DAY)]})
        with mock.patch.object(lp, "urlopen") as net:
            code, _, err = self.run_cli("post", self.text_path, "--visibility", "CONNECTIONS", "--confirm", self.digest())
        self.assertEqual(code, 2)
        net.assert_not_called()
        self.assertIn("tope", err)

    def test_api_error_is_reported_without_the_token(self):
        self.write_session()
        from urllib.error import HTTPError

        def boom(req, timeout=None):
            raise HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b'{"message":"not enough permissions"}'))

        with mock.patch.object(lp, "urlopen", boom):
            code, out, err = self.run_cli("post", self.text_path, "--visibility", "CONNECTIONS", "--confirm", self.digest())
        self.assertEqual(code, 2)
        self.assertIn("403", err)
        self.assertNotIn(TOKEN, out + err)
        self.assertFalse(os.path.exists(os.path.join(self.home, "publicaciones.json")))


class Sesion(Base):
    def test_no_session_and_expired_session_stop_before_anything(self):
        code, _, err = self.run_cli("post", self.text_path, "--visibility", "PUBLIC")
        self.assertEqual(code, 2)
        self.assertIn("auth-start", err)
        self.write_session(expires_in=-10)
        code, _, err = self.run_cli("post", self.text_path, "--visibility", "PUBLIC")
        self.assertEqual(code, 2)
        self.assertIn("venció", err)

    def test_status_and_logout(self):
        self.assertIn("Sin sesión", self.run_cli("status")[1])
        self.write_session()
        out = self.run_cli("status")[1]
        self.assertIn("Sesión activa", out)
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
        code, _, err = self.run_cli("auth-finish", "https://ejemplo.test/callback?error=user_cancelled_authorize&state=x")
        self.assertEqual(code, 2)
        self.assertIn("user_cancelled_authorize", err)


class Red(unittest.TestCase):
    def test_only_linkedin_hosts_over_https_are_allowed(self):
        for url in ("https://evil.test/x", "http://api.linkedin.com/v2/ugcPosts", "https://api.linkedin.com.evil.test/"):
            with mock.patch.object(lp, "urlopen") as net:
                with self.assertRaises(lp.UserError):
                    lp.call("GET", url)
            net.assert_not_called()


class Contrato(unittest.TestCase):
    def test_script_has_no_comment_message_or_reaction_endpoints(self):
        src = read_file(SCRIPT)
        for banned in ("socialActions", "messages", "invitation", "playwright", "selenium", "w_organization", "while True"):
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
        allowed = {"__future__", "argparse", "hashlib", "hmac", "json", "os", "secrets", "sys", "time",
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
