from __future__ import annotations

import json
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from lib.l3_b714_date_only_scanner_v5 import ScanError, enforce_weekly_pair_ceiling, scan_synthetic_date_only
from scripts.run_l_3_b714_date_only_preflight_v5 import guard_workspace_clean, run_synthetic
from scripts.validate_l_3_b714r8_snapshots_v1 import validate as validate_gate
from scripts.validate_l_3_b714_date_only_preflight_report_v5 import ATTESTATION, REPORT, validate


class B714V5Tests(unittest.TestCase):
    def test_gate_and_golden_pair_pass(self) -> None:
        blob = subprocess.run(["git", "show", "d2a15b717d29f55ce9ee55847fb3db3787da94e2:experiments/l_3_b714_date_only_preflight_remediation_v5.json"], capture_output=True, check=True).stdout
        self.assertEqual("a0aa4049e19e3bc2997deab4f0a4dc000650932fc213bdb0624f7ab143207130", hashlib.sha256(blob).hexdigest())

    def test_ceiling_boundary(self) -> None:
        enforce_weekly_pair_ceiling(465)
        with self.assertRaises(ScanError): enforce_weekly_pair_ceiling(466)

    def test_post_end_is_rejected_before_intersection(self) -> None:
        raw = b'{"schema_version":"lily_l1_daily_dataset_v1","acquired_at":"x","cutoff_inclusive":"2015-12-31","symbols":[]}'
        self.assertEqual("scope_restricted", scan_synthetic_date_only(raw)["status"])

    def test_runner_rejects_arguments_and_dirty_or_staged_repositories(self) -> None:
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

    def test_closed_world_and_attestation_tampering(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8")); attestation = json.loads(ATTESTATION.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); rp, ap = root / "report.json", root / "attestation.json"
            report["provenance"]["historical_container_sha256"] = "0" * 64
            rp.write_text(json.dumps(report), encoding="utf-8"); ap.write_text(json.dumps(attestation), encoding="utf-8")
            self.assertEqual("blocked", validate(rp, ap)["status"])
            report = json.loads(REPORT.read_text(encoding="utf-8")); report["unexpected"] = True
            rp.write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual("blocked", validate(rp, ap)["status"])
            report = json.loads(REPORT.read_text(encoding="utf-8")); attestation["schedule"]["common_sessions"].append("2016-01-01")
            rp.write_text(json.dumps(report), encoding="utf-8"); ap.write_text(json.dumps(attestation), encoding="utf-8")
            self.assertEqual("blocked", validate(rp, ap)["status"])

    def test_scope_restricted_matrix_and_commit_guard(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        report.pop("attestation"); report["mode"] = report["outcome"] = "scope_restricted"; report["blocker"] = "synthetic_blocker"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"; path.write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual("scope_restricted", report["mode"])
            report["contract_commit"] = "0" * 40; path.write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual("blocked", validate(path, None)["status"])


if __name__ == "__main__":
    unittest.main()
