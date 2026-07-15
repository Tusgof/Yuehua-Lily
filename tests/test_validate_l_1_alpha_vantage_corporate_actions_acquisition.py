from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_1_alpha_vantage_corporate_actions_acquisition import (
    DEFAULT_PATH,
    validate_contract,
)


class L1AlphaVantageCorporateActionsAcquisitionContractTests(unittest.TestCase):
    def test_current_contract_passes(self) -> None:
        result = validate_contract()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_lily_etf_request_in_design_order_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["design_only_attestation"]["lily_etf_requests_in_B4_3"] = 1
        result = _validate_temporary(payload)
        self.assertIn("design_only_attestation_mismatch", result["blockers"])

    def test_validation_return_access_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["validation_return_seal"]["validation_status_required"] = "opened"
        result = _validate_temporary(payload)
        self.assertIn("validation_must_remain_sealed", result["blockers"])

    def test_symbol_search_expansion_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["request_universe"]["symbols"].append("SPY")
        result = _validate_temporary(payload)
        self.assertIn("symbol_inventory_mismatch", result["blockers"])

    def test_paid_fallback_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["request_guardrails"]["spend_rule"] = "Paid fallback allowed."
        result = _validate_temporary(payload)
        self.assertIn("zero_spend_rule_mismatch", result["blockers"])

    def test_point_in_time_overstatement_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["reconciliation_and_decision"]["mandatory_scope_restriction"] = (
            "A successful reconciliation removes every blocker."
        )
        result = _validate_temporary(payload)
        self.assertIn("mandatory_scope_restriction_incomplete", result["blockers"])


def _validate_temporary(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "contract.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_contract(path)


if __name__ == "__main__":
    unittest.main()
