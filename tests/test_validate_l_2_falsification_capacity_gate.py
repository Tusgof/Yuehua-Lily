from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json, write_json
from scripts.validate_l_2_falsification_capacity_gate import GATE, validate_gate


class L2FalsificationCapacityGateTests(unittest.TestCase):
    def test_locked_gate_is_underfunded(self) -> None:
        result = validate_gate()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_impossible_capacity_or_execution_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(GATE))
        payload["absolute_upper_bound"]["maximum_joint_independent_bet_equivalents"] = 54048
        self.assertIn("absolute_upper_bound_mismatch", _validate(payload)["blockers"])
        payload = copy.deepcopy(load_json(GATE))
        payload["execution_authorized"] = True
        self.assertIn("field_mismatch:execution_authorized", _validate(payload)["blockers"])


def _validate(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "gate.json"
        write_json(path, payload)
        return validate_gate(path, require_manifest=False)


if __name__ == "__main__":
    unittest.main()
