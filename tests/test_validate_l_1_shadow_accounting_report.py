from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_1_shadow_accounting_report import validate_report


FIXTURES = Path(__file__).parent / "fixtures" / "shadow_accounting"


class L1ShadowAccountingReportTests(unittest.TestCase):
    def test_locked_synthetic_examples_pass(self) -> None:
        for name in ("report_no_material.json", "report_material_breach.json", "report_activation_blocked.json"):
            result = validate_report(FIXTURES / name)
            self.assertEqual("pass", result["status"], (name, result["blockers"]))

    def test_opposite_events_cannot_net_away_a_breach(self) -> None:
        payload = _fixture("report_material_breach.json")
        payload["decision"] = "no_material_operational_discrepancy_observed_within_preregistered_scope"
        result = _temporary_validation(payload)
        self.assertIn("decision_mismatch:expected_material_operational_discrepancy_observed", result["blockers"])

    def test_equal_threshold_is_not_material(self) -> None:
        payload = _fixture("report_material_breach.json")
        first = payload["events"][0]["comparisons"][0]
        first["cash_difference_usd"] = 1.0
        first["reported_material_dimensions"] = []
        payload["events"][0]["comparisons"][2]["cash_difference_usd"] = 1.0
        payload["events"][0]["comparisons"][2]["reported_material_dimensions"] = []
        payload["events"][0]["reported_event_breach"] = False
        payload["summary"]["event_breach_count"] = 0
        result = _temporary_validation(payload)
        self.assertIn("report_before_preregistered_decision_gate", result["blockers"])
        self.assertNotIn("event_1:webull_vs_alpha_vantage:material_dimension_mismatch", result["blockers"])

    def test_validation_access_is_blocked(self) -> None:
        payload = _fixture("report_activation_blocked.json")
        payload["validation_return_seal"]["returns_opened"] = True
        result = _temporary_validation(payload)
        self.assertIn("validation_seal_false_field_mismatch:returns_opened", result["blockers"])

    def test_broker_or_order_call_is_blocked(self) -> None:
        payload = _fixture("report_activation_blocked.json")
        payload["request_attestation"]["preview_calls"] = 1
        result = _temporary_validation(payload)
        self.assertIn("request_attestation_must_be_zero:preview_calls", result["blockers"])


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _temporary_validation(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_report(path)


if __name__ == "__main__":
    unittest.main()
