"""Session-cookie policy over isolated HTTP; no real accounts, provider calls or cookies in logs."""
import http.client
from http.cookiejar import CookieJar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import subprocess
import sys
import ssl
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import build_opener, HTTPSHandler, HTTPCookieProcessor, ProxyHandler, Request

import test_http_privacy as fixtures
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import check_session_cookie as probe

@unittest.skipUnless(fixtures.PHP,'PHP is required for isolated HTTP tests')
class SessionTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.HttpPrivacyTests.setUpClass()
        cls.php_version=subprocess.check_output([fixtures.PHP,'-r','echo PHP_VERSION;'],text=True).strip()

    def start(self,secure=False,native_https=False):
        f=fixtures.HttpPrivacyTests();self.addCleanup(f.doCleanups);f.setUp();f.stop_server()
        f.environment.pop('HTTPS',None)
        router='server-router.php'
        if native_https:
            router='native-https-router.php'
            (f.root/router).write_text("<?php $_SERVER['HTTPS']='on'; require __DIR__.'/server-router.php';",encoding='utf-8')
        f.server=subprocess.Popen([fixtures.PHP,'-d','session.cookie_secure='+('1' if secure else '0'),
            '-S',f'127.0.0.1:{f.port}','-t','.',router],cwd=f.root,env=f.environment,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        for _ in range(80):
            try:
                if f.request('/Html/index.html')[0]==200:return f
            except OSError:pass
            time.sleep(.05)
        self.fail('Isolated PHP fixture did not start')

    def api(self,f,route='/auth/session',method='GET',body=None,headers=None):
        client=http.client.HTTPConnection('127.0.0.1',f.port,timeout=8)
        try:
            client.request(method,'/api/index.php?route='+route,
                None if body is None else json.dumps(body),{'Content-Type':'application/json',**(headers or {})})
            response=client.getresponse();self.assertEqual(response.status,200)
            return json.loads(response.read()),response.getheader('Set-Cookie')
        finally:client.close()

    def flags(self,header,secure):
        parsed=SimpleCookie();parsed.load(header or '')
        self.assertTrue('altoidss_session' in parsed,'Expected session cookie absent')
        cookie=parsed['altoidss_session']
        self.assertEqual(bool(cookie['secure']),secure)
        self.assertTrue(bool(cookie['httponly']));self.assertEqual(cookie['samesite'],'Lax')
        self.assertEqual(cookie['path'],'/');self.assertEqual(cookie['domain'],'')
        return cookie.value

    def test_local_http_remains_usable(self):
        _,header=self.api(self.start());self.flags(header,False)

    def test_server_forced_secure_is_not_downgraded(self):
        _,header=self.api(self.start(secure=True));self.flags(header,True)

    def test_forwarded_headers_cannot_enable_secure_in_local_http(self):
        _,header=self.api(self.start(),headers={'X-Forwarded-Proto':'https','Forwarded':'for=fixture;proto=https',
            'X-Forwarded-Ssl':'on','HTTPS':'on'})
        self.flags(header,False)

    def test_forwarded_http_cannot_disable_server_secure(self):
        _,header=self.api(self.start(secure=True),headers={'X-Forwarded-Proto':'http','Forwarded':'for=fixture;proto=http'})
        self.flags(header,True)

    def test_public_health_guard_rejects_existing_insecure_backend(self):
        # Exercise transport on both CI runtimes; the deployed guard stays pinned to production PHP.
        with patch.object(probe,'PHP_VERSION',self.php_version):
            local=self.start()
            with self.assertRaisesRegex(ValueError,'UNSAFE_SESSION_COOKIE'):
                probe.check(f'http://127.0.0.1:{local.port}/api/index.php?route=/health')
            secure=self.start(secure=True)
            self.assertEqual(probe.check(f'http://127.0.0.1:{secure.port}/api/index.php?route=/health')['status'],
                'PUBLIC_SESSION_COOKIE_VERIFIED')

    def test_trusted_sapi_https_signal_is_preserved(self):
        _,header=self.api(self.start(native_https=True));self.flags(header,True)

    def test_login_and_logout_preserve_server_secure_policy(self):
        f=self.start(secure=True)
        data,header=self.api(f,route='/auth/login',method='POST',
            body={'email':'admin@example.invalid','password':f.password})
        session=self.flags(header,True)
        data,_=self.api(f,headers={'Cookie':'altoidss_session='+session})
        self.assertTrue(data['data']['isAuthenticated'])
        _,header=self.api(f,route='/auth/logout',method='POST',body={},
            headers={'Cookie':'altoidss_session='+session,'X-CSRF-Token':data['meta']['csrfToken']})
        self.flags(header,True)

    def test_https_frontend_http_backend_uses_secure_cookies_through_login_logout(self):
        f=self.start(secure=True)
        config=f.root/'tls-test.cnf';cert=f.root/'tls-cert.pem';key=f.root/'tls-key.pem'
        config.write_text('''[req]
distinguished_name=dn
prompt=no
[dn]
CN=localhost
[server]
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:localhost,IP:127.0.0.1
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always
''',encoding='utf-8')
        code="""$options=['config'=>$argv[1],'private_key_bits'=>2048,'private_key_type'=>OPENSSL_KEYTYPE_RSA,'digest_alg'=>'sha256'];
$key=openssl_pkey_new($options);$csr=openssl_csr_new(['commonName'=>'localhost'],$key,$options);
$cert=openssl_csr_sign($csr,null,$key,1,$options+['x509_extensions'=>'server'],13);
if(!$key||!$csr||!$cert||!openssl_pkey_export($key,$private,null,$options)||!openssl_x509_export($cert,$public)){exit(1);}
file_put_contents($argv[2],$public);file_put_contents($argv[3],$private);"""
        run=subprocess.run([fixtures.PHP,'-r',code,str(config),str(cert),str(key)],
            capture_output=True,text=True,env=f.environment,timeout=20)
        self.assertEqual(run.returncode,0,'Could not generate the disposable TLS fixture')
        self.assertEqual(run.stderr.strip(),'','TLS fixture emitted startup errors')
        class Proxy(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def relay(self):
                backend=http.client.HTTPConnection('127.0.0.1',f.port,timeout=8)
                headers={k:v for k,v in self.headers.items() if k.casefold() not in {'host','connection','content-length'}}
                headers['X-Forwarded-Proto']='https'
                body=self.rfile.read(int(self.headers.get('Content-Length','0')))
                try:
                    backend.request(self.command,self.path,body or None,headers)
                    response=backend.getresponse();payload=response.read()
                    self.send_response(response.status)
                    for name,value in response.getheaders():
                        if name.casefold() not in {'connection','transfer-encoding','content-length'}:self.send_header(name,value)
                    self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
                finally:backend.close()
            do_GET=relay
            do_POST=relay
        server=ThreadingHTTPServer(('127.0.0.1',0),Proxy);server.daemon_threads=True
        server_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);server_context.load_cert_chain(cert,key)
        server.socket=server_context.wrap_socket(server.socket,server_side=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def close_proxy():server.shutdown();server.server_close();thread.join(timeout=3)
        self.addCleanup(close_proxy)
        # Trust only this ephemeral certificate; hostname and TLS verification stay enabled.
        client_context=ssl.create_default_context(cafile=str(cert))
        cookies=CookieJar();client=build_opener(ProxyHandler({}),HTTPSHandler(context=client_context),HTTPCookieProcessor(cookies))
        base='https://127.0.0.1:'+str(server.server_port)
        def api(route,body=None,token=None):
            headers={'Content-Type':'application/json'}
            if token:headers['X-CSRF-Token']=token
            request=Request(base+'/api/index.php?route='+route,
                data=None if body is None else json.dumps(body).encode(),headers=headers)
            with client.open(request,timeout=8) as response:
                self.assertEqual(response.status,200)
                header=response.headers.get('Set-Cookie')
                if header:self.flags(header,True)
                return json.load(response)
        api('/auth/session');self.assertTrue(all(c.secure for c in cookies))
        api('/auth/login',{'email':'admin@example.invalid','password':f.password})
        session=api('/auth/session');self.assertTrue(session['data']['isAuthenticated'])
        api('/auth/logout',{},session['meta']['csrfToken'])
        self.assertFalse(api('/auth/session')['data']['isAuthenticated'])

if __name__=='__main__':unittest.main()
