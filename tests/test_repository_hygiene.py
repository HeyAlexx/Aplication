import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import repository_hygiene as hygiene

class RepositoryHygieneTests(unittest.TestCase):
    def test_operational_paths_and_case_aliases_are_rejected(self):
        for name in ['data/usuarios.json','Data/usuarios.json','backups/sessions/session-fixture','outputs/report.txt',
                     'tools/node_modules/tool.js','runtime/deployed-release.local.json','api/config/secrets.local.php',
                     'config/google-oauth-client.json','fixture.sqlite','fixture.zip','../api/file.php']:
            with self.subTest(name=name):self.assertTrue(hygiene.path_rules(name))

    def test_documented_examples_are_allowed_but_not_exempt_from_secret_checks(self):
        for name in ['data/.htaccess','data/README.md','backups/.htaccess','backups/README.md',
                     'api/config/secrets.example.php','config/anime-sync.example.json','qa/package-lock.json']:
            self.assertEqual(hygiene.findings(name,b'placeholder example.invalid'),[])
        secret=b'-----BEGIN '+b'PRIVATE KEY-----\nfictitious\n'
        self.assertTrue(hygiene.findings('api/config/secrets.example.php',secret))

    def test_credentials_are_reported_without_values(self):
        payload=b'ghp_'+b'A'*40
        result=hygiene.findings('api/config/app.php',payload)
        self.assertEqual(result,[{'path':'api/config/app.php','rule':'github-token'}])
        self.assertNotIn(payload.decode(),json.dumps(result))
        with self.assertRaises(ValueError) as caught:hygiene.reject_payload('api/config/app.php',payload)
        self.assertNotIn(payload.decode(),str(caught.exception))

    def test_password_hashes_and_private_keys_cannot_be_renamed_into_code(self):
        for value in [b'$2b$12$'+b'A'*53,b'-----BEGIN '+b'OPENSSH PRIVATE KEY-----']:
            with self.assertRaises(ValueError):hygiene.reject_payload('api/config/app.php',value)

    def test_timing_sentinel_exception_is_exact_in_value_path_and_role(self):
        name='api/services/CredentialService.php'
        payload=(Path(__file__).resolve().parents[1]/name).read_bytes()
        self.assertEqual(hygiene.findings(name,payload),[])
        self.assertTrue(hygiene.findings('api/config/app.php',payload))
        self.assertTrue(hygiene.findings(name,payload.replace(b'private const DUMMY',b'private const ACCOUNT')))
        match=hygiene.SIGNATURES['password-hash'].search(payload)
        self.assertTrue(hygiene.findings(name,payload.replace(match.group(),b'$2b$12$'+b'Z'*53)))

    def test_index_scans_staged_blobs_even_if_working_tree_is_cleaned(self):
        with tempfile.TemporaryDirectory(prefix='altoids-hygiene-') as temp:
            root=Path(temp);hygiene.git(root,'init','-q')
            target=root/'app.php';secret=b'ghp_'+b'B'*40;target.write_bytes(secret)
            hygiene.git(root,'add','app.php');target.write_bytes(b'<?php // clean working tree')
            report=hygiene.scan(root,index=True)
            self.assertEqual(report['status'],'FAILED')
            self.assertEqual(report['findings'][0]['rule'],'github-token')
            self.assertNotIn(secret.decode(),json.dumps(report))

    def test_forced_tracking_of_data_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='altoids-hygiene-') as temp:
            root=Path(temp);hygiene.git(root,'init','-q');(root/'data').mkdir()
            (root/'data/accounts.json').write_text('[]')
            hygiene.git(root,'add','data/accounts.json')
            self.assertEqual(hygiene.scan(root,index=True)['findings'],[{'path':'data/accounts.json','rule':'operational-data'}])

if __name__=='__main__':unittest.main()
