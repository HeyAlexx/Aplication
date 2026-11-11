"""Build y staging aislados de CI; nunca instala en produccion. Ver docs/CI-CD.md."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

from prepare_code_release import code_path, git
from repository_hygiene import reject_payload

ROOT = Path(__file__).resolve().parents[1]


def build(output):
    """Empaqueta blobs del commit exacto, excluyendo datos y configuracion privada."""
    commit = git(ROOT, 'rev-parse', 'HEAD').decode().strip()
    hashes, payloads = {}, {}
    for entry in filter(None, git(ROOT, 'ls-tree', '-rz', commit).split(b'\0')):
        metadata, raw_name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        name = raw_name.decode()
        if not code_path(name):
            continue
        if kind != 'blob' or mode not in {'100644', '100755'}:
            raise ValueError('El paquete no admite enlaces ni submodulos.')
        data = git(ROOT, 'cat-file', 'blob', oid)
        reject_payload(name, data)
        payloads[name] = data
        hashes[name] = hashlib.sha256(data).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output / 'code.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in payloads.items():
            archive.writestr(name, data)
    manifest = {'commit': commit, 'files': hashes}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'commit': commit, 'codeFiles': len(hashes), 'dataIncluded': False}))


def smoke(package, php):
    """Verifica el mismo artefacto y lo sirve con datos ficticios en una carpeta temporal."""
    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='altoidss-staging-') as temporary:
        stage = Path(temporary)
        with zipfile.ZipFile(package / 'code.zip') as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or set(names) != set(manifest['files']):
                raise ValueError('El inventario no coincide con el paquete.')
            for name in names:
                target = stage / name
                if not code_path(name) or not target.resolve().is_relative_to(stage.resolve()):
                    raise ValueError('Ruta no permitida en staging.')
                data = archive.read(name)
                reject_payload(name, data)
                if hashlib.sha256(data).hexdigest() != manifest['files'][name]:
                    raise ValueError('Hash incorrecto: ' + name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        # Fixtures locales: no se copia catalogo, OAuth ni cuentas de ningun entorno.
        catalog = stage / 'fixture-catalog'
        state = stage / 'fixture-state'
        catalog.mkdir()
        state.mkdir()
        (stage / 'data').mkdir(exist_ok=True)
        (stage / 'backups').mkdir(exist_ok=True)
        for name in ('anime.json', 'peliculas.json', 'series.json', 'noticias.json'):
            (catalog / name).write_text('[]', encoding='utf-8')
        descriptor = stage / 'fixture-storage.json'
        descriptor.write_text(json.dumps({'environment': 'isolated-ci-staging',
            'catalogDir': str(catalog), 'syncStateDir': str(state)}), encoding='utf-8')
        # Puerto local libre; el servidor solo vive durante este smoke test.
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        environment = {**os.environ, 'ALTOIDSS_STORAGE_CONFIG': str(descriptor)}
        with tempfile.TemporaryFile() as log:
            server = subprocess.Popen([php, '-S', f'127.0.0.1:{port}', '-t', str(stage),
                str(stage / 'server-router.php')], cwd=stage, env=environment, stdout=log, stderr=log)
            try:
                base = f'http://127.0.0.1:{port}'
                for attempt in range(50):
                    try:
                        with urllib.request.urlopen(base + '/Html/catalogo.html', timeout=1):
                            break
                    except (OSError, urllib.error.URLError):
                        if server.poll() is not None:
                            raise RuntimeError('PHP no pudo iniciar staging.')
                        time.sleep(0.1)
                else:
                    raise RuntimeError('Staging no respondio.')
                # Respuestas reales del artefacto: paginas y recursos aprobados.
                public = ['Html/' + name for name in ('index.html', 'catalogo.html', 'dashboard.html',
                    'favoritos.html', 'login.html', 'noticias.html')]
                public += ['js/catalogo.js', 'css/site-shared.css', 'img/Altoidss.png', 'img/Altoidss.ico']
                for name in public:
                    with urllib.request.urlopen(base + '/' + name, timeout=5) as response:
                        if response.status != 200 or response.read() != (stage / name).read_bytes():
                            raise AssertionError('Contenido inesperado: ' + name)
                for name in ('/config/', '/runtime/', '/api/config/app.php'):
                    try:
                        urllib.request.urlopen(base + name, timeout=5)
                        raise AssertionError('Ruta privada accesible: ' + name)
                    except urllib.error.HTTPError as error:
                        if error.code != 404:
                            raise
                with urllib.request.urlopen(base + '/data/anime.json', timeout=5) as response:
                    if json.load(response) != []:
                        raise AssertionError('No se leyo el catalogo ficticio.')
                print(json.dumps({'status': 'STAGING_PASSED', 'commit': manifest['commit'],
                    'checks': len(public) + 4, 'usesProductionData': False}))
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('build').add_argument('--output', type=Path, required=True)
    staging = commands.add_parser('smoke')
    staging.add_argument('--package', type=Path, required=True)
    staging.add_argument('--php', default='php')
    args = parser.parse_args()
    if args.command == 'build':
        build(args.output.resolve())
    else:
        smoke(args.package.resolve(), args.php)
