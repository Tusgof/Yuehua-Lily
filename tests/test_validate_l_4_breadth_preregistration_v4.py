from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import validate_l_4_breadth_preregistration_v4 as validator

ROOT = Path(__file__).resolve().parents[1]


class L4BreadthV4Tests(unittest.TestCase):
    def _mutate(self, mutate):
        payload = json.loads((ROOT / "experiments/l_4_breadth_preregistration_v4.json").read_text(encoding="utf-8"))
        mutate(payload)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gate.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return validator.validate_gate(path)

    def test_current_gate_passes(self):
        self.assertEqual("pass", validator.validate_gate()["status"])

    def test_e1_and_validation_truth_tables_are_exhaustive_with_precedence(self):
        self.assertEqual("scope_restricted", validator.classify_e1(non_evaluable_or_underfunded=True, breach=True))
        self.assertEqual("falsified_E1_only", validator.classify_e1(non_evaluable_or_underfunded=False, breach=True))
        self.assertEqual("not_falsified_not_validated_E1", validator.classify_e1(non_evaluable_or_underfunded=False, breach=False))
        self.assertEqual("validation_scope_restricted", validator.classify_validation(non_evaluable_or_underfunded=True, breach=True, all_lcb_strictly_above=True, constraints_pass=True, integrity_pass=True))
        self.assertEqual("validation_falsified_E1_only", validator.classify_validation(non_evaluable_or_underfunded=False, breach=True, all_lcb_strictly_above=True, constraints_pass=True, integrity_pass=True))
        self.assertEqual("validation_candidate", validator.classify_validation(non_evaluable_or_underfunded=False, breach=False, all_lcb_strictly_above=True, constraints_pass=True, integrity_pass=True))
        self.assertEqual("not_validated_E1", validator.classify_validation(non_evaluable_or_underfunded=False, breach=False, all_lcb_strictly_above=False, constraints_pass=True, integrity_pass=True))

    def test_capacity_macro_episode_regime_and_authorization_drift_block(self):
        mutations = (
            lambda p: p["static_capacity"].__setitem__("maximum_weekly_slots_before_warmup_missingness_or_evaluable_pair_reductions", 466),
            lambda p: p["macro_sleeves"]["equity"].pop(),
            lambda p: p["robustness_and_side_effects"]["best_trend_episode"].__setitem__("episode_rule", "any episode"),
            lambda p: p["regime_matrix"]["major_subperiods"][1].__setitem__("end", "2015-12-30"),
            lambda p: p["authorizations"].__setitem__("data", True),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assertEqual("blocked", self._mutate(mutation)["status"])

    def test_unknown_nested_key_missing_validation_outcome_and_snapshot_drift_block(self):
        mutations = (
            lambda p: p["mandatory_metrics"]["n_eff_delta"].__setitem__("unknown", True),
            lambda p: p["decision_contract"].__setitem__("validation", ["validation_scope_restricted", "validation_falsified_E1_only", "validation_candidate"]),
            lambda p: p["source_binding"]["snapshots"]["files"][0].__setitem__("sha256", "0" * 64),
            lambda p: p["v3_binding"].__setitem__("gate_sha256", "0" * 64),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assertEqual("blocked", self._mutate(mutation)["status"])


if __name__ == "__main__":
    unittest.main()
