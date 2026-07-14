from __future__ import annotations

import unittest

from scripts.validate_l_1_baseline_summary import TRIAL_IDS


class L1SummaryValidatorTests(unittest.TestCase):
    def test_trial_inventory_is_locked_and_primary_is_first(self) -> None:
        self.assertEqual(
            ["primary_60", "sensitivity_40", "sensitivity_80", "sensitivity_low_cost", "sensitivity_severe_cost"],
            TRIAL_IDS,
        )


if __name__ == "__main__":
    unittest.main()
