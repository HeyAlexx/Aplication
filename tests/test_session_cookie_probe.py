import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import check_session_cookie as probe
from runtime_spec import PHP_VERSION

class SessionCookieProbeTests(unittest.TestCase):
    def body(self):return json.dumps({'ok':True,'data':{'app':'Altoidss API','status':'ok','phpVersion':PHP_VERSION},
        'meta':{'csrfToken':'fictitious-token-not-to-be-reported'}}).encode()

    def header(self):return 'altoidss_session=fictitious-cookie-not-to-be-reported; Path=/; Secure; HttpOnly; SameSite=Lax'

    def test_reports_attributes_without_cookie_or_token_values(self):
        result=probe.evaluate(200,[('Set-Cookie',self.header())],self.body())
        self.assertEqual(result['status'],'PUBLIC_SESSION_COOKIE_VERIFIED')
        self.assertNotIn('fictitious',json.dumps(result));self.assertFalse(result['externalHttpsVerified'])

    def test_missing_security_attributes_are_rejected(self):
        for part in ['; Secure','; HttpOnly','; SameSite=Lax']:
            with self.subTest(part=part):
                with self.assertRaisesRegex(ValueError,'UNSAFE_SESSION_COOKIE'):
                    probe.evaluate(200,[('Set-Cookie',self.header().replace(part,''))],self.body())

    def test_broad_scope_or_duplicate_cookie_is_rejected(self):
        with self.assertRaises(ValueError):probe.evaluate(200,[('Set-Cookie',self.header()+'; Domain=example.invalid')],self.body())
        with self.assertRaises(ValueError):probe.evaluate(200,[('Set-Cookie',self.header().replace('Path=/','Path=/api'))],self.body())
        with self.assertRaises(ValueError):probe.evaluate(200,[('Set-Cookie',self.header())]*2,self.body())

    def test_error_or_unrelated_backend_is_not_accepted(self):
        with self.assertRaises(ValueError):probe.evaluate(302,[('Set-Cookie',self.header())],self.body())
        with self.assertRaises(ValueError):probe.evaluate(200,[('Set-Cookie',self.header())],b'{"ok":true,"data":{"app":"other"}}')
        with self.assertRaises(ValueError):probe.evaluate(200,[('Set-Cookie',self.header())],b'[]')
        with self.assertRaises(ValueError):
            probe.evaluate(200,[('Set-Cookie',self.header())],self.body().replace(PHP_VERSION.encode(),b'0.0.0'))

    def test_url_restrictions_prevent_external_or_unrelated_requests(self):
        with patch.object(probe.http.client,'HTTPConnection') as connect:
            for url in ['https://altoids.codealex.com/api/index.php?route=/health',
                'http://example.invalid/api/index.php?route=/health','http://127.0.0.1/api/index.php?route=/auth/logout',
                'http://name:password@127.0.0.1/api/index.php?route=/health','http://127.0.0.1/api/index.php?route=/health&route=/auth/session']:
                with self.subTest(url=url):
                    with self.assertRaises(ValueError):probe.check(url)
            connect.assert_not_called()

if __name__=='__main__':unittest.main()
