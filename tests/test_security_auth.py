"""Authentication regressions use the HTTP fixture, never real accounts or providers."""
import json
import subprocess
import time
import unittest
import test_http_privacy as fixtures

class AuthSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.HttpPrivacyTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.HttpPrivacyTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()

    def change_admin(self, change):
        path = self.fixture.root / "data/usuarios.json"
        users = json.loads(path.read_text(encoding="utf-8"))
        change(users)
        path.write_text(json.dumps(users), encoding="utf-8")

    def protected(self, cookie):
        return self.fixture.request("/api/index.php?route=/reviews/anime", cookie=cookie)[0]

    def edit_session(self, cookie, php):
        sid = cookie.split("=",1)[1]
        code = "session_save_path($argv[1]);session_id($argv[2]);session_start();" + php + ";session_write_close();"
        run = subprocess.run([fixtures.PHP,"-r",code,
                              str(self.fixture.root/"backups/sessions"),sid],
                             capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,0,run.stderr)

    def test_valid_session_remains_usable(self):
        self.assertEqual(self.protected(self.fixture.login("admin")),200)

    def test_malformed_credentials_fail_without_php_warnings(self):
        for payload in ({"email":[],"password":"fixture"},{"email":"admin@example.invalid","password":{}}):
            status,body,_=self.fixture.request("/api/index.php?route=/auth/login","POST",payload)
            self.assertEqual(status,401)
            self.assertFalse(json.loads(body)["ok"])

    def test_revoked_auth_version_rejects_existing_session(self):
        cookie=self.fixture.login("admin")
        self.change_admin(lambda users:users[0].update(authVersion=20))
        self.assertEqual(self.protected(cookie),401)

    def test_inactive_account_rejects_existing_session(self):
        cookie=self.fixture.login("admin")
        self.change_admin(lambda users:users[0].update(status="Inactivo"))
        self.assertEqual(self.protected(cookie),401)

    def test_removed_account_rejects_existing_session(self):
        cookie=self.fixture.login("admin")
        self.change_admin(lambda users:users.pop(0))
        self.assertEqual(self.protected(cookie),401)

    def test_role_change_requires_authentication_again(self):
        cookie=self.fixture.login("admin")
        self.change_admin(lambda users:users[0].update(role="usuario"))
        self.assertEqual(self.protected(cookie),401)
        self.assertEqual(self.protected(self.fixture.login("admin")),403)

    def test_password_change_without_version_bump_also_revokes(self):
        cookie=self.fixture.login("admin")
        self.change_admin(lambda users:users[0].update(passwordHash="changed-by-fixture"))
        self.assertEqual(self.protected(cookie),401)

    def test_legacy_session_without_security_state_is_rejected(self):
        cookie=self.fixture.login("admin")
        self.edit_session(cookie,'unset($_SESSION["auth"])')
        self.assertEqual(self.protected(cookie),401)

    def test_idle_timeout_is_enforced_server_side(self):
        cookie=self.fixture.login("admin")
        self.edit_session(cookie,'$_SESSION["auth"]["seenAt"]=time()-1801')
        self.assertEqual(self.protected(cookie),401)

    def test_absolute_timeout_even_with_recent_activity(self):
        cookie=self.fixture.login("admin")
        self.edit_session(cookie,'$_SESSION["auth"]["issuedAt"]=time()-28801;$_SESSION["auth"]["seenAt"]=time()')
        self.assertEqual(self.protected(cookie),401)

    def test_inactive_account_cannot_log_in(self):
        self.change_admin(lambda users:users[0].update(status="Inactivo"))
        status,_,_=self.fixture.request("/api/index.php?route=/auth/login","POST",
            {"email":"admin@example.invalid","password":self.fixture.password})
        self.assertEqual(status,401)

    def test_public_identity_is_reloaded_from_the_account(self):
        cookie=self.fixture.login("admin")
        self.change_admin(lambda users:users[0].update(name="Updated fixture name"))
        status,body,_=self.fixture.request("/api/index.php?route=/auth/session",cookie=cookie)
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)["data"]["name"],"Updated fixture name")

    def test_login_limit_survives_new_sessions_and_recovers_after_window(self):
        route="/api/index.php?route=/auth/login"
        for _ in range(5):
            self.assertEqual(self.fixture.request(route,"POST",
                {"email":"admin@example.invalid","password":"incorrect fixture password"})[0],401)
        self.assertEqual(self.fixture.request(route,"POST",
            {"email":"admin@example.invalid","password":self.fixture.password})[0],429)
        path=self.fixture.root/"backups/security/attempts.json"
        attempts=json.loads(path.read_text(encoding="utf-8"))
        for row in attempts:row["expiresAt"]=int(time.time())-1
        path.write_text(json.dumps(attempts),encoding="utf-8")
        self.assertEqual(self.fixture.request(route,"POST",
            {"email":"admin@example.invalid","password":self.fixture.password})[0],200)

    def test_short_registration_password_is_rejected(self):
        before=(self.fixture.root/"data/usuarios.json").read_bytes()
        status,_,_=self.fixture.request("/api/index.php?route=/auth/register","POST",
            {"name":"Fixture","email":"new@example.invalid","password":"short6"})
        self.assertEqual(status,400)
        self.assertEqual((self.fixture.root/"data/usuarios.json").read_bytes(),before)

    def reset(self,password):
        script="""require $argv[1].'/api/core/ApiException.php';
require $argv[1].'/api/core/JsonStorage.php';
require $argv[1].'/api/services/AccountSecurityService.php';
$p=json_decode(stream_get_contents(STDIN),true);
$s=new JsonStorage($argv[2].'/data',$argv[2].'/backups');
try{echo json_encode(['status'=>200,'data'=>(new AccountSecurityService($s))->change('fixture-admin',$p['password'])]);}
catch(ApiException $e){echo json_encode(['status'=>$e->statusCode()]);}
"""
        run=subprocess.run([fixtures.PHP,"-r",script,str(fixtures.APP),str(self.fixture.root)],
            input=json.dumps({"password":password}),capture_output=True,text=True,encoding="utf-8",timeout=15)
        self.assertEqual(run.returncode,0,run.stderr)
        return json.loads(run.stdout)

    def test_reset_revokes_existing_cookie_and_new_password_works(self):
        cookie=self.fixture.login("admin")
        result=self.reset("A-New-Fixture-Passphrase-Only-921")
        self.assertEqual(result["status"],200)
        self.assertEqual(self.protected(cookie),401)
        route="/api/index.php?route=/auth/login"
        self.assertEqual(self.fixture.request(route,"POST",{"email":"admin@example.invalid","password":self.fixture.password})[0],401)
        status,body,_=self.fixture.request(route,"POST",{"email":"admin@example.invalid","password":"A-New-Fixture-Passphrase-Only-921"})
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)["data"]["id"],"fixture-admin")

    def test_revoke_only_preserves_password_and_requires_new_session(self):
        cookie=self.fixture.login("admin")
        self.assertEqual(self.reset(None)["status"],200)
        self.assertEqual(self.protected(cookie),401)
        self.assertEqual(self.protected(self.fixture.login("admin")),200)

    def test_weak_or_unchanged_reset_is_rejected_without_account_changes(self):
        path=self.fixture.root/"data/usuarios.json"
        before=path.read_bytes()
        for password in ("short",self.fixture.password):
            self.assertEqual(self.reset(password)["status"],400)
            self.assertEqual(path.read_bytes(),before)

if __name__=="__main__":
    unittest.main()

