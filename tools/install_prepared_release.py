"""Install only a pinned, reviewed code package; never migrate data or run Sheets.

CLI requires production PHP stopped. Original files and a durable operation report
are kept below the private installation plan. No Git checkout/reset or deletions.
An interrupted operation is NOT safe to serve: inspect its report before restart.
"""
import argparse
import json
import os
import socket
import tempfile
from datetime import datetime
from pathlib import Path

import prepare_code_release as release
from storage_transaction import atomic_json


def replace_bytes(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + '.deploy-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(workspace, plan, approved_commit):
    workspace, plan = workspace.resolve(), plan.absolute()
    production = workspace / 'ProyectoFinal/Aplication'
    source = workspace / 'Desarrollo/Aplication'
    if (plan.resolve() != plan or plan.parent != workspace / 'work/installation-plans'):
        raise ValueError('Plan fuera de la zona privada esperada.')
    manifest = json.loads((plan / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('commit') != approved_commit or manifest.get('mode') != 'PREPARATION_ONLY_NO_DEPLOY':
        raise ValueError('El SHA aprobado no coincide con el plan.')
    if manifest.get('deletionsPlanned'):
        raise ValueError('No se admiten eliminaciones.')
    pinned_paths = set(release.git(source, 'ls-tree', '-r', '--name-only', approved_commit).decode().splitlines())
    if {item['path'] for item in manifest['files']} != {name for name in pinned_paths if release.code_path(name)}:
        raise ValueError('El manifiesto no contiene todo el código permitido del commit.')
    if release.git(production, 'rev-parse', 'HEAD').decode().strip() != manifest['productionHead']:
        raise ValueError('Cambió la identidad Git de producción.')
    if release.protected_hashes(workspace, production) != manifest['protectedHashes']:
        raise ValueError('Cambió un dato protegido; regenerar el plan.')
    for directory in (production / 'data', workspace / 'datos/produccion/catalogo', workspace / 'datos/produccion/anime-sync'):
        if (directory / '.transaction.json').exists():
            raise ValueError('Hay una transacción pendiente.')
    payloads, originals, names = {}, {}, set()
    for item in manifest['files']:
        name = item['path']
        if not release.code_path(name) or name.casefold() in names:
            raise ValueError('Ruta no permitida o duplicada.')
        names.add(name.casefold())
        payload = release.read_inside(plan / 'code', name)
        if payload is None or release.digest(payload) != item['sha256']:
            raise ValueError('El paquete fue modificado.')
        if payload != release.git(source, 'show', approved_commit + ':' + name):
            raise ValueError('El contenido no pertenece al commit aprobado.')
        original = release.read_inside(production, name)
        if (release.digest(original) if original is not None else None) != item['expectedProductionSha256']:
            raise ValueError('Cambió un archivo de producción: ' + name)
        payloads[name], originals[name] = payload, original
    for item in manifest['localChanges']:
        current = release.read_inside(production, item['path'])
        if (release.digest(current) if current is not None else None) != item['productionSha256']:
            raise ValueError('Cambió una modificación local.')
    operation = plan / ('deployment-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    operation.mkdir(exist_ok=False)
    changed = [name for name in payloads if payloads[name] != originals[name]]
    for name in changed:
        if originals[name] is not None:
            replace_bytes(operation / 'originals' / name, originals[name])
            if release.read_inside(operation / 'originals', name) != originals[name]:
                raise RuntimeError('No se verificó el respaldo de código.')
    report = {'status': 'INSTALLING', 'commit': approved_commit,
              'productionGitHeadUnchanged': manifest['productionHead'], 'startedAt': datetime.now().astimezone().isoformat(),
              'changedPaths': changed, 'completedPaths': [], 'dataMigration': False,
              'sheetsStarted': False, 'operation': str(operation)}
    atomic_json(operation / 'report.json', report)
    try:
        for name in changed:
            if release.read_inside(production, name) != originals[name]:
                raise RuntimeError('El destino cambió durante la instalación.')
            replace_bytes(production / name, payloads[name])
            if release.read_inside(production, name) != payloads[name]:
                raise RuntimeError('No se verificó el archivo instalado.')
            report['completedPaths'].append(name)
            atomic_json(operation / 'report.json', report)
        if release.protected_hashes(workspace, production) != manifest['protectedHashes']:
            raise RuntimeError('Cambió un dato protegido durante la instalación.')
        if release.git(production, 'rev-parse', 'HEAD').decode().strip() != manifest['productionHead']:
            raise RuntimeError('Cambió la identidad Git.')
        report.update(status='CODE_INSTALLED_DATA_UNCHANGED', finishedAt=datetime.now().astimezone().isoformat(),
                      protectedFilesUnchanged=len(manifest['protectedHashes']), packageFiles=len(payloads))
        atomic_json(operation / 'report.json', report)
    except Exception:
        report['status'] = 'ROLLING_BACK_CODE_ONLY'
        atomic_json(operation / 'report.json', report)
        for name in reversed(changed):
            current = release.read_inside(production, name)
            if current == originals[name]:
                continue
            if current != payloads[name]:
                report['status'] = 'MANUAL_RECOVERY_REQUIRED'
                atomic_json(operation / 'report.json', report)
                raise RuntimeError('Cambio ajeno detectado; no se sobrescribe durante rollback.')
            if originals[name] is None:
                retained = operation / 'added-files-retained' / name
                retained.parent.mkdir(parents=True, exist_ok=True)
                os.replace(production / name, retained)  # Recoverable move, not deletion.
            else:
                replace_bytes(production / name, originals[name])
        report['status'] = 'CODE_ROLLED_BACK'
        atomic_json(operation / 'report.json', report)
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--apply-approved-commit', required=True)
    parser.add_argument('--reviewed-local-changes', action='store_true', required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[3]
    if workspace != Path('C:/Users/Alvar/Projects/Altoids'):
        raise SystemExit('Solo instalación migrada en C:, nunca la copia G:.')
    with socket.socket() as probe:
        probe.settimeout(1)
        if probe.connect_ex(('127.0.0.1', 8091)) == 0:
            raise SystemExit('Detener y verificar el PHP de producción antes de instalar.')
    result = install(workspace, args.plan, args.apply_approved_commit)
    print(json.dumps({key: result[key] for key in ('status', 'commit', 'operation', 'packageFiles', 'protectedFilesUnchanged')}))


if __name__ == '__main__':
    main()
