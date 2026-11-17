"""Exercise real source dispatch with isolated storage and simulated providers."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import anime_sync_pipeline as pipeline


class SourceSelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="altoidss-source-selection-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        catalog = self.root / "catalog"
        catalog.mkdir()
        for name in ("ANIME_PATH", "STATE_PATH", "REPORT_PATH", "CONFLICTS_PATH",
                     "REVIEW_DATA_PATH", "WRITEBACK_QUEUE_PATH", "SHEET_MIRROR_PATH", "PREVIOUS_JSON_PATH"):
            scoped = patch.object(pipeline, name, catalog / (name.lower() + ".json"))
            scoped.start()
            self.addCleanup(scoped.stop)
        pipeline.write_json_atomic(pipeline.ANIME_PATH, [])
        pipeline.write_json_atomic(pipeline.STATE_PATH, {"sourceHash": pipeline.rows_hash([])})
        self.config = self.root / "source.json"
        self.workbook = self.root / "fixture.xlsx"
        self.workbook.touch()
        self.downloaded = self.root / "downloaded.xlsx"
        self.downloaded.touch()
        self.args = SimpleNamespace(config=self.config, workbook=None, url=None,
                                    apply=False, initialize=False, requests_per_minute=1)
        self.settings = {"workbook": "G:/historical-fixture-do-not-open.xlsx",
                         "googleExportUrl": "https://example.invalid/fixture.xlsx",
                         "googleSheets": {"writeBackEnabled": True}}
        # Merely checking the legacy drive is a test failure; no G: file is opened.
        exists = Path.exists
        def guarded_exists(path):
            if str(path).upper().startswith("G:"):
                raise AssertionError("Historical workbook must not be inspected")
            return exists(path)
        guard = patch.object(Path, "exists", guarded_exists)
        guard.start()
        self.addCleanup(guard.stop)
        self.oauth = self.mock("read_live_google_catalog", return_value=[])
        self.download = self.mock("download_workbook", return_value=self.downloaded)
        self.excel = self.mock("read_catalog", return_value=[])
        self.flush = self.mock("flush_sheet_writebacks")

    def mock(self, name, **kwargs):
        scoped = patch.object(pipeline, name, **kwargs)
        value = scoped.start()
        self.addCleanup(scoped.stop)
        return value

    def run_source(self):
        self.config.write_text(json.dumps(self.settings), encoding="utf-8")
        return pipeline.process_once(self.args)

    def test_oauth_precedes_export_and_cli_workbook_without_legacy_access(self):
        self.args.workbook = self.workbook
        self.args.url = "https://example.invalid/override.xlsx"
        self.run_source()
        self.oauth.assert_called_once_with(self.config)
        self.download.assert_not_called()
        self.excel.assert_not_called()
        self.flush.assert_not_called()

    def test_oauth_failure_never_falls_back_to_export_or_workbook(self):
        self.oauth.side_effect = pipeline.OAuthAuthorizationRequired("fixture authorization expired")
        with self.assertRaises(pipeline.OAuthAuthorizationRequired):
            self.run_source()
        self.download.assert_not_called()
        self.excel.assert_not_called()

    def test_export_precedes_legacy_workbook_when_oauth_disabled(self):
        self.settings["googleSheets"]["writeBackEnabled"] = False
        self.run_source()
        self.oauth.assert_not_called()
        self.download.assert_called_once_with(self.settings["googleExportUrl"])
        self.excel.assert_called_once_with(self.downloaded)
        self.assertFalse(self.downloaded.exists())

    def test_export_failure_does_not_fall_back_to_local_file(self):
        self.settings["googleSheets"]["writeBackEnabled"] = False
        self.settings["workbook"] = str(self.workbook)
        self.download.side_effect = RuntimeError("fixture connection failed")
        with self.assertRaisesRegex(RuntimeError, "fixture connection failed"):
            self.run_source()
        self.excel.assert_not_called()

    def test_explicit_local_source_is_used_without_google(self):
        self.settings = {"workbook": str(self.workbook)}
        self.run_source()
        self.excel.assert_called_once_with(self.workbook)
        self.oauth.assert_not_called()
        self.download.assert_not_called()

    def test_no_source_fails_with_clear_error_and_no_provider_call(self):
        self.settings = {}
        with self.assertRaisesRegex(RuntimeError, "No se configuró un archivo Excel"):
            self.run_source()
        self.oauth.assert_not_called()
        self.download.assert_not_called()
        self.excel.assert_not_called()

    def test_cli_export_overrides_configured_export(self):
        self.settings["googleSheets"]["writeBackEnabled"] = False
        self.args.url = "https://example.invalid/override.xlsx"
        self.run_source()
        self.download.assert_called_once_with(self.args.url)
        self.excel.assert_called_once_with(self.downloaded)

    def test_cli_workbook_overrides_configured_file_when_no_google_source(self):
        self.settings = {"workbook": str(self.root / "absent.xlsx")}
        self.args.workbook = self.workbook
        self.run_source()
        self.excel.assert_called_once_with(self.workbook)
        self.download.assert_not_called()

    def test_removing_workbook_preserves_oauth_source(self):
        del self.settings["workbook"]
        self.run_source()
        self.oauth.assert_called_once_with(self.config)
        self.download.assert_not_called()
        self.excel.assert_not_called()

    def test_export_still_works_after_removing_workbook(self):
        del self.settings["workbook"]
        self.settings["googleSheets"]["writeBackEnabled"] = False
        self.run_source()
        self.download.assert_called_once_with(self.settings["googleExportUrl"])
        self.excel.assert_called_once_with(self.downloaded)


if __name__ == "__main__":
    unittest.main()
