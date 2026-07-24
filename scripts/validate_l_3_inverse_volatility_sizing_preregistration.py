"""Fail-closed validator for the unexecuted L-3 Checkpoint A contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WIKI_ROOT = PROJECT_ROOT.parents[2] / "LLM Wiki" / "LLM Wiki"
GATE = PROJECT_ROOT / "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json"
L1 = PROJECT_ROOT / "experiments/l_1_baseline_preregistration.json"
MANIFEST = PROJECT_ROOT / "experiments/locked_gates.jsonl"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_jsonl, relative_to_root
from lib.statistics import paired_mean_minimum_observations


L1_HASH = "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29"
WIKI_SOURCES = [
    ("wiki/concepts/inverse-volatility-weighting.md", "c59b512d3df9499a738b1ee256d388376f04edee1c59727f2f79ddcc905e7f72"),
    ("wiki/concepts/position-sizing.md", "6d24c4ffc6770590baaeb90402af4e413040ff6856b0585773657da85dc68343"),
    ("wiki/concepts/minimum-track-record-length.md", "ca65225740673bd363be7461b8022281da08ae32e6ff42f8887f1072eb51ad81"),
]
LAGS = [0.25, 0.125, 0.0625, 0.03125, 0.015625]
REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "order_id",
    "checkpoint",
    "hypothesis_id",
    "status",
    "evidence_ceiling",
    "edge_claim",
    "owner_authorization",
    "source_binding",
    "research_question",
    "candidate_and_comparator",
    "primary_metric",
    "decision_thresholds",
    "realized_confirmation",
    "statistics",
    "static_capacity",
    "regime_rule",
    "side_effect_aggregation",
    "decision_matrix",
    "validation_seal",
    "b7_1",
    "hard_stops",
}
EXPECTED_DECISION_MATRIX = {
    "underfunded": "If the source-derived maximum weekly slots are below the validator-recomputed 49-observation falsify requirement, remain E0 scope_restricted and do not read data.",
    "falsification": "Only a separately authorized, funded B7.1 falsification execution may falsify the composite L-3 claim after a mechanism autopsy: either the one-sided 95% upper confidence bound of the ex-ante mean paired delta is below 0.05, or a funded and evaluable primary concentration result has any locked side-effect limit breached. A non-evaluable side effect is scope_restricted, never falsified.",
    "not_falsified_not_validated": "Only a separately authorized, funded B7.1 falsification execution may use this E1 label when the composite falsification rule is not met. Any underfunding, non-evaluable primary metric or side effect, failed side-effect limit without the funded composite-falsification condition, or missing regime funding remains scope_restricted rather than validated.",
    "validation_candidate": "Requires separately funded untouched validation, both validator-recomputed validation plans with their maximum binding requirement, a one-sided 95% lower confidence bound of the mean paired delta above 0.05, the realized confirmation threshold, every locked side-effect limit evaluable and met, and every claimed regime's independent funding. Never pool falsification and validation observations.",
    "regime_funded": "A claimed regime is funded only when its own effective weekly paired observations meet its actual-recomputed paired MinTRL_falsify.",
    "regime_underfunded": "A regime below its own requirement is descriptive at most and cannot contribute to an inferential 2-of-3 statement.",
}


def validate_gate(path: Path = GATE, *, manifest_path: Path = MANIFEST) -> dict[str, Any]:
    gate, blockers = _load_gate(path)
    if gate is None:
        return _result(path, blockers)

    _require_exact_keys(gate, REQUIRED_TOP_LEVEL_FIELDS, "top_level", blockers)
    _require_values(
        gate,
        {
            "schema_version": "lily_l3_inverse_volatility_sizing_preregistration_v1",
            "order_id": "B7",
            "checkpoint": "A_contract_machinery_only",
            "hypothesis_id": "L-3",
            "status": "locked_before_execution",
            "evidence_ceiling": "E0",
            "edge_claim": "none",
            "owner_authorization": "B7 Checkpoint A planning and contract machinery only; B7.1, data access, and execution are not authorized.",
        },
        "field_mismatch",
        blockers,
    )
    _validate_sources(gate, manifest_path, blockers)
    _validate_inherited_contract(gate, blockers)
    _validate_metric_and_realized_contract(gate, blockers)
    _validate_statistics_and_capacity(gate, blockers)
    _validate_decisions_and_hard_stops(gate, blockers)
    return _result(path, blockers)


def _load_gate(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, ["gate_unreadable:FileNotFoundError"]
    except json.JSONDecodeError:
        return None, ["gate_unreadable:JSONDecodeError"]
    except OSError:
        return None, ["gate_unreadable:OSError"]
    if not isinstance(payload, dict):
        return None, ["gate_not_object"]
    return payload, []


def _validate_sources(gate: dict[str, Any], manifest_path: Path, blockers: list[str]) -> None:
    binding = gate.get("source_binding")
    if not isinstance(binding, dict):
        blockers.append("source_binding_invalid")
        return
    _require_exact_keys(binding, {"l1_preregistration", "l1_manifest_row", "wiki_sources"}, "source_binding", blockers)
    expected_l1 = {"path": "experiments/l_1_baseline_preregistration.json", "sha256": L1_HASH}
    if binding.get("l1_preregistration") != expected_l1 or _sha256(L1) != L1_HASH:
        blockers.append("l1_source_path_or_hash_mismatch")
    expected_manifest_row = {
        "gate_id": "l_1_baseline_v1",
        "artifact_path": "experiments/l_1_baseline_preregistration.json",
        "artifact_sha256": L1_HASH,
        "validator_path": "scripts/validate_l_1_baseline_preregistration.py",
        "validator_sha256": "c568f5db8236e253e63056ed2797ead9259397d293c478e7f0abf53bfda70232",
    }
    if binding.get("l1_manifest_row") != expected_manifest_row:
        blockers.append("l1_manifest_row_declaration_mismatch")
    _validate_l1_manifest_identity(manifest_path, expected_manifest_row, blockers)
    expected_wiki = [{"path": path, "sha256": digest} for path, digest in WIKI_SOURCES]
    if binding.get("wiki_sources") != expected_wiki:
        blockers.append("wiki_source_declarations_mismatch")
    for wiki_path, digest in WIKI_SOURCES:
        if _sha256(WIKI_ROOT / wiki_path) != digest:
            blockers.append(f"wiki_source_path_or_hash_mismatch:{wiki_path}")


def _validate_l1_manifest_identity(
    manifest_path: Path,
    expected_row: dict[str, str],
    blockers: list[str],
) -> None:
    try:
        rows = load_jsonl(manifest_path)
    except FileNotFoundError:
        blockers.append("l1_manifest_row_unreadable:FileNotFoundError")
        return
    except (ValueError, json.JSONDecodeError):
        blockers.append("l1_manifest_row_unreadable:invalid_jsonl")
        return
    row = [item for item in rows if isinstance(item, dict) and item.get("gate_id") == "l_1_baseline_v1"]
    if len(row) != 1:
        blockers.append("l1_manifest_row_identity_mismatch")
        return
    if any(row[0].get(key) != value for key, value in expected_row.items()):
        blockers.append("l1_manifest_row_identity_mismatch")


def _validate_inherited_contract(gate: dict[str, Any], blockers: list[str]) -> None:
    candidate = gate.get("candidate_and_comparator")
    expected = {
        "candidate_raw_score": "q[i,t] / max(annualized_volatility[i,t], 0.05)",
        "comparator_raw_score": "q[i,t]",
        "l2_signal": "forbidden",
        "asset_multiplier": "forbidden",
        "shared_universe": "L1 research_signed eight ETFs only",
        "shared_signal": "L1 60_day_directional_count_raw only",
        "shared_rebalance": "weekly only",
        "shared_execution": "next actual NYSE close only",
        "shared_constraints": "L1 90% gross normalization, 10% minimum cash, 25% absolute asset cap, 60-session EWMA PSD-clipped covariance, and target-volatility scale-down-only",
    }
    if candidate != expected:
        blockers.append("candidate_comparator_or_inherited_contract_mismatch")
    try:
        l1 = json.loads(L1.read_text(encoding="utf-8"))
    except FileNotFoundError:
        blockers.append("l1_source_unreadable:FileNotFoundError")
        return
    except json.JSONDecodeError:
        blockers.append("l1_source_unreadable:JSONDecodeError")
        return
    instruments = l1.get("universes", {}).get("research_signed", {}).get("instruments")
    tickers = [item.get("ticker") for item in instruments] if isinstance(instruments, list) else []
    if tickers != ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]:
        blockers.append("l1_universe_mismatch")
    if l1.get("signal", {}).get("name") != "60_day_directional_count_raw":
        blockers.append("l1_signal_mismatch")
    if l1.get("timing_and_calendar", {}).get("execution_timestamp") != "official close of the next NYSE trading session after the signal timestamp":
        blockers.append("l1_execution_timing_mismatch")
    if l1.get("portfolio_construction", {}).get("rebalance") != "weekly":
        blockers.append("l1_rebalance_mismatch")


def _validate_metric_and_realized_contract(gate: dict[str, Any], blockers: list[str]) -> None:
    metric = gate.get("primary_metric")
    required_metric_keys = {
        "unit", "measurement_point", "component_risk_formula", "absolute_share_formula", "hhi_formula", "paired_delta_formula", "active_set_rule", "cash_rule", "all_zero_score_rule", "undefined_denominator_rule", "negative_contribution_rule", "threshold_rationale",
    }
    _require_exact_keys(metric, required_metric_keys, "primary_metric", blockers)
    if not isinstance(metric, dict):
        return
    required_text = {
        "unit": "one weekly paired portfolio observation; never an asset, sleeve, daily, or trade observation",
        "measurement_point": "after each branch independently applies the same inherited constraints and normalization",
        "component_risk_formula": "c[i,t] = w[i,t] * (Sigma[t] * w[t])[i]",
        "absolute_share_formula": "a[i,t] = abs(c[i,t]) / sum_j(abs(c[j,t]))",
        "hhi_formula": "HHI[t] = sum_i(a[i,t]^2)",
        "paired_delta_formula": "delta[t] = HHI_comparator[t] - HHI_inverse_volatility[t]",
        "negative_contribution_rule": "Take the absolute value of every signed component contribution before normalization.",
        "all_zero_score_rule": "If an inherited branch score is all zero, retain that branch's inherited cash weights. That branch creates no HHI pair rather than a zero-concentration observation.",
        "undefined_denominator_rule": "If either branch has nonzero positions and sum_j(abs(c[j,t])) is zero, non-finite, or undefined, the paired metric is non-evaluable: retain inherited weights, record the blocker, do not alter weights, and do not silently drop or complete-case filter the date.",
        "active_set_rule": "For each branch and weekly date, the active set is exactly the fixed L1 eight-ETF order restricted to components with nonzero abs(c[i,t]) after all constraints; zero components remain zero terms and are never substituted or dropped from the paired date.",
        "cash_rule": "Cash is excluded from the eight-asset HHI and reported separately; it is not an asset contribution.",
    }
    _require_values(metric, required_text, "primary_metric_mismatch", blockers)
    expected_rationale = "Synthetic contribution vectors only: comparator (0.50, 0.50, 0, 0, 0, 0, 0, 0) has HHI 0.50; candidate (0.60, 0.2707106781, 0.1292893219, 0, 0, 0, 0, 0) has HHI 0.45. The 0.05 threshold is this concrete portfolio-level redistribution, not a generic one-asset movement or a Lily-return result."
    if metric.get("threshold_rationale") != expected_rationale:
        blockers.append("threshold_rationale_mismatch")
    thresholds = {
        "mean_hhi_delta_minimum": 0.05,
        "mean_largest_absolute_component_share_delta_minimum": 0.05,
        "realized_mean_hhi_delta_minimum": 0.05,
        "turnover_and_cost_relative_increase_maximum": 0.2,
        "cap_cash_scale_down_frequency_increase_maximum_percentage_points": 10.0,
    }
    if gate.get("decision_thresholds") != thresholds:
        blockers.append("decision_thresholds_mismatch")
    realized = gate.get("realized_confirmation")
    required_realized = {
        "weight_lock", "return_rows", "minimum_complete_rows", "missingness_rule", "realized_covariance", "normalization", "overlap_and_dependence", "threshold",
    }
    _require_exact_keys(realized, required_realized, "realized_confirmation", blockers)
    if not isinstance(realized, dict):
        return
    expected_realized = {
        "weight_lock": "Fix each branch's own post-constraint execution-close weights at the next actual NYSE close t+1; never rebalance, rescale, or substitute weights inside the confirmation window.",
        "return_rows": "Use exactly the 20 actual NYSE-session return rows labelled t+1 through t+20, inclusive, for every fixed L1 research_signed asset.",
        "minimum_complete_rows": 20,
        "missingness_rule": "Any missing required asset return row, missing execution-close weight, non-finite covariance, or undefined nonzero-position denominator makes the entire paired date non-evaluable; retain weights and record the blocker without a silent row or asset drop.",
        "realized_covariance": "Compute each branch's component risk from its fixed weights and the covariance of those same 20 actual-session return rows.",
        "normalization": "Use the identical signed absolute component-risk HHI formula and date-specific active-set rule from primary_metric.",
        "overlap_and_dependence": "Twenty-session confirmation windows overlap across weekly observations. Recompute dependence from the resulting weekly paired deltas only; never multiply observations by eight or by twenty.",
        "threshold": "The mean realized comparator-minus-inverse-volatility HHI delta must be at least 0.05.",
    }
    if realized != expected_realized:
        blockers.append("realized_confirmation_contract_mismatch")


def _validate_statistics_and_capacity(gate: dict[str, Any], blockers: list[str]) -> None:
    statistics = gate.get("statistics")
    required_statistics = {
        "observation_unit", "planning_standard_deviation_delta", "one_sided_alpha", "power", "planning_autocorrelations_lags_1_to_5", "asymptotic_autocorrelation_inflation_formula", "asymptotic_autocorrelation_inflation", "paired_mean_power_formula", "falsify_plan", "validation_plans", "actual_recalculation",
    }
    _require_exact_keys(statistics, required_statistics, "statistics", blockers)
    if not isinstance(statistics, dict):
        return
    if statistics.get("observation_unit") != "weekly paired portfolio HHI delta":
        blockers.append("statistics_observation_unit_mismatch")
    if statistics.get("planning_standard_deviation_delta") != 0.1 or statistics.get("one_sided_alpha") != 0.05 or statistics.get("power") != 0.8:
        blockers.append("statistics_variance_alpha_or_power_mismatch")
    if statistics.get("planning_autocorrelations_lags_1_to_5") != LAGS or statistics.get("asymptotic_autocorrelation_inflation") != 1.96875:
        blockers.append("statistics_lags_or_inflation_mismatch")
    if statistics.get("asymptotic_autocorrelation_inflation_formula") != "1 + 2 * sum(lag_1_to_5)" or "ceil(" not in str(statistics.get("paired_mean_power_formula")):
        blockers.append("statistics_formula_mismatch")
    expected_falsify = {"tail": "lower", "null_mean_delta": 0.05, "adverse_alternative_mean_delta": 0.0, "required_weekly_paired_observations": 49}
    expected_validation = {
        "portfolio_zero": {"tail": "upper", "null_mean_delta": 0.0, "expected_alternative_mean_delta": 0.05, "required_weekly_paired_observations": 49},
        "minimum_useful": {"tail": "upper", "null_mean_delta": 0.05, "expected_alternative_mean_delta": 0.1, "required_weekly_paired_observations": 49},
        "binding_required_weekly_paired_observations": 49,
    }
    if statistics.get("falsify_plan") != expected_falsify or statistics.get("validation_plans") != expected_validation:
        blockers.append("statistics_dual_null_or_mintrl_mismatch")
    if statistics.get("actual_recalculation") != "Before either decision, recompute the weekly paired-delta lag-1 through lag-5 autocorrelations, the same asymptotic inflation formula, the falsify requirement, both validation-plan requirements, and their maximum binding validation requirement. Sharpe MinTRL, per-trade counts, assets, daily rows, and return annualization are not inputs.":
        blockers.append("statistics_actual_recalculation_mismatch")
    recomputed_falsify = paired_mean_minimum_observations(alternative_mean=0.0, null_mean=0.05, planning_standard_deviation=0.1, autocorrelations=LAGS, significance=0.05, power=0.8)
    recomputed_validation_zero = paired_mean_minimum_observations(alternative_mean=0.05, null_mean=0.0, planning_standard_deviation=0.1, autocorrelations=LAGS, significance=0.05, power=0.8)
    recomputed_validation_minimum = paired_mean_minimum_observations(alternative_mean=0.1, null_mean=0.05, planning_standard_deviation=0.1, autocorrelations=LAGS, significance=0.05, power=0.8)
    recomputed_validation_binding = max(recomputed_validation_zero or 0, recomputed_validation_minimum or 0)
    if recomputed_falsify != 49 or recomputed_validation_zero != 49 or recomputed_validation_minimum != 49 or recomputed_validation_binding != 49:
        blockers.append("statistics_recomputed_mintrl_mismatch")
    _validate_capacity(gate, recomputed_falsify, recomputed_validation_binding, blockers)


def _validate_capacity(gate: dict[str, Any], mintrl_falsify: int | None, mintrl_validate: int | None, blockers: list[str]) -> None:
    capacity = gate.get("static_capacity")
    required_capacity = {
        "falsification_window", "calendar_day_formula", "calendar_days_inclusive", "weekly_slot_formula", "maximum_weekly_slots_before_actual_session_warmup_or_evaluable_pair_reductions", "portfolio_observations_per_week", "asset_multiplier", "inherited_prior_only_regime_warmup_sessions", "pre_falsification_warmup_window", "maximum_pre_falsification_weekday_slots", "remaining_prior_sessions_to_regime_eligibility", "maximum_sessions_per_calendar_week", "minimum_falsification_week_slots_consumed_for_remaining_warmup", "maximum_regime_eligible_weekly_slots_after_warmup_before_actual_session_or_evaluable_pair_reductions", "planning_capacity_outcome", "validation_pooling",
    }
    _require_exact_keys(capacity, required_capacity, "static_capacity", blockers)
    if not isinstance(capacity, dict):
        return
    try:
        l1 = json.loads(L1.read_text(encoding="utf-8"))
        sample_order = l1["sample_and_unlock_order"]
        window = sample_order["falsification_window"]
        pre_falsification_warmup = sample_order["warmup_and_data_QA"]
        volatility_state = l1["regime_matrix"]["volatility_state"]
    except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError):
        blockers.append("l1_capacity_source_unreadable")
        return
    warmup_match = re.search(r"at least (\d+) prior sessions", str(volatility_state))
    if warmup_match is None:
        blockers.append("l1_regime_warmup_unreadable")
        return
    start, end = date.fromisoformat(window["start"]), date.fromisoformat(window["end"])
    warmup_start = date.fromisoformat(pre_falsification_warmup["start"])
    warmup_end = date.fromisoformat(pre_falsification_warmup["end"])
    days = (end - start).days + 1
    weekly_slots = math.floor((end - start).days / 7) + 1
    warmup_sessions = int(warmup_match.group(1))
    pre_falsification_weekdays = sum(
        date.fromordinal(ordinal).weekday() < 5
        for ordinal in range(warmup_start.toordinal(), warmup_end.toordinal() + 1)
    )
    remaining_sessions = warmup_sessions - pre_falsification_weekdays
    remaining_warmup_weeks = math.ceil(remaining_sessions / 5)
    expected = {
        "falsification_window": {"start": "2007-02-05", "end": "2015-12-31"},
        "calendar_day_formula": "(end - start).days + 1",
        "calendar_days_inclusive": days,
        "weekly_slot_formula": "floor((end - start).days / 7) + 1",
        "maximum_weekly_slots_before_actual_session_warmup_or_evaluable_pair_reductions": weekly_slots,
        "portfolio_observations_per_week": 1,
        "asset_multiplier": 1,
        "inherited_prior_only_regime_warmup_sessions": warmup_sessions,
        "pre_falsification_warmup_window": {"start": "2006-02-03", "end": "2007-02-02"},
        "maximum_pre_falsification_weekday_slots": pre_falsification_weekdays,
        "remaining_prior_sessions_to_regime_eligibility": remaining_sessions,
        "maximum_sessions_per_calendar_week": 5,
        "minimum_falsification_week_slots_consumed_for_remaining_warmup": remaining_warmup_weeks,
        "maximum_regime_eligible_weekly_slots_after_warmup_before_actual_session_or_evaluable_pair_reductions": weekly_slots - remaining_warmup_weeks,
        "planning_capacity_outcome": "funded_for_both_49_observation_plans_but_execution_and_data_remain_sealed",
        "validation_pooling": "forbidden",
    }
    if capacity != expected:
        blockers.append("static_capacity_mismatch")
    if mintrl_falsify is None or mintrl_validate is None or weekly_slots < max(mintrl_falsify, mintrl_validate):
        blockers.append("planning_capacity_outcome_not_supported")


def _validate_decisions_and_hard_stops(gate: dict[str, Any], blockers: list[str]) -> None:
    required_regime = {"classification", "descriptive_coverage", "inferential_funding", "two_of_three_rule"}
    _require_exact_keys(gate.get("regime_rule"), required_regime, "regime_rule", blockers)
    regime = gate.get("regime_rule")
    if not isinstance(regime, dict) or "26 weekly" not in regime.get("descriptive_coverage", "") or "own actual-recomputed paired MinTRL_falsify" not in regime.get("inferential_funding", "") or "two separately funded" not in regime.get("two_of_three_rule", ""):
        blockers.append("regime_funding_contract_mismatch")
    required_side_effects = {"eligible_date_set", "turnover_and_cost", "cap_cash_scale_down"}
    _require_exact_keys(gate.get("side_effect_aggregation"), required_side_effects, "side_effect_aggregation", blockers)
    side_effects = gate.get("side_effect_aggregation")
    expected_side_effects = {
        "eligible_date_set": "Use the identical set of primary-metric-evaluable paired weekly portfolio dates for both branches; a non-evaluable paired date remains a recorded blocker and is not silently deleted.",
        "turnover_and_cost": "For each branch, sum total one-way turnover and all locked costs across the eligible-date set. Relative increase = (candidate aggregate - comparator aggregate) / comparator aggregate. If the comparator aggregate is zero, the relative comparison is non-evaluable and blocks that side-effect decision; it is never replaced with zero, infinity, or a dropped date.",
        "cap_cash_scale_down": "For each branch/date, the indicator is one if any absolute asset cap binds, cash exceeds the inherited 10% minimum, or portfolio target-volatility scaling is below one; otherwise zero. Frequency increase in percentage points = 100 * (candidate indicator sum / paired-date count - comparator indicator sum / paired-date count). A zero paired-date count blocks the comparison.",
    }
    if side_effects != expected_side_effects:
        blockers.append("side_effect_zero_denominator_contract_mismatch")
    required_decisions = set(EXPECTED_DECISION_MATRIX)
    _require_exact_keys(gate.get("decision_matrix"), required_decisions, "decision_matrix", blockers)
    decisions = gate.get("decision_matrix")
    if decisions != EXPECTED_DECISION_MATRIX:
        blockers.append("decision_matrix_mismatch")
    if gate.get("validation_seal") != {"start": "2016-01-04", "end": "2026-06-30", "opened": False, "pooled_with_falsification": False}:
        blockers.append("validation_seal_mismatch")
    b7_1 = gate.get("b7_1")
    required_b7_1 = {"authorized", "data_access_authorized", "execution_authorized", "next_safe_action"}
    _require_exact_keys(b7_1, required_b7_1, "b7_1", blockers)
    if not isinstance(b7_1, dict) or b7_1.get("authorized") is not False or b7_1.get("data_access_authorized") is not False or b7_1.get("execution_authorized") is not False:
        blockers.append("b7_1_hard_stop_mismatch")
    required_stops = {
        "No dataset, market price, market return, signal, position, covariance estimate, regime observation, benchmark, or PnL read or computation.",
        "No validation-window access or falsification/validation pooling.",
        "No B7.1 activity, execution, broker/provider call, credential use, paid action, paper trade, or real-money action.",
        "No L-2 signal, current-capital branch, breadth study, futures path, or asset multiplier.",
        "No daily, per-asset, per-sleeve, per-trade, or twenty-session pseudo-replication.",
        "No threshold weakening, source substitution, locked-history edit, edge claim, E1/E2 promotion, deployment, or real-money claim.",
    }
    if set(gate.get("hard_stops", [])) != required_stops:
        blockers.append("hard_stops_incomplete_or_open")


def _require_exact_keys(value: Any, expected: set[str], label: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        blockers.append(f"{label}_not_object")
        return
    actual = set(value)
    for key in sorted(actual - expected):
        blockers.append(f"unknown_{label}_field:{key}")
    for key in sorted(expected - actual):
        blockers.append(f"missing_{label}_field:{key}")


def _require_values(value: dict[str, Any], expected: dict[str, Any], prefix: str, blockers: list[str]) -> None:
    for key, required in expected.items():
        if value.get(key) != required:
            blockers.append(f"{prefix}:{key}")


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "gate_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=Path, default=GATE)
    args = parser.parse_args()
    result = validate_gate(args.gate)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
