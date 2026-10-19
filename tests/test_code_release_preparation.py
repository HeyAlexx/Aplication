import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import prepare_code_release as release


class CodeReleasePreparationTests(unittest.TestCase):
    def test_package_allowlist(self):
        for path in ('api/config/app.php', 'api/config/catalog-storage.php',
                     'Html/catalogo.html', 'tools/storage_transaction.py', 'img/logo.png'):
            self.assertTrue(release.code_path(path), path)
        for path in ('data/anime.json', 'api/config/secrets.local.php',
                     'api/config/mal-client-id.local.txt', 'config/anime-sync.json',
                     'runtime/google-token.json', 'outputs/test.js', 'backups/test.php',
                     'tools/__pycache__/test.py', 'tools/node_modules/test.js',
                     '../api/test.php', 'api\\test.php', '/api/test.php', 'api/file:stream.php',
                     'iniciar-sincronizacion-anime.cmd', 'img/program.exe'):
            self.assertFalse(release.code_path(path), path)

    def test_local_changes_are_classified_without_automatic_merge(self):
        classify = release.local_classification
        self.assertEqual(classify(b'base\n', b'base\r\n', b'new\n'), 'format-only')
        self.assertEqual(classify(b'base', b'new', b'new'), 'already-in-candidate')
        self.assertEqual(classify(b'base', b'local', b'base'), 'production-only-review')
        self.assertEqual(classify(b'base', b'local', b'new'), 'overlap-review')
        self.assertEqual(classify(None, b'local', b'new'), 'untracked-collision-review')
        self.assertEqual(classify(b'base', None, b'new'), 'local-deletion-review')
        self.assertEqual(classify(b'base', b'local', None), 'preserve-outside-payload')

    def setup_workspace(self):
        directory = tempfile.TemporaryDirectory(prefix='altoidss-release-')
        self.addCleanup(directory.cleanup)
        workspace = Path(directory.name)
        source = workspace / 'Desarrollo' / 'Aplication'
        production = workspace / 'ProyectoFinal' / 'Aplication'
        for repo in (source, production):
            repo.mkdir(parents=True)
            release.git(repo, 'init', '-q')
            release.git(repo, 'config', 'user.name', 'Release test')
            release.git(repo, 'config', 'user.email', 'qa@example.invalid')
            release.git(repo, 'config', 'core.autocrlf', 'false')
            (repo / 'api' / 'config').mkdir(parents=True)
            (repo / 'tools').mkdir()
            (repo / 'data').mkdir()
            (repo / 'server-router.php').write_bytes(b'<?php // committed-router\n')
            (repo / 'api' / 'config' / 'catalog-storage.php').write_bytes(b'<?php // central\n')
            (repo / 'tools' / 'storage_transaction.py').write_bytes(b'# transaction\n')
            (repo / 'data' / 'usuarios.json').write_text('[{"id":"private-fixture"}]')
            (repo / 'api' / 'local.php').write_bytes(b'<?php // base\n')
            release.git(repo, 'add', '.')
            release.git(repo, 'commit', '-qm', 'fixture')
        catalog = workspace / 'datos' / 'produccion' / 'catalogo'
        state = workspace / 'datos' / 'produccion' / 'anime-sync'
        catalog.mkdir(parents=True)
        state.mkdir(parents=True)
        (catalog / 'anime.json').write_text('[{"id":"production-fixture"}]')
        (production.parent / 'catalog-storage.local.json').write_text(json.dumps({
            'environment': 'produccion', 'catalogDir': str(catalog), 'syncStateDir': str(state)}))
        return workspace, source, production

    def test_pinned_commit_ignores_dirty_development_and_preserves_production(self):
        workspace, source, production = self.setup_workspace()
        commit = release.git(source, 'rev-parse', 'HEAD').decode().strip()
        (source / 'server-router.php').write_bytes(b'DIRTY DEVELOPMENT DO NOT EXPORT')
        local = production / 'api' / 'local.php'
        local.write_bytes(b'<?php // unique-production-edit\n')
        (source / 'api' / 'config' / 'secrets.local.php').write_text('PRIVATE NOT TRACKED')
        before = release.protected_hashes(workspace, production)
        output, report = release.prepare(workspace, source, commit)
        self.assertEqual((output / 'code' / 'server-router.php').read_bytes(), b'<?php // committed-router\n')
        self.assertFalse((output / 'code' / 'data').exists())
        self.assertFalse((output / 'code' / 'api' / 'config' / 'secrets.local.php').exists())
        self.assertEqual((output / 'production-local' / 'api' / 'local.php').read_bytes(), local.read_bytes())
        self.assertEqual(report['summary'], {'production-only-review': 1})
        self.assertFalse(report['productionModified'])
        self.assertFalse(report['sheetsStarted'])
        self.assertEqual(release.protected_hashes(workspace, production), before)
        self.assertEqual(json.loads((output / 'manifest.json').read_text(encoding='utf-8'))['commit'], commit)

    def test_requires_fixed_sha_separate_checkout_and_production_descriptor(self):
        workspace, source, production = self.setup_workspace()
        commit = release.git(source, 'rev-parse', 'HEAD').decode().strip()
        with self.assertRaisesRegex(ValueError, 'SHA completo'):
            release.prepare(workspace, source, 'HEAD')
        with self.assertRaisesRegex(ValueError, 'checkout separado'):
            release.prepare(workspace, production, commit)
        (production.parent / 'catalog-storage.local.json').unlink()
        with self.assertRaisesRegex(ValueError, 'descriptor'):
            release.prepare(workspace, source, commit)

    def test_protected_fingerprints_detect_data_and_secret_changes(self):
        workspace, _, production = self.setup_workspace()
        key = production / 'api' / 'config' / 'secrets.local.php'
        key.write_text('fixture-only-one')
        before = release.protected_hashes(workspace, production)
        key.write_text('fixture-only-two')
        self.assertNotEqual(before, release.protected_hashes(workspace, production))
        before = release.protected_hashes(workspace, production)
        (production / 'data' / 'usuarios.json').write_text('[]')
        self.assertNotEqual(before, release.protected_hashes(workspace, production))

    def test_read_rejects_path_outside_checkout(self):
        with tempfile.TemporaryDirectory(prefix='altoidss-boundary-') as directory:
            root = Path(directory) / 'app'
            root.mkdir()
            with self.assertRaisesRegex(ValueError, 'fuera'):
                release.read_inside(root, '../private.txt')
            (root / 'directory.php').mkdir()
            with self.assertRaisesRegex(ValueError, 'directorio'):
                release.read_inside(root, 'directory.php')

    def test_data_drift_leaves_no_validated_manifest(self):
        workspace, source, production = self.setup_workspace()
        commit = release.git(source, 'rev-parse', 'HEAD').decode().strip()
        before = release.protected_hashes(workspace, production)
        with patch.object(release, 'protected_hashes', side_effect=[before, {**before, 'changed': 'fixture'}]):
            with self.assertRaisesRegex(RuntimeError, 'Producción cambió'):
                release.prepare(workspace, source, commit)
        self.assertEqual(list((workspace / 'work' / 'installation-plans').glob('*/manifest.json')), [])


if __name__ == '__main__':
    unittest.main()
