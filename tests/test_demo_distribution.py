"""Nueva entrega: Git limpio, ZIP reproducible, aislamiento y HTTP real con fixtures."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_demo_distribution import build, smoke
from qa import public_code
from run_demo import check, start, stop

PHP = os.environ.get('PHP_BIN') or shutil.which('php')
GIT = shutil.which('git')


@unittest.skipUnless(PHP and GIT, 'PHP and Git required for isolated distribution qualification')
class DemoDistributionTests(unittest.TestCase):
    @classmethod
    def git(cls, source, *args):
        return subprocess.check_output([GIT, '-c', 'safe.directory=' + source.as_posix(),
            '-c', 'user.name=QA Demo', '-c', 'user.email=qa@example.invalid', '-c', 'commit.gpgsign=false',
            '-c', 'core.autocrlf=false', '-c', 'core.hooksPath=' + str(cls.root / 'empty-hooks'),
            '-C', str(source), *args], stderr=subprocess.PIPE)

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='altoidss-demo-tests-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name).resolve()
        (cls.root / 'empty-hooks').mkdir()
        cls.source = cls.root / 'source'
        cls.source.mkdir()
        for name, data in public_code(ROOT).items():
            path = cls.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        cls.git(cls.source, 'init', '--template=')
        cls.git(cls.source, 'add', '--', '.')
        cls.git(cls.source, 'commit', '-m', 'Synthetic distribution source snapshot')
        cls.output = cls.root / 'baseline-package'
        cls.built = build(cls.output, cls.source)

    def unpack(self, name):
        target = self.root / name
        target.mkdir()
        with zipfile.ZipFile(self.output / 'demo.zip') as archive:
            archive.extractall(target)  # Own ZIP already produced from this synthetic Git source.
        return target, target / 'Aplicacion'

    def test_zip_is_reproducible_and_has_no_preloaded_accounts(self):
        second = self.root / 'second-package'
        build(second, self.source)
        self.assertEqual((second / 'demo.zip').read_bytes(), (self.output / 'demo.zip').read_bytes())
        with zipfile.ZipFile(second / 'demo.zip') as archive:
            for name in ('usuarios', 'perfiles', 'configuraciones', 'favoritos', 'historial'):
                self.assertEqual(json.loads(archive.read('Aplicacion/data/' + name + '.json')), [])
                self.assertEqual(archive.read('Aplicacion/data/' + name + '.json'), b'[]\n')
            self.assertNotIn(b'\r\n', archive.read('fixture-storage.json'))
            self.assertIn(b'\r\n', archive.read('Iniciar-Demo.cmd'))
            descriptor = json.loads(archive.read('fixture-storage.json'))
            self.assertEqual(descriptor['catalogDir'], 'fixture-catalog')
            self.assertNotIn(str(self.root), archive.read('fixture-storage.json').decode())

    def test_dirty_code_and_private_working_files_are_not_exported(self):
        path = self.source / 'js/login.js'
        before = path.read_bytes()
        private = self.source / 'api/config/secrets.local.php'
        self.addCleanup(path.write_bytes, before)
        self.addCleanup(private.unlink, missing_ok=True)
        path.write_bytes(b'WORKING_COPY_NOT_COMMITTED')
        private.write_text('PRIVATE_WORKING_FILE_NOT_TO_EXPORT', encoding='utf-8')
        output = self.root / 'dirty-source-package'
        build(output, self.source)
        with zipfile.ZipFile(output / 'demo.zip') as archive:
            self.assertEqual(archive.read('Aplicacion/js/login.js'), before)
            self.assertNotIn('Aplicacion/api/config/secrets.local.php', archive.namelist())

    def test_existing_output_is_preserved(self):
        target = self.root / 'existing-output'
        target.mkdir()
        sentinel = target / 'keep.txt'
        sentinel.write_text('PRESERVE', encoding='utf-8')
        with self.assertRaises(ValueError):
            build(target, self.source)
        self.assertEqual(sentinel.read_text(), 'PRESERVE')
        self.assertEqual(list(target.iterdir()), [sentinel])

    def test_committed_operational_data_refuses_build_before_output_creation(self):
        source = self.root / 'forbidden-source'
        (source / 'data').mkdir(parents=True)
        (source / 'data/usuarios.json').write_text('[]', encoding='utf-8')
        self.git(source, 'init', '--template=')
        self.git(source, 'add', '--', 'data/usuarios.json')
        self.git(source, 'commit', '-m', 'Synthetic unsafe source')
        output = self.root / 'forbidden-output'
        with self.assertRaises(ValueError):
            build(output, source)
        self.assertFalse(output.exists())

    def test_non_demo_installation_is_refused_without_writes(self):
        app = self.root / 'not-a-demo/Aplicacion'
        app.mkdir(parents=True)
        with self.assertRaises(ValueError):
            check(app, PHP)
        self.assertEqual(list(app.iterdir()), [])
        self.assertFalse((app.parent / 'fixture-storage.json').exists())

    def test_tampered_router_is_refused_before_runtime_writes(self):
        bundle, app = self.unpack('tampered-demo')
        descriptor = (bundle / 'fixture-storage.json').read_bytes()
        (app / 'server-router.php').write_text('<?php echo "TAMPERED";', encoding='utf-8')
        with self.assertRaises(ValueError):
            start(app, PHP, 8093)
        self.assertEqual((bundle / 'fixture-storage.json').read_bytes(), descriptor)
        self.assertFalse((app / 'backups/sessions').exists())

    def test_inherited_storage_is_ignored_and_external_files_unchanged(self):
        bundle, app = self.unpack('isolated-demo')
        outside = self.root / 'outside-state.json'
        outside.write_text('EXTERNAL_STATE_MUST_NOT_CHANGE', encoding='utf-8')
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        with mock.patch.dict(os.environ, {'ALTOIDSS_STORAGE_CONFIG': str(outside), 'WATCHMODE_API_KEY': 'QA_IGNORED'}):
            server = start(app, PHP, port)
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            for attempt in range(60):
                try:
                    with opener.open(f'http://127.0.0.1:{port}/data/anime.json', timeout=2) as response:
                        rows = json.load(response)
                    break
                except OSError:
                    time.sleep(.1)
            else:
                self.fail('Demo did not read its own fictitious catalog')
            self.assertEqual(len(rows), 90)
            self.assertTrue(all(row['id'].startswith('qa-anime-') for row in rows))
            self.assertEqual(outside.read_text(), 'EXTERNAL_STATE_MUST_NOT_CHANGE')
            settings = json.loads((bundle / 'fixture-storage.json').read_text())
            self.assertEqual(Path(settings['catalogDir']), bundle / 'fixture-catalog')
        finally:
            stop(server)

    def test_zip_traversal_is_refused_without_escape(self):
        archive = self.root / 'unsafe.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('../escape.txt', 'MUST_NOT_BE_EXTRACTED')
        # Even if the guard regressed, the parent of extraction belongs to this test.
        with mock.patch.object(tempfile, 'tempdir', str(self.root)):
            with self.assertRaises(ValueError):
                smoke(archive, PHP)
        self.assertFalse((self.root / 'escape.txt').exists())

    def test_exact_zip_passes_http_privacy_and_authentication(self):
        result = smoke(self.output / 'demo.zip', PHP)
        self.assertEqual(result['status'], 'DEMO_STAGING_PASSED')
        self.assertEqual(result['privateRoutesBlocked'], 12)
        self.assertTrue(result['registrationLoginLogoutPassed'])
        self.assertTrue(result['serverClosed'])
        self.assertFalse(result['usesProductionData'])

    def test_zip_aliases_and_case_collisions_are_refused_before_extraction(self):
        cases = [('Aplicacion//unsafe.php',), ('Aplicacion/./unsafe.php',),
                 ('Aplicacion/js/site.js', 'Aplicacion/JS/site.js'), ('Aplicacion/NUL.json',),
                 ('Aplicacion/config./secret.json',), ('Aplicacion/COM¹.txt',), ('C:/escape.txt',)]
        for number, names in enumerate(cases):
            archive = self.root / ('alias-' + str(number) + '.zip')
            with zipfile.ZipFile(archive, 'w') as z:
                for name in names:
                    z.writestr(name, 'SYNTHETIC_UNSAFE_ENTRY')
            with self.subTest(names=names), self.assertRaises(ValueError):
                smoke(archive, PHP)


if __name__ == '__main__':
    unittest.main()
