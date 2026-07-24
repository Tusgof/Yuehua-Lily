from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json, write_json
from scripts.validate_l_2_multi_lookback_tstat_preregistration_v3 import DEFAULT_PREREGISTRATION, validate_preregistration


class L2MultiLookbackTstatPreregistrationV3Tests(unittest.TestCase):
    def test_committed_preregistration_passes(self) -> None:
        result = validate_preregistration()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_candidate_t_minus_one_window_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["candidate_signal"]["shared_decision_return_window"] = "Use r[t-k-1] for k=0..h-1."
        self.assertIn("candidate_time_window_changed", _validate_temp(payload)["blockers"])

    def test_comparator_future_return_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["comparators"]["primary"]["shared_decision_return_window"] = "Use r[t+1-k] for k=0..h-1."
        self.assertIn("comparator_time_window_changed", _validate_temp(payload)["blockers"])

    def test_same_close_execution_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["time_index_contract"]["execution_index"] = "Execute at the decision close t."
        self.assertIn("time_index_contract_changed", _validate_temp(payload)["blockers"])

    def test_active_return_window_mismatch_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["primary_utility_and_inference"]["observation_unit"] = "candidate and comparator use separately chosen windows"
        self.assertIn("primary_return_window_changed", _validate_temp(payload)["blockers"])

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
