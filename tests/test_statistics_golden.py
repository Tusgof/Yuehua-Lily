from __future__ import annotations

import json
import unittest
from pathlib import Path

from lib.statistics import (
    asymptotic_autocorrelation_inflation,
    autocorrelation_inflation,
    deflated_sharpe_ratio,
    effective_independent_bets_from_eigenvalues,
    effective_sample_length,
    expected_maximum_sharpe,
    generalized_sharpe_variance_term,
    independent_bet_equivalent_count,
    minimum_track_record_length,
    minimum_track_record_length_falsify,
    minimum_track_record_length_validate,
    newey_west_t_statistic,
    newey_west_variance_of_mean,
    normal_cdf,
    normal_ppf,
    paired_mean_minimum_observations,
    probabilistic_sharpe_ratio,
    raw_kurtosis_population,
    sharpe_ratio,
    skewness_population,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "statistics_golden.json"
GOLDEN = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


class StatisticsGoldenTests(unittest.TestCase):
    def test_fixture_binds_sources_and_conventions(self) -> None:
        sources = " ".join(GOLDEN["provenance"]["methodology_sources"])
        self.assertIn("how-to-use-the-sharpe-ratio.md", sources)
        self.assertIn("newey-west-validation.md", sources)
        self.assertIn("not excess", GOLDEN["conventions"]["kurtosis"])
        self.assertIn("SciPy 1.17.1", GOLDEN["provenance"]["offline_reference"])

    def test_published_psr_mintrl_anchor(self) -> None:
        anchor = GOLDEN["psr_mintrl"]
        inputs = anchor["inputs"]
        expected = anchor["expected"]
        self.assertAlmostEqual(
            expected["generalized_variance_term"],
            generalized_sharpe_variance_term(
                inputs["observed_sharpe"], inputs["skewness"], inputs["raw_kurtosis"]
            ),
            places=12,
        )
        self.assertAlmostEqual(
            expected["probabilistic_sharpe_ratio"],
            probabilistic_sharpe_ratio(**inputs),
            places=12,
        )
        mintrl_inputs = {key: value for key, value in inputs.items() if key != "sample_length"}
        self.assertEqual(expected["minimum_track_record_length"], minimum_track_record_length(**mintrl_inputs))

    def test_raw_kurtosis_convention_slip_fails_anchor(self) -> None:
        anchor = GOLDEN["psr_mintrl"]
        inputs = anchor["inputs"]
        wrong = generalized_sharpe_variance_term(
            inputs["observed_sharpe"],
            inputs["skewness"],
            inputs["raw_kurtosis"] - 3.0,
        )
        self.assertAlmostEqual(anchor["wrong_excess_kurtosis_variance_term"], wrong, places=12)
        self.assertNotAlmostEqual(anchor["expected"]["generalized_variance_term"], wrong, places=9)

    def test_scipy_offline_cross_check(self) -> None:
        anchor = GOLDEN["scipy_cross_check"]
        returns = anchor["returns"]
        self.assertAlmostEqual(anchor["normal_cdf"], normal_cdf(anchor["normal_input"]), places=12)
        self.assertAlmostEqual(anchor["normal_ppf_95"], normal_ppf(0.95), places=12)
        self.assertAlmostEqual(anchor["expected_sharpe"], sharpe_ratio(returns), places=12)
        self.assertAlmostEqual(anchor["expected_skewness"], skewness_population(returns), places=12)
        self.assertAlmostEqual(anchor["expected_raw_kurtosis"], raw_kurtosis_population(returns), places=12)

    def test_autocorrelation_effective_sample_anchor(self) -> None:
        anchor = GOLDEN["autocorrelation"]
        self.assertAlmostEqual(
            anchor["expected_finite_inflation"],
            autocorrelation_inflation(anchor["sample_length"], anchor["coefficients"]),
            places=12,
        )
        self.assertAlmostEqual(
            anchor["expected_asymptotic_inflation"],
            asymptotic_autocorrelation_inflation(anchor["coefficients"]),
            places=12,
        )
        self.assertAlmostEqual(
            anchor["expected_effective_sample_length"],
            effective_sample_length(anchor["sample_length"], anchor["coefficients"]),
            places=12,
        )

    def test_dual_powered_mintrl_anchor(self) -> None:
        anchor = GOLDEN["dual_mintrl"]
        common = anchor["common"]
        validate = anchor["validate"]
        falsify = anchor["falsify"]
        self.assertEqual(
            validate["expected_length"],
            minimum_track_record_length_validate(
                expected_sharpe=validate["expected_sharpe"],
                null_sharpe=validate["null_sharpe"],
                **common,
            ),
        )
        self.assertEqual(
            falsify["expected_length"],
            minimum_track_record_length_falsify(
                claimed_minimum_sharpe=falsify["claimed_minimum_sharpe"],
                adverse_true_sharpe=falsify["adverse_true_sharpe"],
                **common,
            ),
        )

    def test_paired_mean_power_anchor(self) -> None:
        """Hand-calculated L-3-style paired portfolio planning example."""
        lags = [0.25, 0.125, 0.0625, 0.03125, 0.015625]
        self.assertAlmostEqual(1.96875, asymptotic_autocorrelation_inflation(lags), places=12)
        self.assertEqual(
            49,
            paired_mean_minimum_observations(
                alternative_mean=0.05,
                null_mean=0.0,
                planning_standard_deviation=0.10,
                autocorrelations=lags,
                significance=0.05,
                power=0.80,
            ),
        )
        self.assertEqual(
            49,
            paired_mean_minimum_observations(
                alternative_mean=0.0,
                null_mean=0.05,
                planning_standard_deviation=0.10,
                autocorrelations=lags,
                significance=0.05,
                power=0.80,
            ),
        )
        self.assertEqual(
            49,
            paired_mean_minimum_observations(
                alternative_mean=0.10,
                null_mean=0.05,
                planning_standard_deviation=0.10,
                autocorrelations=lags,
                significance=0.05,
                power=0.80,
            ),
        )
        self.assertIsNone(
            paired_mean_minimum_observations(
                alternative_mean=0.05,
                null_mean=0.05,
                planning_standard_deviation=0.10,
            )
        )

    def test_deflated_sharpe_search_hurdle_anchor(self) -> None:
        anchor = GOLDEN["deflated_sharpe"]
        inputs = anchor["inputs"]
        self.assertAlmostEqual(
            anchor["expected_search_hurdle"],
            expected_maximum_sharpe(
                trial_sharpe_std=inputs["trial_sharpe_std"],
                effective_trials=inputs["effective_trials"],
            ),
            places=12,
        )
        self.assertAlmostEqual(
            anchor["expected_deflated_sharpe_ratio"],
            deflated_sharpe_ratio(**inputs),
            places=12,
        )

    def test_newey_west_anchor(self) -> None:
        anchor = GOLDEN["newey_west"]
        self.assertAlmostEqual(
            anchor["expected_variance_of_mean"],
            newey_west_variance_of_mean(anchor["values"], anchor["lags"]),
            places=15,
        )
        self.assertAlmostEqual(
            anchor["expected_t_statistic"],
            newey_west_t_statistic(anchor["values"], anchor["lags"]),
            places=12,
        )

    def test_independent_bet_equivalent_anchor(self) -> None:
        anchor = GOLDEN["independent_bets"]
        self.assertAlmostEqual(
            anchor["expected_cross_section_bets"],
            effective_independent_bets_from_eigenvalues(anchor["eigenvalues"]),
            places=12,
        )
        self.assertAlmostEqual(
            anchor["expected_joint_bet_equivalents"],
            independent_bet_equivalent_count(
                sample_length=anchor["sample_length"],
                autocorrelations=anchor["autocorrelations"],
                cross_section_eigenvalues=anchor["eigenvalues"],
            ),
            places=12,
        )

    def test_invalid_direction_returns_no_mintrl(self) -> None:
        self.assertIsNone(
            minimum_track_record_length_validate(
                expected_sharpe=0.0,
                null_sharpe=0.1,
                skewness=0.0,
                raw_kurtosis=3.0,
            )
        )
        self.assertIsNone(
            minimum_track_record_length_falsify(
                claimed_minimum_sharpe=0.0,
                adverse_true_sharpe=0.1,
                skewness=0.0,
                raw_kurtosis=3.0,
            )
        )


if __name__ == "__main__":
    unittest.main()
