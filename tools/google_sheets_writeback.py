"""OAuth-backed write access for the Altoidss Google Sheet.

The sync import uses a public XLSX export, which is deliberately read-only.
This module is used only for approved changes that must be written back to
Google Sheets.  OAuth client and token files stay outside version control.
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen


SCOPE = "https://www.googleapis.com/auth/spreadsheets"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"


def load_config(config_path: Path) -> dict[str, object]:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    settings = payload.get("googleSheets")
    return settings if isinstance(settings, dict) else {}


def setting_path(config_path: Path, value: object, default: str) -> Path:
    raw = str(value or default)
    path = Path(raw)
    return path if path.is_absolute() else config_path.parent.parent / path


def spreadsheet_id(settings: dict[str, object], config_path: Path) -> str:
    configured = str(settings.get("spreadsheetId") or "").strip()
    if configured:
        return configured
    root = json.loads(config_path.read_text(encoding="utf-8"))
    export_url = str(root.get("googleExportUrl") or "")
    marker = "/spreadsheets/d/"
    if marker in export_url:
        return export_url.split(marker, 1)[1].split("/", 1)[0]
    raise RuntimeError("Falta googleSheets.spreadsheetId en la configuración.")


def client_details(config_path: Path, settings: dict[str, object]) -> tuple[dict[str, object], Path]:
    client_path = setting_path(config_path, settings.get("oauthClientSecrets"), "config/google-oauth-client.json")
    if not client_path.is_file():
        raise RuntimeError(
            f"No se encontró el archivo OAuth: {client_path}. Descargue el cliente de escritorio de Google Cloud y guárdelo allí."
        )
    payload = json.loads(client_path.read_text(encoding="utf-8"))
    details = payload.get("installed") or payload.get("web")
    if not isinstance(details, dict) or not details.get("client_id"):
        raise RuntimeError("El archivo OAuth no contiene un cliente de Google válido.")
    return details, client_path


def token_path(config_path: Path, settings: dict[str, object]) -> Path:
    return setting_path(config_path, settings.get("tokenFile"), "runtime/anime-sync/google-token.json")


def request_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: object | None = None) -> dict[str, object]:
    encoded = None
    request_headers = headers or {}
    if body is not None:
        encoded = json.dumps(body).encode("utf-8")
        request_headers = {"Content-Type": "application/json", **request_headers}
    request = Request(url, data=encoded, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google Sheets respondió HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"No se pudo contactar Google Sheets: {error}") from error


def token_request(values: dict[str, str]) -> dict[str, object]:
    request = Request(
        TOKEN_URL,
        data=urlencode(values).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google OAuth rechazó la autorización (HTTP {error.code}): {detail}") from error


def save_token(path: Path, token: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(token, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def enable_writeback(config_path: Path) -> None:
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    settings = payload.setdefault("googleSheets", {})
    if not isinstance(settings, dict):
        raise RuntimeError("googleSheets debe ser un objeto de configuración.")
    settings["writeBackEnabled"] = True
    temporary = config_path.with_suffix(config_path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(config_path)


def access_token(config_path: Path) -> str:
    settings = load_config(config_path)
    details, _ = client_details(config_path, settings)
    path = token_path(config_path, settings)
    if not path.is_file():
        raise RuntimeError("Google Sheets todavía no está autorizado. Ejecute tools/google_sheets_writeback.py --authorize una vez.")
    token = json.loads(path.read_text(encoding="utf-8"))
    expires_at = float(token.get("expiresAt", 0) or 0)
    if token.get("access_token") and expires_at > time.time() + 60:
        return str(token["access_token"])
    refresh_token = str(token.get("refresh_token") or "")
    if not refresh_token:
        raise RuntimeError("El token OAuth no puede renovarse. Ejecute nuevamente la autorización.")
    refreshed = token_request({
        "client_id": str(details["client_id"]),
        "client_secret": str(details.get("client_secret") or ""),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    token.update(refreshed)
    token["expiresAt"] = time.time() + int(refreshed.get("expires_in", 3600))
    save_token(path, token)
    return str(token["access_token"])


def authorize(config_path: Path) -> None:
    settings = load_config(config_path)
    details, _ = client_details(config_path, settings)
    redirects = [str(url) for url in details.get("redirect_uris", [])]
    redirect_uri = next((url for url in redirects if url.startswith("http://127.0.0.1") or url.startswith("http://localhost")), "http://127.0.0.1:8765/")
    parsed = urlparse(redirect_uri)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("El cliente OAuth debe incluir una URL de redirección local.")
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    result: dict[str, str] = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            query = parse_qs(urlparse(self.path).query)
            result.update({key: values[0] for key, values in query.items() if values})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h1>Autorización completada</h1><p>Ya puede cerrar esta pestaña.</p>".encode("utf-8"))

        def log_message(self, format: str, *args: object) -> None:
            return

    # Desktop OAuth clients commonly list http://localhost without a port.
    # Bind a free loopback port instead of requiring privileged port 80.
    requested_port = parsed.port if parsed.port is not None else 0
    server = HTTPServer((parsed.hostname or "127.0.0.1", requested_port), Callback)
    callback_host = parsed.hostname or "127.0.0.1"
    redirect_uri = f"http://{callback_host}:{server.server_port}/"
    thread = Thread(target=server.handle_request, daemon=True)
    thread.start()
    params = {
        "client_id": str(details["client_id"]), "redirect_uri": redirect_uri, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    }
    url = f"{AUTH_URL}?{urlencode(params, quote_via=quote)}"
    print("Abriendo Google para autorizar la edición de la hoja...", flush=True)
    webbrowser.open(url)
    thread.join(timeout=300)
    server.server_close()
    if result.get("state") != state or not result.get("code"):
        raise RuntimeError("La autorización no se completó o fue cancelada.")
    token = token_request({
        "code": result["code"], "client_id": str(details["client_id"]),
        "client_secret": str(details.get("client_secret") or ""), "redirect_uri": redirect_uri,
        "grant_type": "authorization_code", "code_verifier": verifier,
    })
    token["expiresAt"] = time.time() + int(token.get("expires_in", 3600))
    save_token(token_path(config_path, settings), token)
    enable_writeback(config_path)
    print("[OK] Google Sheets quedó autorizado para esta computadora.")


def update_rows(config_path: Path, updates: list[dict[str, object]]) -> int:
    if not updates:
        return 0
    settings = load_config(config_path)
    sheet_name = str(settings.get("sheetName") or "Catalogo")
    access = access_token(config_path)
    data = []
    for update in updates:
        row = int(update.get("targetRow") or 0)
        values = update.get("values")
        if row < 2 or not isinstance(values, list) or len(values) != 10:
            raise RuntimeError("La cola de actualizaciones contiene una fila inválida.")
        data.append({"range": f"{sheet_name}!A{row}:J{row}", "values": [values]})
    target = f"{API_BASE}/{quote(spreadsheet_id(settings, config_path), safe='')}/values:batchUpdate?valueInputOption=USER_ENTERED"
    request_json(target, method="POST", headers={"Authorization": f"Bearer {access}"}, body={"valueInputOption": "USER_ENTERED", "data": data})
    return len(data)


def read_rows(config_path: Path, range_name: str) -> list[list[object]]:
    """Read the live sheet through the API, bypassing export-XLSX cache."""
    settings = load_config(config_path)
    access = access_token(config_path)
    target = f"{API_BASE}/{quote(spreadsheet_id(settings, config_path), safe='')}/values/{quote(range_name, safe='!')}"
    payload = request_json(target, headers={"Authorization": f"Bearer {access}"})
    values = payload.get("values", [])
    if not isinstance(values, list):
        raise RuntimeError("Google Sheets devolvió una respuesta de filas inválida.")
    return [row if isinstance(row, list) else [] for row in values]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Autoriza la edición de Google Sheets para Altoidss.")
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "config" / "anime-sync.json")
    parser.add_argument("--authorize", action="store_true")
    args = parser.parse_args()
    if not args.authorize:
        parser.error("Use --authorize para iniciar la autorización de Google.")
    authorize(args.config)
