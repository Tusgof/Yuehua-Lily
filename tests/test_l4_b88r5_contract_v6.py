"""Synthetic/adversarial proof for the B8.8R5/v6 scientific correction."""
from __future__ import annotations

import json
import unittest
from datetime import date, timedelta
from pathlib import Path

from lib.l4_b88r5_scientific_engine_v6 import (
    METRICS,
    U8,
    _breakdown_assignment,
    _regimes,
    _side_effects,
    classify_outcome,
    derive,
    USEFUL,
)

ROOT = Path(__file__).resolve().parents[1]


def _side_effect_row(
    gross_u4: float,
    gross_u8: float,
    *,
    turnover_u4: float = 0.2,
    turnover_u8: float = 0.2,
    cost_u4: float = 0.01,
    cost_u8: float = 0.01,
) -> dict:
    return {
        "gross_u4": gross_u4,
        "gross_u8": gross_u8,
        "changes_u4": [turnover_u4, 0.0, 0.0, 0.0],
        "changes_u8": [turnover_u8] + [0.0] * 7,
        "costs_u4": {"total": cost_u4},
        "costs_u8": {"total": cost_u8},
        "flags_u4": {"cap": False, "cash": False, "scale_down": False},
        "flags_u8": {"cap": False, "cash": False, "scale_down": False},
    }


def _regime_row(symbol_index: int, date: str) -> dict:
    weights = [0.0] * len(U8)
    weights[symbol_index] = 0.8
    covariance = [[float(index == other) for other in range(len(U8))] for index in range(len(U8))]
    row = {
        "date": date,
        "regime": {
            "global_state": "mixed",
            "volatility_tercile": "warmup_unclassified",
            "equity_synchronization": "mixed_signs",
        },
        "state": {"u8": {"weights": weights, "covariance": covariance}},
    }
    row["breakdown"] = _breakdown_assignment(row)
    return row


def _statistics_vector(value: float) -> dict:
    return {
        metric: {
            "values": [0.1],
            "mintrl": {"falsify": 1},
            "falsify_ucb": USEFUL[metric] if value == 0.05 else value,
        }
        for metric in METRICS
    }


def _synthetic_container(days: int = 430) -> dict:
    sessions = []
    cursor = date(2013, 1, 2)
    while len(sessions) < days:
        if cursor.weekday() < 5:
            sessions.append(cursor.isoformat())
        cursor += timedelta(days=1)
    returns = {
        symbol: [((index * (asset + 3) + index * index * (asset + 1)) % 17 - 8) / 1000 for index in range(days)]
        for asset, symbol in enumerate(U8)
    }
    return {
        "schema_version": "lily_l4_normalized_container_v1",
        "cutoff_inclusive": "2015-12-31",
        "universe": list(U8),
        "sessions": sessions,
        "returns": returns,
        "cash_returns": [0.00001] * days,
    }


class B88R5V6Contract(unittest.TestCase):
    def test_side_effects_use_aggregate_denominators_and_allow_zero_first_row(self):
        rows = [_side_effect_row(0.0, 0.0), _side_effect_row(0.5, 0.5)]
        result = _side_effects(rows)
        self.assertTrue(result["evaluable"])
        self.assertEqual(result["pre_trade_gross_u4"], 0.5)
        self.assertEqual(result["pre_trade_gross_u8"], 0.5)
        self.assertAlmostEqual(result["turnover_intensity_u4"], 0.8)
        self.assertAlmostEqual(result["turnover_intensity_u8"], 0.8)
        self.assertAlmostEqual(result["cost_intensity_u4"], 0.04)
        self.assertAlmostEqual(result["cost_intensity_u8"], 0.04)
        self.assertEqual(result["turnover_relative_increase"], 0.0)
        self.assertEqual(result["cost_relative_increase"], 0.0)

    def test_zero_aggregate_comparator_remains_non_evaluable(self):
        turnover_zero = _side_effect_row(0.5, 0.5, turnover_u4=0.0)
        cost_zero = _side_effect_row(0.5, 0.5, cost_u4=0.0)
        self.assertFalse(_side_effects([turnover_zero])["evaluable"])
        self.assertFalse(_side_effects([cost_zero])["evaluable"])

    def test_v6_derive_reaches_evaluable_side_effects_after_zero_initial_gross(self):
        container = _synthetic_container()
        result = derive(container, config={"u8_sessions": container["sessions"]})
        self.assertIsNotNone(result)
        self.assertEqual(result["weekly_observations"][0]["gross_u4"], 0.0)
        self.assertEqual(result["weekly_observations"][0]["gross_u8"], 0.0)
        self.assertTrue(result["side_effects"]["evaluable"])
        self.assertTrue(all(row["breakdown"] is not None for row in result["weekly_observations"]))
        self.assertEqual(
            sum(result["regimes"][f"asset:{symbol}"]["weekly_observations"] for symbol in U8),
            len(result["weekly_observations"]),
        )

    def test_all_three_e1_outcomes_are_reachable_from_locked_vectors(self):
        fixture = json.loads((ROOT / "tests/fixtures/l4_b88r5/decision_vectors_v6.json").read_text("ascii"))
        observed = {}
        for vector in fixture["vectors"]:
            outcome = classify_outcome(vector["statistics"], constraints_pass=vector["constraints_pass"])
            self.assertEqual(outcome, vector["expected"], vector["id"])
            observed[vector["id"]] = outcome
        self.assertEqual(
            set(observed.values()),
            {"scope_restricted", "falsified_E1_only", "not_falsified_not_validated_E1"},
        )

    def test_outcome_precedence_and_strict_equality_boundary(self):
        self.assertEqual(classify_outcome(_statistics_vector(0.01), constraints_pass=False), "scope_restricted")
        falsified = _statistics_vector(0.05)
        falsified["n_eff_delta"]["falsify_ucb"] = 0.49
        self.assertEqual(classify_outcome(falsified, constraints_pass=True), "falsified_E1_only")
        self.assertEqual(classify_outcome(_statistics_vector(0.05), constraints_pass=True), "not_falsified_not_validated_E1")

    def test_breakdowns_assign_one_nonduplicated_bucket_per_dimension(self):
        rows = [_regime_row(0, "2008-01-04"), _regime_row(6, "2012-01-06")]
        self.assertEqual(rows[0]["breakdown"]["asset"], "VTI")
        self.assertEqual(rows[0]["breakdown"]["macro_sleeve"], "equity")
        self.assertEqual(rows[0]["breakdown"]["country_or_region"], "United_States")
        self.assertEqual(rows[1]["breakdown"]["asset"], "GLD")
        self.assertEqual(rows[1]["breakdown"]["macro_sleeve"], "gold")
        self.assertEqual(rows[1]["breakdown"]["country_or_region"], "Global")
        result = _regimes(rows)
        self.assertEqual(result["asset:VTI"]["weekly_observations"], 1)
        self.assertEqual(result["asset:GLD"]["weekly_observations"], 1)
        self.assertEqual(result["asset:VGK"]["weekly_observations"], 0)
        self.assertEqual(result["macro_sleeve:equity"]["weekly_observations"], 1)
        self.assertEqual(result["macro_sleeve:gold"]["weekly_observations"], 1)
        self.assertEqual(result["country_or_region:United_States"]["weekly_observations"], 1)
        self.assertEqual(result["country_or_region:Global"]["weekly_observations"], 1)
        self.assertEqual(
            sum(result[f"asset:{symbol}"]["weekly_observations"] for symbol in U8),
            len(rows),
        )


if __name__ == "__main__":
    unittest.main()
