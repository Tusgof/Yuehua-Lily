from __future__ import annotations

import copy
import math
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json, write_json
from lib.statistics import minimum_track_record_length_falsify, minimum_track_record_length_validate
from scripts.validate_l_2_multi_lookback_tstat_preregistration_v2 import DEFAULT_PREREGISTRATION, validate_preregistration


class L2MultiLookbackTstatPreregistrationV2Tests(unittest.TestCase):
    def test_committed_preregistration_passes(self) -> None:
        result = validate_preregistration()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_matched_horizon_comparator_tamper_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["comparators"]["primary"]["lookback_sessions_in_order"] = [60]
        self.assertIn("primary_comparator_not_matched_horizon", _validate_temp(payload)["blockers"])

    def test_per_period_conversion_tamper_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["dual_MinTRL"]["falsify"]["claimed_minimum_per_period_sharpe"] = 0.1
        self.assertIn("MinTRL_falsify_per_period_conversion_mismatch", _validate_temp(payload)["blockers"])

    def test_dsr_input_tamper_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["search_accounting_and_DSR"]["DSR_input_series"] = "candidate return only"
        self.assertIn("DSR_input_series_changed", _validate_temp(payload)["blockers"])

    def test_validation_open_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["validation_seal"]["status"] = "opened"
        self.assertIn("validation_seal_changed", _validate_temp(payload)["blockers"])

    def test_falsification_matrix_tamper_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["falsification_decision_matrix"] = []
        self.assertIn("falsification_decision_matrix_changed", _validate_temp(payload)["blockers"])

    def test_mintrl_per_period_golden_values(self) -> None:
        daily_minimum = 0.1 / math.sqrt(252)
        daily_expected = 0.2 / math.sqrt(252)
        common = dict(skewness=0.0, raw_kurtosis=6.0, autocorrelations=[0.1, 0.05, 0.025, 0.0125, 0.00625], significance=0.05, power=0.8)
        self.assertAlmostEqual(0.00629940788348712, daily_minimum, places=16)
        self.assertEqual(54048, minimum_track_record_length_falsify(claimed_minimum_sharpe=daily_minimum, adverse_true_sharpe=-daily_minimum, **common))
        self.assertEqual(54056, minimum_track_record_length_validate(expected_sharpe=daily_expected, null_sharpe=0.0, **common))
        self.assertEqual(216218, minimum_track_record_length_validate(expected_sharpe=daily_expected, null_sharpe=daily_minimum, **common))


def _validate_temp(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "preregistration.json"
        write_json(path, payload)
        return validate_preregistration(path)


if __name__ == "__main__":
    unittest.main()
