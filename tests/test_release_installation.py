import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import install_prepared_release as installer
import prepare_code_release as release
import test_code_release_preparation as preparation_tests


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


if __name__ == '__main__':
    unittest.main()
