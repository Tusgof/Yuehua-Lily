from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json, write_json
from scripts.validate_l_1_baseline_preregistration import (
    DEFAULT_PREREGISTRATION,
    validate_preregistration,
)


class L1BaselinePreregistrationValidatorTests(unittest.TestCase):
    def test_committed_preregistration_passes(self) -> None:
        result = validate_preregistration()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_signal_window_tamper_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["signal"]["formula"] = "q = sum(last 40 directions) / 40"
        result = _validate_temp(payload)
        self.assertIn("signal_formula_must_lock_60_directional_observations", result["blockers"])

    def test_validation_mintrl_tamper_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["dual_MinTRL"]["validate"]["null_plans"][1][
            "required_joint_independent_bet_equivalents"
        ] = 100
        result = _validate_temp(payload)
        self.assertIn(
            "MinTRL_validate_recalculation_mismatch:minimum_acceptable_Sharpe",
            result["blockers"],
        )

    def test_same_close_execution_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["timing_and_calendar"]["same_close_execution_forbidden"] = False
        result = _validate_temp(payload)
        self.assertIn("execution_delay_or_same_close_rule_changed", result["blockers"])


def _validate_temp(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "preregistration.json"
        write_json(path, payload)
        return validate_preregistration(path)


if __name__ == "__main__":
    unittest.main()
