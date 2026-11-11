"""HTTP and browser approval integration: local PHP, fictitious accounts, local fake Jikan."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import unittest
import test_http_privacy as fixtures

class ApprovalHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.HttpPrivacyTests.setUpClass()

    def setUp(self):
        self.fixture=fixtures.HttpPrivacyTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        owner=self
        self.provider_calls=[]
        self.provider_title="Verified provider title"
        self.provider_id=7
        self.watchmode_type="tv_series"
        class Provider(BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_GET(self):
                owner.provider_calls.append(self.path)
                if self.path=="/title/7/details":
                    response={"id":owner.provider_id,"title":owner.provider_title,"type":owner.watchmode_type,
                              "year":2025,"poster":"https://example.invalid/verified.png",
                              "plot_overview":"Verified fixture metadata","genre_names":["Drama"]}
                    body=json.dumps(response).encode()
                    self.send_response(200);self.send_header("Content-Type","application/json")
                    self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
                    return
                if self.path!="/anime/7/full":
                    self.send_error(404);return
                body=json.dumps({"data":{"mal_id":7,"title":owner.provider_title,"type":"TV",
                    "year":2025,"season":"winter","episodes":12,"status":"Finished Airing",
                    "genres":[{"name":"Anime"}],"synopsis":"Verified on the local provider fixture.",
                    "url":"https://myanimelist.net/anime/7",
                    "images":{"jpg":{"image_url":"https://example.invalid/poster.png"}}}}).encode()
                self.send_response(200);self.send_header("Content-Type","application/json")
                self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
        self.provider=ThreadingHTTPServer(("127.0.0.1",0),Provider)
        self.thread=threading.Thread(target=self.provider.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop_provider)
        config=self.fixture.root/"api/config/app.php"
        source=config.read_text(encoding="utf-8")
        source=source.replace("'https://api.jikan.moe/v4'",repr("http://127.0.0.1:"+str(self.provider.server_port)))
        source=source.replace("'https://api.watchmode.com/v1'",repr("http://127.0.0.1:"+str(self.provider.server_port)))
        config.write_text(source,encoding="utf-8")
        (self.fixture.root/"api/config/secrets.local.php").write_text("<?php return ['watchmode_api_key'=>'fixture-not-a-real-key'];",encoding="utf-8")

    def stop_provider(self):
        self.provider.shutdown();self.provider.server_close();self.thread.join(timeout=3)

    def api(self,method,route,body=None,session=None,expected=200,token=None):
        client=http.client.HTTPConnection("127.0.0.1",self.fixture.port,timeout=12)
        headers={"Content-Type":"application/json"}
        if session:
            headers["Cookie"]=session["cookie"]
            headers["X-CSRF-Token"]=token if token is not None else session["token"]
        try:
            client.request(method,"/api/index.php?route="+route,None if body is None else json.dumps(body),headers)
            response=client.getresponse();payload=response.read()
            self.assertEqual(response.status,expected,payload)
            result=json.loads(payload)
            cookie=response.getheader("Set-Cookie")
            if session and (result.get("meta") or {}).get("csrfToken"):
                session["token"]=result["meta"]["csrfToken"]
            return result,cookie
        finally:client.close()

    def login(self,role):
        body,cookie=self.api("POST","/auth/login",{"email":role+"@example.invalid","password":self.fixture.password})
        return {"cookie":cookie.split(";",1)[0],"token":body["meta"]["csrfToken"]}

    def pending(self):
        user=self.login("user")
        before=(self.fixture.root/"data/anime.json").read_bytes()
        result,_=self.api("POST","/favorites/jikan-7",{"source":"jikan","title":"FORGED",
            "sourceUrl":"http://127.0.0.1:1/private"},user)
        self.assertEqual(result["data"][0]["title"],self.provider_title)
        self.assertEqual(result["data"][0]["catalogRequestStatus"],"pending")
        self.assertEqual((self.fixture.root/"data/anime.json").read_bytes(),before)
        admin=self.login("admin")
        result,_=self.api("GET","/catalog/requests",session=admin)
        return user,admin,result["data"][0]["id"]

    def test_http_requires_role_csrf_and_provider_identity_before_publication(self):
        user,admin,id=self.pending()
        self.api("GET","/catalog/requests",expected=401)
        self.api("GET","/catalog/requests",session=user,expected=403)
        self.api("POST","/catalog/requests/"+id,{"decision":"approve"},user,expected=403)
        self.api("POST","/catalog/requests/"+id,{"decision":"approve"},admin,expected=419,token="invalid")
        self.provider_title="Fresh verified title"
        self.api("POST","/catalog/requests/"+id,{"decision":"approve"},admin)
        result,_=self.api("GET","/favorites",session=user)
        self.assertEqual(result["data"][0]["title"],"Fresh verified title")
        self.assertNotIn("catalogRequestStatus",result["data"][0])
        self.assertEqual(self.provider_calls,["/anime/7/full","/anime/7/full"])
        self.assertEqual(self.fixture.request("/data/catalog-solicitudes.json")[0],404)
        self.assertEqual(self.fixture.request("/BACKUPS/security/attempts.json")[0],404)

    def test_rejection_keeps_favorite_personal(self):
        user,admin,id=self.pending()
        self.api("POST","/catalog/requests/"+id,{"decision":"reject"},admin)
        result,_=self.api("GET","/favorites",session=user)
        self.assertEqual(result["data"][0]["catalogRequestStatus"],"rejected")
        records=json.loads((self.fixture.root/"data/anime.json").read_text(encoding="utf-8"))
        self.assertNotIn("jikan-7",[r["id"] for r in records])

    def test_watchmode_uses_official_title_details_contract_and_validates_identity(self):
        self.watchmode_type="short_film"
        user=self.login("user")
        result,_=self.api("POST","/favorites/watchmode-7",{"source":"watchmode","type":"series","title":"FORGED"},user)
        self.assertEqual(result["data"][0]["type"],"movies")
        self.assertEqual(result["data"][0]["title"],self.provider_title)
        admin=self.login("admin")
        queue,_=self.api("GET","/catalog/requests",session=admin)
        id=queue["data"][0]["id"]
        self.provider_id=8
        self.api("POST","/catalog/requests/"+id,{"decision":"approve"},admin,expected=502)
        self.assertEqual(json.loads((self.fixture.root/"data/peliculas.json").read_text()),[])
        self.provider_id=7
        self.api("POST","/catalog/requests/"+id,{"decision":"approve"},admin)
        self.assertEqual(len(json.loads((self.fixture.root/"data/peliculas.json").read_text())),1)

    def test_dashboard_can_approve_and_renders_provider_title_as_text(self):
        dependency=Path(os.environ.get("ALTOIDSS_QA_NODE_MODULES",str(fixtures.APP/"qa/node_modules")))
        if not (dependency/"playwright").is_dir():
            if os.environ.get("ALTOIDSS_REQUIRE_BROWSER")=="1":self.fail("Install locked QA dependencies before running browser integration")
            self.skipTest("Browser integration requires npm ci in qa/")
        for folder in ("Html","js","css","img"):
            shutil.copytree(fixtures.APP/folder,self.fixture.root/folder,dirs_exist_ok=True)
        self.provider_title="<img src=x onerror=alert(1)> Verified title"
        self.pending()
        script=Path(__file__).with_name("catalog-approval-browser.cjs")
        env={**os.environ,"ALTOIDSS_QA_NODE_MODULES":str(dependency),"ALTOIDSS_TEST_URL":"http://127.0.0.1:"+str(self.fixture.port),
             "ALTOIDSS_FIXTURE_PASSWORD":self.fixture.password}
        result=subprocess.run(["node",str(script)],env=env,capture_output=True,text=True,encoding="utf-8",timeout=90)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        records=json.loads((self.fixture.root/"data/anime.json").read_text(encoding="utf-8"))
        self.assertEqual(sum(row["id"]=="jikan-7" for row in records),1)

if __name__=="__main__":unittest.main()

