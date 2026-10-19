import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
PHP = r'C:\xampp\php\php.exe'


class CentralStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='altoidss-central-')
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.catalog = root / 'catalog'
        self.catalog.mkdir()
        self.state = root / 'state'
        self.state.mkdir()
        (self.catalog / 'anime.json').write_text('[{"id":"central-only"}]', encoding='utf-8')
        self.descriptor = root / 'catalog-storage.local.json'
        self.descriptor.write_text(json.dumps({'catalogDir': str(self.catalog), 'syncStateDir': str(self.state)}))
        self.env = {**os.environ, 'ALTOIDSS_STORAGE_CONFIG': str(self.descriptor),
                    'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}

    def php(self, action):
        code = ('require "api/core/ApiException.php"; require "api/core/JsonStorage.php"; '
                '$s=new JsonStorage(realpath("data"),realpath("backups")); ' + action)
        return subprocess.run([PHP, '-r', code], cwd=APP, env=self.env,
                              capture_output=True, text=True)

    def test_api_reads_central_not_versioned_data(self):
        result = self.php('echo json_encode($s->read("anime.json"));')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [{'id': 'central-only'}])

    def test_api_writes_only_selected_central_environment(self):
        actual = APP / 'data/anime.json'
        before = actual.read_bytes()
        result = self.php('$s->write("anime.json", [["id"=>"test-write"]]);')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.catalog / 'anime.json').read_text()), [{'id': 'test-write'}])
        self.assertEqual(actual.read_bytes(), before)

    def test_private_accounts_stay_local(self):
        result = self.php('echo count($s->read("usuarios.json"));')
        expected = len(json.loads((APP / 'data/usuarios.json').read_text(encoding='utf-8')))
        self.assertEqual(int(result.stdout), expected)
        self.assertFalse((self.catalog / 'usuarios.json').exists())

    def test_missing_config_fails_closed_in_php(self):
        self.env['ALTOIDSS_STORAGE_CONFIG'] += '.missing'
        self.assertNotEqual(self.php('echo count($s->read("anime.json"));').returncode, 0)

    def test_new_worktree_can_resolve_same_descriptor_in_python(self):
        result = subprocess.run([os.sys.executable, '-c',
            'import catalog_storage as s; import json; print(json.dumps([str(s.CATALOG_DIR),str(s.SYNC_STATE_DIR)]))'],
            cwd=APP / 'tools', env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [str(self.catalog), str(self.state)])

    def test_missing_config_fails_closed_in_python(self):
        self.env['ALTOIDSS_STORAGE_CONFIG'] += '.missing'
        result = subprocess.run([os.sys.executable, '-c', 'import catalog_storage'],
            cwd=APP / 'tools', env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
