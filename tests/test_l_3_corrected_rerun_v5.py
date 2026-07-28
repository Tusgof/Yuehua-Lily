from __future__ import annotations

import copy
import json
import math
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from lib.l3_corrected_rerun_v5 import ASSETS, END, build_canonical_schedule, derive_side_effects, scan_synthetic_envelope
from scripts.validate_l_3_corrected_rerun_activation_v5 import validate

ROOT = Path(__file__).resolve().parents[1]


class B79StructuralTests(unittest.TestCase):
    def envelope(self) -> dict:
        record = {"session_date": "2007-02-05", "availability_timestamp": {"ignored": True}, "total_return_close": 999.0}
        return {"schema_version": "lily_l1_daily_dataset_v1", "acquired_at": "ignored", "cutoff_inclusive": END, "symbols": [{"symbol": symbol, "records": [copy.deepcopy(record)]} for symbol in ASSETS]}

    def test_per_symbol_post_end_hard_stop_and_inclusive_end(self) -> None:
        positive = self.envelope()
        positive["symbols"][0]["records"].append({"session_date": END, "availability_timestamp": "metadata", "total_return_close": -123.0})
        result = scan_synthetic_envelope(positive)
        self.assertEqual("pass", result["status"], result)
        self.assertFalse(result["return_values_exposed"])
        for post_end in ("2016-01-04", "2016-01-05", "2017-01-03"):
            payload = self.envelope()
            payload["symbols"][0]["records"].append({"session_date": post_end, "availability_timestamp": "metadata-distraction", "total_return_close": math.nan})
            result = scan_synthetic_envelope(payload)
            self.assertEqual("blocked", result["status"], result)
            self.assertIn("post_end_session_before_intersection", result["blockers"])
            self.assertNotIn(post_end, result["common_sessions"])

    def test_schema_order_schedule_and_side_effect_boundaries(self) -> None:
        payload = self.envelope(); payload["symbols"].reverse()
        self.assertIn("symbol_identity_or_order_mismatch", scan_synthetic_envelope(payload)["blockers"])
        sessions, current = [], date.fromisoformat("2007-02-05")
        while current <= date.fromisoformat(END):
            sessions.append(current.isoformat()); current += timedelta(days=1)
        schedule = build_canonical_schedule(sessions)
        self.assertEqual("pass", schedule["status"], schedule)
        self.assertEqual(465, schedule["candidate_week_count"])
        self.assertEqual("2007-02-05", schedule["first_eligible_session"])
        self.assertEqual("2007-02-12", schedule["execution_dates"][0])
        self.assertEqual("65e610dcdc2f142a9114cf05ef9269d5cc5496d80de4e044ac2a06ec475e4823", schedule["schedule_sha256"])
        self.assertIn("noncanonical_weekly_selection", build_canonical_schedule(sessions, schedule["selected_decision_dates"][:-1])["blockers"])
        self.assertIn("incomplete_t_plus_20_interval", build_canonical_schedule(["2007-02-05", "2007-02-06"], ["2007-02-05"])["blockers"])
        self.assertEqual(465, schedule["candidate_week_count"])
        self.assertEqual(461, len(schedule["selected_decision_dates"]))

    def test_side_effect_contract_is_still_strict(self) -> None:
        def row(day: str, weights: dict[str, float], cost: float) -> dict:
            return {"date": day, "weights": weights, "commission": cost * .3, "spread_slippage": cost * .3, "sell_surcharge": cost * .4, "cap_binding": any(value >= .25 for value in weights.values()), "excess_cash": sum(weights.values()) < .9, "scale_down": False, "pre_scale_volatility": .1, "target_volatility": .2}
        first = {asset: .1 for asset in ASSETS}
        comparator_second = {**first, "VTI": .2, "VGK": .2}; candidate_second = {**first, "VTI": .22, "VGK": .22}
        candidate = [row("2007-02-05", first, .6), row("2007-02-06", candidate_second, .6)]
        comparator = [row("2007-02-05", first, .5), row("2007-02-06", comparator_second, .5)]
        result = derive_side_effects(candidate, comparator)
        self.assertTrue(result["evaluable"]); self.assertTrue(result["met"])
        self.assertAlmostEqual(.20, result["turnover_relative_increase"]); self.assertAlmostEqual(.20, result["cost_relative_increase"])
        bad = copy.deepcopy(candidate); bad[0]["cap_binding"] = "false"
        self.assertFalse(derive_side_effects(bad, comparator)["evaluable"])

    def test_active_gate_closed_world_tamper_cases(self) -> None:
        source = json.loads((ROOT / "experiments/l_3_corrected_rerun_activation_v5.json").read_text())
        cases = []
        wrong_path = copy.deepcopy(source); wrong_path["implementation"]["runner"]["path"] = "scripts/validate_locked_gates.py"; wrong_path["implementation"]["runner"]["sha256"] = __import__("hashlib").sha256((ROOT / "scripts/validate_locked_gates.py").read_bytes()).hexdigest(); cases.append(wrong_path)
        empty_auth = copy.deepcopy(source); empty_auth["authorizations"] = {}; cases.append(empty_auth)
        extra_auth = copy.deepcopy(source); extra_auth["authorizations"]["extra"] = False; cases.append(extra_auth)
        string_false = copy.deepcopy(source); string_false["authorizations"]["execution"] = "false"; cases.append(string_false)
        attestation = copy.deepcopy(source); attestation["attestation"]["market_returns_read_count"] = 1; cases.append(attestation)
        for payload in cases:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "gate.json"; path.write_text(json.dumps(payload), encoding="utf-8")
                self.assertEqual("blocked", validate(path)["status"], validate(path))
        self.assertEqual("pass", validate()["status"], validate())


if __name__ == "__main__":
    unittest.main()
