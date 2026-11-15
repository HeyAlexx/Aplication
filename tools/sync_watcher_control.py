"""Cooperative watcher controls. Never kill a PID or change PHP/Cloudflare processes."""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from storage_transaction import atomic_json, file_lock


def read_state(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def same_path(left, right):
    # Compare identity text only; never inspect another checkout's path.
    return os.path.normcase(os.path.abspath(str(left))) == os.path.normcase(os.path.abspath(str(right)))


class WatchSession:
    def __init__(self, project, state, config, pid_path=None):
        self.project, self.state, self.config = Path(project).resolve(), Path(state).resolve(), Path(config).resolve()
        self.directory = self.state / "watcher-control"
        self.pid_path = pid_path or self.project / "runtime/anime-sync/watcher.pid"
        self.owner = {"instance": uuid.uuid4().hex, "pid": os.getpid(),
                      "project": str(self.project), "config": str(self.config)}

    def record(self, status):
        atomic_json(self.directory / "status.json",
                    {"status": status, "updatedAt": datetime.now(timezone.utc).isoformat()})

    def __enter__(self):
        atomic_json(self.directory / "owner.json", self.owner)
        self.pid_path.parent.mkdir(parents=True, exist_ok=True)
        self.pid_path.write_text(str(os.getpid()), encoding="ascii")
        self.record("RUNNING")
        return self

    def stop_requested(self):
        return read_state(self.directory / "stop.json").get("instance") == self.owner["instance"]

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while not self.stop_requested():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(.2, remaining))
        return True

    def __exit__(self, *args):
        if read_state(self.directory / "owner.json").get("instance") == self.owner["instance"]:
            if read_state(self.directory / "status.json").get("status") != "AUTHORIZATION_REQUIRED":
                self.record("STOPPED")
            for name in ["owner.json", "stop.json"]:
                path = self.directory / name
                if read_state(path).get("instance") == self.owner["instance"]:
                    path.unlink(missing_ok=True)
        if self.pid_path.is_file() and self.pid_path.read_text(encoding="ascii").strip() == str(os.getpid()):
            self.pid_path.unlink()


