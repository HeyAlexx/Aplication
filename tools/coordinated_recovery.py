"""Private coordinated snapshot and isolated restore. Never restore onto live apps.

Windows service pause/resume and destination ACLs are handled by the explicit
PowerShell operator. No network/Google calls; no deletion or overwrite of backups.
"""
import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

from storage_transaction import atomic_json

ROOT = Path(__file__).resolve().parents[1]
TRANSIENT_TREES = ('work/recovery-drills', 'work/step5-operations')
PRIVATE_FILES = ('usuarios.json', 'perfiles.json', 'configuraciones.json', 'favoritos.json', 'historial.json')
CATALOG_FILES = ('anime.json', 'peliculas.json', 'series.json', 'noticias.json', 'temporadas.json',
                 'episodios.json', 'anime-hoja.json', 'anime-revisiones.json', 'anime-sheet-writeback.json')


def filesystem_path(path):
    """Opt in per operation to long Windows paths; never change OS settings."""
    path = path.absolute()
    if os.name == 'nt' and not str(path).startswith('\\\\?\\'):
        raw = str(path)
        return Path('\\\\?\\UNC\\' + raw[2:] if raw.startswith('\\\\') else '\\\\?\\' + raw)
    return path


def sha(path):
    with filesystem_path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_relative(value):
    if '\\' in value or ':' in value or not value or value.startswith('/'):
        raise ValueError('Ruta relativa inválida.')
    relative = Path(value)
    if '..' in relative.parts or relative.as_posix() != value or value == '.':
        raise ValueError('Ruta relativa fuera del respaldo.')
    return relative


def inventory(root):
    files, excluded, directories = [], [], []

    def visit(directory):
        for item in sorted(directory.iterdir()):
            relative = item.relative_to(root).as_posix()
            info = item.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                excluded.append({'path': relative, 'reason': 'reparse-point', 'target': str(item.resolve())})
            elif (any(relative == tree or relative.startswith(tree + '/') for tree in TRANSIENT_TREES)
                  or '__pycache__' in item.parts or item.name.endswith(('.log', '.pyc'))
                  or item.name in {'.storage.lock', '.watcher.lock', 'watcher.pid'}
                  or '.tmp-' in item.name):
                excluded.append({'path': relative, 'reason': 'transient-or-derived'})
            elif item.is_dir():
                directories.append(relative)
                visit(item)
            elif item.is_file():
                files.append((relative, info.st_size))
            else:
                raise ValueError('Tipo de archivo no admitido: ' + relative)
    visit(root)
    return files, excluded, directories


def copy_verified(source, target, expected=None):
    if filesystem_path(target).exists() or filesystem_path(target).is_symlink():
        raise ValueError('El destino ya existe; no se sobrescribe.')
    if not filesystem_path(source).is_file() or source.resolve() != source.absolute():
        raise ValueError('El origen no puede ser un enlace o ruta indirecta.')
    filesystem_path(target.parent).mkdir(parents=True, exist_ok=True)
    before = sha(source)
    if expected and before != expected:
        raise ValueError('La copia de respaldo no coincide con su manifiesto.')
    with filesystem_path(source).open('rb') as incoming, filesystem_path(target).open('xb') as outgoing:
        shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    if sha(source) != before or sha(target) != before:
        raise RuntimeError('No se verificó la copia: ' + source.name)
    return before


