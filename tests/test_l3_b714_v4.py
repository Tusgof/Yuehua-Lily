from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib.l3_b714_date_only_scanner_v4 import ASSETS, scan_synthetic_date_only, skip_return_number_lexeme, skip_timestamp_lexeme, valid_utf8_bytes
from scripts import validate_l_3_b714_v3_timestamp_decode_violation_addendum_v1 as addendum_validator
from scripts import validate_evidence_tiers
from scripts.validate_evidence_tiers import validate_report_payload
from scripts.validate_l_3_b714_date_only_preflight_remediation_v4 import validate as validate_gate
from scripts.validate_l_3_b714_date_only_preflight_report_v4 import ATTESTATION, REPORT, validate, validate_static


def synthetic_bytes(sessions: list[str]) -> bytes:
    return json.dumps(
        {
            "schema_version": "lily_l1_daily_dataset_v1",
            "acquired_at": "synthetic-only",
            "cutoff_inclusive": "2015-12-31",
            "symbols": [
                {
                    "symbol": symbol,
                    "records": [
                        {"session_date": session, "availability_timestamp": "synthetic-only", "total_return_close": 1}
                        for session in sessions
                    ],
                }
                for symbol in ASSETS
            ],
        },
        separators=(",", ":"),
    ).encode("utf-8")


class B714V4Tests(unittest.TestCase):
    def test_addendum_gate_and_fixture_pair_pass(self) -> None:
        self.assertEqual("pass", addendum_validator.validate()["status"])
        self.assertEqual("pass", validate_gate()["status"])
        self.assertEqual("pass", validate()["status"])

    def test_utf8_validator_rejects_noncanonical_sequences(self) -> None:
        self.assertTrue(valid_utf8_bytes("ไทย".encode("utf-8")))
        for raw in (b"\xc0\x80", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"\xe0\x80\x80", b"\xf0\x80\x80\x80", b"\xe2\x82"):
            self.assertFalse(valid_utf8_bytes(raw))
        self.assertTrue(skip_timestamp_lexeme(b'"synthetic\\u0020only"'))
        self.assertFalse(skip_timestamp_lexeme(b'"\xc0\x80"'))
        self.assertTrue(skip_return_number_lexeme(b"-1.2e3"))
        self.assertFalse(skip_return_number_lexeme(b'"1"'))

    def test_synthetic_structural_date_checks(self) -> None:
        sessions = [
            "2007-02-05", "2007-02-06", "2007-02-07", "2007-02-08", "2007-02-09",
            "2007-02-12", "2007-02-13", "2007-02-14", "2007-02-15", "2007-02-16",
            "2007-02-19", "2007-02-20", "2007-02-21", "2007-02-22", "2007-02-23",
            "2007-02-26", "2007-02-27", "2007-02-28", "2007-03-01", "2007-03-02",
            "2007-03-05", "2007-03-06", "2007-03-07", "2007-03-08", "2007-03-09",
        ]
        result = scan_synthetic_date_only(synthetic_bytes(sessions))
        self.assertEqual("synthetic_preflight_pass", result["status"])
        self.assertEqual(["2007-02-09"], result["schedule"]["selected_decision_dates"])
        post_end = scan_synthetic_date_only(synthetic_bytes(sessions + ["2016-01-01"]))
        self.assertEqual("post_end_session_before_intersection", post_end["blocker"])

    def test_skip_call_graph_is_free_of_decode_and_parsers(self) -> None:
        self.assertEqual("pass", validate_static()["status"])

    def test_report_validator_rejects_unknown_fields_and_co_tamper(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        attestation = json.loads(ATTESTATION.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path, attestation_path = root / "report.json", root / "attestation.json"
            report["unexpected"] = True
            report_path.write_text(json.dumps(report), encoding="utf-8")
            attestation_path.write_text(json.dumps(attestation), encoding="utf-8")
            self.assertEqual("blocked", validate(report_path, attestation_path)["status"])
            report.pop("unexpected")
            attestation["schedule"]["common_sessions"].append("2016-01-01")
            attestation_path.write_text(json.dumps(attestation), encoding="utf-8")
            report["attestation_sha256"] = __import__("lib.provenance", fromlist=["file_sha256"]).file_sha256(attestation_path)
            report_path.write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual("blocked", validate(report_path, attestation_path)["status"])

    def test_other_e1_report_without_blockers_is_not_excepted(self) -> None:
        payload = {
            "schema_version": "other", "hypothesis_id": "L-3", "evidence_tier": "E1",
            "outcome": "scope_restricted", "edge_claim": "none",
        }
        self.assertIn("tier_blockers_must_be_list", validate_report_payload(payload, known_ids={"L-3"}))

    def test_tampered_rejection_addendum_or_report_hash_is_not_excepted(self) -> None:
        payload = json.loads((Path(__file__).parents[1] / "reports/experiments/l_3_b714_date_only_preflight_report_v3.json").read_text(encoding="utf-8"))
        report_path = Path(__file__).parents[1] / "reports/experiments/l_3_b714_date_only_preflight_report_v3.json"
        with tempfile.TemporaryDirectory() as directory:
            tampered = Path(directory) / "addendum.json"
            tampered.write_text("{}", encoding="utf-8")
            with patch.object(addendum_validator, "ADDENDUM", tampered):
                self.assertEqual("blocked", addendum_validator.validate()["status"])
        with patch.object(validate_evidence_tiers, "REJECTED_V3_REPORT_SHA256", "0" * 64):
            blockers = validate_report_payload(payload, known_ids={"L-3"}, path=report_path)
        self.assertIn("tier_blockers_must_be_list", blockers)


if __name__ == "__main__":
    unittest.main()
