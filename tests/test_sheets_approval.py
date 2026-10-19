import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import anime_sync_pipeline as pipeline
import google_sheets_writeback as sheets


class ApprovalWritebackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="altoidss-sync-test-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for name in ("WRITEBACK_QUEUE_PATH", "REVIEW_DATA_PATH", "STATE_PATH", "REPORT_PATH", "CONFLICTS_PATH"):
            setter = patch.object(pipeline, name, root / (name.lower().replace('_', '-') + '.json'))
            setter.start()
            self.addCleanup(setter.stop)
        self.config = root / "config.json"
        self.config.write_text(json.dumps({"googleSheets": {"writeBackEnabled": True}}), encoding="utf-8")
        self.values = ["9001", "=Título literal", "Finalizado", "Serie", 12, 1, "S01", "Por Ver", 2026, 3]
        self.entry = {"sourceCode": "9001", "targetRow": 99, "values": self.values, "version": "first"}
        pipeline.write_json_atomic(pipeline.WRITEBACK_QUEUE_PATH, [self.entry])
        pipeline.write_json_atomic(pipeline.REVIEW_DATA_PATH, [{"id": "r", "sourceCode": "9001", "status": "Aprobado"}])

    def test_failure_retains_queue_and_approved_catalog_state(self):
        with patch.object(pipeline, "update_rows", side_effect=RuntimeError("red no disponible")):
            with self.assertRaises(RuntimeError):
                pipeline.flush_sheet_writebacks(self.config)
        self.assertEqual(pipeline.load_json(pipeline.WRITEBACK_QUEUE_PATH, []), [self.entry])
        self.assertEqual(pipeline.load_json(pipeline.REVIEW_DATA_PATH, [])[0]["status"], "Aprobado")

    def test_success_confirms_review_and_retry_is_idempotent(self):
        with patch.object(pipeline, "update_rows", return_value=1) as send:
            self.assertEqual(pipeline.flush_sheet_writebacks(self.config), 1)
            self.assertEqual(pipeline.flush_sheet_writebacks(self.config), 0)
            send.assert_called_once()
        self.assertEqual(pipeline.load_json(pipeline.REVIEW_DATA_PATH, [])[0]["sheetSyncStatus"], "Confirmado")

    def test_newer_approval_is_not_removed_by_old_response(self):
        newer = {**self.entry, "version": "second", "values": ["9001", "Otra versión", *self.values[2:]]}
        def send(*unused):
            pipeline.write_json_atomic(pipeline.WRITEBACK_QUEUE_PATH, [newer])
            return 1
        with patch.object(pipeline, "update_rows", side_effect=send):
            pipeline.flush_sheet_writebacks(self.config)
        self.assertEqual(pipeline.load_json(pipeline.WRITEBACK_QUEUE_PATH, []), [newer])
        self.assertNotIn("sheetSyncStatus", pipeline.load_json(pipeline.REVIEW_DATA_PATH, [])[0])

    def test_preview_never_flushes_queue(self):
        pipeline.write_json_atomic(pipeline.STATE_PATH, {"sourceHash": pipeline.rows_hash([])})
        args = SimpleNamespace(config=self.config, apply=False, initialize=False)
        with patch.object(pipeline, "config_source", return_value=(None, "")), patch.object(pipeline, "read_live_google_catalog", return_value=[]), patch.object(pipeline, "flush_sheet_writebacks") as flush:
            pipeline.process_once(args)
            flush.assert_not_called()

    def test_approval_history_survives_unchanged_source(self):
        previous = {"id": "r", "status": "Aprobado", "original": {"title": "Original"}, "sheetSyncStatus": "Confirmado"}
        pipeline.write_json_atomic(pipeline.REVIEW_DATA_PATH, [previous])
        self.assertEqual(pipeline.merge_reviews([{**previous, "status": "Pendiente"}])[0]["status"], "Aprobado")
        self.assertEqual(pipeline.merge_reviews([{**previous, "original": {"title": "Nuevo"}, "status": "Pendiente"}])[0]["status"], "Pendiente")

    def test_writeback_resolves_moved_row_and_verifies_literal_values(self):
        with patch.object(sheets, "load_config", return_value={"sheetName": "Catalogo", "spreadsheetId": "test"}), patch.object(sheets, "access_token", return_value="test-only"), patch.object(sheets, "read_rows", side_effect=[[["other"], ["9001"]], [["other"], self.values]]), patch.object(sheets, "request_json", return_value={"totalUpdatedRows": 1}) as request:
            self.assertEqual(sheets.update_rows(self.config, [self.entry]), 1)
            body = request.call_args.kwargs["body"]
            self.assertEqual(body["data"][0]["range"], "Catalogo!A3:J3")
            self.assertEqual(body["valueInputOption"], "RAW")

    def test_missing_or_duplicate_code_does_not_write(self):
        for rows in ([], [["9001"], ["9001"]]):
            with self.subTest(rows=rows), patch.object(sheets, "load_config", return_value={}), patch.object(sheets, "access_token", return_value="test-only"), patch.object(sheets, "read_rows", return_value=rows), patch.object(sheets, "request_json") as request:
                with self.assertRaises(RuntimeError):
                    sheets.update_rows(self.config, [self.entry])
                request.assert_not_called()

    def test_confirmation_mismatch_does_not_clear_queue(self):
        with patch.object(sheets, "load_config", return_value={"spreadsheetId": "test"}), patch.object(sheets, "access_token", return_value="test-only"), patch.object(sheets, "read_rows", side_effect=[[["9001"]], [["9001", "otra cosa"]]]), patch.object(sheets, "request_json", return_value={"totalUpdatedRows": 1}):
            with self.assertRaises(RuntimeError):
                sheets.update_rows(self.config, [self.entry])


if __name__ == "__main__":
    unittest.main()
