"""Opt-in TEST Sheet roundtrip, real PHP approvals, real Google readback and restore.

Never run against production. Uses disposable JSON, not the development catalog.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import anime_sync_pipeline as sync
import google_sheets_writeback as sheets
from storage_transaction import atomic_json
from sync_anime_workbook import make_new_record, raw_row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--test-spreadsheet-id', required=True)
    parser.add_argument('--code', required=True)
    parser.add_argument('--php', default='php')
    args = parser.parse_args()
    settings = sheets.load_config(args.config)
    actual_id = sheets.spreadsheet_id(settings, args.config)
    production_config = ROOT.parents[1] / 'ProyectoFinal' / 'Aplication' / 'config' / 'anime-sync.json'
    production = json.loads(production_config.read_text(encoding='utf-8')) if production_config.exists() else {}
    production_id = (production.get('googleSheets') or {}).get('spreadsheetId')
    if actual_id != args.test_spreadsheet_id or actual_id == production_id or args.config.resolve() == production_config.resolve():
        raise SystemExit('Se rechazó el destino: debe ser la configuración y hoja de PRUEBAS.')
    sheet = settings.get('sheetName') or 'Catalogo'
    rows = sheets.read_rows(args.config, f'{sheet}!A2:J', value_render_option='UNFORMATTED_VALUE')
    matches = [(i+2, r) for i, r in enumerate(rows) if r and str(r[0]) == args.code]
    if len(matches) != 1:
        raise SystemExit('El código de prueba debe existir exactamente una vez.')
    row_number, original = matches[0]
    original = (original + [''] * 10)[:10]
    if any(isinstance(v,str) and v.startswith('=') for v in original):
        raise SystemExit('Elegir una fila sin fórmulas para la prueba.')
    fixture = ROOT / 'outputs' / 'qa-writeback' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    data = fixture / 'data'
    data.mkdir(parents=True)
    atomic_json(fixture / '.qa-fixture', {'isolated':True})
    atomic_json(fixture / 'restore-original.json', {'sourceCode':args.code,'targetRow':row_number,'values':original})
    record = make_new_record(raw_row(row_number, tuple(original)), datetime.now().astimezone().isoformat())
    atomic_json(data / 'anime.json', [record])
    for name in ('anime-revisiones.json','anime-sheet-writeback.json'):
        atomic_json(data / name, [])
    report = {'timestamp':datetime.now().astimezone().isoformat(),'isolatedCatalog':True,
              'testSheetOnly':True,'sourceCode':args.code,'checks':[],'restored':False}
    names = {'WRITEBACK_QUEUE_PATH':data/'anime-sheet-writeback.json',
             'REVIEW_DATA_PATH':data/'anime-revisiones.json','STATE_PATH':fixture/'state.json'}
    expected = original[:]
    attempted = False
    def php(action, chapters=0):
        env = dict(os.environ)
        env.pop('ALTOIDSS_STORAGE_CONFIG', None)
        subprocess.run([args.php,str(ROOT/'tests/sheets-roundtrip-fixture.php'),str(fixture),action,str(chapters)],
                       env=env,check=True,capture_output=True,text=True,timeout=30)
    def read_target():
        result = sheets.read_rows(args.config,f'{sheet}!A{row_number}:J{row_number}',value_render_option='UNFORMATTED_VALUE')
        return ((result[0] if result else [])+['']*10)[:10]
    try:
        with patch.multiple(sync, **names):
            for action, delta in [('edit',1),('review',2)]:
                chapters = int(original[4] or 0) + delta
                php(action, chapters)
                queue = sync.load_json(sync.WRITEBACK_QUEUE_PATH, [])
                assert len(queue)==1 and queue[0]['values'][4]==chapters
                expected = queue[0]['values']
                attempted = True
                assert sync.flush_sheet_writebacks(args.config)==1
                assert [str(v).strip() for v in read_target()]==[str(v).strip() for v in expected]
                assert sync.load_json(sync.WRITEBACK_QUEUE_PATH, [])==[]
                if action=='review':
                    assert sync.load_json(sync.REVIEW_DATA_PATH,[])[0]['sheetSyncStatus']=='Confirmado'
                report['checks'].append({'name':action+' PHP -> JSON + queue -> Google readback','passed':True})
            php('local')
            assert len(sheets.read_rows(args.config,f'{sheet}!A2:J'))==len(rows)
            report['checks'].append({'name':'Page creation does not append Sheet rows','passed':True})
    finally:
        if attempted:
            current = read_target()
            if [str(v).strip() for v in current] not in [[str(v).strip() for v in original], [str(v).strip() for v in expected]]:
                atomic_json(fixture/'report.json', report)
                raise RuntimeError('La fila cambió externamente; no se sobrescribió. Revisar restore-original.json.')
            sheets.update_rows(args.config,[{'sourceCode':args.code,'targetRow':row_number,'values':original}])
            restored = read_target()
            assert restored == original, 'La restauración debe conservar valores y tipos numéricos.'
            report['restored'] = True
        atomic_json(fixture/'report.json', report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
