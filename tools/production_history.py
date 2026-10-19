"""Explicit production-only, baseline-scoped historical migration with F: backup.

Does not enable the development initializer for production. Its pure planner is
reused; live writes have separate scope/hash/backup/service-stop requirements.
No Sheet writes, no development catalogue input, no overwriting later batches.
"""
import argparse
import json
import os
import socket
import subprocess
from datetime import datetime
from pathlib import Path

from initialize_historical_order import AUDIT_FIELD, make_plan, targets_for
from prepare_code_release import ROOT, digest, protected_hashes, save_new
from rehearse_production_history import NODE_CHECK, verify_changes
from storage_transaction import atomic_json, commit_collections, file_lock, storage_lock

CUTOFF = '2026-10-09T00:58:35-06:00'
IMPLEMENTATION = ('tools/production_history.py','tools/initialize_historical_order.py',
                  'tools/prepare_code_release.py','tools/rehearse_production_history.py',
                  'tools/storage_transaction.py','tools/historical-order-preview.cjs','js/content-order.js')


def durable_new(path, payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != payload:
        raise RuntimeError('El respaldo durable no coincide con el origen.')


def paths(workspace):
    production = workspace / 'ProyectoFinal/Aplication'
    descriptor = json.loads((production.parent / 'catalog-storage.local.json').read_text(encoding='utf-8-sig'))
    directory, state = workspace / 'datos/produccion/catalogo', workspace / 'datos/produccion/anime-sync'
    if (descriptor.get('environment') != 'produccion' or Path(descriptor['catalogDir']).resolve() != directory.resolve()
            or Path(descriptor['syncStateDir']).resolve() != state.resolve()):
        raise ValueError('Descriptor de producción no esperado.')
    if any((folder / '.transaction.json').exists() for folder in (directory, state, production / 'data')):
        raise ValueError('Hay una transacción pendiente; revisar antes de migrar.')
    return production, directory, state


def load_baseline(workspace, baseline):
    baseline = baseline.resolve()
    if (not baseline.is_relative_to(workspace / 'work/preproduction-snapshots')
            or baseline.parts[-3:] != ('production-central','catalogo','anime.json')):
        raise ValueError('Se requiere el snapshot previo de producción, nunca desarrollo.')
    snapshot = baseline.parents[2]
    manifest = json.loads((snapshot / 'manifest.json').read_text(encoding='utf-8-sig'))
    mirror = baseline.parent / 'anime-hoja.json'
    copies = {entry['source']: entry for entry in manifest['copies']}
    for saved in (baseline, mirror):
        original = str(workspace / 'datos/produccion/catalogo' / saved.name)
        entry = copies.get(original)
        if not entry or Path(entry['backup']).resolve() != saved or entry['sha256'].lower() != digest(saved.read_bytes()):
            raise ValueError('El baseline no corresponde al manifiesto de producción.')
    return json.loads(baseline.read_bytes()), json.loads(mirror.read_bytes())


def order_check(catalog_path, mirror_path):
    result = subprocess.run(['node','-e',NODE_CHECK,str(ROOT/'js/content-order.js'),str(catalog_path),str(mirror_path)],
                            capture_output=True, check=True)
    return json.loads(result.stdout)


def prepare(workspace, baseline, expected_count):
    workspace = workspace.resolve()
    production, directory, state = paths(workspace)
    before_hashes = protected_hashes(workspace, production)
    before_bytes = (directory / 'anime.json').read_bytes()
    mirror_bytes = (directory / 'anime-hoja.json').read_bytes()
    catalog, mirror = json.loads(before_bytes), json.loads(mirror_bytes)
    old_catalog, old_mirror = load_baseline(workspace, baseline)
    codes = {str(item['sourceCode']) for item in old_mirror}
    if len(codes) != len(old_mirror) or len(codes) != expected_count:
        raise ValueError('El tamaño del histórico no corresponde al alcance aprobado.')
    old_by_code = {str(item['sourceCode']): item for item in old_mirror}
    current_by_code = {str(item['sourceCode']): item for item in mirror}
    if len(current_by_code) != len(mirror) or any(current_by_code.get(code) != old_by_code[code] for code in codes):
        raise ValueError('Las filas históricas cambiaron: revisar el baseline y la propuesta.')
    old_ids = {item['id'] for item in old_catalog if str(item.get('sourceCode')) in codes}
    baseline_ids = {item['id'] for item in old_catalog}
    cohort = [item for item in catalog if item['id'] in baseline_ids]
    targets = [item for item in catalog if str(item.get('sourceCode')) in codes]
    if (len(targets) != expected_count or {item['id'] for item in targets} != old_ids
            or any(item.get(AUDIT_FIELD) or str(item.get('sheetImportBatchId','')).startswith('sheet-') for item in targets)):
        raise ValueError('El histórico incluye registros inicializados o altas posteriores protegidas.')
    # Existing baseline records without a current mirror row are protected too,
    # even when they retain an orphaned legacy sourceCode.
    later = [item for item in catalog if item['id'] not in baseline_ids
             and str(item.get('sourceCode')) in current_by_code]
    if any(not str(item.get('sheetImportBatchId','')).startswith('sheet-')
           or item.get('incorporationDateBasis') != 'initial-sheet-sync' for item in later):
        raise ValueError('No se reconocen todas las altas posteriores; revisar sin sobrescribir.')
    output = workspace / 'work/historical-production-previews' / ('scoped-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    if output.resolve() != output.absolute():
        raise ValueError('La zona de plan no puede pasar por enlaces.')
    output.mkdir(parents=True, exist_ok=False)
    atomic_json(output/'inputs/cohort-anime.json',cohort)
    atomic_json(output/'inputs/cohort-mirror.json',old_mirror)
    preview_path = output/'preview.json'
    subprocess.run(['node',str(ROOT/'tools/historical-order-preview.cjs'),str(output/'inputs/cohort-anime.json'),
                    str(output/'inputs/cohort-mirror.json'),CUTOFF,str(output/'report'),'--rebase-sheet-history'],
                   capture_output=True,check=True)
    save_new(preview_path,(output/'report/historical-order-preview.json').read_bytes())
    preview_bytes = preview_path.read_bytes()
    preview = json.loads(preview_bytes)
    if {row['code'] for row in targets_for(preview)} != codes:
        raise ValueError('La propuesta no coincide con los códigos históricos.')
    migration = digest(preview_bytes)
    proposed = make_plan(catalog,preview,migration,datetime.now().astimezone().isoformat())
    checks = verify_changes(catalog,proposed,preview)
    atomic_json(output/'full-before.json',catalog)
    atomic_json(output/'rehearsal-after.json',proposed)
    save_new(output/'full-mirror.json',mirror_bytes)
    order = order_check(output/'rehearsal-after.json',output/'full-mirror.json')
    if protected_hashes(workspace,production) != before_hashes:
        raise RuntimeError('Producción cambió durante la preparación.')
    plan = {'version':1,'environment':'produccion','status':'PREPARED_AND_REHEARSED',
            'baseline':str(baseline),'expectedHistoricalCount':expected_count,'cutoff':CUTOFF,
            'inputSha256':[digest(before_bytes),digest(mirror_bytes)],'protectedHashes':before_hashes,
            'previewSha256':migration,'historicalCodes':sorted(codes),
            'implementationSha256':{name:digest((ROOT/name).read_bytes()) for name in IMPLEMENTATION},
            'laterBatchRecordsPreserved':len(later),'localRecordsPreserved':len(catalog)-len(targets)-len(later),
            'rehearsal':{**checks,**order},'sheetWrites':0,'developmentDataUsed':False}
    atomic_json(output/'plan.json',plan)
    return output,plan


def apply(workspace, plan_path, approved_sha, backup):
    workspace, plan_path, backup = workspace.resolve(), plan_path.absolute(), backup.absolute()
    if (plan_path.resolve() != plan_path or not plan_path.is_relative_to(workspace/'work/historical-production-previews')
            or plan_path.name != 'plan.json' or backup.resolve() != backup or backup.is_relative_to(workspace)):
        raise ValueError('Plan/respaldo fuera de la zona autorizada.')
    plan_bytes = plan_path.read_bytes()
    if digest(plan_bytes) != approved_sha:
        raise ValueError('El plan cambió desde la aprobación.')
    plan = json.loads(plan_bytes)
    if plan.get('environment') != 'produccion' or plan.get('status') != 'PREPARED_AND_REHEARSED':
        raise ValueError('No es un plan específico de producción ensayado.')
    if plan.get('implementationSha256') != {name:digest((ROOT/name).read_bytes()) for name in IMPLEMENTATION}:
        raise ValueError('La implementación cambió desde el ensayo.')
    preview_bytes = (plan_path.parent/'preview.json').read_bytes()
    if digest(preview_bytes) != plan['previewSha256']:
        raise ValueError('La propuesta fue modificada.')
    preview = json.loads(preview_bytes)
    if ({row['code'] for row in targets_for(preview)} != set(plan['historicalCodes'])
            or len(plan['historicalCodes']) != plan['expectedHistoricalCount']):
        raise ValueError('Se amplió el alcance de la propuesta.')
    production,directory,state = paths(workspace)
    with file_lock(state/'.watcher.lock',timeout=0), storage_lock(directory):
        current = (directory/'anime.json').read_bytes()
        current_hashes = protected_hashes(workspace,production)
        result_path = plan_path.parent/'application-result.json'
        if result_path.exists():
            result = json.loads(result_path.read_bytes())
            if result.get('status') != 'APPLIED' or result.get('afterSha256') != digest(current):
                raise ValueError('Inicialización previa alterada; no sobrescribir.')
            expected = {**plan['protectedHashes'],str(directory/'anime.json'):digest(current)}
            if current_hashes != expected:
                raise ValueError('Cambió otro dato desde la aplicación.')
            return {**result,'status':'already-initialized'}
        if current_hashes != plan['protectedHashes']:
            raise ValueError('Producción cambió desde el plan; no aplicar.')
        if json.loads((directory/'anime-sheet-writeback.json').read_bytes()):
            raise ValueError('Hay devoluciones pendientes; conciliar antes de migrar.')
        if [digest(current),digest((directory/'anime-hoja.json').read_bytes())] != plan['inputSha256']:
            raise ValueError('Los datos de entrada cambiaron.')
        before = json.loads(current)
        proposed = make_plan(before,preview,plan['previewSha256'],datetime.now().astimezone().isoformat())
        checks = verify_changes(before,proposed,preview)
        # Exact bytes of ALL protected files before the first live write.
        backup.mkdir(parents=True,exist_ok=False)
        saved = []
        for name, expected in plan['protectedHashes'].items():
            source = Path(name)
            relative = source.relative_to(workspace)
            payload = source.read_bytes()
            if digest(payload) != expected:
                raise RuntimeError('Cambió un archivo durante el respaldo.')
            durable_new(backup/relative,payload)
            if digest((backup/relative).read_bytes()) != expected:
                raise RuntimeError('Respaldo independiente no verificado.')
            saved.append({'path':relative.as_posix(),'sha256':expected})
        durable_new(backup/'approved-plan.json',plan_bytes)
        durable_new(backup/'approved-preview.json',preview_bytes)
        atomic_json(backup/'manifest.json',{'status':'BACKUP_VERIFIED_BEFORE_HISTORY','approvedPlanSha256':approved_sha,'files':saved})
        if protected_hashes(workspace,production) != plan['protectedHashes']:
            raise RuntimeError('Cambió producción después de respaldar; no aplicar.')
        commit_collections(directory,{'anime.json':proposed})
        after = (directory/'anime.json').read_bytes()
        if json.loads(after) != proposed:
            raise RuntimeError('No se verificó el catálogo después de aplicar.')
        expected = {**plan['protectedHashes'],str(directory/'anime.json'):digest(after)}
        if protected_hashes(workspace,production) != expected:
            raise RuntimeError('Cambió una colección ajena; conservar respaldo y revisar.')
        order = order_check(directory/'anime.json',directory/'anime-hoja.json')
        result = {'status':'APPLIED','approvedPlanSha256':approved_sha,'migrationId':plan['previewSha256'],
                  'historicalInitialized':plan['expectedHistoricalCount'],'laterBatchRecordsUnchanged':plan['laterBatchRecordsPreserved'],
                  'localRecordsUnchanged':plan['localRecordsPreserved'],'checks':{**checks,**order},
                  'beforeSha256':digest(current),'afterSha256':digest(after),'backup':str(backup),'sheetWrites':0}
        atomic_json(result_path,result)
        atomic_json(backup/'application-result.json',result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['prepare','apply'])
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--plan',type=Path)
    parser.add_argument('--approved-plan-sha')
    parser.add_argument('--independent-backup',type=Path)
    args = parser.parse_args()
    workspace = ROOT.parents[1].resolve()
    if workspace != Path('C:/Users/Alvar/Projects/Altoids'):
        raise SystemExit('Solo el workspace migrado en C:.')
    if args.mode == 'prepare':
        if not args.baseline: parser.error('Falta --baseline de producción.')
        output,plan = prepare(workspace,args.baseline,781)
        print(json.dumps({'plan':str(output/'plan.json'),'approvedPlanSha256':digest((output/'plan.json').read_bytes()),
                         'historicalCount':781,'laterPreserved':plan['laterBatchRecordsPreserved'],
                         'localsPreserved':plan['localRecordsPreserved'],'rehearsal':plan['rehearsal']}))
    else:
        if not all((args.plan,args.approved_plan_sha,args.independent_backup)): parser.error('Faltan plan, SHA aprobado o respaldo.')
        if not args.independent_backup.resolve().is_relative_to(Path('F:/Altoidss-Backups').resolve()):
            raise SystemExit('El respaldo independiente debe estar bajo F:/Altoidss-Backups.')
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex(('127.0.0.1',8091)) == 0:
                raise SystemExit('Detener PHP de producción antes de migrar.')
        print(json.dumps(apply(workspace,args.plan,args.approved_plan_sha,args.independent_backup)))


if __name__ == '__main__':
    main()
