"""Read production; rehearse its historical migration ONLY in a new private copy.

No live apply flag, network, Sheets, service control or development-to-production copy.
The existing initializer's production CLI prohibition remains unchanged.
"""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from incorporation import FIELDS
from initialize_historical_order import AUDIT_FIELD, apply_report, targets_for
from prepare_code_release import ROOT, digest, protected_hashes, save_new

COLLECTIONS = ('anime.json', 'anime-hoja.json', 'peliculas.json', 'series.json',
               'noticias.json', 'temporadas.json', 'episodios.json',
               'anime-revisiones.json', 'anime-sheet-writeback.json')


def verify_changes(before, after, report):
    if [item['id'] for item in before] != [item['id'] for item in after]:
        raise ValueError('Se alteraron IDs, cantidad u orden físico del JSON.')
    targets = {row['id']: row for row in targets_for(report)}
    allowed = {*FIELDS, AUDIT_FIELD}
    local_count = 0
    for original, changed in zip(before, after):
        row = targets.get(original['id'])
        if row is None:
            if original != changed:
                raise ValueError('Se modificó un registro local.')
            local_count += 1
            continue
        if ({key: value for key, value in original.items() if key not in allowed}
                != {key: value for key, value in changed.items() if key not in allowed}):
            raise ValueError('Se modificaron metadatos, filas o fechas originales.')
        if (str(changed.get('sourceCode')) != row['code'] or changed.get('sourceRow') != row['row']
                or changed.get('sheetImportRow') != row['row']
                or changed.get('incorporatedAt') != row['proposedAt']
                or changed.get('incorporationDateBasis') != row['basis']):
            raise ValueError('La incorporación no corresponde a la propuesta.')
        audit = changed.get(AUDIT_FIELD, {})
        expected = {key: original[key] for key in (*FIELDS, 'createdAt', 'importedAt') if key in original}
        if audit.get('originalDates') != expected or audit.get('sheetRow') != row['row']:
            raise ValueError('Falta la auditoría exacta de fechas/fila originales.')
    return {'linkedInitialized': len(targets), 'localRecordsUnchanged': local_count,
            'metadataRowsIdsAndOriginalDatesUnchanged': True}


NODE_CHECK = r"""
const fs = require('node:fs'), assert = require('node:assert/strict');
const {sort} = require(process.argv[1]);
const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const mirror = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const codes = new Set(mirror.map(r => String(r.sourceCode)));
for (const direction of ['newest','oldest']) {
 const expected = [...mirror].sort((a,b) => direction === 'newest' ? b.row-a.row : a.row-b.row)
   .map(r => String(r.sourceCode));
 const actual = sort(data, direction).filter(r => codes.has(String(r.sourceCode))).map(r => String(r.sourceCode));
 assert.deepEqual(actual, expected);
}
process.stdout.write(JSON.stringify({allLinkedRowsBothDirections:true,
 firstCodes:sort(data).filter(r=>codes.has(String(r.sourceCode))).slice(0,5).map(r=>String(r.sourceCode))}));
"""


def rehearse(workspace, report_path, node='node'):
    workspace, report_path = workspace.resolve(), report_path.resolve()
    expected = workspace / 'work' / 'historical-production-previews'
    if not report_path.is_relative_to(expected) or expected.resolve() != expected.absolute():
        raise ValueError('El informe debe estar en la zona privada de vistas previas de producción.')
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    targets_for(report)
    production = workspace / 'ProyectoFinal' / 'Aplication'
    fingerprints = protected_hashes(workspace, production)
    settings = json.loads((production.parent / 'catalog-storage.local.json').read_text(encoding='utf-8-sig'))
    central = Path(settings['catalogDir']).resolve()
    if (central / '.transaction.json').exists():
        raise ValueError('Producción tiene una transacción pendiente; no copiar un estado parcial.')
    inputs = [(central / name).read_bytes() for name in COLLECTIONS[:2]]
    if [digest(data) for data in inputs] != report['inputSha256']:
        raise ValueError('Vista previa obsoleta: catálogo o espejo cambió; no se ensaya.')
    output = report_path.parent / ('rehearsal-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    if output.resolve() != output.absolute():
        raise ValueError('La salida de ensayo no puede contener enlaces o junctions.')
    output.mkdir(parents=True, exist_ok=False)
    directory = output / 'catalog'
    for name in COLLECTIONS:
        source = central / name
        data = source.read_bytes() if source.is_file() else b'[]\n'
        if (digest(data) if source.is_file() else None) != fingerprints.get(str(source)):
            raise RuntimeError('Una colección cambió durante la copia.')
        save_new(directory / name, data)
    if protected_hashes(workspace, production) != fingerprints:
        raise RuntimeError('Producción cambió durante la copia; repetir vista previa.')
    before_bytes = (directory / 'anime.json').read_bytes()
    other_hashes = {name: digest((directory / name).read_bytes()) for name in COLLECTIONS if name != 'anime.json'}
    first = apply_report(directory, report_path, output / 'backup', environment='isolated-rehearsal')
    after_bytes = (directory / 'anime.json').read_bytes()
    checks = verify_changes(json.loads(before_bytes), json.loads(after_bytes), report)
    second = apply_report(directory, report_path, output / 'backup', environment='isolated-rehearsal')
    if second['status'] != 'already-initialized' or (directory / 'anime.json').read_bytes() != after_bytes:
        raise RuntimeError('La reejecución no fue idempotente.')
    if any(digest((directory / name).read_bytes()) != value for name, value in other_hashes.items()):
        raise RuntimeError('El ensayo alteró una colección ajena a incorporación.')
    order = subprocess.run([str(node), '-e', NODE_CHECK, str(ROOT / 'js' / 'content-order.js'),
                            str(directory / 'anime.json'), str(directory / 'anime-hoja.json')],
                           capture_output=True, check=True)
    checks.update(json.loads(order.stdout))
    if protected_hashes(workspace, production) != fingerprints or report_path.read_bytes() != report_bytes:
        raise RuntimeError('Producción o la propuesta cambió durante el ensayo; revisar.')
    checks.update(mode='production-source-isolated-rehearsal', passed=True,
                  previewSha256=digest(report_bytes), beforeSha256=digest(before_bytes),
                  afterSha256=digest(after_bytes), cutoff=report['cutoff'],
                  originalBackupExact=(output / 'backup' / 'anime.before.json').read_bytes() == before_bytes,
                  idempotent=True, otherCollectionsUnchanged=len(other_hashes),
                  protectedProductionFilesUnchanged=len(fingerprints), protectedHashes=fingerprints,
                  sourceEnvironment='produccion', executionEnvironment='isolated-rehearsal',
                  productionMigrationApplied=False, sheetWrites=0, productionCliStillBlocked=True,
                  reviewedPreviewRequired=True, firstRunStatus=first['status'])
    save_new(output / 'report.json', (json.dumps(checks, ensure_ascii=False, indent=2) + '\n').encode())
    return output, checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=ROOT.parents[1])
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--node', default='node')
    args = parser.parse_args()
    output, checks = rehearse(args.workspace, args.report, args.node)
    print(json.dumps({'output': str(output), **{key: value for key, value in checks.items()
                                              if key != 'protectedHashes'}}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
