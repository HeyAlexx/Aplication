import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from initialize_historical_order import apply_report, make_plan


class HistoricalInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='altoidss-history-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'catalog'
        self.directory.mkdir()
        self.catalog = [{'id': 'sheet', 'sourceCode': '01', 'sourceRow': 2,
                         'createdAt': '2026-10-04T08:00:00-06:00', 'title': 'Original',
                         'emissionYear': 1998, 'activeSeason': 'S02'},
                        {'id': 'app', 'importedAt': '2026-08-23T10:00:00-06:00'}]
        self.mirror = [{'sourceCode': '01', 'row': 2}]
        for name, records in [('anime.json', self.catalog), ('anime-hoja.json', self.mirror),
                              ('anime-sheet-writeback.json', [{'version': 'keep'}])]:
            (self.directory / name).write_text(json.dumps(records), encoding='utf-8')
        self.report = {'strategy': 'rebase-all-linked-sheet-row-order', 'sheetOrderMatches': True,
                       'missingCodes': [], 'mirrorRows': 1, 'rows': [
                           {'id': 'sheet', 'code': '01', 'row': 2, 'proposedAt': '2026-10-01T00:00:00-06:00',
                            'basis': 'historical-quarter-estimate', 'quarterAnchor': '1998-04-01T00:00:00-06:00'}],
                       'inputSha256': [hashlib.sha256((self.directory / name).read_bytes()).hexdigest()
                                       for name in ['anime.json', 'anime-hoja.json']]}
        self.report_path = self.root / 'report.json'
        self.report_path.write_text(json.dumps(self.report), encoding='utf-8')
        self.backup = self.root / 'backup'

    def test_apply_preserves_local_dates_rows_metadata_and_queue(self):
        before = (self.directory / 'anime.json').read_bytes()
        mirror = (self.directory / 'anime-hoja.json').read_bytes()
        queue = (self.directory / 'anime-sheet-writeback.json').read_bytes()
        result = apply_report(self.directory, self.report_path, self.backup)
        self.assertEqual(result['status'], 'applied')
        saved = json.loads((self.directory / 'anime.json').read_bytes())
        self.assertEqual(saved[1], self.catalog[1])
        for key, value in self.catalog[0].items():
            self.assertEqual(saved[0][key], value)
        self.assertEqual(saved[0]['historicalOrderInitialization']['originalDates']['createdAt'], self.catalog[0]['createdAt'])
        self.assertEqual(saved[0]['sheetImportRow'], 2)
        self.assertEqual((self.backup / 'anime.before.json').read_bytes(), before)
        self.assertEqual((self.directory / 'anime-hoja.json').read_bytes(), mirror)
        self.assertEqual((self.directory / 'anime-sheet-writeback.json').read_bytes(), queue)

    def test_rerun_is_idempotent_and_never_resets_dates(self):
        apply_report(self.directory, self.report_path, self.backup)
        before = (self.directory / 'anime.json').read_bytes()
        result = apply_report(self.directory, self.report_path, self.backup)
        self.assertEqual(result['status'], 'already-initialized')
        self.assertEqual((self.directory / 'anime.json').read_bytes(), before)

    def test_stale_approval_is_rejected_before_backup_or_write(self):
        (self.directory / 'anime.json').write_text(json.dumps(self.catalog + [{'id': 'new-app'}]), encoding='utf-8')
        before = (self.directory / 'anime.json').read_bytes()
        with self.assertRaises(ValueError):
            apply_report(self.directory, self.report_path, self.backup)
        self.assertEqual((self.directory / 'anime.json').read_bytes(), before)
        self.assertFalse(self.backup.exists())

    def test_plan_does_not_mutate_input_and_rejects_changed_rows(self):
        before = json.dumps(self.catalog)
        make_plan(self.catalog, self.report, 'fixture', '2026-10-09T03:00:00-06:00')
        self.assertEqual(json.dumps(self.catalog), before)
        self.catalog[0]['sourceRow'] = 3
        with self.assertRaises(ValueError):
            make_plan(self.catalog, self.report, 'fixture', '2026-10-09T03:00:00-06:00')
