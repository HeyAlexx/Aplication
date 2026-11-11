import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import qa


class QaIsolationTests(unittest.TestCase):
    def test_operational_data_and_secrets_are_not_copied(self):
        with tempfile.TemporaryDirectory(prefix='altoids-qa-safety-') as temporary:
            root = Path(temporary)
            source = root/'source'
            for name in ['api/config/secrets.local.php','data/usuarios.json','config/google-oauth-client.json',
                         'runtime/anime-sync/google-token.json','qa/node_modules/private.js']:
                target = source/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'PRIVATE_SENTINEL_NEVER_COPY')
            (source/'Html').mkdir()
            (source/'Html/index.html').write_text('<title>Public fixture</title>',encoding='utf-8')
            descriptor, hashes = qa.fixture(source, root/'stage/app')
            self.assertEqual(set(hashes), {'Html/index.html'})
            self.assertEqual(json.loads((root/'stage/app/data/usuarios.json').read_text()), [])
            self.assertFalse((root/'stage/app/api/config/secrets.local.php').exists())
            self.assertFalse((root/'stage/app/config/google-oauth-client.json').exists())
            self.assertEqual(json.loads(descriptor.read_text())['environment'], 'isolated-qa-fictitious-data')
            self.assertEqual((source/'data/usuarios.json').read_bytes(), b'PRIVATE_SENTINEL_NEVER_COPY')

    def test_inherited_production_and_profile_configuration_is_removed(self):
        with patch.dict(os.environ, {'ALTOIDSS_STORAGE_CONFIG':'private descriptor', 'WATCHMODE_API_KEY':'private key',
                                   'MAL_CLIENT_ID':'private key','NODE_PATH':'private profile', 'PATH':'keep'}, clear=True):
            self.assertEqual(qa.environment(), {'PATH':'keep'})


if __name__ == '__main__':
    unittest.main()
