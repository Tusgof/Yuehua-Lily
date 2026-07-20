from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_1_shadow_accounting_activation_contract import DEFAULT_PATH, validate_contract


class L1WebullApiScopeAndFractionalPreviewTests(unittest.TestCase):
    def test_current_contract_passes(self) -> None:
        result = validate_contract()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_B4_9_cannot_execute_preview(self) -> None:
        payload = _payload()
        payload["fractional_preview_probe"]["execution_authorized_by_B4_9"] = True
        result = _temporary_validation(payload)
        self.assertIn("B4_9_must_not_authorize_preview_execution", result["blockers"])

    def test_production_preview_cannot_be_enabled(self) -> None:
        payload = _payload()
        payload["fractional_preview_probe"]["production_host_or_account_allowed"] = True
        result = _temporary_validation(payload)
        self.assertIn("production_preview_must_be_forbidden", result["blockers"])

    def test_preview_path_and_grid_are_fixed(self) -> None:
        payload = _payload()
        payload["fractional_preview_probe"]["only_non_auth_path"]["path"] = "/openapi/trade/order/place"
        payload["fractional_preview_probe"]["quantity_grid_in_request_order"].append("0.00000001")
        result = _temporary_validation(payload)
        self.assertIn("preview_path_mismatch", result["blockers"])
        self.assertIn("quantity_grid_mismatch", result["blockers"])

    def test_corporate_action_scope_cannot_restore_broker_ledger(self) -> None:
        payload = _payload()
        payload["decision"]["webull_account_corporate_action_ledger_classification"] = "available"
        result = _temporary_validation(payload)
        self.assertIn("scope_decision_mismatch", result["blockers"])

    def test_validation_return_access_is_blocked(self) -> None:
        payload = _payload()
        payload["validation_return_seal"]["pnl_opened"] = True
        result = _temporary_validation(payload)
        self.assertIn("validation_seal_false_field_mismatch:pnl_opened", result["blockers"])


def _payload() -> dict[str, object]:
    return json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))


def _temporary_validation(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "contract.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_contract(path)


if __name__ == "__main__":
    unittest.main()
