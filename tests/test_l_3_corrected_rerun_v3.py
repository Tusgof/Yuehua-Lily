from __future__ import annotations

import copy
import json
import math
import unittest
from datetime import date, timedelta
from pathlib import Path

from lib.l3_corrected_rerun_v3 import ASSETS, END, VALIDATION, build_canonical_schedule, derive_side_effects, scan_synthetic_envelope
from scripts.validate_l_3_corrected_rerun_activation_v3 import validate

ROOT = Path(__file__).resolve().parents[1]


class B78StructuralTests(unittest.TestCase):
    def envelope(self) -> dict:
        records = [{"session_date": "2007-02-05", "availability_timestamp": "metadata-distraction", "total_return_close": 1.0}]
        return {"schema_version": "lily_l1_daily_dataset_v1", "acquired_at": {"not": "validated metadata"}, "cutoff_inclusive": END, "symbols": [{"symbol": symbol, "records": copy.deepcopy(records)} for symbol in ASSETS]}

    def test_scanner_exact_schema_order_and_individual_boundary_stops(self) -> None:
        for session in (END, VALIDATION):
            payload = self.envelope()
            payload["symbols"][0]["records"].append({"session_date": session, "availability_timestamp": "ignored", "total_return_close": 9.0})
            result = scan_synthetic_envelope(payload)
            self.assertIn("forbidden_boundary_session_before_intersection", result["blockers"])
        payload = self.envelope()
        payload["symbols"].reverse()
        self.assertIn("symbol_identity_or_order_mismatch", scan_synthetic_envelope(payload)["blockers"])
        payload = self.envelope()
        payload["symbols"][0]["records"][0]["extra"] = "no"
        self.assertIn("record_shape_mismatch", scan_synthetic_envelope(payload)["blockers"])
        result = scan_synthetic_envelope(self.envelope())
        self.assertEqual("pass", result["status"])
        self.assertFalse(result["return_values_exposed"])

    def test_canonical_weekly_schedule_has_465_candidates_and_complete_t20(self) -> None:
        sessions: list[str] = []
        current = date.fromisoformat("2007-02-05")
        while current <= date.fromisoformat(END):
            sessions.append(current.isoformat())
            current += timedelta(days=1)
        result = build_canonical_schedule(sessions)
        self.assertEqual("pass", result["status"], result)
        self.assertEqual(465, result["candidate_week_count"])
        self.assertEqual("2007-02-05", result["first_eligible_session"])
        self.assertEqual("2007-02-11", result["selected_decision_dates"][0])
        self.assertEqual("2007-02-12", result["execution_dates"][0])
        self.assertEqual(END, result["falsification_end"])
        self.assertTrue(result["all_confirmations_within_falsification_end"])
        self.assertEqual("65e610dcdc2f142a9114cf05ef9269d5cc5496d80de4e044ac2a06ec475e4823", result["schedule_sha256"])

    def test_schedule_rejects_duplicate_and_incomplete_inputs(self) -> None:
        self.assertIn("common_sessions_not_strictly_monotonic", build_canonical_schedule(["2007-02-05", "2007-02-05"])["blockers"])
        result = build_canonical_schedule(["2007-02-05", "2007-02-06"], ["2007-02-05"])
        self.assertIn("incomplete_t_plus_20_interval", result["blockers"])
        self.assertIn("noncanonical_weekly_selection", result["blockers"])
        self.assertIn("duplicate_or_noncanonical_week", build_canonical_schedule(["2007-02-05"], ["2007-02-05", "2007-02-05"])["blockers"])

    def row(self, day: str, weights: dict[str, float], cost: float) -> dict:
        return {"date": day, "weights": weights, "commission": cost * 0.3, "spread_slippage": cost * 0.3, "sell_surcharge": cost * 0.4, "cap_binding": any(weight >= .25 for weight in weights.values()), "excess_cash": sum(weights.values()) < .90, "scale_down": False, "pre_scale_volatility": .1, "target_volatility": .2}

    def paired_rows(self) -> tuple[list[dict], list[dict]]:
        first = {asset: .1 for asset in ASSETS}
        comparator_second = {asset: .1 for asset in ASSETS}; comparator_second["VTI"] = .2; comparator_second["VGK"] = .2
        candidate_second = {asset: .1 for asset in ASSETS}; candidate_second["VTI"] = .22; candidate_second["VGK"] = .22
        comparator = [self.row("2007-02-05", first, .5), self.row("2007-02-06", comparator_second, .5)]
        candidate = [self.row("2007-02-05", first, .6), self.row("2007-02-06", candidate_second, .6)]
        return candidate, comparator

    def test_side_effects_are_strict_and_boundary_arithmetic_is_inclusive(self) -> None:
        candidate, comparator = self.paired_rows()
        result = derive_side_effects(candidate, comparator)
        self.assertTrue(result["evaluable"])
        self.assertTrue(result["met"])
        self.assertAlmostEqual(.20, result["turnover_relative_increase"])
        self.assertAlmostEqual(.20, result["cost_relative_increase"])
        cap_candidate, cap_comparator = [], []
        for offset in range(10):
            day = f"2007-03-{offset + 1:02d}"
            base = {asset: .1 for asset in ASSETS}
            alternate = {asset: .1 for asset in ASSETS}; alternate["VTI"] = .2; alternate["VGK"] = .2
            cap_comparator.append(self.row(day, base if offset % 2 == 0 else alternate, 1.0))
            cap_candidate.append(self.row(day, base if offset % 2 == 0 else alternate, 1.0))
        cap_candidate[0]["weights"] = {**cap_candidate[0]["weights"], "VTI": .25}; cap_candidate[0]["cap_binding"] = True; cap_candidate[0]["excess_cash"] = False
        self.assertAlmostEqual(.10, derive_side_effects(cap_candidate, cap_comparator)["cap_frequency_increase"])
        for mutate in (
            lambda rows: rows[0].__setitem__("cap_binding", "false"),
            lambda rows: rows[0]["weights"].__setitem__("VTI", -1.0),
            lambda rows: rows[0]["weights"].__setitem__("VTI", math.nan),
            lambda rows: rows[0].pop("commission"),
            lambda rows: rows[0].__setitem__("extra", 1),
        ):
            bad = copy.deepcopy(candidate); mutate(bad)
            self.assertFalse(derive_side_effects(bad, comparator)["evaluable"])
        mismatch = copy.deepcopy(candidate); mismatch[1]["date"] = "2007-02-07"
        self.assertEqual("paired_dates_mismatch", derive_side_effects(mismatch, comparator)["reason"])
        zero = copy.deepcopy(comparator)
        zero[1]["weights"] = copy.deepcopy(zero[0]["weights"])
        zero[1]["excess_cash"] = True
        self.assertEqual("zero_denominator", derive_side_effects(candidate, zero)["reason"])

    def test_gate_is_hash_bound_and_closed_world(self) -> None:
        self.assertEqual("pass", validate()["status"], validate())


if __name__ == "__main__":
    unittest.main()
