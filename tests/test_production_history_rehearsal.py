import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import rehearse_production_history as rehearsal
from initialize_historical_order import apply_report, make_plan
from prepare_code_release import digest, protected_hashes


class ProductionHistoryRehearsalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='altoidss-prod-history-')
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.production = self.workspace / 'ProyectoFinal' / 'Aplication'
        (self.production / 'data').mkdir(parents=True)
        self.central = self.workspace / 'datos' / 'produccion' / 'catalogo'
        self.central.mkdir(parents=True)
        state = self.central.parent / 'anime-sync'
        state.mkdir()
        (self.production.parent / 'catalog-storage.local.json').write_text(json.dumps({
            'environment': 'produccion', 'catalogDir': str(self.central), 'syncStateDir': str(state)}))
        self.catalog = [{'id': 'sheet', 'sourceCode': '01', 'sourceRow': 2, 'title': 'Original',
                         'createdAt': '2026-10-04T08:00:00-06:00', 'activeSeason': 'S02', 'emissionYear': 1998},
                        {'id': 'local', 'importedAt': '2026-08-23T10:00:00-06:00'}]
        self.mirror = [{'sourceCode': '01', 'row': 2}]
        for name in rehearsal.COLLECTIONS:
            value = self.catalog if name == 'anime.json' else self.mirror if name == 'anime-hoja.json' else []
            (self.central / name).write_text(json.dumps(value), encoding='utf-8')
        self.report = {'strategy': 'rebase-all-linked-sheet-row-order', 'sheetOrderMatches': True,
                       'missingCodes': [], 'mirrorRows': 1, 'cutoff': '2026-10-09T00:58:35-06:00',
                       'rows': [{'id': 'sheet', 'code': '01', 'row': 2,
                                 'proposedAt': '2025-10-01T00:00:00-06:00',
                                 'basis': 'historical-quarter-estimate'}],
                       'inputSha256': [digest((self.central / name).read_bytes()) for name in rehearsal.COLLECTIONS[:2]]}
        self.report_path = self.workspace / 'work' / 'historical-production-previews' / 'fixture' / 'preview.json'
        self.report_path.parent.mkdir(parents=True)
        self.report_path.write_text(json.dumps(self.report), encoding='utf-8')

    def test_rehearsal_only_applies_inside_new_copy_and_is_idempotent(self):
        before = protected_hashes(self.workspace, self.production)
        node = SimpleNamespace(stdout=b'{"allLinkedRowsBothDirections":true,"firstCodes":["01"]}')
        with patch.object(rehearsal.subprocess, 'run', return_value=node):
            output, result = rehearsal.rehearse(self.workspace, self.report_path)
        self.assertEqual(result['linkedInitialized'], 1)
        self.assertEqual(result['localRecordsUnchanged'], 1)
        self.assertTrue(result['idempotent'])
        self.assertTrue(result['originalBackupExact'])
        self.assertFalse(result['productionMigrationApplied'])
        self.assertEqual(protected_hashes(self.workspace, self.production), before)
        self.assertEqual(json.loads((output / 'backup' / 'manifest.json').read_text())['environment'], 'isolated-rehearsal')
        self.assertEqual(json.loads((self.central / 'anime.json').read_text()), self.catalog)

    def test_stale_preview_rejected_before_copy(self):
        (self.central / 'anime.json').write_text('[]')
        with self.assertRaisesRegex(ValueError, 'obsoleta'):
            rehearsal.rehearse(self.workspace, self.report_path)
        self.assertFalse(list(self.report_path.parent.glob('rehearsal-*')))

    def test_live_directory_cannot_be_used_as_report_location(self):
        with self.assertRaisesRegex(ValueError, 'zona privada'):
            rehearsal.rehearse(self.workspace, self.central / 'preview.json')

    def test_pending_transaction_rejected_without_recovery_on_live_data(self):
        journal = self.central / '.transaction.json'
        journal.write_text('{"version":1,"files":{}}')
        with self.assertRaisesRegex(ValueError, 'transacción pendiente'):
            rehearsal.rehearse(self.workspace, self.report_path)
        self.assertTrue(journal.exists())

    def test_verification_rejects_metadata_local_or_row_changes(self):
        planned = make_plan(self.catalog, self.report, 'fixture', '2026-10-19T09:00:00-06:00')
        rehearsal.verify_changes(self.catalog, planned, self.report)
        for index, key, value in [(0, 'title', 'Unexpected'), (0, 'sourceRow', 99),
                                  (0, 'createdAt', '2020-01-01'), (1, 'importedAt', '2020-01-01')]:
            broken = copy.deepcopy(planned)
            broken[index][key] = value
            with self.assertRaises(ValueError):
                rehearsal.verify_changes(self.catalog, broken, self.report)

    def test_engine_does_not_enable_production_environment(self):
        before = (self.central / 'anime.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'producción'):
            apply_report(self.central, self.report_path, self.workspace / 'forbidden-backup', environment='produccion')
        self.assertEqual((self.central / 'anime.json').read_bytes(), before)
        self.assertFalse((self.workspace / 'forbidden-backup').exists())


if __name__ == '__main__':
    unittest.main()
