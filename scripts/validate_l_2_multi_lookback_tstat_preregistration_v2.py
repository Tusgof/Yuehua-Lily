from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root
from lib.statistics import minimum_track_record_length_falsify, minimum_track_record_length_validate

DEFAULT_PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_2_multi_lookback_tstat_preregistration_v2.json"
L1_PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_1_baseline_preregistration.json"
V1_PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_2_multi_lookback_tstat_preregistration.json"
L1_SHA256 = "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29"
V1_SHA256 = "1e7c1a4c5743ddb21bce4ad96b8c5a5a8092e4e04af4642ebcd1fa66c674786f"
HORIZONS = [32, 64, 126, 252]
PLANNING_LAGS = [0.10, 0.05, 0.025, 0.0125, 0.00625]
ANNUALIZATION_SESSIONS = 252
MINIMUM_USEFUL_ANNUAL_SHARPE = 0.10
EXPECTED_ANNUAL_SHARPE = 0.20


def validate_preregistration(path: Path = DEFAULT_PREREGISTRATION) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        payload = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"preregistration_unreadable:{exc.__class__.__name__}"])
    if not isinstance(payload, dict):
        return _result(path, ["preregistration_must_be_object"])

    for field, expected in {
        "schema_version": "lily_l2_multi_lookback_tstat_preregistration_v2",
        "hypothesis_id": "L-2",
        "status": "locked_before_execution",
        "supersedes_gate_id": "l_2_multi_lookback_tstat_v1",
        "evidence_ceiling_without_adversarial_review": "E1",
        "edge_claim_before_execution": "none",
    }.items():
        if payload.get(field) != expected:
            blockers.append(f"invalid_locked_field:{field}")

    superseded = payload.get("superseded_artifact", {})
    if superseded.get("path") != "experiments/l_2_multi_lookback_tstat_preregistration.json":
        blockers.append("superseded_artifact_path_changed")
    if superseded.get("sha256") != V1_SHA256 or _sha256(V1_PREREGISTRATION) != V1_SHA256:
        blockers.append("superseded_artifact_hash_mismatch")

    pre = payload.get("pre_measurement_state")
    if not isinstance(pre, dict) or not pre:
        blockers.append("pre_measurement_state_missing")
    elif any(value is not False for value in pre.values()):
        blockers.append("pre_measurement_state_must_be_all_false")

    inheritance = payload.get("baseline_inheritance", {})
    expected_sections = ["universes", "timing_and_calendar", "portfolio_construction", "costs", "return_accounting", "benchmarks", "sample_and_unlock_order", "data_integrity"]
    if inheritance.get("source_path") != "experiments/l_1_baseline_preregistration.json":
        blockers.append("baseline_source_path_changed")
    if inheritance.get("source_sha256") != L1_SHA256 or _sha256(L1_PREREGISTRATION) != L1_SHA256:
        blockers.append("baseline_source_hash_mismatch")
    if inheritance.get("shared_sections") != expected_sections:
        blockers.append("shared_protocol_sections_changed")

    blockers.extend(_validate_candidate_and_comparators(payload))
    blockers.extend(_validate_utility_and_inference(payload))
    blockers.extend(_validate_dsr(payload))
    blockers.extend(_validate_mintrl(payload.get("dual_MinTRL", {})))
    blockers.extend(_validate_decision_matrix(payload))

    seal = payload.get("validation_seal", {})
    if seal.get("window") != {"start": "2016-01-04", "end": "2026-06-30"} or seal.get("status") != "sealed_not_accessed":
        blockers.append("validation_seal_changed")
    if seal.get("forbidden_fields") != ["prices", "returns", "signals", "positions", "regimes", "benchmarks", "PnL"]:
        blockers.append("validation_forbidden_fields_changed")

    hard_stops = " ".join(payload.get("hard_stops", []))
    for phrase in ("backtest execution", "2016-01-04 through 2026-06-30", "broker or provider request", "edge, E2"):
        if phrase not in hard_stops:
            blockers.append(f"hard_stop_missing:{phrase}")
    return _result(path, blockers)


