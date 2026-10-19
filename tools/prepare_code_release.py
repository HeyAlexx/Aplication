"""Prepare code and a private inventory outside both checkouts. NEVER installs.

Reads committed Git blobs, not dirty development files. No Google/network calls,
process control, branch switches, resets, merges or writes to production.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
TEXT_ROOTS = {'api', 'Html', 'css', 'js', 'docs', 'tests', 'tools', '.github'}
TEXT_SUFFIXES = {'.php', '.html', '.css', '.js', '.cjs', '.py', '.ps1', '.md', '.yml', '.yaml'}
ROOT_FILES = {'server-router.php', 'README.md', 'CONTRIBUTING.md', 'CHANGELOG.md', 'ROADMAP.md', 'VERSION'}
ASSET_SUFFIXES = {'.svg', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.ico', '.woff', '.woff2', '.ttf'}


def git(repo, *arguments):
    return subprocess.run(
        ['git', '--no-optional-locks', '-c', f'safe.directory={repo.as_posix()}',
         '-C', str(repo), *arguments], check=True, capture_output=True,
        env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'},
    ).stdout


def code_path(name):
    path = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or path.is_absolute() or '..' in path.parts:
        return False
    if any(part in {'node_modules', '__pycache__', '.git', 'data', 'runtime', 'outputs', 'backups', 'config'}
           for part in path.parts if not (part == 'config' and path.parts[:2] == ('api', 'config'))):
        return False
    if '.local.' in path.name or path.name.startswith('.env'):
        return False
    if name in ROOT_FILES:
        return True
    return ((path.parts[0] in TEXT_ROOTS and path.suffix in TEXT_SUFFIXES)
            or (path.parts[0] == 'img' and path.suffix.lower() in ASSET_SUFFIXES))


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def normalized(payload):
    return None if payload is None else payload.replace(b'\r\n', b'\n')


def local_classification(base, current, candidate):
    if current is None:
        return 'local-deletion-review'
    if normalized(current) == normalized(candidate):
        return 'already-in-candidate'
    if base is not None and normalized(current) == normalized(base):
        return 'format-only'
    if candidate is None:
        return 'preserve-outside-payload'
    if base is None:
        return 'untracked-collision-review'
    if normalized(base) == normalized(candidate):
        return 'production-only-review'
    return 'overlap-review'


def read_inside(root, name):
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Una ruta de código apunta fuera de su checkout.')
    if path.exists() and not path.is_file():
        raise ValueError('Una ruta de archivo corresponde a un directorio.')
    return path.read_bytes() if path.is_file() else None


def save_new(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(payload)


def production_status(production):
    records = git(production, 'status', '--porcelain=v1', '-z', '--untracked-files=all').split(b'\0')
    result, excluded = [], 0
    for record in filter(None, records):
        entry = record.decode('utf-8')
        status, name = entry[:2], entry[3:]
        if 'R' in status or 'C' in status:
            raise ValueError('Hay renombrados/copias locales; revisar manualmente antes de preparar.')
        if name.startswith(('outputs/', 'backups/', 'runtime/')) or '__pycache__' in PurePosixPath(name).parts:
            excluded += 1
        else:
            result.append((status, name))
    return result, excluded


def protected_hashes(workspace, production):
    paths = set((production / 'data').glob('*.json'))
    for relative in ('api/config/secrets.local.php', 'api/config/mal-client-id.local.txt',
                     'config/anime-sync.json', 'config/google-oauth-client.json',
                     'runtime/anime-sync/google-token.json'):
        path = production / relative
        if path.is_file():
            paths.add(path)
    descriptor = production.parent / 'catalog-storage.local.json'
    if not descriptor.is_file():
        raise ValueError('Falta el descriptor externo de producción.')
    settings = json.loads(descriptor.read_text(encoding='utf-8-sig'))
    if settings.get('environment') != 'produccion':
        raise ValueError('El descriptor no corresponde a producción.')
    paths.add(descriptor)
    for key in ('catalogDir', 'syncStateDir'):
        directory = Path(settings[key]).resolve()
        if not directory.is_relative_to((workspace / 'datos' / 'produccion').resolve()) or not directory.is_dir():
            raise ValueError('El almacenamiento de producción está fuera de su zona esperada.')
        paths.update(directory.glob('*.json'))
    return {str(path): digest(path.read_bytes()) for path in sorted(paths)}


def prepare(workspace, source, commit):
    workspace, source = workspace.resolve(), source.resolve()
    production = workspace / 'ProyectoFinal' / 'Aplication'
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Indica un SHA completo, no una rama móvil.')
    if source == production.resolve() or not source.is_relative_to(workspace):
        raise ValueError('La fuente debe ser un checkout separado dentro del workspace.')
    git(source, 'cat-file', '-e', commit + '^{commit}')
    before_status, excluded = production_status(production)
    before_protected = protected_hashes(workspace, production)
    production_head = git(production, 'rev-parse', 'HEAD').decode().strip()
    stamp = datetime.now().astimezone().strftime('%Y%m%d-%H%M%S-%f')
    output = workspace / 'work' / 'installation-plans' / (stamp + '-' + commit[:12])
    if output.resolve() != output.absolute():
        raise ValueError('La zona de preparación no puede contener enlaces o junctions.')
    output.mkdir(parents=True, exist_ok=False)
    payloads, tree_paths = {}, set()
    for entry in filter(None, git(source, 'ls-tree', '-r', '-z', commit).split(b'\0')):
        metadata, raw_name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        name = raw_name.decode('utf-8')
        if not code_path(name):
            continue
        if mode not in {'100644', '100755'} or kind != 'blob' or name.casefold() in tree_paths:
            raise ValueError('El paquete contiene un enlace, submódulo o ruta ambigua.')
        tree_paths.add(name.casefold())
        payloads[name] = git(source, 'cat-file', 'blob', oid)
        save_new(output / 'code' / name, payloads[name])
    if not {'server-router.php', 'api/config/catalog-storage.php', 'tools/storage_transaction.py'} <= payloads.keys():
        raise ValueError('El commit no contiene el soporte central requerido.')
    local_changes = []
    for status, name in before_status:
        current = read_inside(production, name)
        try:
            base = git(production, 'show', production_head + ':' + name)
        except subprocess.CalledProcessError:
            base = None
        candidate = payloads.get(name)
        # Preserve dirty code only. Operational data/credentials never enter the package.
        if current is not None and (code_path(name) or name == 'Iniciar-Desarrollo.cmd'):
            save_new(output / 'production-local' / name, current)
        local_changes.append({'path': name, 'status': status,
                              'classification': local_classification(base, current, candidate),
                              'productionSha256': digest(current) if current is not None else None,
                              'candidateSha256': digest(candidate) if candidate is not None else None})
    local_names = {item['path'] for item in local_changes}
    files = []
    tracked = set(git(production, 'ls-files', '-z').decode().rstrip('\0').split('\0'))
    for name, payload in payloads.items():
        current = read_inside(production, name)
        action = 'unchanged' if current == payload else 'add' if current is None else 'replace-after-approval'
        if name in local_names or (current is not None and name not in tracked):
            action = 'review-local-before-replace'
        files.append({'path': name, 'sha256': digest(payload),
                      'expectedProductionSha256': digest(current) if current is not None else None,
                      'plannedAction': action})
    if (production_status(production) != (before_status, excluded)
            or protected_hashes(workspace, production) != before_protected
            or git(production, 'rev-parse', 'HEAD').decode().strip() != production_head):
        raise RuntimeError('Producción cambió durante la lectura; el plan no se valida. Repetir sin escritores.')
    # Hash preconditions become stale on any later code edit. This is not an installer.
    for item in files:
        current = read_inside(production, item['path'])
        if (digest(current) if current is not None else None) != item['expectedProductionSha256']:
            raise RuntimeError('Cambió un archivo de código mientras se preparaba el plan.')
    for item in local_changes:
        current = read_inside(production, item['path'])
        if (digest(current) if current is not None else None) != item['productionSha256']:
            raise RuntimeError('Cambió una modificación local durante la preparación.')
    manifest = {'version': 1, 'preparedAt': datetime.now().astimezone().isoformat(),
                'mode': 'PREPARATION_ONLY_NO_DEPLOY', 'commit': commit,
                'productionHead': production_head, 'productionModified': False,
                'sheetsStarted': False, 'containsPrivateInventory': True,
                'excludedGeneratedStatusEntries': excluded, 'deletionsPlanned': [],
                'protectedHashes': before_protected, 'localChanges': local_changes,
                'files': files, 'summary': dict(Counter(item['classification'] for item in local_changes)),
                'pending': ['review-local-code', 'historical-production-preview',
                            'coordinated-backup-and-restore', 'explicit-merge-and-deploy-approval']}
    save_new(output / 'manifest.json', (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode())
    return output, manifest


def rehearse(output, manifest, workspace, php):
    """Read old production data with new code in a disposable, credential-free copy."""
    production = workspace / 'ProyectoFinal' / 'Aplication'
    if protected_hashes(workspace, production) != manifest['protectedHashes']:
        raise RuntimeError('Los datos cambiaron desde el inventario; repetir preparación.')
    settings = json.loads((production.parent / 'catalog-storage.local.json').read_text(encoding='utf-8-sig'))
    central = Path(settings['catalogDir'])
    if (central / '.transaction.json').exists():
        raise RuntimeError('Hay una transacción pendiente en producción; no se ensaya con una copia parcial.')
    root = output / 'rehearsal'
    app, catalog, state = root / 'app', root / 'catalog', root / 'state'
    for item in manifest['files']:
        original = (output / 'code' / item['path']).read_bytes()
        if digest(original) != item['sha256']:
            raise RuntimeError('El paquete de código fue modificado.')
        save_new(app / item['path'], original)
    for directory in (app / 'data', app / 'backups', catalog, state):
        directory.mkdir(parents=True, exist_ok=True)
    for name in ('anime.json', 'peliculas.json', 'series.json', 'noticias.json',
                 'temporadas.json', 'episodios.json', 'anime-revisiones.json',
                 'anime-sheet-writeback.json', 'anime-hoja.json'):
        original = central / name
        payload = original.read_bytes() if original.is_file() else b'[]\n'
        expected = manifest['protectedHashes'].get(str(original))
        if (digest(payload) if original.is_file() else None) != expected:
            raise RuntimeError('Cambió una colección durante la copia de ensayo.')
        save_new(catalog / name, payload)
    save_new(app / 'data' / 'usuarios.json', b'[{"id":"isolated-local-only"}]\n')
    descriptor = root / 'catalog-storage.local.json'
    save_new(descriptor, json.dumps({'environment': 'isolated-release-rehearsal',
                                    'catalogDir': str(catalog), 'syncStateDir': str(state)}).encode())
    environment = {**os.environ, 'ALTOIDSS_STORAGE_CONFIG': str(descriptor)}
    # Only PHP CLI local reads. No HTTP server, provider calls, OAuth or real users.
    result = subprocess.run([str(php), str(ROOT / 'tests' / 'code-release-compatibility.php'), str(app)],
                            env=environment, capture_output=True, check=True)
    checks = json.loads(result.stdout)
    if protected_hashes(workspace, production) != manifest['protectedHashes']:
        raise RuntimeError('Producción cambió durante el ensayo; revisar antes de continuar.')
    checks['productionProtectedFilesUnchanged'] = len(manifest['protectedHashes'])
    checks['codeCommit'] = manifest['commit']
    checks['testHarnessSha256'] = digest((ROOT / 'tests' / 'code-release-compatibility.php').read_bytes())
    save_new(root / 'report.json', (json.dumps(checks, ensure_ascii=False, indent=2) + '\n').encode())
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=ROOT.parents[1])
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--php', type=Path, help='Opcional: ensayo CLI aislado; no inicia un servidor.')
    args = parser.parse_args()
    output, report = prepare(args.workspace, args.source, args.commit)
    checks = rehearse(output, report, args.workspace.resolve(), args.php) if args.php else None
    print(json.dumps({'plan': str(output), 'commit': report['commit'], 'codeFiles': len(report['files']),
                      'localChanges': len(report['localChanges']), 'summary': report['summary'],
                      'protectedFilesUnchanged': len(report['protectedHashes']),
                      'productionModified': False, 'sheetsStarted': False,
                      'rehearsal': checks}, ensure_ascii=False))


if __name__ == '__main__':
    main()
