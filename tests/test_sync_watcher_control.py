"""Watcher controls use disposable workers and mocked Google consent; never operational data."""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

TOOLS=Path(__file__).resolve().parents[1]/"tools"
sys.path.insert(0,str(TOOLS))
import sync_watcher_control as control
import google_sheets_writeback as google
from storage_transaction import atomic_json,file_lock


class WatchControlTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="altoids-watch-control-")
        self.root=Path(self.temp.name).resolve()
        self.project=self.root/"app with spaces";self.state=self.root/"state"
        (self.project/"tools").mkdir(parents=True);(self.project/"config").mkdir()
        self.state.mkdir()
        self.config=self.project/"config/anime-sync.json"
        self.config.write_text('{"googleSheets":{"sheetName":"Catalogo"}}',encoding="utf-8")
        self.controller=control.WatchController(self.project,self.state,self.config,timeout=3)
        self.children=[]
        self.addCleanup(self.temp.cleanup);self.addCleanup(self.close_workers)
        real=subprocess.Popen
        def capture(*args,**kwargs):
            child=real(*args,**kwargs);self.children.append(child);return child
        self.popen_patch=patch.object(control.subprocess,"Popen",side_effect=capture)
        self.popen_patch.start();self.addCleanup(self.popen_patch.stop)
        worker=f'''import sys,time
from pathlib import Path
sys.path.insert(0,{str(TOOLS)!r})
from sync_watcher_control import WatchSession
from storage_transaction import file_lock,atomic_json
p=Path(__file__).resolve().parents[1];s=p.parent/"state";deadline=time.monotonic()+20
with file_lock(s/".watcher.lock",timeout=0):
 with WatchSession(p,s,p/"config/anime-sync.json") as c:
  while time.monotonic()<deadline and not c.stop_requested():
   if (s/"block").exists():
    (s/"in-cycle").touch()
    while (s/"block").exists() and time.monotonic()<deadline:time.sleep(.02)
    atomic_json(s/"cycle.json",{{"complete":True}})
   if c.wait(.05):break
'''
        (self.project/"tools/anime_sync_pipeline.py").write_text(worker,encoding="utf-8")
        self.sentinel=self.project/"catalog.json";self.sentinel.write_text('[{"id":"fixture"}]',encoding="utf-8")

    def close_workers(self):
        (self.state/"block").unlink(missing_ok=True)
        try:self.controller.stop()
        except RuntimeError:pass
        # Every fixture worker also has a hard lifetime bound; cleanup never kills a PID.
        for child in self.children:child.wait(timeout=25)
        self.assertEqual(self.sentinel.read_text(encoding="utf-8"),'[{"id":"fixture"}]')

    def wait(self,predicate):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            if predicate():return
            time.sleep(.03)
        self.fail("Disposable watcher did not reach the expected state")

    def test_idle_stop_is_responsive_and_clears_owner_pid(self):
        self.assertEqual(self.controller.run("start"),"RUNNING")
        self.assertEqual(self.controller.run("stop"),"STOPPED")
        self.assertFalse((self.project/"runtime/anime-sync/watcher.pid").exists())
        self.assertFalse((self.controller.directory/"owner.json").exists())
        self.assertFalse(self.controller.busy())

    def test_restart_waits_for_old_worker_and_creates_a_new_instance(self):
        self.controller.run("start");old=self.controller.owner()["instance"]
        self.assertEqual(self.controller.run("restart"),"RUNNING")
        self.assertNotEqual(self.controller.owner()["instance"],old)
        self.assertEqual(len(self.children),2)
        self.children[0].wait(timeout=5)

    def test_repeated_start_keeps_one_worker(self):
        self.controller.run("start");old=self.controller.owner()["instance"]
        self.assertEqual(self.controller.run("start"),"RUNNING")
        self.assertEqual(self.controller.owner()["instance"],old)
        self.assertEqual(len(self.children),1)

    def test_stop_and_restart_during_cycle_wait_without_interrupting_commit(self):
        (self.state/"block").touch()
        self.controller.run("start");self.wait(lambda:(self.state/"in-cycle").exists())
        self.controller.timeout=.15
        self.assertEqual(self.controller.run("restart"),"STOP_REQUESTED")
        self.assertEqual(len(self.children),1)
        self.assertFalse((self.state/"cycle.json").exists())
        (self.state/"block").unlink()
        self.wait(lambda:not self.controller.busy())
        self.assertTrue(json.loads((self.state/"cycle.json").read_text())["complete"])

    def test_stale_pid_is_never_used_to_terminate_another_process(self):
        pid=self.project/"runtime/anime-sync/watcher.pid";pid.parent.mkdir(parents=True)
        pid.write_text(str(os.getpid()),encoding="ascii")
        self.assertEqual(self.controller.run("stop"),"STOPPED")
        self.assertEqual(pid.read_text(),str(os.getpid()))

    def test_legacy_locked_worker_is_refused_without_a_stop_request(self):
        with file_lock(self.state/".watcher.lock",timeout=0):
            with self.assertRaisesRegex(RuntimeError,"no admite"):self.controller.run("stop")
        self.assertFalse((self.controller.directory/"stop.json").exists())

    def test_other_checkout_owner_is_refused_without_accessing_its_path(self):
        atomic_json(self.controller.directory/"owner.json",{"project":"G:\\historical","config":"G:\\historical\\config",
            "pid":os.getpid(),"instance":"a"*32})
        with file_lock(self.state/".watcher.lock",timeout=0):
            with self.assertRaises(RuntimeError):self.controller.run("stop")
        self.assertFalse((self.controller.directory/"stop.json").exists())

    def test_stale_stop_request_does_not_stop_a_new_instance(self):
        atomic_json(self.controller.directory/"stop.json",{"instance":"a"*32})
        self.assertEqual(self.controller.run("start"),"RUNNING")
        time.sleep(.1)
        self.assertTrue(self.controller.busy())
        self.assertEqual(self.controller.run("stop"),"STOPPED")

    def test_concurrent_control_operation_is_refused(self):
        with file_lock(self.controller.directory/".control.lock",timeout=0):
            with self.assertRaises(RuntimeError):self.controller.run("start")
        self.assertEqual(len(self.children),0)

    def test_known_oauth_failure_blocks_automatic_and_explicit_restart(self):
        atomic_json(self.controller.directory/"status.json",{"status":"AUTHORIZATION_REQUIRED"})
        self.assertEqual(self.controller.run("start"),"AUTHORIZATION_REQUIRED")
        self.assertEqual(self.controller.run("restart"),"AUTHORIZATION_REQUIRED")
        self.assertEqual(len(self.children),0)

    def test_reauthorization_validates_read_before_resuming(self):
        events=[]
        atomic_json(self.controller.directory/"status.json",{"status":"AUTHORIZATION_REQUIRED"})
        with patch.object(google,"authorize",side_effect=lambda p:events.append("consent")), \
             patch.object(google,"read_rows",side_effect=lambda *a:events.append("read") or []), \
             patch.object(self.controller,"start",side_effect=lambda:events.append("start") or "RUNNING"):
            self.assertEqual(self.controller.run("authorize"),"RUNNING")
        self.assertEqual(events,["consent","read","start"])

    def test_reauthorization_excludes_manually_launched_writers(self):
        def consent(config):
            self.assertTrue(self.controller.busy())
            self.assertEqual(self.controller.status(),"AUTHORIZING")
            with self.assertRaises(RuntimeError):
                with file_lock(self.state/".watcher.lock",timeout=0):pass
        with patch.object(google,"authorize",side_effect=consent),patch.object(google,"read_rows",return_value=[]), \
             patch.object(self.controller,"start",return_value="RUNNING"):
            self.assertEqual(self.controller.run("authorize"),"RUNNING")
        self.assertFalse(self.controller.busy())

    def test_cancelled_consent_keeps_the_watcher_stopped(self):
        with patch.object(google,"authorize",side_effect=RuntimeError("fixture cancellation")), \
             patch.object(self.controller,"start") as start:
            with self.assertRaisesRegex(RuntimeError,"sigue detenido"):self.controller.run("authorize")
            start.assert_not_called()
        self.assertEqual(self.controller.status(),"AUTHORIZATION_REQUIRED")

    def test_failed_sheet_validation_keeps_the_watcher_stopped(self):
        with patch.object(google,"authorize"),patch.object(google,"read_rows",side_effect=RuntimeError("fixture denied")), \
             patch.object(self.controller,"start") as start:
            with self.assertRaises(RuntimeError):self.controller.run("authorize")
            start.assert_not_called()
        self.assertEqual(self.controller.status(),"AUTHORIZATION_REQUIRED")

    def test_reauthorization_waits_for_current_cycle_before_opening_browser(self):
        (self.state/"block").touch();self.controller.run("start")
        self.wait(lambda:(self.state/"in-cycle").exists());self.controller.timeout=.15
        with patch.object(google,"authorize") as consent:
            self.assertEqual(self.controller.run("authorize"),"STOP_REQUESTED")
            consent.assert_not_called()