def _validate_candidate_and_comparators(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    signal = payload.get("candidate_signal", {})
    if signal.get("name") != "equal_weight_multi_lookback_t_stat" or signal.get("lookback_sessions_in_order") != HORIZONS:
        blockers.append("candidate_horizons_or_name_changed")
    if signal.get("component_standard_deviation_ddof") != 1 or signal.get("additional_horizons_forbidden") is not True:
        blockers.append("candidate_signal_convention_changed")
    if "same-close execution is forbidden" not in str(signal.get("same_signal_availability_rule", "")):
        blockers.append("candidate_same_close_guard_missing")
    comparators = payload.get("comparators", {})
    primary = comparators.get("primary", {})
    if primary.get("id") != "matched_32_64_126_252_directional_count" or primary.get("lookback_sessions_in_order") != HORIZONS:
        blockers.append("primary_comparator_not_matched_horizon")
    if primary.get("name") != "equal_weight_multi_lookback_directional_count" or "q_count_h" not in str(primary.get("component_formula", "")):
        blockers.append("primary_comparator_formula_changed")
    secondary = comparators.get("secondary", {})
    if secondary.get("id") != "L1_60_day_directional_count_raw" or secondary.get("source_path") != "experiments/l_1_baseline_preregistration.json":
        blockers.append("secondary_L1_reference_changed")
    if "Secondary descriptive reference only" not in str(secondary.get("role", "")):
        blockers.append("secondary_L1_role_changed")
    return blockers


def _validate_utility_and_inference(payload: dict[str, Any]) -> list[str]:
    utility = payload.get("primary_utility_and_inference", {})
    expected_daily = MINIMUM_USEFUL_ANNUAL_SHARPE / math.sqrt(ANNUALIZATION_SESSIONS)
    blockers: list[str] = []
    if utility.get("annualization_sessions") != ANNUALIZATION_SESSIONS or utility.get("minimum_useful_improvement_annual_sharpe") != MINIMUM_USEFUL_ANNUAL_SHARPE:
        blockers.append("primary_utility_annualization_changed")
    if not math.isclose(utility.get("minimum_useful_improvement_per_period_sharpe", float("nan")), expected_daily, rel_tol=0.0, abs_tol=1e-15):
        blockers.append("minimum_useful_per_period_conversion_mismatch")
    if "candidate net portfolio return minus primary matched-horizon comparator" not in str(utility.get("observation_unit", "")):
        blockers.append("primary_active_return_series_changed")
    if utility.get("primary_utility") != "annualized Sharpe of the paired daily net active-return series":
        blockers.append("primary_utility_definition_changed")
    if "before every MinTRL, PSR, or DSR calculation" not in str(utility.get("annual_to_per_period_conversion", "")):
        blockers.append("per_period_inference_rule_missing")
    if "paired daily net active-return series" not in str(utility.get("primary_margin_PSR_requirement", "")):
        blockers.append("primary_PSR_input_changed")
    return blockers


def _validate_dsr(payload: dict[str, Any]) -> list[str]:
    search = payload.get("search_accounting_and_DSR", {})
    blockers: list[str] = []
    if "paired same-date daily net active-return series" not in str(search.get("DSR_input_series", "")):
        blockers.append("DSR_input_series_changed")
    trials = search.get("locked_trial_inventory", [])
    expected_ids = ["primary_32_64_126_252", "leave_out_32", "leave_out_64", "leave_out_126", "leave_out_252"]
    if [row.get("trial_id") for row in trials] != expected_ids:
        blockers.append("DSR_trial_inventory_changed")
    elif any(row.get("candidate_horizons") != row.get("comparator_horizons") for row in trials):
        blockers.append("DSR_trial_comparators_not_matched")
    if search.get("effective_trials_for_DSR") != "maximum of 5 and the effective-rank estimate from the complete locked trial active-return correlation matrix":
        blockers.append("DSR_effective_trial_rule_changed")
    if "minimum_useful_improvement_per_period_sharpe plus expected_maximum_sharpe" not in str(search.get("search_aware_null_per_period", "")):
        blockers.append("DSR_search_aware_null_changed")
    if "primary paired daily active-return series" not in str(search.get("DSR_requirement", "")) or "at least 0.95" not in str(search.get("DSR_requirement", "")):
        blockers.append("DSR_requirement_changed")
    return blockers


def _validate_mintrl(config: Any) -> list[str]:
    if not isinstance(config, dict):
        return ["dual_MinTRL_missing"]
    blockers: list[str] = []
    if config.get("annualization_sessions") != ANNUALIZATION_SESSIONS or config.get("planning_autocorrelations_lags_1_to_5") != PLANNING_LAGS:
        blockers.append("MinTRL_planning_convention_changed")
    common = dict(skewness=0.0, raw_kurtosis=6.0, autocorrelations=PLANNING_LAGS, significance=0.05, power=0.80)
    daily_minimum = MINIMUM_USEFUL_ANNUAL_SHARPE / math.sqrt(ANNUALIZATION_SESSIONS)
    daily_expected = EXPECTED_ANNUAL_SHARPE / math.sqrt(ANNUALIZATION_SESSIONS)
    falsify = config.get("falsify", {})
    expected_falsify = minimum_track_record_length_falsify(claimed_minimum_sharpe=daily_minimum, adverse_true_sharpe=-daily_minimum, **common)
    if not _close(falsify.get("claimed_minimum_per_period_sharpe"), daily_minimum) or not _close(falsify.get("adverse_true_per_period_sharpe"), -daily_minimum):
        blockers.append("MinTRL_falsify_per_period_conversion_mismatch")
    if falsify.get("required_joint_independent_bet_equivalents") != expected_falsify:
        blockers.append("MinTRL_falsify_recalculation_mismatch")
    validate = config.get("validate", {})
    expected = {
        "no_improvement": minimum_track_record_length_validate(expected_sharpe=daily_expected, null_sharpe=0.0, **common),
        "minimum_useful_improvement": minimum_track_record_length_validate(expected_sharpe=daily_expected, null_sharpe=daily_minimum, **common),
    }
    plans = validate.get("null_plans", [])
    if [row.get("id") for row in plans] != list(expected):
        return blockers + ["MinTRL_validate_null_inventory_changed"]
    for row in plans:
        expected_null = 0.0 if row["id"] == "no_improvement" else daily_minimum
        if not _close(row.get("expected_per_period_sharpe"), daily_expected) or not _close(row.get("null_per_period_sharpe"), expected_null):
            blockers.append(f"MinTRL_validate_per_period_conversion_mismatch:{row['id']}")
        if row.get("required_joint_independent_bet_equivalents") != expected[row["id"]]:
            blockers.append(f"MinTRL_validate_recalculation_mismatch:{row['id']}")
    if validate.get("binding_required_joint_independent_bet_equivalents") != max(expected.values()):
        blockers.append("MinTRL_validate_binding_mismatch")
    return blockers


def _validate_decision_matrix(payload: dict[str, Any]) -> list[str]:
    matrix = payload.get("falsification_decision_matrix", [])
    expected = ["underfunded", "falsified", "not_falsified_not_validated", "validation_grade_candidate"]
    if [row.get("outcome") for row in matrix] != expected:
        return ["falsification_decision_matrix_changed"]
    combined = " ".join(str(row.get("conditions", "")) for row in matrix)
    return [] if all(phrase in combined for phrase in ("54048", "below 0.10", "at most 0.05", "216218", "DSR")) else ["falsification_decision_matrix_incomplete"]


def _close(value: Any, expected: float) -> bool:
    return isinstance(value, (int, float)) and math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-15)


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {"status": "fail" if blockers else "pass", "path": relative_to_root(path, PROJECT_ROOT), "blockers": blockers}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=DEFAULT_PREREGISTRATION)
    args = parser.parse_args()
    result = validate_preregistration(args.path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
