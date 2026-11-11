"""Approval and recovery tests with distinct private/central stores and a fake provider."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP=Path(os.environ.get("ALTOIDSS_TEST_SOURCE",Path(__file__).resolve().parents[1]))
PHP=os.environ.get("PHP_BIN") or shutil.which("php") or "C:/xampp/php/php.exe"
DRIVER=r"""<?php
require $argv[1].'/api/core/ApiException.php';
require $argv[1].'/api/core/JsonStorage.php';
require $argv[1].'/api/services/AuthService.php';
require $argv[1].'/api/services/CatalogService.php';
require $argv[1].'/api/services/UserService.php';
require $argv[1].'/api/services/ExternalCatalogService.php';
require $argv[1].'/api/services/CatalogRequestService.php';
require $argv[1].'/api/services/AccountSecurityService.php';
$input=json_decode(stream_get_contents(STDIN),true,32,JSON_THROW_ON_ERROR);
session_save_path($argv[1].'/sessions');session_start();
$s=new JsonStorage($argv[1].'/data',$argv[1].'/backups');
$catalog=new CatalogService($s);$auth=new AuthService($s);
try {
 $session=$auth->login(['email'=>($input['actor']??'user').'@example.invalid','password'=>'Long-Fixture-Only-Password-98']);
 $resolver=function(string $id)use($argv,$s,$session):array{
   $provider=json_decode(file_get_contents($argv[1].'/provider.json'),true,32,JSON_THROW_ON_ERROR);
   if($provider['fail']??false)throw new ApiException('Fixture provider unavailable',502);
   if($provider['revokeDuringResolve']??false){
     $s->transaction(function()use($s,$session):void{
       $users=$s->read('usuarios.json');
       foreach($users as &$u){if($u['id']===$session['id'])$u['status']='Inactivo';}unset($u);
       $s->write('usuarios.json',$users);
     });
   }
   if(!isset($provider['items'][$id]))throw new ApiException('Fixture title missing',404);
   return $provider['items'][$id];
 };
 $requests=new CatalogRequestService($s,$catalog,$resolver,fn()=>$auth->requireAdmin(),fn()=>$auth->requireUser());
 $users=new UserService($s,$catalog,$requests);
 $id=$input['id']??'';
 $result=match($input['action']){
   'favorite'=>$users->addFavorite($auth->requireUser(),$id,$input['payload']??[]),
   'remove'=>$users->removeFavorite($auth->requireUser(),$id),
   'favorites'=>$users->favorites($auth->requireUser()),
   'list'=>$requests->all(),
   'decide'=>$requests->decide($id,$input['decision']),
   'reset'=>(new AccountSecurityService($s))->change($id,$input['password']??null),
   'directImport'=>$catalog->importExternal($id,$input['payload']??[]),
   default=>throw new ApiException('Unknown fixture operation'),
 };
 echo json_encode(['status'=>200,'data'=>$result],JSON_THROW_ON_ERROR);
}catch(ApiException $e){echo json_encode(['status'=>$e->statusCode(),'error'=>$e->getMessage()],JSON_THROW_ON_ERROR);}
"""
@unittest.skipUnless(Path(PHP).is_file() or shutil.which(PHP),"PHP required")
class CatalogApprovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw_hash=subprocess.check_output([PHP,"-r","echo password_hash('Long-Fixture-Only-Password-98',PASSWORD_DEFAULT);"],text=True).strip()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="altoidss-approval-")
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.app=root/"app";self.app.mkdir()
        shutil.copytree(APP/"api",self.app/"api",ignore=shutil.ignore_patterns("secrets.local.php","mal-client-id.local.txt"))
        for name in ("data","sessions","backups"):(self.app/name).mkdir()
        self.central=root/"central";self.central.mkdir();state=root/"state";state.mkdir()
        self.descriptor=root/"storage.json"
        self.descriptor.write_text(json.dumps({"environment":"isolated-approval","catalogDir":str(self.central),"syncStateDir":str(state)}),encoding="utf-8")
        self.environment={k:v for k,v in os.environ.items() if not k.startswith("ALTOIDSS_")}
        self.environment["ALTOIDSS_STORAGE_CONFIG"]=str(self.descriptor)
        self.driver=root/"driver.php";self.driver.write_text(DRIVER,encoding="utf-8")
        for name in ("anime","peliculas","series","noticias","anime-revisiones","anime-sheet-writeback"):
            self.write(name,[],central=True)
        for name in ("favoritos","perfiles","historial","configuraciones"):
            self.write(name,[])
        self.write("usuarios",[
            {"id":"fixture-admin","email":"admin@example.invalid","name":"Admin","role":"admin","status":"Activo","passwordHash":self.pw_hash},
            {"id":"fixture-user","email":"user@example.invalid","name":"User","role":"usuario","status":"Activo","passwordHash":self.pw_hash}])
        self.candidate={"id":"jikan-7","source":"jikan","type":"anime","title":"Verified server title",
                        "genre":"Anime","description":"Verified metadata","image":"https://example.invalid/poster.png"}
        self.provider={"items":{"jikan-7":dict(self.candidate)}}
        self.save_provider()

    def save_provider(self):
        (self.app/"provider.json").write_text(json.dumps(self.provider),encoding="utf-8")

    def write(self,name,records,central=False):
        ((self.central if central else self.app/"data")/(name+".json")).write_text(json.dumps(records),encoding="utf-8")

    def read(self,name,central=False):
        path=(self.central if central else self.app/"data")/(name+".json")
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    def hashes(self):
        return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.central.glob("*.json")}

    def command(self,action,actor="user",id="jikan-7",**data):
        run=subprocess.run([PHP,str(self.driver),str(self.app)],input=json.dumps(dict(action=action,actor=actor,id=id,**data)),
            env=self.environment,capture_output=True,text=True,encoding="utf-8",timeout=25)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(run.stderr,"")
        return json.loads(run.stdout)

    def request(self):
        result=self.command("favorite",payload={"id":"jikan-7","source":"jikan","title":"CLIENT FORGED","sourceCode":"forged"})
        self.assertEqual(result["status"],200,result)
        return self.read("catalog-solicitudes")[0]

    def test_pending_favorite_is_private_and_uses_verified_metadata(self):
        before=self.hashes();self.request()
        self.assertEqual(self.hashes(),before)
        favorite=self.command("favorites")["data"][0]
        self.assertEqual(favorite["title"],"Verified server title")
        self.assertEqual(favorite["catalogRequestStatus"],"pending")
        self.assertNotIn("sourceCode",favorite)
        self.assertEqual(self.command("list")["status"],403)
        self.assertEqual(len(self.command("list",actor="admin")["data"]),1)

    def test_unknown_id_provider_mismatch_and_unsafe_identifier_rejected(self):
        before=self.hashes()
        for id,payload,status in [("invented",{},400),("jikan-7",{"source":"kitsu"},400),
                                  ("jikan-999",{"title":"forged"},404),("jikan-../7",{},400)]:
            with self.subTest(id=id):
                self.assertEqual(self.command("favorite",id=id,payload=payload)["status"],status)
        self.assertEqual(self.hashes(),before)
        self.assertEqual(self.read("favoritos"),[])

    def test_provider_failure_does_not_create_a_fake_favorite(self):
        self.provider["fail"]=True;self.save_provider();before=self.hashes()
        self.assertEqual(self.command("favorite")["status"],502)
        self.assertEqual(self.hashes(),before)
        self.assertEqual(self.read("favoritos"),[])
        self.assertEqual(self.read("catalog-solicitudes"),[])

    def test_approval_refreshes_metadata_and_is_idempotent(self):
        row=self.request()
        self.provider["items"]["jikan-7"]["title"]="Fresh provider title";self.save_provider()
        self.assertEqual(self.command("decide",id=row["id"],decision="approve")["status"],403)
        result=self.command("decide",actor="admin",id=row["id"],decision="approve")
        self.assertEqual(result["status"],200,result)
        self.assertEqual(self.read("anime",True)[0]["title"],"Fresh provider title")
        self.assertEqual(self.command("decide",actor="admin",id=row["id"],decision="approve")["status"],200)
        self.assertEqual(len(self.read("anime",True)),1)
        self.assertEqual(self.read("anime-sheet-writeback",True),[])
        self.assertNotIn("catalogRequestStatus",self.command("favorites")["data"][0])
        self.assertNotIn("claim",self.command("list",actor="admin")["data"][0])

    def test_rejection_retains_personal_favorite_without_publication(self):
        row=self.request();before=self.hashes()
        self.assertEqual(self.command("decide",actor="admin",id=row["id"],decision="reject")["status"],200)
        self.assertEqual(self.hashes(),before)
        self.assertEqual(self.command("favorites")["data"][0]["catalogRequestStatus"],"rejected")

    def test_removal_cancels_pending_and_approval_is_refused(self):
        row=self.request()
        self.assertEqual(self.command("remove")["data"],[])
        self.assertEqual(self.read("catalog-solicitudes")[0]["status"],"cancelled")
        self.assertEqual(self.command("decide",actor="admin",id=row["id"],decision="approve")["status"],409)
        self.assertEqual(self.read("anime",True),[])

    def test_admin_revoked_during_provider_lookup_cannot_publish(self):
        row=self.request();before=self.hashes()
        self.provider["revokeDuringResolve"]=True;self.save_provider()
        self.assertEqual(self.command("decide",actor="admin",id=row["id"],decision="approve")["status"],401)
        self.assertEqual(self.hashes(),before)
        self.assertEqual(self.read("catalog-solicitudes")[0]["status"],"pending")

    def test_user_revoked_during_lookup_cannot_store_a_request(self):
        self.provider["revokeDuringResolve"]=True;self.save_provider()
        self.assertEqual(self.command("favorite")["status"],401)
        self.assertEqual(self.read("favoritos"),[])
        self.assertEqual(self.read("catalog-solicitudes"),[])

    def test_failed_approval_keeps_request_pending(self):
        row=self.request()
        self.provider["fail"]=True;self.save_provider()
        self.assertEqual(self.command("decide",actor="admin",id=row["id"],decision="approve")["status"],502)
        self.assertEqual(self.read("catalog-solicitudes")[0]["status"],"pending")
        self.assertEqual(self.read("anime",True),[])

    def test_resume_after_catalog_commit_before_private_finalization(self):
        row=self.request();row.update(status="approving",claim={"token":"interrupted","by":"fixture-admin","expiresAt":0})
        self.write("catalog-solicitudes",[row])
        self.write("anime",[dict(self.candidate,status="Activo")],central=True)
        self.assertEqual(self.command("decide",actor="admin",id=row["id"],decision="approve")["status"],200)
        self.assertEqual(len(self.read("anime",True)),1)
        self.assertEqual(self.read("catalog-solicitudes")[0]["status"],"approved")

    def test_hidden_title_does_not_reappear_from_snapshot(self):
        self.request()
        self.write("anime",[dict(self.candidate,status="Oculto")],central=True)
        self.assertEqual(self.command("favorites")["data"],[])
        self.assertEqual(self.command("favorite")["status"],404)

    def test_parallel_favorites_have_one_request_and_relation(self):
        jobs=[]
        try:
            for _ in range(8):
                jobs.append(subprocess.Popen([PHP,str(self.driver),str(self.app)],stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",env=self.environment))
            for job in jobs:
                job.stdin.write(json.dumps({"action":"favorite","id":"jikan-7"}));job.stdin.close();job.stdin=None
            for job in jobs:
                stdout,stderr=job.communicate(timeout=35)
                self.assertEqual(job.returncode,0,stderr);self.assertEqual(json.loads(stdout)["status"],200)
        finally:
            for job in jobs:
                if job.poll() is None:job.kill();job.communicate()
        self.assertEqual(len(self.read("favoritos")),1)
        self.assertEqual(len(self.read("catalog-solicitudes")),1)
        self.assertEqual(self.read("anime",True),[])

    def test_direct_import_without_authorization_is_forbidden(self):
        result=self.command("directImport",payload=self.candidate)
        self.assertEqual(result["status"],403)
        self.assertEqual(self.read("anime",True),[])

    def test_resolution_budget_is_bounded_even_if_requests_cancelled(self):
        self.write("catalog-resolutions",[{"userId":"fixture-user","expiresAt":9999999999} for _ in range(20)])
        self.assertEqual(self.command("favorite")["status"],429)
        self.assertEqual(self.read("favoritos"),[])

    def test_password_reset_preserves_identity_relations_and_changes_version(self):
        before=self.read("usuarios");self.write("favoritos",[{"userId":"fixture-user","contentId":"existing"}])
        relations=(self.app/"data/favoritos.json").read_bytes()
        result=self.command("reset",actor="admin",id="fixture-user",password="A-different-private-fixture-passphrase")
        self.assertEqual(result["status"],200)
        after=self.read("usuarios")
        self.assertEqual([u["id"] for u in before],[u["id"] for u in after])
        self.assertEqual(after[0],before[0])
        self.assertEqual(after[1]["authVersion"],1)
        self.assertNotEqual(after[1]["passwordHash"],before[1]["passwordHash"])
        self.assertEqual((self.app/"data/favoritos.json").read_bytes(),relations)
        # Old credentials no longer validate; no password or hash is returned.
        self.assertEqual(self.command("favorites")["status"],401)
        self.assertNotIn("passwordHash",result["data"])

if __name__=="__main__":unittest.main()

