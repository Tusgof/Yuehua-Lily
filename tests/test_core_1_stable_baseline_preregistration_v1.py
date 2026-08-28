from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json, write_json
from scripts.validate_core_1_stable_baseline_preregistration_v1 import (
    DEFAULT_PREREGISTRATION,
    validate_preregistration,
)


class Core1StableBaselinePreregistrationTests(unittest.TestCase):
    def test_committed_preregistration_passes(self) -> None:
        result = validate_preregistration()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_each_locked_scientific_and_governance_field_fails_closed(self) -> None:
        cases = {
            "question": (lambda p: p.__setitem__("research_question", "changed"), "question_changed"),
            "variants": (lambda p: p["development_candidates_in_locked_order"].pop(), "variants_changed"),
            "universe_order": (lambda p: p["universe"]["symbols_in_order"].reverse(), "universe_order_changed"),
            "timing": (lambda p: p["timing"].__setitem__("same_close_execution", True), "timing_changed"),
            "portfolio_and_band": (lambda p: p["portfolio_construction"]["no_trade_band"].__setitem__("trade_when_absolute_difference_at_least", 0.01), "portfolio_and_band_changed"),
            "costs_and_stress": (lambda p: p["costs"]["stress"]["double"].append("ETF expenses"), "costs_and_stress_changed"),
            "windows_and_seal": (lambda p: p["windows"]["final_validation"].__setitem__("status", "opened"), "windows_and_seal_changed"),
            "benchmark": (lambda p: p["matched_benchmark"].__setitem__("same_costs", False), "benchmark_changed"),
            "A_H_gates": (lambda p: p["development_eligibility_gates"].__setitem__("A", "changed"), "A_H_gates_changed"),
            "selection": (lambda p: p["selection_rule"].__setitem__("primary", "changed"), "selection_changed"),
            "stop_rule": (lambda p: p.__setitem__("stop_rule", "changed"), "stop_rule_changed"),
            "claim_ceiling": (lambda p: p.__setitem__("claim_ceiling", "E1"), "claim_ceiling_changed"),
            "authorizations": (lambda p: p["authorizations"].__setitem__("backtest", True), "authorizations_changed"),
            "source_identity_and_hash": (lambda p: p["source_provenance"]["wiki"][0].__setitem__("sha256", "0" * 64), "source_identity_and_hash_changed"),
            "next_action": (lambda p: p.__setitem__("exact_next_safe_action", "open validation"), "next_action_changed"),
        }
        for name, (mutate, expected_blocker) in cases.items():
            with self.subTest(name=name):
                payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
                mutate(payload)
                result = _validate_temp(payload)
                self.assertEqual("fail", result["status"])
                self.assertIn(expected_blocker, result["blockers"])
                self.assertIn("locked_contract_sha256_changed", result["blockers"])

    def test_search_inventory_and_unknown_fields_fail_closed(self) -> None:
        cases = {
            "search_inventory": lambda p: p["search_accounting_and_inference"].__setitem__("search_inventory_exact_trials", 4),
            "unknown_top_level": lambda p: p.__setitem__("unexpected", True),
            "unknown_nested": lambda p: p["costs"]["primary"].__setitem__("unexpected", True),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                payload = copy.deepcopy(load_json(DEFAULT_PREREGISTRATION))
                mutate(payload)
                result = _validate_temp(payload)
                self.assertEqual("fail", result["status"])
                self.assertIn("locked_contract_sha256_changed", result["blockers"])
                if name == "search_inventory":
                    self.assertIn("search_and_inference_changed", result["blockers"])
                else:
                    self.assertIn("top_level_structure_changed" if name == "unknown_top_level" else "costs_and_stress_changed", result["blockers"])


def _validate_temp(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "preregistration.json"
        write_json(path, payload)
        return validate_preregistration(path)


if __name__ == "__main__":
    unittest.main()
