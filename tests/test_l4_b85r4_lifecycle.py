from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from lib.l4_b85r4_structural_scanner_v5 import MAX_BYTES, PAYLOAD_SCHEMA, U8, ScanError, scan_payload
from scripts.run_l_4_breadth_b85r4_phase_b_preflight_v5 import GATE_ID, MANIFEST_RELATIVE, PAYLOAD_RELATIVE, identities, main, run_one_shot, synthetic
from scripts.validate_l_4_breadth_b85r4_phase_a_activation_order_v5 import GATE, validate as validate_gate
from scripts.validate_l_4_breadth_b85r4_structural_preflight_report_v5 import MANIFEST, PAYLOAD, validate


def acceptance() -> bytes:
    return json.dumps({"schema_version":"lily_l4_b85r4_phase_b_activation_v5","gate_id":GATE_ID,"gate_sha256":identities()["phase_a_gate"]["sha256"],"accepted_gate_head_sha":"a" * 40,"hermetic_ci_run_id":1,"hermetic_ci_head_sha":"a" * 40,"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.5R4 Phase B owner authorization","scope":"one_structural_u8_preflight_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}}, separators=(",", ":")).encode("ascii")


def maximum_payload() -> bytes:
    days = [(date(2000, 1, 1) + timedelta(days=index)).isoformat() for index in range(4096)]
    return json.dumps({"schema_version":PAYLOAD_SCHEMA,"symbol_sessions":[{"symbol":symbol,"session_dates":days} for symbol in U8]}, separators=(",", ":")).encode("ascii")


class B85R4LifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = synthetic(MANIFEST.read_bytes(), PAYLOAD.read_bytes())

    def test_gate_and_fixture_pass(self) -> None:
        self.assertEqual("pass", validate_gate()["status"])
        self.assertEqual("pass", validate(self.report)["status"])

    def test_gate_tampering_blocks(self) -> None:
        payload = json.loads(GATE.read_text(encoding="utf-8"))
        payload["future_phase_b_contract"]["exact_execution_flag"] = "--wrong"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "gate.json"; path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual("blocked", validate_gate(path)["status"])

    def test_every_pass_binding_tamper_blocks(self) -> None:
        changes = (
            lambda r: r["artifacts"]["manifest"].__setitem__("complete_raw_sha256", "0" * 64),
            lambda r: r["artifacts"]["payload"].__setitem__("bounded_prefix_sha256", "0" * 64),
            lambda r: r["artifacts"]["payload"].__setitem__("observed_byte_count", 0),
            lambda r: r["artifacts"]["payload"].__setitem__("scan_count", 0),
            lambda r: r["artifacts"]["payload"].__setitem__("minimal_ascii_decode_count", 0),
            lambda r: r["manifest"].__setitem__("metadata_sha256", "0" * 64),
            lambda r: r.__setitem__("structural_summary_sha256", "0" * 64),
            lambda r: r["payload"].__setitem__("complete_raw_sha256", "0" * 64),
            lambda r: r["payload"].__setitem__("observed_byte_count", 0),
            lambda r: r["payload"].__setitem__("max_session_date", "2000-01-01"),
            lambda r: r["payload"].__setitem__("session_count", 1),
            lambda r: r["payload"]["session_counts_by_symbol"].__setitem__("VTI", 1),
            lambda r: r["payload"].__setitem__("u8_members_in_order", list(reversed(U8))),
            lambda r: r["payload"]["session_dates_by_symbol"]["VTI"].__setitem__(0, "2015-12-29"),
        )
        for change in changes:
            report = copy.deepcopy(self.report); change(report)
            self.assertEqual("blocked", validate(report)["status"])

    def test_capacity_and_over_limit_block(self) -> None:
        raw = maximum_payload()
        self.assertEqual(MAX_BYTES, len(raw))
        self.assertEqual(32768, scan_payload(raw)["session_count"])
        with self.assertRaises(ScanError):
            scan_payload(raw + b"x")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"; report_path = Path(temporary) / "report.json"; marker = Path(temporary) / "marker.json"
            (root / MANIFEST_RELATIVE).parent.mkdir(parents=True)
            (root / MANIFEST_RELATIVE).write_bytes(b"x" * (MAX_BYTES + 1))
            report = run_one_shot(root, report_path=report_path, attempt_marker_path=marker, activation_raw=acceptance(), activation_head="b" * 40)
            self.assertEqual("manifest_input_over_limit", report["blocker"])
            self.assertFalse(report["artifacts"]["manifest"]["complete_read"])
            self.assertIsNone(report["artifacts"]["manifest"]["complete_raw_sha256"])

    def test_second_invocation_preserves_first_report_and_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"; report_path = Path(temporary) / "report.json"; marker = Path(temporary) / "marker.json"
            (root / MANIFEST_RELATIVE).parent.mkdir(parents=True)
            shutil.copyfile(MANIFEST, root / MANIFEST_RELATIVE); shutil.copyfile(PAYLOAD, root / PAYLOAD_RELATIVE)
            first = run_one_shot(root, report_path=report_path, attempt_marker_path=marker, activation_raw=acceptance(), activation_head="b" * 40)
            hashes = (hashlib.sha256(report_path.read_bytes()).hexdigest(), hashlib.sha256(marker.read_bytes()).hexdigest())
            second = run_one_shot(root, report_path=report_path, attempt_marker_path=marker, activation_raw=acceptance(), activation_head="b" * 40)
            self.assertEqual("structural_pass", first["outcome"]); self.assertEqual("refused_already_consumed", second["outcome"])
            self.assertEqual(hashes, (hashlib.sha256(report_path.read_bytes()).hexdigest(), hashlib.sha256(marker.read_bytes()).hexdigest()))

    def test_missing_wrong_acceptance_and_bare_cli_are_inert(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "report.json"; marker = Path(temporary) / "marker.json"
            self.assertEqual("refused_activation", run_one_shot(Path(temporary) / "root", report_path=report_path, attempt_marker_path=marker, activation_raw=b"{}", activation_head="b" * 40)["outcome"])
            self.assertFalse(report_path.exists() or marker.exists())
            self.assertEqual(2, main([])); self.assertEqual(2, main(["--wrong"]))

    def test_lifecycle_is_provenance_not_current_head_equality(self) -> None:
        report = copy.deepcopy(self.report)
        record = json.loads(acceptance())
        report.update({"mode":"real_one_shot","real_preflight_consumed":True,"producing_git_commit":"b" * 40,"activation_provenance":{"path":"experiments/activation_records/l_4_breadth_b85r4_phase_b_activation_v5.json","raw_sha256":"c" * 64,"content":record,"activation_checkpoint_head":"b" * 40}})
        for artifact in report["artifacts"].values():
            artifact["attempted_read_count"] = artifact["read_count"] = 1
        self.assertEqual("pass", validate(report, provenance_check=lambda p, commit: p["activation_checkpoint_head"] == commit and commit == "b" * 40 and p["content"]["accepted_gate_head_sha"] == "a" * 40)["status"])


if __name__ == "__main__":
    unittest.main()
