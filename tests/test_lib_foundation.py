from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib import environment
from lib.guardrails import append_forbidden_true_fields, append_missing_fields, status_from_blockers
from lib.io import load_json, load_jsonl, relative_to_root, write_json, write_jsonl
from lib.provenance import file_sha256, git_commit, provenance_metadata
from lib.report import render_markdown_report, write_report_pair
from lib.search_log import write_search_log
from lib.timestamps import is_available_by, require_available_by, session_date, timestamp_utc_iso


class EnvironmentTests(unittest.TestCase):
    def test_environment_overrides_machine_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            configured = root / "configured"
            overridden = root / "overridden"
            config = root / "machine.json"
            config.write_text(
                json.dumps({"environment_variables": {"LILY_DATA_ROOT": str(configured)}}),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"LILY_DATA_ROOT": str(overridden)}, clear=False):
                self.assertEqual(overridden.resolve(), environment.configured_path("LILY_DATA_ROOT", config_path=config))

    def test_missing_path_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_config = Path(tmp) / "missing.json"
            with patch.dict(os.environ, {}, clear=True):
                self.assertIsNone(environment.configured_path("LILY_WIKI_ROOT", config_path=missing_config))
                with self.assertRaisesRegex(ValueError, "LILY_WIKI_ROOT"):
                    environment.require_configured_path("LILY_WIKI_ROOT", config_path=missing_config)

    def test_configured_marker_resolves_under_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"LILY_WIKI_ROOT": str(root)}, clear=False):
                resolved = environment.resolve_configured_path("${LILY_WIKI_ROOT}/concepts/example.md")
        self.assertEqual(root.resolve() / "concepts" / "example.md", resolved)

    def test_interpreter_metadata_does_not_expose_absolute_executable(self) -> None:
        metadata = environment.interpreter_metadata()
        self.assertEqual({"python_executable", "python_implementation", "python_version", "platform"}, set(metadata))
        self.assertEqual(Path(metadata["python_executable"]).name, metadata["python_executable"])
        self.assertFalse(Path(metadata["python_executable"]).is_absolute())


class IoTests(unittest.TestCase):
    def test_json_and_jsonl_round_trip_with_lf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_path = root / "nested" / "payload.json"
            jsonl_path = root / "rows.jsonl"
            write_json(json_path, {"thai": "ลิลลี่", "b": 2, "a": 1})
            count = write_jsonl(jsonl_path, [{"z": 2, "a": 1}, {"row": 2}])
            self.assertEqual({"a": 1, "b": 2, "thai": "ลิลลี่"}, load_json(json_path))
            self.assertEqual([{"a": 1, "z": 2}, {"row": 2}], load_jsonl(jsonl_path))
            self.assertEqual(2, count)
            self.assertNotIn(b"\r\n", json_path.read_bytes())

    def test_invalid_jsonl_names_line_without_echoing_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text('{}\n{"broken"\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 2"):
                load_jsonl(path)

    def test_relative_path_does_not_leak_external_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            self.assertEqual("inside.json", relative_to_root(root / "inside.json", root))
            self.assertEqual("<external>/outside.json", relative_to_root(root.parent / "outside.json", root))


class TimestampTests(unittest.TestCase):
    def test_utc_and_session_date_are_explicit(self) -> None:
        value = "2026-07-15T00:30:00+07:00"
        self.assertEqual("2026-07-14T17:30:00Z", timestamp_utc_iso(value))
        self.assertEqual("2026-07-14", session_date(value, "America/New_York").isoformat())

    def test_naive_and_post_decision_timestamps_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone"):
            timestamp_utc_iso("2026-07-15T00:30:00")
        self.assertTrue(is_available_by("2026-07-14T09:00:00Z", "2026-07-14T09:01:00Z"))
        with self.assertRaisesRegex(ValueError, "input bar"):
            require_available_by(
                "2026-07-14T09:02:00Z",
                "2026-07-14T09:01:00Z",
                label="input bar",
            )


class ProvenanceAndReportTests(unittest.TestCase):
    def test_hash_and_no_git_fallback_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "source.txt"
            path.write_bytes(b"abc")
            self.assertEqual(hashlib.sha256(b"abc").hexdigest(), file_sha256(path))
            self.assertEqual("unavailable", git_commit(root))
            self.assertEqual("unavailable", provenance_metadata(root)["git_commit"])

    def test_report_pair_and_search_log_use_shared_writers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            markdown = render_markdown_report("Control report", [("Result", "- Status: `pass`")])
            stored = write_report_pair(
                {"status": "pass"},
                root / "report.json",
                root / "report.md",
                markdown,
                project_root=root,
            )
            count = write_search_log(root / "search.jsonl", [{"trial_id": "t1", "value": 1}])
            self.assertIn("provenance", stored)
            self.assertEqual("# Control report\n\n## Result\n\n- Status: `pass`\n", (root / "report.md").read_text(encoding="utf-8"))
            self.assertEqual([{"trial_id": "t1", "value": 1}], load_jsonl(root / "search.jsonl"))
            self.assertEqual(1, count)


class GuardrailTests(unittest.TestCase):
    def test_collects_blockers_without_mutating_record(self) -> None:
        record = {"network_used": True, "hypothesis_id": "L-0"}
        blockers: list[str] = []
        append_missing_fields(record, ["hypothesis_id", "evidence_tier"], blockers)
        append_forbidden_true_fields(record, ["network_used", "paid_data_used"], blockers)
        self.assertEqual(
            ["missing_required_field:evidence_tier", "forbidden_guardrail_true:network_used"],
            blockers,
        )
        self.assertEqual("blocked", status_from_blockers(blockers))
        self.assertEqual("pass", status_from_blockers([]))


if __name__ == "__main__":
    unittest.main()
