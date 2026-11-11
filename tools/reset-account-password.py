"""Local password reset/revocation. Passwords enter through getpass and an anonymous pipe."""
import argparse
import getpass
import json
from pathlib import Path
import shutil
import subprocess
import sys
import warnings

ALLOWED = {
    Path("C:/Users/Alvar/Projects/Altoids/ProyectoFinal/Aplication").resolve(),
    Path("C:/Users/Alvar/Projects/Altoids/Desarrollo/Aplication").resolve(),
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True, type=Path)
    parser.add_argument("--php", default=shutil.which("php") or "C:/xampp/php/php.exe")
    parser.add_argument("--user-id")
    parser.add_argument("--revoke-only", action="store_true")
    args, extra = parser.parse_known_args()
    if extra:
        parser.error("No se aceptan argumentos adicionales ni contraseñas en línea de comandos.")
    app = args.app.resolve()
    if app not in ALLOWED or args.app.absolute() != app:
        parser.error("Indique una instalación prevista en C:, sin enlaces. G: queda excluido.")
    if not sys.stdin.isatty():
        parser.error("Ejecute este operador en su terminal local interactiva; no pegue contraseñas en chat.")
    helper = app / "tools/account-security.php"
    if not helper.is_file():
        parser.error("La herramienta debe estar instalada mediante el release aprobado.")

    def call(action, payload):
        # Only app/action metadata are argv. Secret input stays in the child pipe.
        run = subprocess.run([args.php, str(helper), str(app), action],
            input=json.dumps(payload, ensure_ascii=False), capture_output=True,
            text=True, encoding="utf-8", timeout=35)
        if run.returncode:
            raise RuntimeError(run.stderr.strip() or "Operación incompleta; revise el estado antes de reintentar.")
        return json.loads(run.stdout)["result"]

    users = call("list", {})
    if not users:
        raise RuntimeError("No hay cuentas disponibles.")
    for number, user in enumerate(users, 1):
        print(f"{number}. {user['name']} ({user['role']}, {user['status']})")
    if args.user_id:
        user = next((u for u in users if u["id"] == args.user_id), None)
    else:
        choice = input("Número de la cuenta que desea actualizar: ").strip()
        user = users[int(choice)-1] if choice.isdecimal() and 1 <= int(choice) <= len(users) else None
    if user is None:
        raise RuntimeError("Selección de cuenta inválida.")
    if args.revoke_only:
        result = call("revoke", {"userId": user["id"]})
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("Nueva contraseña (mínimo 15 caracteres, máximo 72 bytes): ")
            confirmation = getpass.getpass("Confirme la contraseña: ")
        if password != confirmation:
            raise RuntimeError("La confirmación no coincide; no se modificó la cuenta.")
        if len(password) < 15 or len(password.encode("utf-8")) > 72 or "\0" in password:
            raise RuntimeError("Longitud de contraseña inválida; no se modificó la cuenta.")
        result = call("reset", {"userId": user["id"], "password": password})
        del password, confirmation
    print(json.dumps(result, ensure_ascii=False))
    print("IDs y relaciones conservados. Las sesiones previas quedan revocadas.")

if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        print("Operación no completada: " + str(error), file=sys.stderr)
        sys.exit(1)

