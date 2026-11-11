"""Operator refuses unattended secret input and never echoes rejected password arguments."""
from pathlib import Path
import os
import subprocess
import sys
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ProtectedOperatorTests(unittest.TestCase):
    def run_operator(self,extra=(),input_text=""):
        return subprocess.run([sys.executable,"-B",str(ROOT/"tools/reset-account-password.py"),
            "--app","C:/Users/Alvar/Projects/Altoids/ProyectoFinal/Aplication",*extra],
            input=input_text,capture_output=True,text=True,encoding="utf-8",timeout=10,
            env={**os.environ,"PYTHONUTF8":"1"})

    def test_noninteractive_pipe_cannot_reset_a_real_account(self):
        sentinel="Only-a-fixture-secret-never-echo-this"
        run=self.run_operator(input_text=sentinel)
        self.assertEqual(run.returncode,2)
        self.assertNotIn(sentinel,run.stdout+run.stderr)
        self.assertIn("terminal",run.stderr)

    def test_password_arguments_are_rejected_without_echo(self):
        sentinel="Only-a-fixture-secret-in-rejected-argument"
        run=self.run_operator(("--password",sentinel))
        self.assertEqual(run.returncode,2)
        self.assertNotIn(sentinel,run.stdout+run.stderr)

    def test_php_helper_rejects_other_roots_without_writes(self):
        php=os.environ.get("PHP_BIN") or shutil.which("php") or "php"
        if not Path(php).is_file() and not shutil.which(php):self.skipTest("PHP required")
        with tempfile.TemporaryDirectory(prefix="altoidss-reset-denied-") as temporary:
            root=Path(temporary)
            sentinel="Fixture-secret-never-echo"
            run=subprocess.run([php,str(ROOT/"tools/account-security.php"),str(root),"reset"],
                input=sentinel,capture_output=True,text=True,encoding="utf-8",timeout=10)
            self.assertEqual(run.returncode,1)
            self.assertEqual(list(root.iterdir()),[])
            self.assertNotIn(sentinel,run.stdout+run.stderr)

if __name__=="__main__":unittest.main()

