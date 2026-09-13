from __future__ import annotations

import copy
import math
import unittest
from decimal import Decimal

from lib.core_1e_b2b_r3_decision_kernel import (
    CANDIDATE_ORDER,
    STOP_NO_CANDIDATE,
    SELECTED_CANDIDATE,
    EvidenceValidationError,
    ForgedDecisionError,
    derive_decision,
)


ASSETS = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
PERIODS = ("2007-2009", "2010-2012", "2013-2015")


def _candidate(candidate_id: str, **changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "candidate_id": candidate_id,
        "primary_net_annual_geometric_return": 0.05,
        "primary_net_annual_sharpe": 0.60,
        "stress_net_annual_geometric_return": 0.03,
        "stress_net_annual_sharpe": 0.40,
        "primary_max_drawdown": -0.10,
        "benchmark_max_drawdown": -0.20,
        "leave_one_asset_id": "VTI",
        "leave_one_asset_net_annual_geometric_return": 0.04,
        "asset_net_contributions": {asset: 0.02 for asset in ASSETS},
        "subperiod_net_annual_geometric_return": {period: 0.03 for period in PERIODS},
        "subperiod_net_sharpe": {period: 0.20 for period in PERIODS},
        "one_way_turnover": 0.10,
        "critical_blockers": [],
        "trials": [
            {"annual_sharpe": 0.60, "psr_vs_zero": 0.95, "hac_mean_return_p_value": 0.04, "dsr_probability": 0.91},
            {"annual_sharpe": 0.50, "psr_vs_zero": 0.93, "hac_mean_return_p_value": 0.05, "dsr_probability": 0.88},
            {"annual_sharpe": 0.40, "psr_vs_zero": 0.92, "hac_mean_return_p_value": 0.06, "dsr_probability": 0.85},
        ],
        "best_episode_concentration": 0.25,
    }
    value.update(changes)
    return value


def _evidence() -> dict[str, object]:
    return {"candidates": [_candidate(candidate_id) for candidate_id in CANDIDATE_ORDER]}


def _scores(evidence: dict[str, object], scores: tuple[float, float, float], turnovers: tuple[float, float, float]) -> None:
    for candidate, score, turnover in zip(evidence["candidates"], scores, turnovers):
        candidate["subperiod_net_sharpe"] = {period: score for period in PERIODS}
        candidate["one_way_turnover"] = turnover


