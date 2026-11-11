import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import install_prepared_release as installer
import prepare_code_release as release
import test_code_release_preparation as preparation_tests
import release_identity as identity


class ReleaseInstallationTests(unittest.TestCase):
    setup_workspace = preparation_tests.CodeReleasePreparationTests.setup_workspace

    def candidate(self):
        workspace, source, production = self.setup_workspace()
        (source / 'server-router.php').write_bytes(b'<?php // approved new router\n')
        (source / 'api/new.php').write_bytes(b'<?php // new file\n')
        release.git(source, 'add', 'server-router.php', 'api/new.php')
        release.git(source, 'commit', '-qm', 'approved candidate')
        commit = release.git(source, 'rev-parse', 'HEAD').decode().strip()
        plan, _ = release.prepare(workspace, source, commit)
        return workspace, production, plan, commit

    def test_install_preserves_data_local_unrelated_code_and_git_identity(self):
        workspace, production, plan, commit = self.candidate()
        before = release.protected_hashes(workspace, production)
        head = release.git(production, 'rev-parse', 'HEAD')
        report = installer.install(workspace, plan, commit)
        self.assertEqual(report['status'], 'CODE_INSTALLED_DATA_UNCHANGED')
        self.assertEqual(release.protected_hashes(workspace, production), before)
        self.assertEqual(release.git(production, 'rev-parse', 'HEAD'), head)
        self.assertEqual((production / 'server-router.php').read_bytes(), b'<?php // approved new router\n')
        self.assertEqual((Path(report['operation']) / 'originals/server-router.php').read_bytes(), b'<?php // committed-router\n')

    def test_stale_data_blocks_every_code_write(self):
        workspace, production, plan, commit = self.candidate()
        (production / 'data/usuarios.json').write_text('[]')
        with self.assertRaisesRegex(ValueError, 'protegido'):
            installer.install(workspace, plan, commit)
        self.assertEqual((production / 'server-router.php').read_bytes(), b'<?php // committed-router\n')

    def test_changed_release_receipt_blocks_every_code_write(self):
        workspace, production, plan, commit = self.candidate()
        receipt = production / identity.RELATIVE_PATH
        receipt.parent.mkdir()
        receipt.write_text('{"external":"new receipt"}')
        with self.assertRaisesRegex(ValueError, 'comprobante'):
            installer.install(workspace, plan, commit)
        self.assertEqual((production / 'server-router.php').read_bytes(), b'<?php // committed-router\n')

    def test_failure_after_first_receipt_write_recovers_receipt_and_code(self):
        workspace, production, plan, commit = self.candidate()
        replace = installer.replace_bytes
        failed = False
        def fail_after_write(path, payload):
            nonlocal failed
            replace(path, payload)
            if path == production / identity.RELATIVE_PATH and not failed:
                failed = True
                raise OSError('simulated failure after receipt rename')
        with patch.object(installer, 'replace_bytes', side_effect=fail_after_write):
            with self.assertRaises(OSError):
                installer.install(workspace, plan, commit)
        self.assertEqual((production / 'server-router.php').read_bytes(), b'<?php // committed-router\n')
        self.assertFalse((production / identity.RELATIVE_PATH).exists())
        operation = next(plan.glob('deployment-*'))
        self.assertTrue((operation / 'added-files-retained' / identity.RELATIVE_PATH).is_file())
        self.assertEqual(json.loads((operation / 'report.json').read_text())['status'], 'CODE_ROLLED_BACK')

    def test_failure_after_updating_existing_receipt_restores_previous_identity(self):
        workspace, production, plan, commit = self.candidate()
        installer.install(workspace, plan, commit)
        previous = (production / identity.RELATIVE_PATH).read_bytes()
        source = workspace / 'Desarrollo/Aplication'
        (source / 'server-router.php').write_bytes(b'<?php // second release\n')
        release.git(source, 'add', 'server-router.php')
        release.git(source, 'commit', '-qm', 'second candidate')
        next_commit = release.git(source, 'rev-parse', 'HEAD').decode().strip()
        next_plan, _ = release.prepare(workspace, source, next_commit)
        replace = installer.replace_bytes
        failed = False
        def fail_after_write(path, payload):
            nonlocal failed
            replace(path, payload)
            if path == production / identity.RELATIVE_PATH and not failed:
                failed = True
                raise OSError('simulated receipt update failure')
        with patch.object(installer, 'replace_bytes', side_effect=fail_after_write):
            with self.assertRaises(OSError):
                installer.install(workspace, next_plan, next_commit, commit)
        self.assertEqual((production / identity.RELATIVE_PATH).read_bytes(), previous)
        self.assertEqual((production / 'server-router.php').read_bytes(), b'<?php // approved new router\n')
        self.assertEqual(identity.status(production)['commit'], commit)

    def test_mid_install_outside_scope_drift_is_preserved_and_never_certified(self):
        workspace, production, plan, commit = self.candidate()
        source = workspace / 'Desarrollo/Aplication'
        base = release.git(source, 'rev-parse', commit + '^').decode().strip()
        replace = installer.replace_bytes
        def external_edit(path, payload):
            replace(path, payload)
            if path == production / 'server-router.php':
                (production / 'api/local.php').write_bytes(b'external edit outside scope')
        with patch.object(installer, 'replace_bytes', side_effect=external_edit):
            with self.assertRaisesRegex(RuntimeError, 'Cambió código'):
                installer.install(workspace, plan, commit, base)
        self.assertEqual((production / 'api/local.php').read_bytes(), b'external edit outside scope')
        self.assertEqual((production / 'server-router.php').read_bytes(), b'<?php // committed-router\n')
        self.assertFalse((production / identity.RELATIVE_PATH).exists())

    def test_tampered_package_and_wrong_commit_are_rejected(self):
        workspace, production, plan, commit = self.candidate()
        with self.assertRaises(ValueError):
            installer.install(workspace, plan, '0' * 40)
        (plan / 'code/server-router.php').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'paquete'):
            installer.install(workspace, plan, commit)

    def test_code_drift_is_not_overwritten(self):
        workspace, production, plan, commit = self.candidate()
        (production / 'server-router.php').write_bytes(b'new external edit')
        with self.assertRaisesRegex(ValueError, 'Cambió un archivo'):
            installer.install(workspace, plan, commit)
        self.assertEqual((production / 'server-router.php').read_bytes(), b'new external edit')

    def test_normal_failure_rolls_back_code_and_retains_added_files(self):
        workspace, production, plan, commit = self.candidate()
        replace = installer.replace_bytes
        failed = False
        def fail_once(path, payload):
            nonlocal failed
            if path == production / 'server-router.php' and not failed:
                failed = True
                raise OSError('simulated install failure')
            replace(path, payload)
        with patch.object(installer, 'replace_bytes', side_effect=fail_once):
            with self.assertRaises(OSError):
                installer.install(workspace, plan, commit)
        self.assertEqual((production / 'server-router.php').read_bytes(), b'<?php // committed-router\n')
        self.assertFalse((production / 'api/new.php').exists())
        operation = next(plan.glob('deployment-*'))
        self.assertEqual(json.loads((operation / 'report.json').read_text())['status'], 'CODE_ROLLED_BACK')
        self.assertTrue((operation / 'added-files-retained/api/new.php').is_file())

    def test_scoped_install_preserves_earlier_unrelated_difference(self):
        """Un despliegue del PR no incorpora diferencias anteriores de otro archivo."""
        workspace, source, production = self.setup_workspace()
        (source / 'api/local.php').write_bytes(b'<?php // older unrelated main change\n')
        release.git(source, 'add', 'api/local.php')
        release.git(source, 'commit', '-qm', 'earlier unrelated change')
        base = release.git(source, 'rev-parse', 'HEAD').decode().strip()
        (source / 'server-router.php').write_bytes(b'<?php // scoped candidate\n')
        release.git(source, 'add', 'server-router.php')
        release.git(source, 'commit', '-qm', 'scoped candidate')
        commit = release.git(source, 'rev-parse', 'HEAD').decode().strip()
        plan, _ = release.prepare(workspace, source, commit)
        before = release.protected_hashes(workspace, production)
        report = installer.install(workspace, plan, commit, base)
        self.assertEqual((production / 'api/local.php').read_bytes(), b'<?php // base\n')
        self.assertEqual((production / 'server-router.php').read_bytes(), b'<?php // scoped candidate\n')
        self.assertEqual(report['changedPaths'], ['server-router.php'])
        self.assertEqual(report['preservedOutsideScope'], ['api/local.php'])
        self.assertEqual(release.protected_hashes(workspace, production), before)

    def test_scoped_install_rejects_mobile_ref_before_writes(self):
        """La base de alcance es inmutable; no se aceptan ramas moviles."""
        workspace, production, plan, commit = self.candidate()
        with self.assertRaisesRegex(ValueError, 'SHA completo'):
            installer.install(workspace, plan, commit, 'main')
        self.assertEqual((production / 'server-router.php').read_bytes(), b'<?php // committed-router\n')


if __name__ == '__main__':
    unittest.main()
