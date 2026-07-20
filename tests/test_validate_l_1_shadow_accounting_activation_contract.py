from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_1_shadow_accounting_activation_contract import DEFAULT_PATH, validate_contract


class L1ShadowAccountingActivationContractTests(unittest.TestCase):
    def test_current_contract_passes(self) -> None:
        result = validate_contract()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_activation_cannot_be_claimed(self) -> None:
        payload = _payload()
        payload["decision"]["dry_run_started"] = True
        result = _temporary_validation(payload)
        self.assertIn("decision_boundary_mismatch", result["blockers"])

    def test_runtime_path_cannot_be_added_after_lock(self) -> None:
        payload = _payload()
        payload["environment_contract"]["runtime_network_allowlist"] = ["/openapi/account/list"]
        result = _temporary_validation(payload)
        self.assertIn("runtime_allowlist_must_be_empty", result["blockers"])

    def test_shared_or_production_account_cannot_be_enabled(self) -> None:
        payload = _payload()
        payload["environment_contract"]["shared_test_account_allowed"] = True
        payload["environment_contract"]["production_account_fallback_allowed"] = True
        result = _temporary_validation(payload)
        self.assertIn("environment_false_field_mismatch:shared_test_account_allowed", result["blockers"])
        self.assertIn("environment_false_field_mismatch:production_account_fallback_allowed", result["blockers"])

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
