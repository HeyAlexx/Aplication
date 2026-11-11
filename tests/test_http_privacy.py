"""HTTP privacy regressions. All writes and sessions belong to temporary fixtures."""
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest

APP = Path(os.environ.get("ALTOIDSS_TEST_SOURCE", Path(__file__).resolve().parents[1]))
PHP = os.environ.get("PHP_BIN") or shutil.which("php")

@unittest.skipUnless(PHP, "PHP is required for isolated HTTP tests")
class HttpPrivacyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password = "Only-In-Isolated-Fixture-721"
        cls.password_hash = subprocess.check_output(
            [PHP, "-r", "echo password_hash($argv[1],PASSWORD_DEFAULT);", cls.password],
            text=True,
        ).strip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="altoidss-http-privacy-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(APP / "api", self.root / "api", ignore=shutil.ignore_patterns(
            "secrets.local.php", "mal-client-id.local.txt", "__pycache__"))
        shutil.copy2(APP / "server-router.php", self.root / "server-router.php")
        for name in ("data", "backups", "runtime", "config", "tools", "tests", "outputs", "docs", "Html", "css", "js", "img"):
            (self.root / name).mkdir(exist_ok=True)
        for name in ("index", "catalogo", "dashboard", "favoritos", "login", "noticias"):
            (self.root / "Html" / (name + ".html")).write_text("<!doctype html><title>Fixture</title>", encoding="utf-8")
        for name, body in (("css/site.css", "body{color:black}"), ("js/site.js", "const fixture = true;"),
                           ("img/logo.svg", '<svg xmlns="http://www.w3.org/2000/svg"></svg>')):
            (self.root / name).write_text(body, encoding="utf-8")
        for name in ("peliculas", "series", "perfiles", "configuraciones", "favoritos", "historial",
                     "anime-revisiones", "anime-sheet-writeback"):
            self.write(name + ".json", [])
        self.write("anime.json", [
            {"id": "visible", "title": "Visible", "type": "anime", "status": "Activo"},
            {"id": "hidden", "title": "Private hidden", "type": "anime", "status": "Oculto"},
        ])
        self.write("noticias.json", [
            {"id": "published", "title": "Public", "status": "publicada"},
            {"id": "draft", "title": "Private draft", "status": "borrador"},
            {"id": "archived", "title": "Private archive", "status": "archivada"},
            {"id": "hidden-news", "title": "Hidden public", "status": "publicada", "visibilityStatus": "Oculto"},
        ])
        self.write("usuarios.json", [
            {"id": "fixture-admin", "name": "Fixture admin", "email": "admin@example.invalid",
             "passwordHash": self.password_hash, "role": "admin", "status": "Activo"},
            {"id": "fixture-user", "name": "Fixture user", "email": "user@example.invalid",
             "passwordHash": self.password_hash, "role": "usuario", "status": "Activo"},
        ])
        for name in ("runtime/private.json", "config/private.json", "backups/private.json",
                     "tools/private.json", "tests/private.json", "outputs/private.json", "docs/private.json",
                     "img/private.json"):
            (self.root / name).write_text('{"sentinel":"FIXTURE_PRIVATE"}', encoding="utf-8")
        for name in ("api/config/fixture-private.php", "img/private.php", "private.php"):
            (self.root / name).write_text("<?php echo 'FIXTURE_PRIVATE';", encoding="utf-8")
        (self.root / "README.md").write_text("FIXTURE_PRIVATE", encoding="utf-8")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.environment = dict(os.environ)
        for key in list(self.environment):
            if key.startswith(("ALTOIDSS_", "WATCHMODE", "MAL_")):
                self.environment.pop(key, None)
        self.server = subprocess.Popen(
            [PHP, "-S", f"127.0.0.1:{self.port}", "-t", ".", "server-router.php"],
            cwd=self.root, env=self.environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.addCleanup(self.stop_server)
        for _ in range(80):
            try:
                if self.request("/Html/index.html")[0] == 200:
                    return
            except OSError:
                pass
            time.sleep(.05)
        self.fail("Fixture HTTP server did not start")

    def stop_server(self):
        if self.server.poll() is None:
            self.server.terminate()
            try:
                self.server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait(timeout=5)

    def write(self, name, value):
        (self.root / "data" / name).write_text(json.dumps(value), encoding="utf-8")

    def request(self, path, method="GET", body=None, cookie=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        try:
            connection.request(method, path, None if body is None else json.dumps(body), headers)
            response = connection.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            connection.close()

    def login(self, role):
        status, body, headers = self.request("/api/index.php?route=/auth/login", "POST",
            {"email": role + "@example.invalid", "password": self.password})
        self.assertEqual(status, 200, body)
        return headers["Set-Cookie"].split(";", 1)[0]

    def test_public_pages_and_static_assets_remain_available(self):
        for name in ("index", "catalogo", "dashboard", "favoritos", "login", "noticias"):
            self.assertEqual(self.request("/Html/" + name + ".html")[0], 200)
        for path in ("/css/site.css?v=1", "/js/site.js", "/img/logo.svg"):
            self.assertEqual(self.request(path)[0], 200)

    def test_root_redirect_remains_available(self):
        status, _, headers = self.request("/")
        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], "/Html/index.html")

    def test_private_directory_capitalization_does_not_bypass_policy(self):
        paths = ("/DATA/usuarios.json", "/Data/usuarios.json", "/RUNTIME/private.json",
                 "/Runtime/private.json", "/CONFIG/private.json", "/Backups/private.json",
                 "/TOOLS/private.json", "/TESTS/private.json", "/Outputs/private.json")
        for path in paths:
            with self.subTest(path=path):
                status, body, _ = self.request(path)
                self.assertEqual(status, 404)
                self.assertNotIn(b"FIXTURE_PRIVATE", body)
                self.assertNotIn(self.password_hash.encode(), body)

    def test_only_api_entry_can_execute_php(self):
        for path in ("/API/config/fixture-private.php", "/img/private.php", "/private.php",
                     "/server-router.php", "/api/index.php/extra"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_nonpublic_files_are_not_served_from_public_directories(self):
        for path in ("/img/private.json", "/docs/private.json", "/README.md",
                     "/data/anime-sheet-writeback.json"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_private_target_cannot_be_exposed_by_public_symlink(self):
        try:
            (self.root / "img/exposed.png").symlink_to(self.root / "config/private.json")
        except OSError:
            self.skipTest("Symbolic links require OS permission")
        self.assertEqual(self.request("/img/exposed.png")[0], 404)

    def test_dot_segments_and_ntfs_streams_are_denied(self):
        for path in ("/img/../data/usuarios.json", "/img/%2e%2e/data/usuarios.json",
                     "/%252e%252e/data/usuarios.json", "/img/logo.svg::$DATA"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_public_catalog_json_filters_hidden_content(self):
        status, body, _ = self.request("/data/anime.json")
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in json.loads(body)], ["visible"])
        self.assertNotIn(b"Private hidden", body)

    def test_public_news_json_filters_editorial_state_and_hidden(self):
        status, body, _ = self.request("/data/noticias.json")
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in json.loads(body)], ["published"])

    def test_anonymous_news_api_does_not_return_drafts(self):
        status, body, _ = self.request("/api/index.php?route=/news")
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in json.loads(body)["data"]], ["published"])

    def test_normal_user_news_api_does_not_return_drafts(self):
        cookie = self.login("user")
        status, body, _ = self.request("/api/index.php?route=/news", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in json.loads(body)["data"]], ["published"])

    def test_admin_retains_editorial_management(self):
        cookie = self.login("admin")
        status, body, _ = self.request("/api/index.php?route=/news", cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual({row["id"] for row in json.loads(body)["data"]},
                         {"published", "draft", "archived"})

if __name__ == "__main__":
    unittest.main()
