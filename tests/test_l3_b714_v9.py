from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from lib.l3_b714_date_only_scanner_v9 import ScanError, enforce_weekly_pair_ceiling, scan_synthetic_date_only, valid_utf8_bytes
from scripts.run_l_3_b714_date_only_preflight_v9 import guard_workspace_clean, run_synthetic
from scripts.validate_l_3_b714r8_snapshots_v1 import validate as validate_gate
from scripts.validate_l_3_b714_date_only_preflight_report_v9 import ATTESTATION, REPORT, validate


class B714V9Tests(unittest.TestCase):
    def test_gate_and_fixture_pass(self) -> None:
        self.assertEqual("pass", validate_gate()["status"])
        self.assertEqual("pass", validate()["status"])

    def test_465_466_and_utf8_byte_boundary(self) -> None:
        enforce_weekly_pair_ceiling(465)
        with self.assertRaises(ScanError):
            enforce_weekly_pair_ceiling(466)
        self.assertTrue(valid_utf8_bytes(b'{"session_date":"2015-12-31"}'))
        self.assertFalse(valid_utf8_bytes(b"\xff"))

    def test_skip_before_intersection_and_ast_like_metadata_rejection(self) -> None:
        raw = b'{"schema_version":"lily_l1_daily_dataset_v1","acquired_at":"x","cutoff_inclusive":"2015-12-31","symbols":[]}'
        self.assertEqual("scope_restricted", scan_synthetic_date_only(raw)["status"])
        self.assertEqual("scope_restricted", scan_synthetic_date_only(raw.replace(b"symbols", b"__import__"))["status"])

    def test_runner_is_inert_and_workspace_guard_rejects_dirty_and_staged(self) -> None:
        self.assertEqual(2, run_synthetic("not-a-path"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True)
            (root / "a").write_text("a", encoding="utf-8")
            subprocess.run(["git", "add", "a"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "base"], cwd=root, check=True, capture_output=True)
            self.assertTrue(guard_workspace_clean(root))
            (root / "a").write_text("dirty", encoding="utf-8")
            self.assertFalse(guard_workspace_clean(root))
            subprocess.run(["git", "add", "a"], cwd=root, check=True)
            self.assertFalse(guard_workspace_clean(root))

    def test_nested_tamper_attestation_and_commit_tree_are_blocked(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        attestation = json.loads(ATTESTATION.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); report_path = root / "report.json"; attestation_path = root / "attestation.json"
            report["provenance"]["b73_original_ledger_row_sha256"] = "0" * 64
            report_path.write_text(json.dumps(report), encoding="utf-8"); attestation_path.write_text(json.dumps(attestation), encoding="utf-8")
            self.assertEqual("blocked", validate(report_path, attestation_path)["status"])
            report = json.loads(REPORT.read_text(encoding="utf-8")); report["contract_commit"] = "0" * 40
            report_path.write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual("blocked", validate(report_path, attestation_path)["status"])
            report = json.loads(REPORT.read_text(encoding="utf-8")); attestation["schedule"]["execution_dates"] = []
            report_path.write_text(json.dumps(report), encoding="utf-8"); attestation_path.write_text(json.dumps(attestation), encoding="utf-8")
            self.assertEqual("blocked", validate(report_path, attestation_path)["status"])

    def test_scope_matrix_and_manifest_negative(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8")); report.pop("attestation"); report["mode"] = report["outcome"] = "scope_restricted"; report["blocker"] = "synthetic_blocker"
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"; report_path.write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual("pass", validate(report_path, None)["status"])
        self.assertEqual("pass", validate_gate()["status"])


if __name__ == "__main__":
    unittest.main()