def json_state(workspace):
    counts = {}
    for folder, name in (('ProyectoFinal', 'production'), ('Desarrollo', 'development')):
        descriptor = json.loads((workspace / folder / 'catalog-storage.local.json').read_text(encoding='utf-8-sig'))
        expected_environment = 'produccion' if name == 'production' else 'desarrollo'
        if descriptor.get('environment') != expected_environment:
            raise ValueError('Descriptor de entorno inesperado.')
        for key, suffix in (('catalogDir', 'catalogo'), ('syncStateDir', 'anime-sync')):
            directory = Path(descriptor[key]).resolve()
            if directory != (workspace / 'datos' / expected_environment / suffix).resolve():
                raise ValueError('El almacenamiento no corresponde al entorno esperado.')
            if (directory / '.transaction.json').exists():
                raise ValueError('Transacción pendiente: requiere revisión antes del snapshot coordinado.')
            for path in directory.glob('*.json'):
                json.loads(path.read_text(encoding='utf-8-sig'))
        data = workspace / folder / 'Aplication' / 'data'
        if (data / '.transaction.json').exists():
            raise ValueError('Transacción privada pendiente: revisar antes del respaldo.')
        for path in data.glob('*.json'):
            json.loads(path.read_text(encoding='utf-8-sig'))
        central = Path(descriptor['catalogDir'])
        anime = json.loads((central / 'anime.json').read_text(encoding='utf-8-sig'))
        mirror = json.loads((central / 'anime-hoja.json').read_text(encoding='utf-8-sig'))
        codes = [str(item['sourceCode']) for item in anime if item.get('sourceCode')]
        mirror_codes = [str(item['sourceCode']) for item in mirror]
        if len(codes) != len(set(codes)) or len(mirror_codes) != len(set(mirror_codes)) or not set(mirror_codes) <= set(codes):
            raise ValueError('Códigos de catálogo/espejo incompletos o duplicados.')
        counts[name] = {'anime': len(anime), 'mirror': len(mirror), 'collections': {}}
        for filename in (*CATALOG_FILES,):
            path = central / filename
            counts[name]['collections'][filename] = len(json.loads(path.read_text(encoding='utf-8-sig')))
        for filename in PRIVATE_FILES:
            path = data / filename
            if path.exists():
                counts[name]['collections']['private:' + filename] = len(json.loads(path.read_text(encoding='utf-8-sig')))
    return counts


def snapshot(workspace, destination):
    workspace, destination = workspace.resolve(), destination.absolute()
    staging = destination.name == 'snapshot' and destination.is_relative_to(workspace / 'work' / 'step5-operations')
    if (destination.resolve() != destination or (destination.is_relative_to(workspace) and not staging)
            or workspace.is_relative_to(destination)):
        raise ValueError('El respaldo debe estar en una zona nueva, independiente y sin enlaces.')
    destination.mkdir(parents=True, exist_ok=True)
    if any(item.name != 'operator.json' for item in destination.iterdir()):
        raise ValueError('La carpeta de respaldo ya contiene archivos; no se reutiliza.')
    if (workspace / 'ProyectoFinal' / 'Aplication' / '.git' / 'objects' / 'info' / 'alternates').exists():
        raise ValueError('Git usa objetos externos: no sería un respaldo independiente.')
    before_state = json_state(workspace)
    atomic_json(destination / 'status.json', {'status': 'INCOMPLETE', 'containsPrivateData': True})
    files, excluded, directories = inventory(workspace)
    if sum(size for _, size in files) + 2 * 1024**3 > shutil.disk_usage(destination).free:
        raise ValueError('Espacio insuficiente para completar el respaldo con margen.')
    manifest = {'version': 1, 'source': str(workspace), 'snapshotAt': datetime.now().astimezone().isoformat(),
                'status': 'INCOMPLETE', 'containsPrivateData': True, 'encrypted': False,
                'writerPauseRequired': True, 'excluded': excluded, 'directories': directories,
                'files': [], 'jsonState': before_state}
    for relative in directories:
        filesystem_path(destination / 'payload' / safe_relative(relative)).mkdir(parents=True, exist_ok=True)
    for index, (relative, _) in enumerate(files, 1):
        source = workspace / safe_relative(relative)
        digest = copy_verified(source, destination / 'payload' / safe_relative(relative))
        manifest['files'].append({'path': relative, 'size': source.stat().st_size, 'sha256': digest})
        if index % 250 == 0:
            print(f'Backup: {index}/{len(files)} archivos verificados', flush=True)
    after_files, after_excluded, after_directories = inventory(workspace)
    if (files != after_files or excluded != after_excluded or directories != after_directories
            or json_state(workspace) != before_state):
        raise RuntimeError('El origen cambió durante el respaldo; no se valida.')
    for item in manifest['files']:
        if sha(workspace / item['path']) != item['sha256']:
            raise RuntimeError('Cambió un archivo durante la pausa; respaldo incompleto.')
    manifest['status'] = 'VERIFIED'
    manifest['totalBytes'] = sum(item['size'] for item in manifest['files'])
    atomic_json(destination / 'manifest.json', manifest)
    atomic_json(destination / 'status.json', {'status': 'VERIFIED', 'files': len(files), 'totalBytes': manifest['totalBytes'],
                                            'containsPrivateData': True, 'manifestSha256': sha(destination / 'manifest.json')})
    print(f'Backup verificado: {len(files)} archivos, {manifest["totalBytes"]} bytes', flush=True)
    return manifest


