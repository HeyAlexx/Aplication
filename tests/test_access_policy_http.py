"""HTTP checks verify actual permission enforcement, using owned temporary fixtures."""
import json
import unittest
import test_http_privacy as http
import test_catalog_approval as catalog

class AccessHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        http.HttpPrivacyTests.setUpClass()

    def setUp(self):
        self.f = http.HttpPrivacyTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    def change(self, index, **changes):
        path = self.f.root / 'data/usuarios.json'
        rows = json.loads(path.read_text(encoding='utf-8'))
        rows[index].update(changes)
        self.f.write('usuarios.json', rows)

    def get(self, route, cookie):
        return self.f.request('/api/index.php?route=' + route, cookie=cookie)

    def test_content_reviewer_is_allowed_without_exporting_private_records(self):
        self.change(1, permissionOverrides={'catalog.review':True})
        cookie = self.f.login('user')
        self.assertEqual(self.get('/catalog/requests', cookie)[0], 200)
        self.assertEqual(self.get('/export', cookie)[0], 403)
        self.assertEqual(self.get('/reviews/anime', cookie)[0], 403)

    def test_permission_revocation_applies_to_an_existing_session(self):
        cookie = self.f.login('admin')
        self.assertEqual(self.get('/catalog/requests', cookie)[0], 200)
        self.change(0, permissionOverrides={'catalog.review':False})
        self.assertEqual(self.get('/catalog/requests', cookie)[0], 403)
        self.assertEqual(self.get('/reviews/anime', cookie)[0], 200)

    def test_permission_grant_applies_to_an_existing_session(self):
        cookie = self.f.login('user')
        self.assertEqual(self.get('/catalog/requests', cookie)[0], 403)
        self.change(1, permissionOverrides={'catalog.review':True})
        self.assertEqual(self.get('/catalog/requests', cookie)[0], 200)

    def test_pending_approval_blocks_an_existing_active_session(self):
        cookie = self.f.login('admin')
        self.change(0, approvalStatus='pending')
        self.assertEqual(self.get('/reviews/anime', cookie)[0], 401)
        status, _, _ = self.f.request('/api/index.php?route=/auth/login', 'POST',
                                     {'email':'admin@example.invalid','password':self.f.password})
        self.assertEqual(status, 401)

    def test_registration_cannot_assign_permissions_or_master_identity(self):
        payload = {'name':'Synthetic new user','email':'new@example.invalid',
                   'password':'New-Isolated-Fixture-Password-890', 'role':'admin',
                   'permissionOverrides':{'data.export':True}, 'approvalStatus':'approved',
                   'masterAccountId':'chosen-by-client', 'isMaster':True}
        status, body, headers = self.f.request('/api/index.php?route=/auth/register', 'POST', payload)
        self.assertEqual(status, 201, body)
        cookie = headers['Set-Cookie'].split(';',1)[0]
        self.assertEqual(self.get('/export', cookie)[0], 403)
        rows = json.loads((self.f.root/'data/usuarios.json').read_text(encoding='utf-8'))
        self.assertEqual(rows[-1]['role'], 'usuario')
        self.assertNotIn('permissionOverrides', rows[-1])
        self.assertNotIn('isMaster', rows[-1])

    def test_public_session_exposes_only_effective_permissions(self):
        self.change(1, permissionOverrides={'catalog.review':True})
        cookie = self.f.login('user')
        status, body, _ = self.get('/auth/session', cookie)
        self.assertEqual(status, 200)
        session = json.loads(body)['data']
        self.assertIn('catalog.review', session['permissions'])
        for field in ['passwordHash','permissionOverrides','masterAccountId','access_policy']:
            self.assertNotIn(field, session)

    def test_malformed_overrides_do_not_retain_old_admin_permissions(self):
        cookie = self.f.login('admin')
        self.change(0, permissionOverrides={'data.export':'yes'})
        self.assertEqual(self.get('/export', cookie)[0], 403)
        self.assertEqual(self.get('/catalog/requests', cookie)[0], 403)

    def test_operator_profile_defaults_are_applied_without_changing_accounts(self):
        (self.f.root/'api/config/secrets.local.php').write_text(
            "<?php return ['access_policy'=>['profilePermissions'=>['admin'=>['data.export'=>false]]]];",
            encoding='utf-8')
        cookie = self.f.login('admin')
        self.assertEqual(self.get('/export', cookie)[0], 403)
        self.assertEqual(self.get('/reviews/anime', cookie)[0], 200)
        self.change(0, permissionOverrides={'data.export':True})
        self.assertEqual(self.get('/export', cookie)[0], 200)

class ContentReviewPermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog.CatalogApprovalTests.setUpClass()

    def setUp(self):
        self.f = catalog.CatalogApprovalTests()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    def test_admin_cannot_approve_own_real_request(self):
        f = self.f
        self.assertEqual(f.command('favorite', actor='admin')['status'], 200)
        row = f.read('catalog-solicitudes')[0]
        before = f.hashes()
        self.assertEqual(f.command('decide', actor='admin', id=row['id'], decision='approve')['status'], 403)
        self.assertEqual(f.hashes(), before)
        self.assertEqual(f.read('catalog-solicitudes')[0]['status'], 'pending')

    def test_delegated_different_reviewer_can_approve_real_request(self):
        f = self.f
        self.assertEqual(f.command('favorite', actor='admin')['status'], 200)
        row = f.read('catalog-solicitudes')[0]
        users = f.read('usuarios'); users[1]['permissionOverrides'] = {'catalog.review':True}
        f.write('usuarios', users)
        result = f.command('decide', actor='user', id=row['id'], decision='approve')
        self.assertEqual(result['status'], 200, result)
        self.assertEqual(len(f.read('anime', True)), 1)

    def test_revoked_reviewer_cannot_commit_after_provider_io(self):
        f = self.f
        row = f.request()
        f.provider['revokeDuringResolve'] = True; f.save_provider()
        before = f.hashes()
        self.assertEqual(f.command('decide', actor='admin', id=row['id'], decision='approve')['status'], 401)
        self.assertEqual(f.hashes(), before)

    def test_direct_creation_cannot_bypass_a_pending_external_proposal(self):
        f = self.f
        f.request(); before = f.hashes()
        payload = dict(f.candidate, emissionYear=2026, emissionSeason='Fall', seasonsCount=1)
        result = f.command('directCreate', actor='admin', payload=payload)
        self.assertEqual(result['status'], 409, result)
        self.assertEqual(f.hashes(), before)

    def test_permission_revoked_during_provider_io_cannot_commit(self):
        f = self.f
        row = f.request(); before = f.hashes()
        f.provider['revokePermissionsDuringResolve'] = True; f.save_provider()
        self.assertEqual(f.command('decide', actor='admin', id=row['id'], decision='approve')['status'], 403)
        self.assertEqual(f.hashes(), before)
