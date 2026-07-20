from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_1_prospective_shadow_accounting_preregistration import (
    DEFAULT_PATH,
    validate_preregistration,
)


class L1ProspectiveShadowAccountingPreregistrationTests(unittest.TestCase):
    def test_current_preregistration_passes(self) -> None:
        result = validate_preregistration()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_activation_or_paper_order_authorization_is_blocked(self) -> None:
        payload = _payload()
        payload["execution_state"]["activation_authorized_by_this_gate"] = True
        payload["execution_state"]["paper_order_authorized_by_this_gate"] = True
        result = _validate_temporary(payload)
        self.assertIn("execution_state_boundary_mismatch", result["blockers"])

    def test_weakened_cash_threshold_is_blocked(self) -> None:
        payload = _payload()
        payload["materiality_thresholds"]["cash_balance_difference_usd"] = "greater than USD 10"
        result = _validate_temporary(payload)
        self.assertIn("materiality_threshold_mismatch:cash_balance_difference_usd", result["blockers"])

    def test_too_few_events_cannot_be_treated_as_clean(self) -> None:
        payload = _payload()
        payload["breach_and_decision_rules"]["insufficient_evidence_rule"] = "Treat as clean."
        result = _validate_temporary(payload)
        self.assertIn("decision_rule_missing:insufficient_operational_evidence", result["blockers"])

    def test_validation_return_access_is_blocked(self) -> None:
        payload = _payload()
        payload["validation_return_seal"]["returns_opened"] = True
        result = _validate_temporary(payload)
        self.assertIn("validation_seal_false_field_mismatch:returns_opened", result["blockers"])

    def test_no_netting_rule_cannot_be_removed(self) -> None:
        payload = _payload()
        payload["breach_and_decision_rules"]["no_netting_rule"] = "Net all events."
        result = _validate_temporary(payload)
        self.assertIn("decision_rule_missing:Never net opposite", result["blockers"])


def _payload() -> dict[str, object]:
    return json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))


def _validate_temporary(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "preregistration.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_preregistration(path)


if __name__ == "__main__":
    unittest.main()
