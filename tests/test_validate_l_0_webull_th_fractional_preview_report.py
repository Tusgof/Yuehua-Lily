from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_0_webull_th_fractional_preview_report import validate_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "webull_fractional_preview"


class L0WebullThailandFractionalPreviewReportTests(unittest.TestCase):
    def test_all_locked_fixtures_pass(self) -> None:
        for name in ("report_all_accepted.json", "report_mixed.json", "report_blocked.json"):
            with self.subTest(name=name):
                result = validate_report(FIXTURE_ROOT / name)
                self.assertEqual("pass", result["status"], result["blockers"])

    def test_summary_tampering_is_blocked(self) -> None:
        payload = _fixture("report_mixed.json")
        payload["summary"]["accepted_count"] = 5
        result = _validate_temporary(payload)
        self.assertIn("summary_mismatch", result["blockers"])

    def test_decision_tampering_is_blocked(self) -> None:
        payload = _fixture("report_all_accepted.json")
        payload["decision"] = "mixed_tested_quantity_acceptance"
        result = _validate_temporary(payload)
        self.assertIn("decision_mismatch:expected_all_tested_quantities_accepted", result["blockers"])

    def test_one_unclassified_attempt_requires_a_blocker(self) -> None:
        payload = _fixture("report_mixed.json")
        payload["rows"] = payload["rows"][:4]
        payload["summary"] = {
            "tested_quantity_count": 4,
            "accepted_count": 4,
            "rejected_count": 0,
            "smallest_accepted_tested_quantity": "0.001",
            "largest_rejected_tested_quantity": None,
            "exact_broker_minimum_known": False,
        }
        payload["decision"] = "blocked_after_partial_preview"
        payload["blockers"] = ["unexpected_RuntimeError"]
        payload["request_attestation"]["preview_request_count"] = 5
        payload["request_attestation"]["synthetic_preview_row_count"] = 4
        result = _validate_temporary(payload)
        self.assertIn("request_attestation_mismatch:preview_request_count", result["blockers"])

    def test_uat_partial_report_allows_one_unclassified_attempt(self) -> None:
        payload = _fixture("report_mixed.json")
        payload["report_mode"] = "uat_preview"
        payload["activation_gate_id"] = "l_0_webull_th_fractional_preview_activation_v1"
        payload["rows"] = payload["rows"][:4]
        payload["summary"] = {
            "tested_quantity_count": 4,
            "accepted_count": 4,
            "rejected_count": 0,
            "smallest_accepted_tested_quantity": "0.001",
            "largest_rejected_tested_quantity": None,
            "exact_broker_minimum_known": False,
        }
        payload["decision"] = "blocked_after_partial_preview"
        payload["blockers"] = ["unexpected_RuntimeError"]
        payload["request_attestation"]["preview_request_count"] = 5
        payload["request_attestation"]["synthetic_preview_row_count"] = 0
        payload["request_attestation"]["total_broker_request_count"] = 5
        result = _validate_temporary(payload)
        self.assertEqual("pass", result["status"], result["blockers"])


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _validate_temporary(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_report(path)


if __name__ == "__main__":
    unittest.main()
