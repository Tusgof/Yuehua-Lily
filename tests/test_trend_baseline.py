from __future__ import annotations

import unittest

from lib.statistics import symmetric_eigenvalues
from lib.trend_baseline import _breakdown, _cap_and_redistribute, performance_metrics


class TrendBaselineTests(unittest.TestCase):
    def test_cap_redistributes_without_exceeding_gross_or_asset_cap(self) -> None:
        weights = {"VTI": 0.50, "VGK": 0.10, "EWJ": 0.10, "VWO": 0.10,
                   "IEF": 0.05, "TIP": 0.03, "GLD": 0.01, "DBC": 0.01}
        result = _cap_and_redistribute(weights, cap=0.25, gross_limit=0.90)
        self.assertAlmostEqual(0.90, sum(abs(value) for value in result.values()))
        self.assertLessEqual(max(abs(value) for value in result.values()), 0.25)

    def test_symmetric_eigenvalues_match_known_two_by_two(self) -> None:
        values = symmetric_eigenvalues([[2.0, 1.0], [1.0, 2.0]])
        self.assertAlmostEqual(3.0, values[0], places=10)
        self.assertAlmostEqual(1.0, values[1], places=10)

    def test_performance_metrics_compound(self) -> None:
        result = performance_metrics([0.10, -0.05])
        self.assertAlmostEqual(0.045, result["cumulative_return"])

    def test_regime_coverage_requires_effective_length_and_separated_episodes(self) -> None:
        result = _breakdown([0.001] * 300, ["mixed"] * 300)
        self.assertFalse(result["mixed"]["adequately_covered"])
        self.assertEqual(1, result["mixed"]["separated_episode_count"])


if __name__ == "__main__":
    unittest.main()
