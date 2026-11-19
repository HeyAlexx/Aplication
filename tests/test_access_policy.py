"""Authorization contracts use only synthetic accounts and isolated PHP processes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

APP = Path(os.environ.get('ALTOIDSS_TEST_SOURCE', Path(__file__).resolve().parents[1]))
PHP = os.environ.get('PHP_BIN') or shutil.which('php')
DRIVER = r'''
require $argv[1].'/api/core/ApiException.php';
require $argv[1].'/api/services/AccessPolicy.php';
$d=json_decode(stream_get_contents(STDIN),true,32,JSON_THROW_ON_ERROR);
$p=new AccessPolicy($d['config']??[]);
$a=$d['actor'];$target=$d['target']??[];
try {
 $v=match($d['operation']) {
  'allows'=>$p->allows($a,$d['permission']),
  'permissions'=>$p->permissions($a),
  'review'=>$p->canApproveContent($a,$d['author']),
  'account'=>$p->canChangeAccount($a,$target,$d['action']),
  'appointment'=>$p->appointmentDecision($a,$target),
  default=>throw new RuntimeException('Unknown test operation')
 };
 echo json_encode(['value'=>$v]);
}catch(ApiException $e){echo json_encode(['status'=>$e->statusCode()]);}
'''

class AccessPolicyTests(unittest.TestCase):
    def setUp(self):
        self.admin = dict(id='fixture-admin', role='admin', status='Activo')
        self.user = dict(id='fixture-user', role='usuario', status='Activo')
        self.master = dict(id='fixture-master', role='admin', status='Activo')
        self.config = dict(masterAccountId='fixture-master')

    def call(self, actor=None, operation='allows', **values):
        payload = dict(actor=self.admin if actor is None else actor, operation=operation,
                       config=self.config) | values
        result = subprocess.run([PHP, '-r', DRIVER, str(APP)], input=json.dumps(payload),
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_legacy_roles_keep_existing_permissions(self):
        self.assertTrue(self.call(permission='catalog.create')['value'])
        self.assertTrue(self.call(permission='data.export')['value'])
        self.assertFalse(self.call(self.user, permission='catalog.create')['value'])

    def test_pending_suspended_and_unknown_accounts_cannot_gain_permissions(self):
        for changes in [dict(approvalStatus='pending'), dict(approvalStatus='rejected'),
                        dict(approvalStatus=None), dict(status='Inactivo'), dict(role='master')]:
            with self.subTest(changes=changes):
                self.assertEqual(self.call(self.admin | changes, operation='permissions')['value'], [])

    def test_individual_overrides_and_profile_inheritance(self):
        profile = dict(masterAccountId='fixture-master', profilePermissions={'admin':{'catalog.create':False}})
        self.assertFalse(self.call(permission='catalog.create', config=profile)['value'])
        self.assertTrue(self.call(self.admin | dict(permissionOverrides={'catalog.create':True}),
                                  permission='catalog.create', config=profile)['value'])
        self.assertFalse(self.call(self.admin | dict(permissionOverrides={'catalog.create':False}),
                                   permission='catalog.create')['value'])
        self.assertTrue(self.call(self.admin | dict(permissionOverrides={'catalog.create':False}),
                                  permission='catalog.review')['value'])

    def test_content_reviewer_does_not_inherit_private_export(self):
        reviewer = self.user | dict(permissionOverrides={'catalog.review':True})
        self.assertTrue(self.call(reviewer, permission='catalog.review')['value'])
        for permission in ['data.export','accounts.approve','permissions.manage','catalog.create']:
            self.assertFalse(self.call(reviewer, permission=permission)['value'])

    def test_unknown_and_malformed_permissions_fail_closed(self):
        self.assertFalse(self.call(permission='everything')['value'])
        for overrides in [None, ['catalog.create'], {'catalog.create':'yes'}, {'everything':True}]:
            self.assertEqual(self.call(self.admin | dict(permissionOverrides=overrides),
                                       operation='permissions')['value'], [])

    def test_master_identity_cannot_be_self_declared(self):
        fake = self.admin | dict(isMaster=True, masterAccountId='fixture-admin',
                                permissionOverrides={'permissions.manage':True, 'accounts.appoint':True})
        self.assertFalse(self.call(fake, permission='permissions.manage')['value'])
        self.assertTrue(self.call(self.master, permission='permissions.manage')['value'])
        self.assertFalse(self.call(self.master, permission='permissions.manage', config={})['value'])

    def test_nominations_wait_for_master_and_master_appoints_directly(self):
        self.assertEqual(self.call(operation='appointment', target=self.user)['value'], 'pending')
        self.assertEqual(self.call(self.master, operation='appointment', target=self.user)['value'], 'approved')
        self.assertEqual(self.call(self.user, operation='appointment', target=self.user)['status'], 403)
        self.assertFalse(self.call(permission='accounts.appoint')['value'])

    def test_other_admin_can_temporarily_suspend_but_cannot_delete_admin(self):
        target = self.admin | dict(id='fixture-other-admin')
        self.assertTrue(self.call(operation='account', target=target, action='suspend')['value'])
        for action in ['delete','demote','credentials','restore']:
            self.assertFalse(self.call(operation='account', target=target, action=action)['value'])
        self.assertTrue(self.call(self.master, operation='account', target=target, action='restore')['value'])

    def test_master_is_protected_even_from_indirect_paths(self):
        actor = self.admin | dict(permissionOverrides={'accounts.delete':True, 'accounts.credentials':True})
        for action in ['delete','suspend','demote','credentials','appoint','nominate']:
            self.assertFalse(self.call(actor, operation='account', target=self.master, action=action)['value'])
        for action in ['delete','suspend','demote']:
            self.assertFalse(self.call(self.master, operation='account', target=self.master, action=action)['value'])

    def test_administrator_cannot_delete_self_or_another_admin_even_with_override(self):
        actor = self.admin | dict(permissionOverrides={'accounts.delete':True})
        for target in [self.admin, self.admin | dict(id='fixture-other')]:
            self.assertFalse(self.call(actor, operation='account', target=target, action='delete')['value'])
        self.assertTrue(self.call(self.master, operation='account', target=self.admin, action='delete')['value'])

    def test_content_self_approval_is_forbidden_including_master(self):
        for actor in [self.admin, self.master, self.user | dict(permissionOverrides={'catalog.review':True})]:
            self.assertFalse(self.call(actor, operation='review', author=actor['id'])['value'])
            self.assertTrue(self.call(actor, operation='review', author='fixture-other')['value'])
            self.assertFalse(self.call(actor, operation='review', author='')['value'])

    def test_suspended_master_cannot_use_saved_permissions(self):
        self.assertEqual(self.call(self.master | dict(status='Inactivo'), operation='permissions')['value'], [])

    def test_user_cannot_nominate_or_suspend_admin_even_with_permission_flags(self):
        actor = self.user | dict(permissionOverrides={'accounts.nominate':True, 'accounts.suspend':True})
        self.assertFalse(self.call(actor, operation='account', target=self.user, action='nominate')['value'])
        self.assertFalse(self.call(actor, operation='account', target=self.admin, action='suspend')['value'])