def transfer(stage, backup):
    """Sequential archive transfer after services resume; never read the live apps."""
    stage, backup = stage.resolve(), backup.absolute()
    status = json.loads((stage / 'status.json').read_text())
    manifest_path = stage / 'manifest.json'
    if status.get('status') != 'VERIFIED' or status.get('manifestSha256') != sha(manifest_path):
        raise ValueError('La captura local no está verificada.')
    manifest = json.loads(manifest_path.read_text())
    if backup.resolve() != backup or backup.is_relative_to(stage) or stage.is_relative_to(backup):
        raise ValueError('La transferencia necesita un destino independiente y sin enlaces.')
    backup.mkdir(parents=True, exist_ok=True)
    if any(item.name != 'operator.json' for item in backup.iterdir()):
        raise ValueError('No sobrescribir un respaldo existente.')
    atomic_json(backup / 'status.json', {'status': 'INCOMPLETE', 'format': 'zip', 'containsPrivateData': True})
    archive = backup / 'project.zip.incomplete'
    with archive.open('xb') as output:
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as packed:
            packed.writestr('manifest.json', manifest_path.read_bytes())
            for index, item in enumerate(manifest['files'], 1):
                relative = safe_relative(item['path'])
                source = stage / 'payload' / relative
                if sha(source) != item['sha256']:
                    raise RuntimeError('La captura local cambió antes de transferir.')
                with filesystem_path(source).open('rb') as incoming, packed.open('payload/' + item['path'], 'w', force_zip64=True) as target:
                    shutil.copyfileobj(incoming, target, 1024 * 1024)
                if index % 1000 == 0:
                    print(f'Transferencia secuencial: {index}/{len(manifest["files"])} archivos', flush=True)
        output.flush()
        os.fsync(output.fileno())
    with zipfile.ZipFile(archive) as packed:
        if packed.testzip() is not None:
            raise RuntimeError('El archivo de respaldo tiene un error CRC.')
    archive.rename(backup / 'project.zip')
    archive = backup / 'project.zip'
    atomic_json(backup / 'status.json', {'status': 'VERIFIED', 'format': 'zip', 'containsPrivateData': True,
                                       'archiveSha256': sha(archive), 'manifestSha256': sha(manifest_path),
                                       'files': len(manifest['files']), 'totalBytes': manifest['totalBytes']})
    print('Archivo independiente de F: escrito, CRC y SHA-256 verificados.', flush=True)


def archive_snapshot(workspace, backup):
    """Capture directly to one independent archive while HTTP writers are paused.

    Avoid a second full write to the system SSD. An interrupted archive is never
    promoted: state, inventory, every live hash, CRC and archive SHA must pass.
    """
    workspace, backup = workspace.resolve(), backup.absolute()
    if (backup.resolve() != backup or backup.is_relative_to(workspace)
            or workspace.is_relative_to(backup)):
        raise ValueError('El archivo necesita un destino independiente y sin enlaces.')
    backup.mkdir(parents=True, exist_ok=True)
    if any(item.name != 'operator.json' for item in backup.iterdir()):
        raise ValueError('No sobrescribir un respaldo existente.')
    if (workspace / 'ProyectoFinal/Aplication/.git/objects/info/alternates').exists():
        raise ValueError('Git usa objetos externos: respaldo no independiente.')
    before_state = json_state(workspace)
    files, excluded, directories = inventory(workspace)
    total = sum(size for _, size in files)
    if total + 2 * 1024**3 > shutil.disk_usage(backup).free:
        raise ValueError('Espacio insuficiente para el respaldo independiente.')
    atomic_json(backup / 'status.json', {'status': 'INCOMPLETE', 'format': 'zip',
                                       'containsPrivateData': True})
    manifest = {'version': 1, 'source': str(workspace),
                'snapshotAt': datetime.now().astimezone().isoformat(),
                'status': 'INCOMPLETE', 'containsPrivateData': True, 'encrypted': False,
                'writerPauseRequired': True, 'excluded': excluded,
                'directories': directories, 'files': [], 'jsonState': before_state}
    archive = backup / 'project.zip.incomplete'
    with archive.open('xb') as output:
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as packed:
            for index, (relative, size) in enumerate(files, 1):
                source = workspace / safe_relative(relative)
                if source.resolve() != source.absolute():
                    raise ValueError('El origen cambió a una ruta indirecta.')
                digest = hashlib.sha256()
                copied = 0
                with filesystem_path(source).open('rb') as incoming, packed.open('payload/' + relative, 'w', force_zip64=True) as target:
                    while chunk := incoming.read(1024 * 1024):
                        target.write(chunk)
                        digest.update(chunk)
                        copied += len(chunk)
                if copied != size or sha(source) != digest.hexdigest():
                    raise RuntimeError('El origen cambió durante la captura.')
                manifest['files'].append({'path': relative, 'size': size, 'sha256': digest.hexdigest()})
                if index % 1000 == 0:
                    atomic_json(backup / 'status.json', {'status': 'INCOMPLETE', 'format': 'zip',
                                'containsPrivateData': True, 'filesCaptured': index, 'filesExpected': len(files)})
                    print(f'Captura secuencial F: {index}/{len(files)} archivos', flush=True)
            if inventory(workspace) != (files, excluded, directories) or json_state(workspace) != before_state:
                raise RuntimeError('El origen cambió; no se valida el respaldo.')
            for item in manifest['files']:
                if sha(workspace / item['path']) != item['sha256']:
                    raise RuntimeError('Cambió un archivo durante la pausa.')
            manifest.update(status='VERIFIED', totalBytes=total)
            manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            packed.writestr('manifest.json', manifest_bytes)
        output.flush()
        os.fsync(output.fileno())
    with zipfile.ZipFile(archive) as packed:
        if packed.testzip() is not None:
            raise RuntimeError('Error CRC: respaldo incompleto.')
    archive.rename(backup / 'project.zip')
    atomic_json(backup / 'status.json', {'status': 'VERIFIED', 'format': 'zip', 'containsPrivateData': True,
                'archiveSha256': sha(backup / 'project.zip'),
                'manifestSha256': hashlib.sha256(manifest_bytes).hexdigest(), 'files': len(files), 'totalBytes': total})
    print(f'Captura independiente verificada: {len(files)} archivos, {total} bytes', flush=True)
    return manifest


