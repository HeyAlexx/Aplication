import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import release_identity as identity

class ReleaseIdentityTests(unittest.TestCase):
    def setup_receipt(self):
        temp=tempfile.TemporaryDirectory(prefix='altoids-identity-');self.addCleanup(temp.cleanup);app=Path(temp.name)
        (app/'api').mkdir();(app/'api/changed.php').write_bytes(b'new');(app/'api/preserved.php').write_bytes(b'local')
        receipt=identity.create('1'*40,'2'*40,'3'*40,{'api/changed.php'},
            {'api/changed.php':b'new','api/preserved.php':b'upstream','api/missing.php':b'upstream'},
            {'api/changed.php':b'old','api/preserved.php':b'local','api/missing.php':None},None,'plan-fixture','operation-fixture')
        path=app/identity.RELATIVE_PATH;path.parent.mkdir();path.write_text(json.dumps(receipt))
        return app,receipt

    def test_scoped_identity_does_not_claim_checkout_or_full_package_equality(self):
        app,_=self.setup_receipt();result=identity.status(app)
        self.assertEqual(result['status'],'VERIFIED_SCOPED_RELEASE');self.assertEqual(result['commit'],'1'*40)
        self.assertEqual(result['gitHeadAtInstall'],'3'*40);self.assertFalse(result['fullPackageMatches'])
        self.assertEqual(result['scopeFiles'],1);self.assertEqual(result['preservedStates'],2)

    def test_distinguishes_scope_drift_and_preserved_state_drift(self):
        app,_=self.setup_receipt();(app/'api/changed.php').write_bytes(b'edited');(app/'api/missing.php').write_bytes(b'added')
        result=identity.status(app);self.assertEqual(result['status'],'DRIFT')
        self.assertEqual(result['changedScopePaths'],['api/changed.php']);self.assertEqual(result['changedPreservedPaths'],['api/missing.php'])

    def test_missing_receipt_is_not_invented_from_git_head(self):
        with tempfile.TemporaryDirectory(prefix='altoids-identity-') as tmp:
            self.assertEqual(identity.status(Path(tmp))['status'],'UNRECORDED')

    def test_corrupt_receipt_or_private_inventory_is_rejected(self):
        app,data=self.setup_receipt();data['codeHashes']['data/usuarios.json']='a'*64
        (app/identity.RELATIVE_PATH).write_text(json.dumps(data));self.assertEqual(identity.status(app)['status'],'INVALID_RECEIPT')
        (app/identity.RELATIVE_PATH).write_text('{broken');self.assertEqual(identity.status(app)['status'],'INVALID_RECEIPT')

if __name__=='__main__':unittest.main()
