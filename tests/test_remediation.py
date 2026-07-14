from __future__ import annotations

import unittest
from datetime import date

from lib.remediation import cash_returns_for_sessions


class RemediationTests(unittest.TestCase):
    def test_cash_yield_is_lagged_and_accrues_calendar_days(self) -> None:
        payload = {
            "observations": [
                {"date": "2015-12-24", "yield_percent": 1.0},
                {"date": "2015-12-28", "yield_percent": 2.0},
            ]
        }
        result = cash_returns_for_sessions(payload, ["2015-12-24", "2015-12-28", "2015-12-29"])
        self.assertEqual(0.0, result["2015-12-24"])
        self.assertAlmostEqual((1.01 ** (4 / 365)) - 1.0, result["2015-12-28"])
        self.assertAlmostEqual((1.02 ** (1 / 365)) - 1.0, result["2015-12-29"])


if __name__ == "__main__":
    unittest.main()
