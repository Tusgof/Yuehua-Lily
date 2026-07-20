from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_0_webull_th_fractional_preview_activation_v2 import DEFAULT_PATH, validate_activation


class L0WebullThailandFractionalPreviewActivationV2Tests(unittest.TestCase):
    def test_current_activation_passes(self) -> None:
        result = validate_activation()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_production_orders_or_long_polling_cannot_be_authorized(self) -> None:
        payload = _activation()
        payload["production_allowed"] = True
        payload["orders_allowed"] = True
        payload["execution_scope"]["authentication_polling_duration_seconds"] = 300
        result = _validate_temporary(payload)
        self.assertIn("field_mismatch:production_allowed", result["blockers"])
        self.assertIn("field_mismatch:orders_allowed", result["blockers"])
        self.assertIn("execution_scope_mismatch", result["blockers"])

    def test_request_caps_and_preview_matrix_are_locked(self) -> None:
        payload = _activation()
        payload["execution_scope"]["maximum_authentication_requests"] = 9
        payload["execution_scope"]["quantity_grid_in_request_order"].pop()
        result = _validate_temporary(payload)
        self.assertIn("execution_scope_mismatch", result["blockers"])

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
