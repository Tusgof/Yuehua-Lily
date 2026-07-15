from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_0_webull_th_read_only_capability_probe import DEFAULT_PATH, validate_contract


class L0WebullThailandReadOnlyCapabilityProbeTests(unittest.TestCase):
    def test_current_contract_passes(self) -> None:
        result = validate_contract()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_order_path_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["allowed_requests"]["read_only_paths"].append("/openapi/orders/place")
        result = _validate_temporary(payload)
        self.assertIn("read_only_path_inventory_mismatch", result["blockers"])

    def test_account_id_persistence_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["environment"]["selected_account_may_be_persisted_or_logged"] = True
        result = _validate_temporary(payload)
        self.assertIn("account_id_persistence_must_be_false", result["blockers"])

    def test_candidate_expansion_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["candidate_universe"]["symbols"].append("SPY")
        result = _validate_temporary(payload)
        self.assertIn("candidate_symbol_inventory_mismatch", result["blockers"])

    def test_validation_unlock_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["validation_return_seal"]["status_required"] = "opened"
        result = _validate_temporary(payload)
        self.assertIn("validation_must_remain_sealed", result["blockers"])


def _validate_temporary(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "contract.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_contract(path)


if __name__ == "__main__":
    unittest.main()
