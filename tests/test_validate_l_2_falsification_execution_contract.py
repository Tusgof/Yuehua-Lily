from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json, write_json
from scripts.validate_l_2_falsification_execution_contract import DEFAULT_CONTRACT, validate_contract


class L2FalsificationExecutionContractTests(unittest.TestCase):
    def test_committed_contract_passes(self) -> None:
        result = validate_contract()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_v3_hash_tamper_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_CONTRACT))
        payload["preregistration_sources"]["v3_sha256"] = "0" * 64
        self.assertIn("v2_or_v3_hash_mismatch", _validate_temp(payload)["blockers"])

    def test_execution_authorization_tamper_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_CONTRACT))
        payload["machinery_state"]["execution_authorized_by_B6"] = True
        self.assertIn("execution_authorization_boundary_changed", _validate_temp(payload)["blockers"])

    def test_overlay_tamper_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_CONTRACT))
        payload["overlay_rule"] = "merge v2 and v3 opportunistically"
        self.assertIn("v2_v3_overlay_rule_changed", _validate_temp(payload)["blockers"])


def _validate_temp(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "contract.json"
        write_json(path, payload)
        return validate_contract(path, require_manifest=False)


if __name__ == "__main__":
    unittest.main()
