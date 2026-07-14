from __future__ import annotations

import json
import unittest
from datetime import date

from lib.yahoo_daily import normalize_chart, request_specification


class YahooDailyTests(unittest.TestCase):
    def test_normalization_reconstructs_distribution_return_and_stops_at_cutoff(self) -> None:
        raw = json.dumps(
            {
                "chart": {
                    "error": None,
                    "result": [
                        {
                            "meta": {"currency": "USD"},
                            "timestamp": [1138924800, 1139184000],
                            "indicators": {"quote": [{"close": [100.0, 101.0]}]},
                            "events": {"dividends": {"x": {"date": 1139184000, "amount": 1.0}}},
                        }
                    ],
                }
            }
        ).encode()
        spec = request_specification("TEST", date(2006, 2, 3), date(2006, 2, 6))
        result = normalize_chart(
            raw,
            spec,
            legal_inception=date(2000, 1, 1),
            cutoff_inclusive=date(2006, 2, 6),
        )
        self.assertAlmostEqual(1.02, result["records"][1]["total_return_close"])
        self.assertEqual("2006-02-06", result["coverage"]["end"])

    def test_normalization_rejects_validation_record(self) -> None:
        raw = json.dumps(
            {
                "chart": {
                    "error": None,
                    "result": [
                        {
                            "meta": {"currency": "USD"},
                            "timestamp": [1451865600],
                            "indicators": {"quote": [{"close": [100.0]}]},
                        }
                    ],
                }
            }
        ).encode()
        with self.assertRaisesRegex(ValueError, "beyond locked cutoff"):
            normalize_chart(
                raw,
                request_specification("TEST", date(2015, 12, 31), date(2015, 12, 31)),
                legal_inception=date(2000, 1, 1),
                cutoff_inclusive=date(2015, 12, 31),
            )


if __name__ == "__main__":
    unittest.main()
