from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json, write_json
from scripts.validate_l_2_multi_lookback_tstat_preregistration import DEFAULT_PREREGISTRATION, validate_preregistration


class L2MultiLookbackTstatPreregistrationTests(unittest.TestCase):
    def test_committed_preregistration_passes(self) -> None:
        result = validate_preregistration()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_horizon_tamper_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["candidate_signal"]["lookback_sessions_in_order"] = [32, 64, 126, 504]
        self.assertIn("candidate_horizons_changed", _validate_temp(payload)["blockers"])

    def test_mintrl_tamper_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["dual_MinTRL"]["validate"]["null_plans"][1]["required_joint_independent_bet_equivalents"] = 1
        self.assertIn("MinTRL_validate_recalculation_mismatch:minimum_useful_improvement", _validate_temp(payload)["blockers"])

    def test_validation_open_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["validation_seal"]["status"] = "opened"
        self.assertIn("validation_seal_changed", _validate_temp(payload)["blockers"])


def _validate_temp(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "preregistration.json"
        write_json(path, payload)
        return validate_preregistration(path)


if __name__ == "__main__":
    unittest.main()
