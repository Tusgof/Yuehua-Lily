from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_0_webull_th_fractional_preview_activation import DEFAULT_PATH, validate_activation


class L0WebullThailandFractionalPreviewActivationTests(unittest.TestCase):
    def test_current_activation_passes(self) -> None:
        result = validate_activation()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_production_cannot_be_authorized(self) -> None:
        payload = _activation()
        payload["production_allowed"] = True
        payload["execution_scope"]["host"] = "api.webull.co.th"
        result = _validate_temporary(payload)
        self.assertIn("field_mismatch:production_allowed", result["blockers"])
        self.assertIn("execution_scope_mismatch", result["blockers"])

    def test_orders_cannot_be_authorized(self) -> None:
        payload = _activation()
        payload["orders_allowed"] = True
        result = _validate_temporary(payload)
        self.assertIn("field_mismatch:orders_allowed", result["blockers"])

    def test_path_and_matrix_tampering_are_blocked(self) -> None:
        payload = _activation()
        payload["execution_scope"]["only_non_auth_request"]["path"] = "/openapi/trade/order/place"
        payload["execution_scope"]["quantity_grid_in_request_order"].pop()
        result = _validate_temporary(payload)
        self.assertIn("execution_scope_mismatch", result["blockers"])

    def test_pre_execution_requests_must_remain_zero(self) -> None:
        payload = _activation()
        payload["request_attestation_before_execution"]["preview_calls"] = 1
        result = _validate_temporary(payload)
        self.assertIn("pre_execution_attestation_nonzero:preview_calls", result["blockers"])

    def test_validation_unlock_is_blocked(self) -> None:
        payload = _activation()
        payload["validation_return_seal"]["returns_opened"] = True
        result = _validate_temporary(payload)
        self.assertIn("validation_seal_false_field_mismatch:returns_opened", result["blockers"])


def _activation() -> dict[str, object]:
    return json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))


def _validate_temporary(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "activation.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_activation(path)


if __name__ == "__main__":
    unittest.main()
