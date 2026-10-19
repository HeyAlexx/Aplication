import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import coordinated_recovery as recovery


class CoordinatedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='altoidss-coordinated-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.backup = self.root / 'independent-backup'
        for folder, environment in (('ProyectoFinal', 'produccion'), ('Desarrollo', 'desarrollo')):
            app = self.workspace / folder / 'Aplication'
            (app / 'data').mkdir(parents=True)
            (app / 'empty-folder').mkdir()
            for name in recovery.PRIVATE_FILES:
                (app / 'data' / name).write_text('[]')
            central = self.workspace / 'datos' / environment / 'catalogo'
            state = central.parent / 'anime-sync'
            central.mkdir(parents=True)
            state.mkdir()
            for name in recovery.CATALOG_FILES:
                records = [{'id': 'sheet', 'sourceCode': '01'}] if name == 'anime.json' else [{'sourceCode': '01', 'row': 2}] if name == 'anime-hoja.json' else []
                (central / name).write_text(json.dumps(records))
            (app.parent / 'catalog-storage.local.json').write_text(json.dumps({
                'environment': environment, 'catalogDir': str(central), 'syncStateDir': str(state)}))

    def test_paths_cannot_escape_or_use_windows_streams(self):
        for path in ('../secret', '/root', 'a\\b', 'a:stream', '.', 'a/./b'):
            with self.assertRaises(ValueError):
                recovery.safe_relative(path)

    def test_verified_copy_refuses_overwrite_and_bad_hash(self):
        source, target = self.root / 'source', self.root / 'target'
        source.write_bytes(b'original')
        with self.assertRaises(ValueError):
            recovery.copy_verified(source, target, 'wrong-hash')
        self.assertFalse(target.exists())
        recovery.copy_verified(source, target)
        with self.assertRaises(ValueError):
            recovery.copy_verified(source, target)
        self.assertEqual(target.read_bytes(), b'original')

    def test_snapshot_and_full_restore_use_backup_not_later_live_data(self):
        manifest = recovery.snapshot(self.workspace, self.backup)
        self.assertEqual(manifest['status'], 'VERIFIED')
        self.assertTrue((self.backup / 'payload' / 'ProyectoFinal' / 'Aplication' / 'empty-folder').is_dir())
        live = self.workspace / 'datos' / 'produccion' / 'catalogo' / 'anime.json'
        live.write_text('[{"id":"later-edit"}]')
        completed = SimpleNamespace(stdout=b'{"passed":true}', returncode=0)
        with patch.object(recovery.subprocess, 'run', return_value=completed):
            report = recovery.restore(self.workspace, self.backup, 'fixture-php')
        self.assertEqual(report['status'], 'PASSED')
        self.assertEqual(json.loads((Path(report['restoredTo']) / 'datos' / 'produccion' / 'catalogo' / 'anime.json').read_text())[0]['id'], 'sheet')
        self.assertEqual(json.loads(live.read_text())[0]['id'], 'later-edit')
        self.assertFalse(report['liveDataRestored'])

    def test_tampered_backup_is_rejected(self):
        recovery.snapshot(self.workspace, self.backup)
        (self.backup / 'payload' / 'datos' / 'produccion' / 'catalogo' / 'anime.json').write_text('[]')
        with self.assertRaises(ValueError):
            recovery.restore(self.workspace, self.backup, 'not-invoked')

    def test_live_destination_and_existing_backup_are_rejected(self):
        with self.assertRaises(ValueError):
            recovery.snapshot(self.workspace, self.workspace / 'nested-backup')
        self.backup.mkdir()
        (self.backup / 'user-file.txt').write_text('keep')
        with self.assertRaises(ValueError):
            recovery.snapshot(self.workspace, self.backup)
        self.assertEqual((self.backup / 'user-file.txt').read_text(), 'keep')

    def test_transient_trees_and_logs_are_excluded(self):
        cache = self.workspace / 'work' / 'recovery-drills' / 'old-copy'
        cache.mkdir(parents=True)
        (cache / 'private.json').write_text('[]')
        (self.workspace / 'active.log').write_text('log')
        files, excluded, _ = recovery.inventory(self.workspace)
        self.assertFalse(any(path.startswith('work/recovery-drills/') or path.endswith('.log') for path, _ in files))
        self.assertTrue(excluded)

    def test_archive_restore_is_independent_of_local_capture(self):
        stage = self.workspace / 'work' / 'step5-operations' / 'fixture' / 'snapshot'
        recovery.snapshot(self.workspace, stage)
        recovery.transfer(stage, self.backup)
        (stage / 'payload' / 'datos' / 'produccion' / 'catalogo' / 'anime.json').write_text('[]')
        completed = SimpleNamespace(stdout=b'{"passed":true}', returncode=0)
        with patch.object(recovery.subprocess, 'run', return_value=completed):
            report = recovery.restore(self.workspace, self.backup, 'fixture-php')
        self.assertEqual(report['status'], 'PASSED')
        restored = Path(report['restoredTo']) / 'datos' / 'produccion' / 'catalogo' / 'anime.json'
        self.assertEqual(json.loads(restored.read_text())[0]['id'], 'sheet')

    def test_modified_archive_is_rejected_before_restore(self):
        stage = self.workspace / 'work' / 'step5-operations' / 'fixture' / 'snapshot'
        recovery.snapshot(self.workspace, stage)
        recovery.transfer(stage, self.backup)
        with (self.backup / 'project.zip').open('ab') as stream:
            stream.write(b'corruption-fixture')
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            recovery.restore(self.workspace, self.backup, 'not-invoked')

    def test_direct_archive_restores_all_files_independently(self):
        recovery.archive_snapshot(self.workspace, self.backup)
        live = self.workspace / 'datos/produccion/catalogo/anime.json'
        live.write_text('[{"id":"later"}]')
        completed = SimpleNamespace(stdout=b'{"passed":true}', returncode=0)
        with patch.object(recovery.subprocess, 'run', return_value=completed):
            report = recovery.restore(self.workspace, self.backup, 'fixture-php')
        restored = Path(report['restoredTo']) / 'datos/produccion/catalogo/anime.json'
        self.assertEqual(json.loads(restored.read_text())[0]['id'], 'sheet')
        self.assertEqual(json.loads(live.read_text())[0]['id'], 'later')

    def test_interrupted_direct_archive_cannot_be_restored(self):
        with patch.object(recovery, 'sha', side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError):
                recovery.archive_snapshot(self.workspace, self.backup)
        self.assertEqual(json.loads((self.backup / 'status.json').read_text())['status'], 'INCOMPLETE')
        self.assertFalse((self.backup / 'project.zip').exists())
        with self.assertRaises(ValueError):
            recovery.restore(self.workspace, self.backup, 'not-invoked')

    def test_pending_private_transaction_blocks_capture(self):
        (self.workspace / 'Desarrollo/Aplication/data/.transaction.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'privada pendiente'):
            recovery.archive_snapshot(self.workspace, self.backup)

    def test_long_windows_destination_and_readback(self):
        source = self.root / 'short-source'
        source.write_bytes(b'long-path-fixture')
        target = self.root / 'long-destination' / ('folder-' * 12) / ('nested-' * 12) / ('deeper-' * 12) / 'data.bin'
        def cleanup_long_fixture():
            directory = self.root / 'long-destination'
            if directory.parent.resolve() != self.root.resolve():
                raise ValueError('Limpieza fuera de la carpeta temporal propia.')
            shutil.rmtree(recovery.filesystem_path(directory))
        self.addCleanup(cleanup_long_fixture)
        recovery.copy_verified(source, target)
        self.assertEqual(recovery.sha(target), recovery.sha(source))
        second = self.root / 'readback'
        recovery.copy_verified(target, second)
        self.assertEqual(second.read_bytes(), source.read_bytes())


if __name__ == '__main__':
    unittest.main()