class OAuthWatcherTests(unittest.TestCase):
    def test_invalid_grant_is_distinct_from_a_temporary_token_error(self):
        for status,body,kind in [(400,b'{"error":"invalid_grant"}',google.OAuthAuthorizationRequired),
                                 (503,b'{"error":"temporarily_unavailable"}',RuntimeError)]:
            with self.subTest(status=status):
                error=HTTPError(google.TOKEN_URL,status,"fixture",{},io.BytesIO(body))
                with patch.object(google,"urlopen",side_effect=error):
                    with self.assertRaises(kind) as caught:google.token_request({"grant_type":"refresh_token"})
                if status==503:self.assertNotIsInstance(caught.exception,google.OAuthAuthorizationRequired)
        for error in [URLError("fixture unavailable"),TimeoutError("fixture timeout")]:
            with self.subTest(error=type(error).__name__):
                with patch.object(google,"urlopen",side_effect=error):
                    with self.assertRaises(RuntimeError) as caught:google.token_request({"grant_type":"refresh_token"})
                self.assertNotIsInstance(caught.exception,google.OAuthAuthorizationRequired)

    def run_watcher(self,effects):
        import anime_sync_pipeline as pipeline
        with tempfile.TemporaryDirectory(prefix="altoids-oauth-watch-") as name:
            root=Path(name).resolve();state=root/"state";state.mkdir();pid=root/"watcher.pid"
            config=root/"config.json";config.write_text("{}")
            args=argparse.Namespace(interval=60,watch=True,apply=True,initialize=False,config=config)
            with patch.object(pipeline,"parse_args",return_value=args), \
                 patch.object(pipeline,"PROJECT_DIR",root),patch.object(pipeline,"STATE_DIR",state), \
                 patch.object(pipeline,"LOCK_PATH",pid),patch.object(pipeline,"process_once",side_effect=effects) as process, \
                 patch.object(control.WatchSession,"wait",side_effect=[False,True]):
                try:pipeline.main();exit_code=0
                except SystemExit as error:exit_code=error.code
            return exit_code,process.call_count,control.read_state(state/"watcher-control/status.json"),pid.exists(),(state/"watcher-control/owner.json").exists()

    def test_invalid_grant_stops_automatically_after_one_attempt(self):
        code,calls,status,pid,owner=self.run_watcher([google.OAuthAuthorizationRequired("fixture")])
        self.assertEqual(code,2);self.assertEqual(calls,1)
        self.assertEqual(status["status"],"AUTHORIZATION_REQUIRED")
        self.assertFalse(pid);self.assertFalse(owner)

    def test_temporary_network_error_keeps_retrying(self):
        code,calls,status,pid,owner=self.run_watcher([RuntimeError("fixture network"),{"ok":True}])
        self.assertEqual(code,0);self.assertEqual(calls,2)
        self.assertEqual(status["status"],"STOPPED")
        self.assertFalse(pid);self.assertFalse(owner)


if __name__=="__main__":unittest.main()
