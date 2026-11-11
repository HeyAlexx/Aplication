"""Account transactions use only private temporary fixtures, never application data."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP = Path(os.environ.get("ALTOIDSS_TEST_SOURCE", Path(__file__).resolve().parents[1]))
PHP = os.environ.get("PHP_BIN") or shutil.which("php") or (
    "C:/xampp/php/php.exe" if Path("C:/xampp/php/php.exe").exists() else None
)
BOOT = """require $argv[1].'/api/core/ApiException.php';
require $argv[1].'/api/core/JsonStorage.php';
require $argv[1].'/api/services/AuthService.php';
session_save_path($argv[2].'/sessions'); session_start();
$s=new JsonStorage($argv[2].'/data',$argv[2].'/backups'); $auth=new AuthService($s);
"""

@unittest.skipUnless(PHP, "PHP is required for transaction tests")
class AuthTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="altoidss-auth-transaction-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("data", "backups", "sessions"):
            (self.root / name).mkdir()
        for name in ("usuarios", "perfiles", "configuraciones"):
            (self.root / "data" / (name + ".json")).write_text("[]", encoding="utf-8")

    def records(self, name):
        return json.loads((self.root / "data" / (name + ".json")).read_text(encoding="utf-8"))

    def parallel(self, same_email=False):
        script = BOOT + """
fwrite(STDERR,'ready'.PHP_EOL); fflush(STDERR); fgets(STDIN);
try {
    $u=$auth->register(['name'=>'Fixture '.$argv[3], 'email'=>$argv[4],
                       'password'=>'Fixture-Only-Transaction-918','role'=>'admin']);
    echo json_encode(['status'=>201,'id'=>$u['id']]);
} catch(ApiException $e) { echo json_encode(['status'=>$e->statusCode()]); }
"""
        processes = []
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for key in list(environment):
            if key.startswith("ALTOIDSS_"):
                environment.pop(key, None)
        try:
            for number in range(8):
                email = "same@example.invalid" if same_email else f"fixture-{number}@example.invalid"
                processes.append(subprocess.Popen(
                    [PHP, "-d", "log_errors=0", "-r", script, str(APP), str(self.root), str(number), email],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", env=environment,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
            for process in processes:
                self.assertEqual(process.stderr.readline().strip(), "ready")
            for process in processes:
                process.stdin.write("\n")
                process.stdin.flush()
            results = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=35)
                self.assertEqual(process.returncode, 0, stderr)
                self.assertEqual(stderr, "")
                results.append(json.loads(stdout))
            return results
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)

    def test_parallel_registrations_preserve_all_accounts_and_relations(self):
        results = self.parallel()
        self.assertEqual([r["status"] for r in results], [201] * 8)
        users = self.records("usuarios")
        self.assertEqual(len(users), 8)
        ids = {row["id"] for row in users}
        self.assertEqual(len(ids), 8)
        self.assertEqual({row["role"] for row in users}, {"usuario"})
        self.assertEqual({row["userId"] for row in self.records("perfiles")}, ids)
        self.assertEqual({row["userId"] for row in self.records("configuraciones")}, ids)
        self.assertEqual(len(self.records("perfiles")), 8)
        self.assertEqual(len(self.records("configuraciones")), 8)

    def test_parallel_same_email_has_one_success_and_conflicts(self):
        results = self.parallel(same_email=True)
        self.assertEqual(sum(r["status"] == 201 for r in results), 1)
        self.assertEqual(sum(r["status"] == 409 for r in results), 7)
        for name in ("usuarios", "perfiles", "configuraciones"):
            self.assertEqual(len(self.records(name)), 1)

    def test_failed_profile_creation_does_not_leave_an_account(self):
        (self.root / "data/perfiles.json").write_text("{invalid", encoding="utf-8")
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root / "data").glob("*.json")}
        script = BOOT + """
try {
    $auth->register(['name'=>'Fixture','email'=>'fixture@example.invalid',
                     'password'=>'Fixture-Only-Transaction-918']);
    echo 'unexpected-success';
} catch(ApiException $e) { echo 'failed-before-commit'; }
"""
        result = subprocess.run(
            [PHP, "-d", "log_errors=0", "-r", script, str(APP), str(self.root)],
            capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "failed-before-commit")
        self.assertEqual({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root / "data").glob("*.json")}, before)
        self.assertFalse((self.root / "data/.transaction.json").exists())

if __name__ == "__main__":
    unittest.main()
