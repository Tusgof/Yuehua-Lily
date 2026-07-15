from __future__ import annotations

import unittest
from collections import Counter
from datetime import date

from lib.market_calendar import nyse_sessions


class MarketCalendarTests(unittest.TestCase):
    def test_l1_validation_window_session_inventory(self) -> None:
        sessions = nyse_sessions(date(2016, 1, 4), date(2026, 6, 30))
        self.assertEqual(2637, len(sessions))
        self.assertEqual(date(2016, 1, 4), sessions[0])
        self.assertEqual(date(2026, 6, 30), sessions[-1])
        self.assertEqual(
            {
                2016: 252,
                2017: 251,
                2018: 251,
                2019: 252,
                2020: 253,
                2021: 252,
                2022: 251,
                2023: 250,
                2024: 252,
                2025: 250,
                2026: 123,
            },
            dict(Counter(item.year for item in sessions)),
        )

    def test_national_days_of_mourning_are_closed(self) -> None:
        sessions = set(nyse_sessions(date(2018, 12, 1), date(2025, 1, 10)))
        self.assertNotIn(date(2018, 12, 5), sessions)
        self.assertNotIn(date(2025, 1, 9), sessions)

    def test_early_close_remains_a_session(self) -> None:
        self.assertIn(
            date(2024, 11, 29),
            nyse_sessions(date(2024, 11, 29), date(2024, 11, 29)),
        )


if __name__ == "__main__":
    unittest.main()
