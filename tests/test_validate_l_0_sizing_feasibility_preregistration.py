from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json
from scripts.validate_l_0_sizing_feasibility_preregistration import (
    DEFAULT_PREREGISTRATION,
    validate_preregistration,
)


class L0SizingPreregistrationTests(unittest.TestCase):
    def test_current_preregistration_passes(self) -> None:
        result = validate_preregistration()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_post_measurement_state_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["pre_measurement_state"]["analysis_code_written"] = True
        result = _validate_temp(payload)
        self.assertIn(
            "pre_measurement_state_must_be_false:analysis_code_written",
            result["blockers"],
        )

    def test_margin_threshold_weakening_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
        payload["futures_branch"]["margin_and_cash_limits"][
            "base_initial_margin_max_fraction_of_capital"
        ] = 0.80
        result = _validate_temp(payload)
        self.assertIn(
            "futures_margin_limit_changed:base_initial_margin_max_fraction_of_capital",
            result["blockers"],
        )


def _validate_temp(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "preregistration.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_preregistration(path)


if __name__ == "__main__":
    unittest.main()
