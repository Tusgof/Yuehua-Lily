from __future__ import annotations

import copy
import json
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

from lib.io import load_json, write_json
from scripts.validate_l_3_inverse_volatility_sizing_preregistration import GATE, MANIFEST, validate_gate


Mutation = Callable[[dict[str, Any]], None]


class L3InverseVolatilityPreregistrationTests(unittest.TestCase):
    def test_gate_passes(self) -> None:
        self.assertEqual("pass", validate_gate()["status"])

    def test_rejects_source_declaration_forgery(self) -> None:
        cases: list[tuple[Mutation, str]] = [
            (
                lambda gate: gate["source_binding"]["l1_preregistration"].update(
                    path="experiments/forged_l1.json"
                ),
                "l1_source_path_or_hash_mismatch",
            ),
            (
                lambda gate: gate["source_binding"]["l1_preregistration"].update(
                    sha256="0" * 64
                ),
                "l1_source_path_or_hash_mismatch",
            ),
            (
                lambda gate: gate["source_binding"]["l1_manifest_row"].update(
                    artifact_sha256="0" * 64
                ),
                "l1_manifest_row_declaration_mismatch",
            ),
            (
                lambda gate: gate["source_binding"]["l1_manifest_row"].update(
                    gate_id="forged_gate"
                ),
                "l1_manifest_row_declaration_mismatch",
            ),
            (
                lambda gate: gate["source_binding"]["wiki_sources"][0].update(sha256="0" * 64),
                "wiki_source_declarations_mismatch",
            ),
        ]
        self._assert_mutations_block(cases)

    def test_rejects_forged_l1_manifest_row_in_temporary_manifest(self) -> None:
        gate = load_json(GATE)
        rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines()]
        matching = [row for row in rows if row["gate_id"] == "l_1_baseline_v1"]
        self.assertEqual(1, len(matching))
        matching[0]["validator_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            gate_path = temporary / "l3_gate.json"
            manifest_path = temporary / "locked_gates.jsonl"
            write_json(gate_path, gate)
            manifest_path.write_text(
                "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
                encoding="utf-8",
            )
            result = validate_gate(gate_path, manifest_path=manifest_path)
        self.assertIn("l1_manifest_row_identity_mismatch", result["blockers"])

    def test_rejects_universe_signal_comparator_timing_and_window_changes(self) -> None:
        cases: list[tuple[Mutation, str]] = [
            (
                lambda gate: gate["candidate_and_comparator"].update(
                    shared_universe="L1 implementable_long_or_cash ETFs"
                ),
                "candidate_comparator_or_inherited_contract_mismatch",
            ),
            (
                lambda gate: gate["candidate_and_comparator"].update(l2_signal="allowed"),
                "candidate_comparator_or_inherited_contract_mismatch",
            ),
            (
                lambda gate: gate["candidate_and_comparator"].update(comparator_raw_score="q[i,t] / max(annualized_volatility[i,t], 0.05)"),
                "candidate_comparator_or_inherited_contract_mismatch",
            ),
            (
                lambda gate: gate["candidate_and_comparator"].update(shared_execution="same close"),
                "candidate_comparator_or_inherited_contract_mismatch",
            ),
            (
                lambda gate: gate["static_capacity"]["falsification_window"].update(end="2016-01-01"),
                "static_capacity_mismatch",
            ),
            (
                lambda gate: gate["static_capacity"]["pre_falsification_warmup_window"].update(
                    end="2007-02-01"
                ),
                "static_capacity_mismatch",
            ),
        ]
        self._assert_mutations_block(cases)

    def test_rejects_capacity_statistics_and_outcome_tampering(self) -> None:
        cases: list[tuple[Mutation, str]] = [
            (
                lambda gate: gate["static_capacity"].update(
                    maximum_weekly_slots_before_actual_session_warmup_or_evaluable_pair_reductions=464
                ),
                "static_capacity_mismatch",
            ),
            (
                lambda gate: gate["static_capacity"].update(
                    maximum_pre_falsification_weekday_slots=260
                ),
                "static_capacity_mismatch",
            ),
            (
                lambda gate: gate["static_capacity"].update(
                    remaining_prior_sessions_to_regime_eligibility=494
                ),
                "static_capacity_mismatch",
            ),
            (
                lambda gate: gate["static_capacity"].update(
                    minimum_falsification_week_slots_consumed_for_remaining_warmup=98
                ),
                "static_capacity_mismatch",
            ),
            (
                lambda gate: gate["static_capacity"].update(
                    maximum_regime_eligible_weekly_slots_after_warmup_before_actual_session_or_evaluable_pair_reductions=365
                ),
                "static_capacity_mismatch",
            ),
            (lambda gate: gate["static_capacity"].update(asset_multiplier=8), "static_capacity_mismatch"),
            (
                lambda gate: gate["decision_thresholds"].update(mean_hhi_delta_minimum=0.04),
                "decision_thresholds_mismatch",
            ),
            (
                lambda gate: gate["statistics"].update(planning_standard_deviation_delta=0.08),
                "statistics_variance_alpha_or_power_mismatch",
            ),
            (
                lambda gate: gate["statistics"].update(one_sided_alpha=0.1),
                "statistics_variance_alpha_or_power_mismatch",
            ),
            (
                lambda gate: gate["statistics"].update(power=0.9),
                "statistics_variance_alpha_or_power_mismatch",
            ),
            (
                lambda gate: gate["statistics"]["falsify_plan"].update(
                    required_weekly_paired_observations=48
                ),
                "statistics_dual_null_or_mintrl_mismatch",
            ),
            (
                lambda gate: gate["statistics"]["validation_plans"]["minimum_useful"].update(
                    expected_alternative_mean_delta=0.05
                ),
                "statistics_dual_null_or_mintrl_mismatch",
            ),
            (
                lambda gate: gate["statistics"]["validation_plans"].update(
                    binding_required_weekly_paired_observations=48
                ),
                "statistics_dual_null_or_mintrl_mismatch",
            ),
            (
                lambda gate: gate["static_capacity"].update(
                    planning_capacity_outcome="underfunded_scope_restricted"
                ),
                "static_capacity_mismatch",
            ),
        ]
        self._assert_mutations_block(cases)

    def test_rejects_realized_denominator_and_regime_pseudo_funding_changes(self) -> None:
        cases: list[tuple[Mutation, str]] = [
            (lambda gate: gate["realized_confirmation"].pop("return_rows"), "missing_realized_confirmation_field:return_rows"),
            (lambda gate: gate["primary_metric"].pop("undefined_denominator_rule"), "missing_primary_metric_field:undefined_denominator_rule"),
            (
                lambda gate: gate["primary_metric"].update(
                    undefined_denominator_rule="drop the date"
                ),
                "primary_metric_mismatch:undefined_denominator_rule",
            ),
            (
                lambda gate: gate["regime_rule"].update(
                    inferential_funding="26 weekly observations funds each regime"
                ),
                "regime_funding_contract_mismatch",
            ),
            (
                lambda gate: gate["decision_matrix"].update(
                    regime_funded="All three regimes may pool observations."
                ),
                "decision_matrix_mismatch",
            ),
            (
                lambda gate: gate["decision_matrix"].update(
                    falsification="A side-effect breach is only descriptive."
                ),
                "decision_matrix_mismatch",
            ),
        ]
        self._assert_mutations_block(cases)

    def test_rejects_validation_execution_unknown_fields_and_missing_hard_stops(self) -> None:
        cases: list[tuple[Mutation, str]] = [
            (
                lambda gate: gate["validation_seal"].update(opened=True),
                "validation_seal_mismatch",
            ),
            (
                lambda gate: gate["b7_1"].update(data_access_authorized=True),
                "b7_1_hard_stop_mismatch",
            ),
            (
                lambda gate: gate["b7_1"].update(execution_authorized=True),
                "b7_1_hard_stop_mismatch",
            ),
            (
                lambda gate: gate["decision_matrix"].update(unapproved="open validation"),
                "unknown_decision_matrix_field:unapproved",
            ),
            (lambda gate: gate.update(unapproved="open data"), "unknown_top_level_field:unapproved"),
            (lambda gate: gate.update(hard_stops=[]), "hard_stops_incomplete_or_open"),
        ]
        self._assert_mutations_block(cases)

    def _assert_mutations_block(self, cases: list[tuple[Mutation, str]]) -> None:
        for mutate, blocker in cases:
            with self.subTest(blocker=blocker):
                payload = copy.deepcopy(load_json(GATE))
                mutate(payload)
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "l3_gate.json"
                    write_json(path, payload)
                    result = validate_gate(path)
                self.assertIn(blocker, result["blockers"])


if __name__ == "__main__":
    unittest.main()