def restore(workspace, backup, php):
    workspace, backup = workspace.resolve(), backup.resolve()
    status = json.loads((backup / 'status.json').read_text())
    if status.get('status') != 'VERIFIED':
        raise ValueError('El respaldo no está completo/verificado.')
    archive = None
    if status.get('format') == 'zip':
        if status.get('archiveSha256') != sha(backup / 'project.zip'):
            raise ValueError('SHA-256 del archivo independiente incorrecto.')
        archive = zipfile.ZipFile(backup / 'project.zip')
        manifest_bytes = archive.read('manifest.json')
        if hashlib.sha256(manifest_bytes).hexdigest() != status['manifestSha256']:
            archive.close()
            raise ValueError('Manifiesto del archivo independiente incorrecto.')
    else:
        manifest_bytes = (backup / 'manifest.json').read_bytes()
        if hashlib.sha256(manifest_bytes).hexdigest() != status['manifestSha256']:
            raise ValueError('El manifiesto de respaldo no coincide.')
    manifest = json.loads(manifest_bytes)
    if manifest.get('source') != str(workspace) or manifest.get('status') != 'VERIFIED':
        raise ValueError('El respaldo no corresponde al workspace esperado.')
    if manifest['totalBytes'] + 2 * 1024**3 > shutil.disk_usage(workspace).free:
        raise ValueError('Espacio insuficiente para el ensayo de recuperación en C:.')
    root = workspace / 'work' / 'recovery-drills' / ('coordinated-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    if root.resolve() != root.absolute():
        raise ValueError('El ensayo no puede pasar por enlaces/junctions.')
    root.mkdir(parents=True, exist_ok=False)
    restored = root / 'workspace'
    for relative in manifest['directories']:
        filesystem_path(restored / safe_relative(relative)).mkdir(parents=True, exist_ok=True)
    names = set()
    if archive:
        expected_names = {'manifest.json', *('payload/' + item['path'] for item in manifest['files'])}
        if len(archive.namelist()) != len(expected_names) or set(archive.namelist()) != expected_names:
            archive.close()
            raise ValueError('Entradas inesperadas o duplicadas en el archivo de respaldo.')
    for index, item in enumerate(manifest['files'], 1):
        relative = safe_relative(item['path'])
        if item['path'].casefold() in names:
            raise ValueError('Manifiesto con rutas duplicadas.')
        names.add(item['path'].casefold())
        if archive:
            target = restored / relative
            filesystem_path(target.parent).mkdir(parents=True, exist_ok=True)
            entry = archive.getinfo('payload/' + item['path'])
            if entry.file_size != item['size'] or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('Tamaño/tipo inesperado en el archivo de respaldo.')
            with archive.open(entry) as incoming, filesystem_path(target).open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            if sha(target) != item['sha256']:
                raise ValueError('No coincide la huella del archivo restaurado.')
        else:
            copy_verified(backup / 'payload' / relative, restored / relative, item['sha256'])
        if index % 250 == 0:
            print(f'Restore aislado: {index}/{len(manifest["files"])} archivos verificados', flush=True)
    if archive:
        archive.close()
    checks = []
    for folder, environment in (('ProyectoFinal', 'production'), ('Desarrollo', 'development')):
        app = restored / folder / 'Aplication'
        central = restored / 'datos' / ('produccion' if environment == 'production' else 'desarrollo')
        descriptor = root / (environment + '-isolated-storage.json')
        atomic_json(descriptor, {'environment': 'isolated-recovery', 'catalogDir': str(central / 'catalogo'),
                                 'syncStateDir': str(central / 'anime-sync')})
        result = subprocess.run([str(php), str(ROOT / 'tests' / 'coordinated-restore.php'), str(app)],
                                env={**os.environ, 'ALTOIDSS_STORAGE_CONFIG': str(descriptor)},
                                capture_output=True, check=True)
        checks.append({'environment': environment, **json.loads(result.stdout)})
    git_dir = restored / 'ProyectoFinal' / 'Aplication' / '.git'
    git_check = subprocess.run(['git', '--no-optional-locks', '--git-dir=' + str(git_dir), '-c', 'core.bare=true',
                                'fsck', '--full', '--no-reflogs'], capture_output=True, check=True,
                               env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    # Recheck all restored bytes after read-only services; never execute restored launchers/Git worktrees.
    for item in manifest['files']:
        if sha(restored / item['path']) != item['sha256']:
            raise RuntimeError('El ensayo alteró un archivo restaurado: ' + item['path'])
    report = {'status': 'PASSED', 'backup': str(backup), 'restoredTo': str(restored), 'files': len(names),
              'bytes': manifest['totalBytes'], 'manifestSha256': status['manifestSha256'], 'checks': checks,
              'gitObjectsFsckPassed': git_check.returncode == 0, 'originalDescriptorsNotExecuted': True,
              'liveDataRestored': False, 'googleRequests': 0,
              'limits': ['No SO/runtime installation', 'No automatic worktree relocation',
                         'No external junction targets', 'No restored live PHP sessions', 'Not encrypted']}
    atomic_json(root / 'report.json', report)
    atomic_json(backup / 'recovery-report.json', report)
    print(json.dumps({'status': 'PASSED', 'report': str(root / 'report.json'), 'files': len(names),
                      'environments': len(checks), 'gitObjectsFsckPassed': True}, ensure_ascii=False), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['preflight', 'snapshot', 'archive', 'transfer', 'restore'])
    parser.add_argument('--workspace', type=Path, default=ROOT.parents[1])
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--php', type=Path, default=Path('C:/xampp/php/php.exe'))
    parser.add_argument('--stage', type=Path)
    args = parser.parse_args()
    backup_root = Path('F:/Altoidss-Backups').resolve()
    staging_root = args.workspace.resolve() / 'work' / 'step5-operations'
    local_snapshot = args.mode == 'snapshot' and args.backup.name == 'snapshot' and args.backup.resolve().is_relative_to(staging_root)
    if not local_snapshot and (not args.backup.resolve().is_relative_to(backup_root) or args.backup.resolve() == backup_root):
        raise SystemExit('Use una carpeta nueva bajo F:/Altoidss-Backups, nunca la raíz del disco.')
    if args.mode == 'preflight':
        json_state(args.workspace.resolve())
        files, excluded, _ = inventory(args.workspace.resolve())
        print(json.dumps({'files': len(files), 'totalBytes': sum(size for _, size in files),
                          'excludedEntries': len(excluded),
                          'reparsePoints': sum(item['reason'] == 'reparse-point' for item in excluded)}))
    elif args.mode == 'snapshot':
        snapshot(args.workspace, args.backup)
    elif args.mode == 'archive':
        archive_snapshot(args.workspace, args.backup)
    elif args.mode == 'transfer':
        if not args.stage or not args.stage.resolve().is_relative_to(staging_root) or args.stage.name != 'snapshot':
            raise SystemExit('La captura local debe residir en work/step5-operations/.../snapshot.')
        transfer(args.stage, args.backup)
    else:
        restore(args.workspace, args.backup, args.php)


if __name__ == '__main__':
    main()
