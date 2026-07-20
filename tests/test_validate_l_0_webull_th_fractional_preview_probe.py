from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_0_webull_th_fractional_preview_probe import DEFAULT_PATH, validate_contract


class L0WebullThailandFractionalPreviewProbeTests(unittest.TestCase):
    def test_current_contract_passes(self) -> None:
        result = validate_contract()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_B4_10_cannot_authorize_execution(self) -> None:
        payload = _contract()
        payload["machinery_state"]["execution_authorized_by_B4_10"] = True
        result = _validate_temporary(payload)
        self.assertIn("machinery_state_mismatch", result["blockers"])

    def test_production_tampering_is_blocked(self) -> None:
        payload = _contract()
        payload["environment"]["host"] = "api.webull.co.th"
        payload["environment"]["production_allowed"] = True
        result = _validate_temporary(payload)
        self.assertIn("uat_environment_mismatch", result["blockers"])

    def test_preview_path_tampering_is_blocked(self) -> None:
        payload = _contract()
        payload["request_boundary"]["only_non_auth_request"]["path"] = "/openapi/trade/stock/order/preview"
        result = _validate_temporary(payload)
        self.assertIn("request_boundary_mismatch", result["blockers"])

    def test_quantity_matrix_tampering_is_blocked(self) -> None:
        payload = _contract()
        payload["request_boundary"]["quantity_grid_in_request_order"].pop()
        result = _validate_temporary(payload)
        self.assertIn("request_boundary_mismatch", result["blockers"])

    def test_validation_unlock_is_blocked(self) -> None:
        payload = _contract()
        payload["validation_return_seal"]["returns_opened"] = True
        result = _validate_temporary(payload)
        self.assertIn("validation_seal_false_field_mismatch:returns_opened", result["blockers"])


def _contract() -> dict[str, object]:
    return json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))


def _validate_temporary(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "contract.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_contract(path)


if __name__ == "__main__":
    unittest.main()