class WatchController:
    def __init__(self, project, state, config, timeout=30):
        self.project, self.state, self.config = Path(project).resolve(), Path(state).resolve(), Path(config).resolve()
        self.directory, self.timeout = self.state / "watcher-control", timeout

    def busy(self):
        try:
            with file_lock(self.state / ".watcher.lock", timeout=0):
                return False
        except RuntimeError:
            return True

    def owner(self):
        owner = read_state(self.directory / "owner.json")
        if (not same_path(owner.get("project", ""), self.project)
                or not same_path(owner.get("config", ""), self.config)
                or not isinstance(owner.get("pid"), int) or owner["pid"] <= 0
                or not isinstance(owner.get("instance"), str) or len(owner["instance"]) != 32):
            raise RuntimeError("El sincronizador activo no admite este control o pertenece a otro entorno. Cierra su ventana una vez.")
        return owner

    def status(self):
        if self.busy():
            self.owner()  # A stale PID alone never establishes ownership.
            status = read_state(self.directory / "status.json").get("status")
            return status if status in {"RUNNING", "RETRYING", "AUTHORIZING", "AUTHORIZATION_REQUIRED"} else "RUNNING"
        status = read_state(self.directory / "status.json").get("status")
        return "AUTHORIZATION_REQUIRED" if status == "AUTHORIZATION_REQUIRED" else "STOPPED"

    def stop(self):
        if not self.busy():
            return "STOPPED"
        owner = self.owner()
        atomic_json(self.directory / "stop.json", {"instance": owner["instance"]})
        deadline = time.monotonic() + self.timeout
        while self.busy():
            if read_state(self.directory / "owner.json").get("instance") not in {None, owner["instance"]}:
                raise RuntimeError("Cambio de sincronizador durante la parada; no se reinicio.")
            if time.monotonic() >= deadline:
                return "STOP_REQUESTED"
            time.sleep(.1)
        return "STOPPED"

    def start(self):
        status = self.status()
        if status == "AUTHORIZATION_REQUIRED":
            return status
        if status != "STOPPED":
            return status
        logs = self.project / "runtime/anime-sync"
        logs.mkdir(parents=True, exist_ok=True)
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
        with (logs / "watcher.log").open("ab") as out, (logs / "watcher-error.log").open("ab") as err:
            child = subprocess.Popen([sys.executable, "-u", "-B", str(self.project / "tools/anime_sync_pipeline.py"),
                "--config", str(self.config), "--apply", "--watch", "--interval", "300"],
                cwd=self.project, stdin=subprocess.DEVNULL, stdout=out, stderr=err, **options)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                status = self.status()
            except RuntimeError:  # Lock acquired before owner registration.
                status = "STARTING"
            if status not in {"STOPPED", "STARTING"}:
                return status
            if child.poll() is not None:
                raise RuntimeError("El sincronizador no pudo iniciar; consulta runtime/anime-sync/watcher-error.log.")
            time.sleep(.1)
        raise RuntimeError("Inicio pendiente. No se lanzara otro proceso; vuelve a consultar el estado.")

    def reauthorize(self):
        if self.stop() == "STOP_REQUESTED":
            return "STOP_REQUESTED"
        from google_sheets_writeback import authorize, load_config, read_rows
        try:
            # Also exclude manually launched/one-shot writers while credentials are updated.
            with file_lock(self.state / ".watcher.lock", timeout=0):
                with WatchSession(self.project, self.state, self.config) as session:
                    session.record("AUTHORIZING")
                    authorize(self.config)
                    sheet = str(load_config(self.config).get("sheetName") or "Catalogo")
                    read_rows(self.config, f"{sheet}!A1:J1")  # Validate read access before resuming.
        except Exception as error:
            atomic_json(self.directory / "status.json", {"status": "AUTHORIZATION_REQUIRED"})
            raise RuntimeError("No se completo la autorizacion o la lectura de comprobacion. El sincronizador sigue detenido.") from error
        atomic_json(self.directory / "status.json", {"status": "STOPPED"})
        return self.start()

    def run(self, action):
        if action == "status":
            return self.status()
        # Serialize simultaneous menu/shortcut operations without sharing the writer lock.
        with file_lock(self.directory / ".control.lock", timeout=0):
            if action == "stop":
                return self.stop()
            if action == "restart":
                if self.stop() == "STOP_REQUESTED":
                    return "STOP_REQUESTED"
                return self.start()
            if action == "authorize":
                return self.reauthorize()
            return self.start()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "restart", "authorize", "status"])
    args = parser.parse_args()
    from catalog_storage import PROJECT_DIR, SYNC_STATE_DIR
    control = WatchController(PROJECT_DIR, SYNC_STATE_DIR, PROJECT_DIR / "config/anime-sync.json")
    messages = {"RUNNING": "[OK] Proceso de sincronizacion activo.",
        "AUTHORIZING": "[INFO] Autorizacion de Google en curso en otro acceso.",
        "RETRYING": "[AVISO] Sincronizador activo; reintentando un error temporal.",
        "STOPPED": "[OK] Sincronizador detenido.",
        "STOP_REQUESTED": "[AVISO] Parada solicitada; terminara el ciclo en curso. Repite la accion cuando termine.",
        "AUTHORIZATION_REQUIRED": "[ATENCION] Google requiere autorizacion. Sincronizador detenido; usa A para reautorizar."}
    try:
        status = control.run(args.action)
        print(messages[status], flush=True)
        return {"AUTHORIZATION_REQUIRED": 4, "STOP_REQUESTED": 2}.get(status, 3 if args.action == "status" and status == "STOPPED" else 0)
    except (RuntimeError, OSError, ValueError) as error:
        print("[ERROR] " + str(error), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
