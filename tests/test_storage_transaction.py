"""Real PHP/Python process locks and crash recovery; only temporary fixtures."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from storage_transaction import atomic_json, commit_collections, file_lock, storage_lock
import test_catalog_completeness
import anime_sync_pipeline as sync

PHP = shutil.which('php') or ('C:/xampp/php/php.exe' if Path('C:/xampp/php/php.exe').exists() else None)
BOOT = "require $argv[1].'/api/core/ApiException.php'; require $argv[1].'/api/core/JsonStorage.php'; "


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='altoidss-transaction-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def php(self, script, *args):
        return subprocess.run([PHP, '-r', script, str(ROOT), str(self.directory), *args],
                              capture_output=True, text=True, timeout=25, check=True).stdout.strip()

    @unittest.skipUnless(PHP, 'PHP not available')
    def test_python_lock_excludes_php(self):
        with file_lock(self.directory / '.storage.lock'):
            result = self.php("$h=fopen($argv[2].'/.storage.lock','c+b'); echo flock($h,LOCK_EX|LOCK_NB)?'unsafe':'blocked';")
        self.assertEqual(result, 'blocked')

    @unittest.skipUnless(PHP, 'PHP not available')
    def test_php_lock_excludes_python(self):
        script = "$h=fopen($argv[1],'c+b'); flock($h,LOCK_EX); echo 'ready'.PHP_EOL; fflush(STDOUT); fgets(STDIN);"
        proc = subprocess.Popen([PHP, '-r', script, str(self.directory / '.storage.lock')],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(proc.stdout.readline().strip(), 'ready')
            with self.assertRaises(RuntimeError):
                with file_lock(self.directory / '.storage.lock', timeout=0):
                    self.fail('Python entered a PHP-owned lock')
        finally:
            proc.communicate('\n', timeout=10)
            proc.stdout.close()
            proc.stderr.close()

    def seed_interrupted(self):
        files = {'anime.json': [{'id':'a','title':'Approved'}],
                 'anime-sheet-writeback.json': [{'sourceCode':'9001','version':'new'}]}
        atomic_json(self.directory / 'anime.json', [{'id':'a','title':'Old'}])
        atomic_json(self.directory / '.transaction.json', {'version':1,'files':files})
        # Simulate a crash after one collection was replaced.
        atomic_json(self.directory / 'anime.json', files['anime.json'])
        return files

    def test_python_rolls_forward_catalog_and_queue(self):
        files = self.seed_interrupted()
        with storage_lock(self.directory):
            for name, records in files.items():
                self.assertEqual(json.loads((self.directory / name).read_text()), records)
        self.assertFalse((self.directory / '.transaction.json').exists())

    @unittest.skipUnless(PHP, 'PHP not available')
    def test_php_recovers_python_journal(self):
        files = self.seed_interrupted()
        self.php(BOOT + "$s=new JsonStorage($argv[2],$argv[2].'/backups'); $s->read('anime.json'); echo 'recovered';")
        for name, records in files.items():
            self.assertEqual(json.loads((self.directory / name).read_text()), records)
        self.assertFalse((self.directory / '.transaction.json').exists())

    @unittest.skipUnless(PHP, 'PHP not available')
    def test_php_exception_before_journal_preserves_original(self):
        atomic_json(self.directory / 'anime.json', [{'title':'Old'}])
        script = BOOT + "$s=new JsonStorage($argv[2],$argv[2].'/backups'); try {$s->transaction(function()use($s){$s->write('anime.json',[['title'=>'New']]); throw new Exception('abort');});}catch(Exception $e){}"
        self.php(script)
        self.assertEqual(json.loads((self.directory / 'anime.json').read_text()), [{'title':'Old'}])
        self.assertFalse((self.directory / '.transaction.json').exists())

    @unittest.skipUnless(PHP, 'PHP not available')
    def test_concurrent_php_updates_do_not_lose_rows(self):
        atomic_json(self.directory / 'anime.json', [])
        script = BOOT + "$s=new JsonStorage($argv[2],$argv[2].'/backups'); $s->transaction(function()use($s){$r=$s->read('anime.json'); usleep(10000); $r[]=['id'=>getmypid()]; $s->write('anime.json',$r);});"
        processes = [subprocess.Popen([PHP,'-r',script,str(ROOT),str(self.directory)],
                                     stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(8)]
        for process in processes:
            out, err = process.communicate(timeout=25)
            self.assertEqual(process.returncode, 0, err.decode())
        self.assertEqual(len(json.loads((self.directory / 'anime.json').read_text())), 8)

    def test_watcher_lock_exclusive_across_processes(self):
        script = "import sys; from pathlib import Path; from storage_transaction import file_lock;\ntry:\n with file_lock(Path(sys.argv[1]),timeout=0): print('entered')\nexcept RuntimeError: print('blocked')"
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'tools'), PYTHONDONTWRITEBYTECODE='1')
        with file_lock(self.directory / '.watcher.lock'):
            output = subprocess.check_output([sys.executable,'-c',script,str(self.directory / '.watcher.lock')],env=env,text=True)
            independent = subprocess.check_output([sys.executable,'-c',script,str(self.directory / 'other' / '.watcher.lock')],env=env,text=True)
        self.assertEqual(output.strip(), 'blocked')
        self.assertEqual(independent.strip(), 'entered')


class ConcurrentSyncTests(unittest.TestCase):
    setUp = test_catalog_completeness.CompletenessTests.setUp

    def test_approval_during_source_read_is_not_overwritten(self):
        def concurrent_read(*args):
            with storage_lock(sync.ANIME_PATH.parent):
                commit_collections(sync.ANIME_PATH.parent,
                                   {sync.ANIME_PATH.name:[{'id':'approved','title':'User decision'}]})
            return [self.row]
        with patch.object(sync,'read_live_google_catalog',side_effect=concurrent_read), \
             patch.object(sync,'flush_sheet_writebacks',return_value=0), \
             patch.object(sync,'best_candidate',return_value=(None,0,[])):
            with self.assertRaisesRegex(RuntimeError, 'no se sobrescribió'):
                sync.process_once(self.args)
        self.assertEqual(sync.load_json(sync.ANIME_PATH,[])[0]['title'], 'User decision')


if __name__ == '__main__':
    unittest.main()