class Core1EB2BR3DecisionKernelTests(unittest.TestCase):
    def test_all_gates_and_e0_output_are_derived(self) -> None:
        decision = derive_decision(_evidence())
        self.assertEqual(decision.outcome, SELECTED_CANDIDATE)
        self.assertEqual(decision.selected_candidate, "CORE1_DC60")
        self.assertEqual(decision.eligible_candidates, CANDIDATE_ORDER)
        self.assertEqual(decision.ranking_order, CANDIDATE_ORDER)
        self.assertEqual(decision.as_mapping()["evidence_tier"], "E0")
        self.assertEqual(decision.edge_claim, "none")
        self.assertEqual(decision.validation_status, "sealed_not_accessed")
        self.assertEqual(decision.as_mapping()["future_provenance_bound_empirical_ceiling"], "E1_development_ceiling_only")
        for evaluation in decision.candidate_evaluations:
            self.assertEqual(evaluation.gates, {letter: True for letter in "ABCDEFGH"})
            self.assertEqual(evaluation.worst_subperiod_net_sharpe, Decimal("0.20"))
            self.assertEqual(evaluation.largest_positive_contribution_share, Decimal("0.125"))
            self.assertEqual(evaluation.positive_contribution_hhi, Decimal("0.125"))
            self.assertEqual(evaluation.removed_asset, "VTI")
            self.assertIsInstance(evaluation.worst_subperiod_net_sharpe, Decimal)

    def test_gate_a_is_strict_at_zero(self) -> None:
        for field in ("primary_net_annual_geometric_return", "primary_net_annual_sharpe"):
            evidence = _evidence()
            evidence["candidates"][0][field] = 0.0
            if field.endswith("sharpe"):
                evidence["candidates"][0]["trials"][0]["annual_sharpe"] = 0.0
            self.assertFalse(derive_decision(evidence).candidate_evaluations[0].gates["A"])

    def test_gate_b_psr_boundary_is_inclusive(self) -> None:
        evidence = _evidence()
        evidence["candidates"][0]["trials"][0]["psr_vs_zero"] = 0.90
        self.assertTrue(derive_decision(evidence).candidate_evaluations[0].gates["B"])
        evidence["candidates"][0]["trials"][0]["psr_vs_zero"] = 0.899999
        self.assertFalse(derive_decision(evidence).candidate_evaluations[0].gates["B"])

    def test_gate_c_requires_positive_stress_return_and_sharpe(self) -> None:
        for field in ("stress_net_annual_geometric_return", "stress_net_annual_sharpe"):
            evidence = _evidence()
            evidence["candidates"][0][field] = 0.0
            self.assertFalse(derive_decision(evidence).candidate_evaluations[0].gates["C"])

    def test_gate_d_drawdown_improvement_boundary_is_inclusive(self) -> None:
        evidence = _evidence()
        evidence["candidates"][0]["primary_max_drawdown"] = -0.15
        evidence["candidates"][0]["benchmark_max_drawdown"] = -0.20
        self.assertTrue(derive_decision(evidence).candidate_evaluations[0].gates["D"])
        evidence["candidates"][0]["primary_max_drawdown"] = -0.150001
        self.assertFalse(derive_decision(evidence).candidate_evaluations[0].gates["D"])

    def test_gate_e_uses_independent_largest_positive_contributor(self) -> None:
        evidence = _evidence()
        contributions = evidence["candidates"][0]["asset_net_contributions"]
        contributions["GLD"] = 0.20
        evidence["candidates"][0]["leave_one_asset_id"] = "GLD"
        evaluation = derive_decision(evidence).candidate_evaluations[0]
        self.assertEqual(evaluation.removed_asset, "GLD")
        self.assertTrue(evaluation.gates["E"])
        evidence["candidates"][0]["leave_one_asset_id"] = "VTI"
        self.assertFalse(derive_decision(evidence).candidate_evaluations[0].gates["E"])
        evidence["candidates"][0]["leave_one_asset_net_annual_geometric_return"] = 0.0
        self.assertFalse(derive_decision(evidence).candidate_evaluations[0].gates["E"])

    def test_gate_f_boundaries_and_float_attack_are_exact_decimal(self) -> None:
        evidence = _evidence()
        contributions = evidence["candidates"][0]["asset_net_contributions"]
        contributions.update({asset: 0.0 for asset in ASSETS})
        contributions["VTI"], contributions["VGK"] = 0.50, 0.50
        self.assertTrue(derive_decision(evidence).candidate_evaluations[0].gates["F"])
        contributions["VTI"], contributions["VGK"] = 0.500001, 0.499999
        self.assertFalse(derive_decision(evidence).candidate_evaluations[0].gates["F"])
        contributions["VTI"], contributions["VGK"] = 1.0, 0.9999999999999999
        self.assertFalse(derive_decision(evidence).candidate_evaluations[0].gates["F"])

    def test_gate_g_subperiod_floor_is_inclusive_and_requires_two_positive(self) -> None:
        evidence = _evidence()
        returns = evidence["candidates"][0]["subperiod_net_annual_geometric_return"]
        returns.update({"2007-2009": 0.01, "2010-2012": -0.05, "2013-2015": 0.02})
        self.assertTrue(derive_decision(evidence).candidate_evaluations[0].gates["G"])
        returns["2010-2012"] = -0.050001
        self.assertFalse(derive_decision(evidence).candidate_evaluations[0].gates["G"])

    def test_gate_h_uses_critical_blockers(self) -> None:
        evidence = _evidence()
        evidence["candidates"][0]["critical_blockers"] = ["timestamp"]
        self.assertFalse(derive_decision(evidence).candidate_evaluations[0].gates["H"])

    def test_no_candidate_passes_has_only_stop_outcome(self) -> None:
        evidence = _evidence()
        for candidate in evidence["candidates"]:
            candidate["critical_blockers"] = ["synthetic blocker"]
        decision = derive_decision(evidence)
        self.assertEqual(decision.outcome, STOP_NO_CANDIDATE)
        self.assertIsNone(decision.selected_candidate)
        self.assertEqual(decision.eligible_candidates, ())
        self.assertEqual(decision.ranking_order, ())

    def test_primary_ranking_uses_worst_subperiod_sharpe(self) -> None:
        evidence = _evidence()
        _scores(evidence, (0.30, 0.20, 0.10), (0.30, 0.20, 0.10))
        decision = derive_decision(evidence)
        self.assertEqual(decision.ranking_order, CANDIDATE_ORDER)
        self.assertEqual(decision.selected_candidate, "CORE1_DC60")

    def test_near_tie_is_inclusive_at_031_vs_029_and_outside_is_not(self) -> None:
        evidence = _evidence()
        _scores(evidence, (0.31, 0.29, 0.10), (0.30, 0.10, 0.20))
        self.assertEqual(derive_decision(evidence).selected_candidate, "CORE1_DC120")
        evidence = _evidence()
        _scores(evidence, (0.31, 0.289999, 0.10), (0.05, 0.30, 0.90))
        self.assertEqual(derive_decision(evidence).selected_candidate, "CORE1_DC60")

    def test_near_tie_uses_lower_turnover(self) -> None:
        evidence = _evidence()
        _scores(evidence, (0.31, 0.30, 0.10), (0.20, 0.05, 0.90))
        self.assertEqual(derive_decision(evidence).selected_candidate, "CORE1_DC120")

    def test_exact_final_turnover_tie_is_inclusive_and_just_outside_is_not(self) -> None:
        evidence = _evidence()
        _scores(evidence, (0.31, 0.30, 0.10), (0.100000000001, 0.10, 0.90))
        self.assertEqual(derive_decision(evidence).selected_candidate, "CORE1_DC60")
        evidence = _evidence()
        _scores(evidence, (0.31, 0.30, 0.10), (0.1000000000011, 0.10, 0.90))
        self.assertEqual(derive_decision(evidence).selected_candidate, "CORE1_DC120")

    def test_missing_unknown_supplied_decision_and_candidate_order_fail_closed(self) -> None:
        evidence = _evidence()
        del evidence["candidates"][0]["trials"]
        with self.assertRaises(EvidenceValidationError):
            derive_decision(evidence)
        evidence = _evidence()
        evidence["candidates"][0]["gates"] = {letter: True for letter in "ABCDEFGH"}
        with self.assertRaises(EvidenceValidationError):
            derive_decision(evidence)
        evidence = _evidence()
        evidence["outcome"] = SELECTED_CANDIDATE
        with self.assertRaises(EvidenceValidationError):
            derive_decision(evidence)
        evidence = _evidence()
        evidence["candidates"][0], evidence["candidates"][1] = evidence["candidates"][1], evidence["candidates"][0]
        with self.assertRaises(EvidenceValidationError):
            derive_decision(evidence)

    def test_nan_infinity_huge_int_and_aggregate_overflow_fail(self) -> None:
        for field, value in (("primary_net_annual_sharpe", math.nan), ("stress_net_annual_sharpe", math.inf)):
            evidence = _evidence()
            evidence["candidates"][0][field] = value
            if field == "primary_net_annual_sharpe":
                evidence["candidates"][0]["trials"][0]["annual_sharpe"] = value
            with self.assertRaises(EvidenceValidationError):
                derive_decision(evidence)
        evidence = _evidence()
        evidence["candidates"][0]["primary_net_annual_sharpe"] = 10**10000
        evidence["candidates"][0]["trials"][0]["annual_sharpe"] = 10**10000
        with self.assertRaises(EvidenceValidationError):
            derive_decision(evidence)
        evidence = _evidence()
        contributions = evidence["candidates"][0]["asset_net_contributions"]
        contributions["VTI"], contributions["VGK"] = 1.79e308, 1.79e308
        with self.assertRaises(EvidenceValidationError):
            derive_decision(evidence)

    def test_bool_bad_ranges_and_all_trial_fields_fail_closed(self) -> None:
        for field, value in (("one_way_turnover", True), ("primary_net_annual_geometric_return", -1.000001), ("primary_max_drawdown", 0.01), ("best_episode_concentration", 1.01)):
            evidence = _evidence()
            evidence["candidates"][0][field] = value
            with self.assertRaises(EvidenceValidationError):
                derive_decision(evidence)
        evidence = _evidence()
        evidence["candidates"][0]["trials"][0]["psr_vs_zero"] = True
        with self.assertRaises(EvidenceValidationError):
            derive_decision(evidence)
        evidence = _evidence()
        evidence["candidates"][0]["leave_one_asset_id"] = True
        with self.assertRaises(EvidenceValidationError):
            derive_decision(evidence)
        evidence = _evidence()
        del evidence["candidates"][0]["trials"][2]["dsr_probability"]
        with self.assertRaises(EvidenceValidationError):
            derive_decision(evidence)

    def test_forged_decision_and_e1_masquerade_are_rejected_exactly(self) -> None:
        evidence = _evidence()
        expected = derive_decision(evidence).as_mapping()
        for field, value in (("outcome", STOP_NO_CANDIDATE), ("future_provenance_bound_empirical_ceiling", "E1")):
            forged = copy.deepcopy(expected)
            forged[field] = value
            with self.assertRaises(ForgedDecisionError):
                derive_decision(evidence, reported_decision=forged)
        forged = copy.deepcopy(expected)
        forged["candidate_gates"]["CORE1_DC60"]["A"] = False
        with self.assertRaises(ForgedDecisionError):
            derive_decision(evidence, reported_decision=forged)
        missing = copy.deepcopy(expected)
        del missing["outcome"]
        with self.assertRaises(EvidenceValidationError):
            derive_decision(evidence, reported_decision=missing)
        unknown = copy.deepcopy(expected)
        unknown["reported_pass"] = True
        with self.assertRaises(EvidenceValidationError):
            derive_decision(evidence, reported_decision=unknown)


if __name__ == "__main__":
    unittest.main()
