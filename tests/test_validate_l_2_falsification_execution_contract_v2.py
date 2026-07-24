from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json, write_json
from scripts.validate_l_2_falsification_execution_contract_v2 import DEFAULT_CONTRACT, validate_contract


class L2FalsificationExecutionContractV2Tests(unittest.TestCase):
    def test_locked_contract_passes(self) -> None:
        result = validate_contract()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_changed_supersession_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_CONTRACT))
        payload["supersedes_gate_id"] = "wrong"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contract.json"
            write_json(path, payload)
            result = validate_contract(path, require_manifest=False)
        self.assertIn("field_mismatch:supersedes_gate_id", result["blockers"])


if __name__ == "__main__":
    unittest.main()
