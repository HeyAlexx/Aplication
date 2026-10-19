import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import anime_sync_pipeline as sync
from sync_anime_workbook import raw_row, make_new_record


class CompletenessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='altoidss-completeness-')
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for name in ('ANIME_PATH', 'STATE_PATH', 'REPORT_PATH', 'CONFLICTS_PATH',
                     'REVIEW_DATA_PATH', 'WRITEBACK_QUEUE_PATH', 'PREVIOUS_JSON_PATH',
                     'SHEET_MIRROR_PATH'):
            setter = patch.object(sync, name, root / (name.lower().replace('_', '-') + '.json'))
            setter.start()
            self.addCleanup(setter.stop)
        setter = patch.object(sync, 'STATE_DIR', root)
        setter.start()
        self.addCleanup(setter.stop)
        self.config = root / 'config.json'
        sync.write_json_atomic(self.config, {'googleSheets': {'writeBackEnabled': True}})
        self.row = raw_row(2, ('9001', 'Title', 'Emision', 'Serie', 0, 1, 'S01', 'Por Ver', 2026, 4))
        sync.write_json_atomic(sync.ANIME_PATH, [])
        sync.write_json_atomic(sync.STATE_PATH, {'sourceHash': sync.rows_hash([self.row]),
                                                'rows': [sync.row_payload(self.row)]})
        self.args = SimpleNamespace(config=self.config, workbook=None, url=None,
                                    apply=True, initialize=False, requests_per_minute=30)

    def run_sync(self, candidate=None, score=0):
        with patch.object(sync, 'read_live_google_catalog', return_value=[self.row]), \
             patch.object(sync, 'flush_sheet_writebacks', return_value=0), \
             patch.object(sync, 'best_candidate', return_value=(candidate, score, [])):
            return sync.process_once(self.args)

    def test_same_hash_missing_record_is_recovered_even_if_api_unavailable(self):
        report = self.run_sync()
        self.assertEqual(report['status'], 'applied')
        record = sync.load_json(sync.ANIME_PATH, [])[0]
        self.assertEqual(record['sourceCode'], '9001')
        self.assertFalse(record['metadataVerified'])
        self.assertTrue(record['metadataNeedsReview'])
        self.assertEqual(record['sheetValues'], self.row['raw'])
        self.assertEqual(report['pendingReviewCount'], 1)

    def test_no_duplicate_on_second_run(self):
        self.run_sync()
        self.assertEqual(self.run_sync()['status'], 'unchanged')
        self.assertEqual(len(sync.load_json(sync.ANIME_PATH, [])), 1)

    def test_deleted_record_is_detected_again(self):
        self.run_sync()
        sync.write_json_atomic(sync.ANIME_PATH, [])
        self.assertEqual(self.run_sync()['status'], 'applied')

    def test_unchanged_source_still_saves_complete_mirror(self):
        sync.write_json_atomic(sync.ANIME_PATH, [make_new_record(self.row, '2026-10-09T00:00:00-06:00')])
        self.assertEqual(self.run_sync()['status'], 'unchanged')
        self.assertEqual(sync.load_json(sync.SHEET_MIRROR_PATH, []), [self.row])

    def test_preview_does_not_modify_catalog_mirror_or_state(self):
        self.args.apply = False
        before = sync.STATE_PATH.read_bytes()
        self.run_sync()
        self.assertEqual(sync.load_json(sync.ANIME_PATH, []), [])
        self.assertFalse(sync.SHEET_MIRROR_PATH.exists())
        self.assertEqual(sync.STATE_PATH.read_bytes(), before)

    def test_invalid_source_stays_in_mirror_and_pending_record(self):
        self.row['format'] = 'INVALID'
        report = self.run_sync()
        self.assertEqual(report['pendingReviewCount'], 1)
        self.assertEqual(sync.load_json(sync.SHEET_MIRROR_PATH, [])[0]['format'], 'INVALID')
        self.assertEqual(len(sync.load_json(sync.ANIME_PATH, [])), 1)

    def test_external_candidate_verifies_without_duplicate(self):
        candidate = {'title': 'Title', 'format': 'Serie', 'emissionYear': 2026,
                     'source': 'anilist', 'id': '123', 'chapters': 12}
        self.run_sync(candidate, 1)
        records = sync.load_json(sync.ANIME_PATH, [])
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]['metadataVerified'])

    def test_changed_source_mirror_keeps_literal_values(self):
        self.row['title'] = '=Not a formula'
        self.run_sync()
        self.assertEqual(sync.load_json(sync.SHEET_MIRROR_PATH, [])[0]['title'], '=Not a formula')


if __name__ == '__main__':
    unittest.main()
