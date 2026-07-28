from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from lib.l4_b85r3_structural_scanner_v4 import MAX_BYTES, PAYLOAD_SCHEMA, U8, ScanError, scan_payload
from lib.provenance import git_commit
from scripts.run_l_4_breadth_b85r3_phase_b_preflight_v4 import GATE_ID, MANIFEST_RELATIVE, PAYLOAD_RELATIVE, contract_identities, main, run_one_shot
from scripts.validate_l_4_breadth_b85r3_structural_preflight_report_v4 import MANIFEST, PAYLOAD, validate


def activation(path: Path) -> None:
    identities = contract_identities()
    path.write_text(json.dumps({"schema_version":"lily_l4_b85r3_phase_b_activation_v4","gate_id":GATE_ID,"gate_sha256":identities["phase_a_gate"]["sha256"],"accepted_head_sha":git_commit(),"hermetic_ci_run_id":1,"hermetic_ci_head_sha":git_commit(),"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.5R3 Phase B owner authorization","scope":"one_structural_u8_preflight_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}}), encoding="ascii")


def maximum_payload() -> bytes:
    days = [(date(2000, 1, 1) + timedelta(days=index)).isoformat() for index in range(4096)]
    return json.dumps({"schema_version":PAYLOAD_SCHEMA,"symbol_sessions":[{"symbol":symbol,"session_dates":days} for symbol in U8]}, separators=(",", ":")).encode("ascii")


class B85R3StructuralPreflightTests(unittest.TestCase):
    def test_capacity_formula_accepts_near_capacity_and_rejects_bound_plus_one(self) -> None:
        raw = maximum_payload()
        self.assertEqual(MAX_BYTES, len(raw))
        self.assertEqual(32768, scan_payload(raw)["session_count"])
        with self.assertRaises(ScanError): scan_payload(raw + b"x")

    def test_synthetic_fixture_passes(self) -> None:
        from scripts.run_l_4_breadth_b85r3_phase_b_preflight_v4 import preflight_from_raw
        report = preflight_from_raw(MANIFEST.read_bytes(), PAYLOAD.read_bytes())
        self.assertEqual("pass", validate(report)["status"])

    def test_over_limit_report_has_prefix_not_complete_hash_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, report_path, marker, accepted = Path(temporary) / "root", Path(temporary) / "report.json", Path(temporary) / "marker.json", Path(temporary) / "accepted.json"
            (root / MANIFEST_RELATIVE).parent.mkdir(parents=True)
            (root / MANIFEST_RELATIVE).write_bytes(b"x" * (MAX_BYTES + 1))
            activation(accepted)
            report = run_one_shot(root, report_path=report_path, attempt_marker_path=marker, activation_record_path=accepted)
            observed = report["artifacts"]["manifest"]
            self.assertEqual("manifest_input_over_limit", report["blocker"])
            self.assertFalse(observed["complete_read"])
            self.assertIsNone(observed["complete_raw_sha256"])
            self.assertEqual(MAX_BYTES + 1, observed["observed_byte_count"])
            self.assertEqual("pass", validate(report, marker_path=marker)["status"])

    def test_second_invocation_preserves_first_report_and_marker_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, report_path, marker, accepted = Path(temporary) / "root", Path(temporary) / "report.json", Path(temporary) / "marker.json", Path(temporary) / "accepted.json"
            (root / MANIFEST_RELATIVE).parent.mkdir(parents=True)
            shutil.copyfile(MANIFEST, root / MANIFEST_RELATIVE)
            shutil.copyfile(PAYLOAD, root / PAYLOAD_RELATIVE)
            activation(accepted)
            first = run_one_shot(root, report_path=report_path, attempt_marker_path=marker, activation_record_path=accepted)
            report_hash, marker_hash = hashlib.sha256(report_path.read_bytes()).hexdigest(), hashlib.sha256(marker.read_bytes()).hexdigest()
            second = run_one_shot(root, report_path=report_path, attempt_marker_path=marker, activation_record_path=accepted)
            self.assertEqual("structural_pass", first["outcome"])
            self.assertEqual("refused_already_consumed", second["outcome"])
            self.assertEqual(report_hash, hashlib.sha256(report_path.read_bytes()).hexdigest())
            self.assertEqual(marker_hash, hashlib.sha256(marker.read_bytes()).hexdigest())

    def test_missing_or_wrong_activation_and_bare_cli_are_inert(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_path, marker, accepted = Path(temporary) / "report.json", Path(temporary) / "marker.json", Path(temporary) / "accepted.json"
            self.assertEqual("refused_activation", run_one_shot(Path(temporary) / "root", report_path=report_path, attempt_marker_path=marker, activation_record_path=accepted)["outcome"])
            self.assertFalse(report_path.exists() or marker.exists())
            activation(accepted)
            accepted.write_text("{}", encoding="ascii")
            self.assertEqual("refused_activation", run_one_shot(Path(temporary) / "root", report_path=report_path, attempt_marker_path=marker, activation_record_path=accepted)["outcome"])
            self.assertEqual(2, main([])); self.assertEqual(2, main(["--wrong"]))


if __name__ == "__main__":
    unittest.main()
