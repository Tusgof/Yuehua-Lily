from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_1_corporate_action_scope_decision import DEFAULT_PATH, validate_decision


class L1CorporateActionScopeDecisionTests(unittest.TestCase):
    def test_current_decision_passes(self) -> None:
        result = validate_decision()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_validation_unlock_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["decision"]["validation_unlock_authorized"] = True
        result = _validate_temporary(payload)
        self.assertIn("decision_boundary_mismatch", result["blockers"])

    def test_paper_trade_authorization_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["decision"]["paper_trade_authorized_by_this_decision"] = True
        result = _validate_temporary(payload)
        self.assertIn("decision_boundary_mismatch", result["blockers"])

    def test_unlocked_materiality_threshold_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["prospective_shadow_accounting"]["materiality_threshold_status"] = "set_after_observation"
        result = _validate_temporary(payload)
        self.assertIn("shadow_field_mismatch:materiality_threshold_status", result["blockers"])


def _validate_temporary(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "decision.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_decision(path)


if __name__ == "__main__":
    unittest.main()
