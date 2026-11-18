"""Construir y probar una distribución nueva desde blobs Git y datos ficticios."""
import argparse
import hashlib
import http.cookiejar
import json
from pathlib import Path
import secrets
import socket
import stat
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

from prepare_code_release import ROOT, code_path, git
from repository_hygiene import reject_payload, scan
from qa import fixture
from run_demo import inside, start, stop


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build(output, source=ROOT):
    source, output = source.resolve(), output.absolute()
    if output.resolve() != output or output.exists() or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError('Elija un directorio nuevo fuera del checkout; no se sobrescribe una entrega.')
    if Path(git(source, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != source:
        raise ValueError('La fuente debe ser la raíz de su propio checkout.')
    commit = git(source, 'rev-parse', 'HEAD').decode().strip()
    if scan(source, commit=commit)['status'] != 'PASSED':
        raise ValueError('La fuente Git contiene datos, artefactos o firmas prohibidas; use el checkout saneado.')
    # Solo blobs del SHA: no leer secretos, datos o archivos sueltos del entorno.
    with tempfile.TemporaryDirectory(prefix='altoidss-demo-build-') as temporary:
        root = Path(temporary).resolve()
        exported, bundle = root / 'exported', root / 'bundle'
        exported.mkdir()
        bundle.mkdir()
        for entry in filter(None, git(source, 'ls-tree', '-rz', commit).split(b'\0')):
            metadata, raw_name = entry.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            name = raw_name.decode()
            if not code_path(name):
                continue
            if kind != 'blob' or mode not in {'100644', '100755'}:
                raise ValueError('La entrega no admite enlaces ni submódulos.')
            data = git(source, 'cat-file', 'blob', oid)
            reject_payload(name, data)
            target = exported / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        if not (exported / 'tools/run_demo.py').is_file():
            raise ValueError('El SHA debe incluir el launcher revisado; haga commit antes de construir.')
        descriptor, hashes = fixture(exported, bundle / 'Aplicacion')
        for path in (bundle / 'Aplicacion/data').glob('*.json'):
            path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n'))
        # Los paths absolutos del generador de fixtures no se distribuyen.
        descriptor.write_text(json.dumps({'environment': 'isolated-demo',
            'catalogDir': 'fixture-catalog', 'syncStateDir': 'fixture-sync-state'}, indent=2) + '\n', encoding='utf-8', newline='\n')
        for name in ('Aplicacion/data', 'Aplicacion/backups', 'fixture-catalog', 'fixture-sync-state'):
            (bundle / name / '.htaccess').write_bytes(b'Require all denied\n')
        (bundle / '.htaccess').write_bytes(b'Require all denied\n')
        (bundle / 'Iniciar-Demo.cmd').write_bytes(b'@echo off\r\nsetlocal\r\npython -B "%~dp0Aplicacion\\tools\\run_demo.py" %*\r\nexit /b %errorlevel%\r\n')
        (bundle / 'LEEME.md').write_text(f'''# Altoidss — demostración aislada

Fuente: {commit}. Datos ficticios, sin cuentas o contraseñas precargadas.
Esta entrega nueva no actualiza ni sustituye la entrega histórica o producción.

Requiere Python 3.13 y PHP del perfil revisado en Aplicacion/docs/RUNTIME-AND-QA.md.
No descarga herramientas, inicia Sheets ni abre un túnel automáticamente.

Windows: Iniciar-Demo.cmd --php "RUTA_A_PHP_EXE" --check
Después: Iniciar-Demo.cmd --php "RUTA_A_PHP_EXE"
Otros sistemas: python3 -B Aplicacion/tools/run_demo.py --php /ruta/a/php

Abrir http://127.0.0.1:8093/Html/index.html. Ctrl+C detiene ese servidor.
Use el registro para una cuenta de prueba con correo example.invalid; no use datos reales.
El registro crea un usuario normal, sin administrador predeterminado.

Mantenga juntas todas las carpetas. El launcher verifica código, regenera su descriptor
y limita PHP a loopback. No copie configuración, OAuth o secretos de otros entornos.
Cada carpeta/puerto usa su propio nombre de sesión para evitar interferencia accidental.
El perfil HTTP local no es el perfil HTTPS de producción. La privacidad por servidor
se prueba con el PHP integrado y su router; no se certifica una publicación Apache.
Los .htaccess son una defensa adicional solo cuando el servidor los respeta.
Las búsquedas externas de la interfaz pueden consultar proveedores si usted las usa;
la construcción y el smoke no hacen esas consultas.
''', encoding='utf-8', newline='\n')
        payloads = {p.relative_to(bundle).as_posix(): p.read_bytes() for p in bundle.rglob('*') if p.is_file()}
        manifest = {'schema': 1, 'kind': 'altoidss-isolated-demo', 'commit': commit,
            'codeHashes': dict(sorted(hashes.items())), 'files': {name: digest(data) for name, data in sorted(payloads.items())},
            'usesProductionData': False, 'preloadedAccounts': 0, 'supportedServer': 'PHP built-in with bundled router'}
        raw = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
        payloads['demo-distribution.json'] = raw
        output.mkdir(parents=True)
        with zipfile.ZipFile(output / 'demo.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(payloads.items()):
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        (output / 'demo-distribution.json').write_bytes(raw)
    return {'status': 'DEMO_BUILT', 'commit': commit, 'codeFiles': len(hashes),
        'files': len(payloads), 'preloadedAccounts': 0, 'usesProductionData': False}


def smoke(archive_path, php):
    """Validar el mismo ZIP y probar HTTP/registro/login en una extracción descartable."""
    with tempfile.TemporaryDirectory(prefix='altoidss-demo-smoke-') as temporary:
        root = Path(temporary).resolve()
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            if len(names) != len({name.casefold() for name in names}) or len(names) > 2000 or sum(i.file_size for i in archive.infolist()) > 50_000_000:
                raise ValueError('Inventario de distribución inválido.')
            for entry in archive.infolist():
                inside(root, entry.filename)
                if stat.S_ISLNK(entry.external_attr >> 16):
                    raise ValueError('Ruta o enlace no permitido en el ZIP.')
            manifest = json.loads(archive.read('demo-distribution.json'))
            if set(names) != set(manifest['files']) | {'demo-distribution.json'} or archive.testzip() is not None:
                raise ValueError('El ZIP no coincide con el manifiesto.')
            for name in names:
                data = archive.read(name)
                if name != 'demo-distribution.json' and digest(data) != manifest['files'][name]:
                    raise ValueError('Hash de distribución incorrecto.')
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        app = root / 'Aplicacion'
        for name in ('usuarios', 'perfiles', 'configuraciones', 'favoritos', 'historial'):
            if json.loads((app / 'data' / (name + '.json')).read_text(encoding='utf-8')) != []:
                raise ValueError('Una distribución nueva debe iniciar sin cuentas o actividad precargadas.')
        for name in ('data/private.json', 'backups/private.json', 'runtime/private.json', 'config/private.json'):
            target = app / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('QA_PRIVATE_SENTINEL', encoding='utf-8')
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def request(path, data=None, token=None):
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['X-CSRF-Token'] = token
            body = None if data is None else json.dumps(data).encode()
            with opener.open(urllib.request.Request(f'http://127.0.0.1:{port}' + path, body, headers), timeout=5) as response:
                return response.status, response.read()
        server = start(app, php, port)
        try:
            for attempt in range(60):
                try:
                    if request('/Html/index.html')[0] == 200:
                        break
                except OSError:
                    if server.poll() is not None:
                        raise RuntimeError('El servidor de la demo terminó antes de responder.')
                    time.sleep(.1)
            else:
                raise RuntimeError('La demo no respondió.')
            public = ('/Html/catalogo.html', '/js/catalogo.js', '/css/site-shared.css', '/data/anime.json')
            for path in public:
                assert request(path)[0] == 200
            private = ('/data/usuarios.json', '/data/private.json', '/DATA/usuarios.json', '/data/./usuarios.json',
                '/data%5cusuarios.json', '/data/%75suarios.json', '/api/config/app.php',
                '/backups/private.json', '/runtime/private.json', '/config/private.json',
                '/../fixture-storage.json', '/tools/run_demo.py')
            for path in private:
                try:
                    request(path)
                    raise AssertionError('Una ruta privada respondió sin bloqueo.')
                except urllib.error.HTTPError as error:
                    assert error.code == 404 and b'QA_PRIVATE_SENTINEL' not in error.read()
            password = secrets.token_urlsafe(24)
            account = {'name': 'Demo smoke', 'email': 'demo-smoke@example.invalid', 'password': password}
            assert request('/api/index.php?route=/auth/register', account)[0] == 201
            status, body = request('/api/index.php?route=/auth/login', account)
            login = json.loads(body)
            assert status == 200 and login['data']['isAuthenticated'] and login['data']['role'] == 'usuario'
            assert request('/api/index.php?route=/auth/logout', {}, login['meta']['csrfToken'])[0] == 200
            assert not json.loads(request('/api/index.php?route=/auth/session')[1])['data']['isAuthenticated']
        finally:
            stop(server)
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError('El servidor temporal no se cerró.')
    return {'status': 'DEMO_STAGING_PASSED', 'commit': manifest['commit'], 'privateRoutesBlocked': len(private),
        'publicChecks': len(public) + 1, 'registrationLoginLogoutPassed': True, 'serverClosed': True,
        'usesProductionData': False, 'externalProviderCalls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build_args = commands.add_parser('build')
    build_args.add_argument('--output', type=Path, required=True)
    smoke_args = commands.add_parser('smoke')
    smoke_args.add_argument('--archive', type=Path, required=True)
    smoke_args.add_argument('--php', required=True)
    args = parser.parse_args()
    result = build(args.output) if args.command == 'build' else smoke(args.archive, args.php)
    print(json.dumps(result, ensure_ascii=False))
