"""Apply an approved, hash-bound historical preview to DEVELOPMENT only, once."""
import argparse
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path

from incorporation import FIELDS
from storage_transaction import atomic_json, commit_collections, storage_lock

VERSION = 'sheet-history-v1'
AUDIT_FIELD = 'historicalOrderInitialization'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def targets_for(report):
    if report.get('strategy') != 'rebase-all-linked-sheet-row-order' or not report.get('sheetOrderMatches') or report.get('missingCodes'):
        raise ValueError('Solo se aplica una propuesta completa de orden de filas aprobada.')
    targets = [row for row in report['rows'] if row.get('row') is not None]
    if len(targets) != report['mirrorRows'] or len({row['id'] for row in targets}) != len(targets):
        raise ValueError('Propuesta incompleta o IDs duplicados.')
    previous = None
    for row in sorted(targets, key=lambda entry: entry['row']):
        if not isinstance(row['row'], int) or row['row'] < 2 or not row.get('basis', '').startswith('historical-'):
            raise ValueError('Fila o procedencia inválida.')
        date = datetime.fromisoformat(row['proposedAt'])
        if date.tzinfo is None or (previous and date < previous):
            raise ValueError('Referencia inválida o secuencia temporal incompatible con filas.')
        previous = date
    return targets


def make_plan(catalog, report, migration_id, initialized_at):
    targets = {row['id']: row for row in targets_for(report)}
    if len({item['id'] for item in catalog}) != len(catalog):
        raise ValueError('IDs de catálogo duplicados.')
    if not targets.keys() <= {item['id'] for item in catalog}:
        raise ValueError('Faltan registros vinculados.')
    result = copy.deepcopy(catalog)
    for item in result:
        row = targets.get(item['id'])
        if row is None:
            continue
        if str(item.get('sourceCode')) != row['code'] or item.get('sourceRow') != row['row']:
            raise ValueError('Vínculo o fila cambió respecto a la propuesta.')
        if item.get(AUDIT_FIELD):
            raise ValueError('Un histórico ya inicializado no se sobrescribe.')
        original = {key: copy.deepcopy(item[key]) for key in (*FIELDS, 'createdAt', 'importedAt') if key in item}
        item.update({'incorporatedAt': row['proposedAt'],
                     'sheetImportBatchId': 'historical-' + sha(row['proposedAt'].encode())[:24],
                     'sheetImportRow': row['row'], 'incorporationDateBasis': row['basis'],
                     AUDIT_FIELD: {'version': VERSION, 'migrationId': migration_id,
                                   'initializedAt': initialized_at, 'precision': 'estimated-quarter-or-row-reference',
                                   'originalDates': original, 'quarterAnchor': row.get('quarterAnchor'),
                                   'borrowedSourceCode': row.get('borrowedCode'),
                                   'sheetRow': row['row']}})
    return result


def apply_report(directory, report_path, backup_dir):
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    targets = targets_for(report)
    migration_id = sha(report_bytes)
    with storage_lock(directory):
        catalog_path, mirror_path = directory / 'anime.json', directory / 'anime-hoja.json'
        before, mirror_bytes = catalog_path.read_bytes(), mirror_path.read_bytes()
        catalog = json.loads(before)
        by_id = {item['id']: item for item in catalog}
        if len(by_id) != len(catalog):
            raise ValueError('IDs duplicados en catálogo.')
        initialized = [by_id.get(row['id'], {}).get(AUDIT_FIELD, {}) for row in targets]
        if any(initialized):
            if not all(audit.get('migrationId') == migration_id for audit in initialized):
                raise ValueError('Inicialización parcial o diferente: revisar, no sobrescribir.')
            for row in targets:
                current = by_id[row['id']]
                if (current.get('incorporatedAt') != row['proposedAt'] or current.get('sheetImportRow') != row['row']
                        or current.get('sheetImportBatchId') != 'historical-' + sha(row['proposedAt'].encode())[:24]
                        or current.get('incorporationDateBasis') != row['basis']):
                    raise ValueError('Las referencias inicializadas fueron alteradas; revisar.')
            return {'status': 'already-initialized', 'count': len(targets), 'migrationId': migration_id}
        if [sha(before), sha(mirror_bytes)] != report['inputSha256']:
            raise ValueError('Catálogo/espejo cambió desde la aprobación: generar y revisar nueva propuesta.')
        mirror = json.loads(mirror_bytes)
        expected = {(str(row['sourceCode']), row['row']) for row in mirror}
        if len(expected) != len(mirror) or expected != {(row['code'], row['row']) for row in targets}:
            raise ValueError('Propuesta no corresponde a todas las filas del espejo.')
        now = datetime.now().astimezone().isoformat()
        plan = make_plan(catalog, report, migration_id, now)
        backup_dir.mkdir(parents=True, exist_ok=False)
        # Backup exact input bytes, not reserialized JSON. Kept outside Git.
        for name, data in [('anime.before.json', before), ('anime-hoja.before.json', mirror_bytes), ('approved-preview.json', report_bytes)]:
            with (backup_dir / name).open('xb') as handle:
                handle.write(data)
            if (backup_dir / name).read_bytes() != data:
                raise RuntimeError('Respaldo no verificado; no se aplica.')
        manifest = {'version': VERSION, 'environment': 'desarrollo', 'migrationId': migration_id,
                    'initializedAt': now, 'beforeSha256': sha(before), 'mirrorSha256': sha(mirror_bytes),
                    'count': len(targets), 'status': 'prepared', 'sheetWrites': 0}
        atomic_json(backup_dir / 'manifest.json', manifest)
        commit_collections(directory, {'anime.json': plan})
        saved = catalog_path.read_bytes()
        if json.loads(saved) != plan or mirror_path.read_bytes() != mirror_bytes:
            raise RuntimeError('Fallo en verificación posterior; conservar respaldo y revisar.')
        manifest.update(status='applied', afterSha256=sha(saved))
        atomic_json(backup_dir / 'manifest.json', manifest)
        return {**manifest, 'backupDir': str(backup_dir)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--backup-dir', required=True, type=Path)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[3]
    expected_config = (workspace / 'Desarrollo/catalog-storage.local.json').resolve()
    if args.config.resolve() != expected_config:
        raise SystemExit('Solo se permite el descriptor de desarrollo de este workspace.')
    settings = json.loads(expected_config.read_text(encoding='utf-8'))
    directory = Path(settings['catalogDir']).resolve()
    if (settings.get('environment') != 'desarrollo' or directory != (workspace / 'datos/desarrollo/catalogo').resolve()
            or directory == (workspace / 'datos/produccion/catalogo').resolve()):
        raise SystemExit('Inicialización bloqueada fuera del catálogo central de desarrollo.')
    if not args.backup_dir.resolve().is_relative_to((workspace / 'work/historical-migrations').resolve()):
        raise SystemExit('El respaldo debe residir en work/historical-migrations, fuera de Git.')
    print(json.dumps(apply_report(directory, args.report, args.backup_dir), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
