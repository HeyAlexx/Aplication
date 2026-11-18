"""Arranque local de una distribución de demostración; nunca de una instalación operativa."""
import argparse
import hashlib
import json
import ntpath
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess


def inside(root, name):
    path = PurePosixPath(name)
    if not name or path.as_posix() != name or path.is_absolute() or '..' in path.parts or ':' in name or ntpath.isreserved(name) or '\\' in name:
        raise ValueError('Ruta no permitida en la demostración.')
    target = root / name
    if target.resolve() != target.absolute() or not target.resolve().is_relative_to(root):
        raise ValueError('La demostración no admite enlaces o junctions.')
    if target.is_file() and target.stat().st_nlink != 1:
        raise ValueError('La demostración no admite archivos compartidos por hardlink.')
    return target


def environment():
    return {key: value for key, value in os.environ.items()
        if not key.startswith(('ALTOIDSS_', 'WATCHMODE', 'MAL_', 'GOOGLE_'))
        and key not in {'PHPRC', 'PHP_INI_SCAN_DIR'}}


def check(app, php):
    """Leer y validar antes de escribir; el marcador distingue demo de producción."""
    app = app.absolute()
    if app.resolve() != app or app.name != 'Aplicacion':
        raise ValueError('Ejecute el launcher de una distribución nueva.')
    bundle = app.parent
    marker = inside(bundle, 'demo-distribution.json')
    if not marker.is_file():
        raise ValueError('Falta el marcador de demostración; no se modifica esta instalación.')
    manifest = json.loads(marker.read_text(encoding='utf-8'))
    if manifest.get('kind') != 'altoidss-isolated-demo' or not re.fullmatch(r'[a-f0-9]{40}', manifest.get('commit', '')):
        raise ValueError('Marcador de demostración inválido.')
    if 'server-router.php' not in manifest.get('codeHashes', {}) or 'tools/run_demo.py' not in manifest['codeHashes']:
        raise ValueError('Distribución incompleta: falta el arranque protegido.')
    for name, digest in manifest['codeHashes'].items():
        target = inside(app, name)
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError('El código difiere del manifiesto; vuelva a extraer el paquete.')
    for name in ('api/config/secrets.local.php', 'api/config/mal-client-id.local.txt',
                 'config/google-oauth-client.json', 'config/anime-sync.json', 'runtime/anime-sync/google-token.json'):
        if inside(app, name).exists():
            raise ValueError('La demostración no acepta configuración privada de otro entorno.')
    for name in ('Aplicacion/data', 'Aplicacion/backups', 'Aplicacion/runtime', 'Aplicacion/config',
                 'fixture-catalog', 'fixture-sync-state'):
        directory = inside(bundle, name)
        if directory.exists():
            if not directory.is_dir():
                raise ValueError('Un directorio de la demo fue sustituido por un archivo.')
            for parent, directories, files in os.walk(directory, followlinks=False):
                for child in directories + files:
                    inside(bundle, (Path(parent) / child).relative_to(bundle).as_posix())
    inside(bundle, 'fixture-storage.json')
    executable = shutil.which(str(php)) or str(Path(php).absolute())
    version = subprocess.check_output([executable, '-r', 'echo PHP_VERSION;'], text=True, timeout=15, env=environment()).strip()
    from runtime_spec import PHP_VERSION, PHP_COMPATIBILITY_VERSION
    if version not in {PHP_VERSION, PHP_COMPATIBILITY_VERSION}:
        raise ValueError('Seleccione uno de los PHP fijados y probados en docs/RUNTIME-AND-QA.md.')
    from bootstrap_php import doctor
    profile = doctor(executable, expected_version=version)
    return manifest, executable, profile


def start(app, php, port):
    if not 1024 <= port <= 65535:
        raise ValueError('El puerto debe estar entre 1024 y 65535.')
    _, executable, _ = check(app, php)
    app = app.resolve()
    bundle = app.parent
    for name in ('fixture-catalog', 'fixture-sync-state', 'Aplicacion/backups/sessions'):
        inside(bundle, name).mkdir(parents=True, exist_ok=True)
    descriptor = inside(bundle, 'fixture-storage.json')
    descriptor.write_text(json.dumps({'environment': 'isolated-demo',
        'catalogDir': str(bundle / 'fixture-catalog'),
        'syncStateDir': str(bundle / 'fixture-sync-state')}, indent=2) + '\n', encoding='utf-8')
    env = environment()
    env['ALTOIDSS_STORAGE_CONFIG'] = str(descriptor)
    # Ports do not isolate cookies: avoid overwriting another local app's cookie.
    env['ALTOIDSS_SESSION_NAME'] = 'ALTOIDSSDEMO' + hashlib.sha256((str(app) + '|' + str(port)).encode()).hexdigest()[:20]
    command = [executable, '-d', 'expose_php=Off', '-d', 'date.timezone=America/Costa_Rica',
        '-d', 'session.cookie_secure=0', '-d', 'session.cookie_httponly=1',
        '-d', 'session.cookie_samesite=Lax', '-S', f'127.0.0.1:{port}',
        '-t', str(app), str(app / 'server-router.php')]
    return subprocess.Popen(command, cwd=app, env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)


def stop(server):
    if server.poll() is None:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--php', default=shutil.which('php'))
    parser.add_argument('--port', type=int, default=8093)
    parser.add_argument('--check', action='store_true', help='Validar sin escribir ni iniciar PHP.')
    args = parser.parse_args()
    try:
        if not args.php:
            raise ValueError('Indique --php con la ruta de su PHP validado; no se descarga ni instala automáticamente.')
        app = Path(__file__).resolve().parents[1]
        if args.check:
            manifest, _, profile = check(app, args.php)
            print(json.dumps({'status': 'DEMO_CHECK_PASSED', 'commit': manifest['commit'], 'php': profile['version']}))
        else:
            server = start(app, args.php, args.port)
            print(f'Altoidss demo: http://127.0.0.1:{args.port}/Html/index.html\nCtrl+C para detener.', flush=True)
            try:
                raise SystemExit(server.wait())
            finally:
                stop(server)
    except KeyboardInterrupt:
        pass
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + '\n')
