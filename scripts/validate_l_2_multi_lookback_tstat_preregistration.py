from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root
from lib.statistics import minimum_track_record_length_falsify, minimum_track_record_length_validate

DEFAULT_PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_2_multi_lookback_tstat_preregistration.json"
L1_PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_1_baseline_preregistration.json"
L1_SHA256 = "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29"
WIKI_SOURCES = {
    "wiki/concepts/multi-lookback-trend-following.md": "e6791d5ecf781a06b4c96befa33cdb9d3866f49caa8b2bd91efa1d0ce8f4d4d7",
    "wiki/concepts/minimum-track-record-length.md": "ca65225740673bd363be7461b8022281da08ae32e6ff42f8887f1072eb51ad81",
    "wiki/concepts/deflated-sharpe-ratio.md": "90663b67e49dcec90bd641e801f9464e593ff8fe9091b2d70e9f4645381af556",
    "wiki/concepts/probabilistic-sharpe-ratio.md": "a644495d207403711a55d815abb0722018bba23d428d3d904dd6c4b5a8cef6a5",
    "wiki/concepts/directional-count-trend-signal.md": "0eb4e3cbd6eceab838d5fc88c0500bedfbe345389eb3646fb19200b6b97b7490",
}
PLANNING_LAGS = [0.10, 0.05, 0.025, 0.0125, 0.00625]


def validate_preregistration(path: Path = DEFAULT_PREREGISTRATION) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        payload = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"preregistration_unreadable:{exc.__class__.__name__}"])
    if not isinstance(payload, dict):
        return _result(path, ["preregistration_must_be_object"])

    for field, expected in {
        "schema_version": "lily_l2_multi_lookback_tstat_preregistration_v1",
        "hypothesis_id": "L-2",
        "status": "locked_before_execution",
        "evidence_ceiling_without_adversarial_review": "E1",
        "edge_claim_before_execution": "none",
    }.items():
        if payload.get(field) != expected:
            blockers.append(f"invalid_locked_field:{field}")

    pre = payload.get("pre_measurement_state")
    if not isinstance(pre, dict) or not pre:
        blockers.append("pre_measurement_state_missing")
    elif any(value is not False for value in pre.values()):
        blockers.append("pre_measurement_state_must_be_all_false")

    inheritance = payload.get("baseline_inheritance", {})
    if inheritance.get("source_path") != "experiments/l_1_baseline_preregistration.json":
        blockers.append("baseline_source_path_changed")
    if inheritance.get("source_sha256") != L1_SHA256 or _sha256(L1_PREREGISTRATION) != L1_SHA256:
        blockers.append("baseline_source_hash_mismatch")
    expected_sections = ["universes", "timing_and_calendar", "portfolio_construction", "costs", "return_accounting", "benchmarks", "sample_and_unlock_order", "data_integrity"]
    if inheritance.get("shared_sections") != expected_sections:
        blockers.append("shared_protocol_sections_changed")
    if "Only the signal differs" not in str(inheritance.get("comparison_rule", "")):
        blockers.append("matched_protocol_rule_missing")

    signal = payload.get("candidate_signal", {})
    if signal.get("name") != "equal_weight_multi_lookback_t_stat":
        blockers.append("candidate_signal_name_changed")
    if signal.get("lookback_sessions_in_order") != [32, 64, 126, 252]:
        blockers.append("candidate_horizons_changed")
    if signal.get("component_standard_deviation_ddof") != 1 or signal.get("additional_horizons_forbidden") is not True:
        blockers.append("candidate_signal_convention_changed")
    for field in ("component_formula", "combined_signal_formula", "same_signal_availability_rule"):
        if not signal.get(field):
            blockers.append(f"candidate_signal_missing:{field}")
    if "same-close execution is forbidden" not in str(signal.get("same_signal_availability_rule", "")):
        blockers.append("candidate_same_close_guard_missing")

    utility = payload.get("comparison_and_utility", {})
    expected_utility = {
        "primary_branch": "research_signed",
        "baseline_signal": "locked L-1 60_day_directional_count_raw",
        "minimum_useful_improvement_annual_sharpe": 0.1,
    }
    for field, expected in expected_utility.items():
        if utility.get(field) != expected:
            blockers.append(f"utility_rule_changed:{field}")
    if "identical eligible dates" not in str(utility.get("primary_utility", "")):
        blockers.append("paired_primary_utility_missing")
    if "Only primary_32_64_126_252" not in str(utility.get("selection_rule", "")):
        blockers.append("primary_selection_rule_missing")

    search = payload.get("search_accounting_and_DSR", {})
    trials = search.get("locked_trial_inventory", [])
    if [row.get("trial_id") for row in trials] != ["primary_32_64_126_252", "leave_out_32", "leave_out_64", "leave_out_126", "leave_out_252"]:
        blockers.append("DSR_trial_inventory_changed")
    if search.get("effective_trials_for_DSR") != "maximum of 5 and the effective-rank estimate from the complete locked trial-return correlation matrix":
        blockers.append("DSR_effective_trial_rule_changed")
    if "at least 0.95" not in str(search.get("DSR_requirement", "")):
        blockers.append("DSR_threshold_missing")

    blockers.extend(_validate_mintrl(payload.get("dual_MinTRL", {})))

    seal = payload.get("validation_seal", {})
    if seal.get("window") != {"start": "2016-01-04", "end": "2026-06-30"} or seal.get("status") != "sealed_not_accessed":
        blockers.append("validation_seal_changed")
    if seal.get("forbidden_fields") != ["prices", "returns", "signals", "positions", "regimes", "benchmarks", "PnL"]:
        blockers.append("validation_forbidden_fields_changed")

    sources = {row.get("path"): row.get("sha256") for row in payload.get("wiki_sources", []) if isinstance(row, dict)}
    if sources != WIKI_SOURCES:
        blockers.append("wiki_sources_or_hashes_changed")
    hard_stops = " ".join(payload.get("hard_stops", []))
    for phrase in ("backtest execution", "2016-01-04 through 2026-06-30", "broker or provider request", "edge, E2"):
        if phrase not in hard_stops:
            blockers.append(f"hard_stop_missing:{phrase}")
    return _result(path, blockers)


def _validate_mintrl(config: Any) -> list[str]:
    if not isinstance(config, dict):
        return ["dual_MinTRL_missing"]
    blockers: list[str] = []
    if config.get("planning_autocorrelations_lags_1_to_5") != PLANNING_LAGS:
        blockers.append("MinTRL_planning_lags_changed")
    common = dict(skewness=0.0, raw_kurtosis=6.0, autocorrelations=PLANNING_LAGS, significance=0.05, power=0.80)
    falsify = config.get("falsify", {})
    expected_falsify = minimum_track_record_length_falsify(claimed_minimum_sharpe=0.1, adverse_true_sharpe=-0.1, **common)
    if falsify.get("required_joint_independent_bet_equivalents") != expected_falsify:
        blockers.append("MinTRL_falsify_recalculation_mismatch")
    validate = config.get("validate", {})
    expected = {
        "no_improvement": minimum_track_record_length_validate(expected_sharpe=0.2, null_sharpe=0.0, **common),
        "minimum_useful_improvement": minimum_track_record_length_validate(expected_sharpe=0.2, null_sharpe=0.1, **common),
    }
    plans = validate.get("null_plans", [])
    if [row.get("id") for row in plans] != list(expected):
        return blockers + ["MinTRL_validate_null_inventory_changed"]
    for row in plans:
        if row.get("required_joint_independent_bet_equivalents") != expected[row["id"]]:
            blockers.append(f"MinTRL_validate_recalculation_mismatch:{row['id']}")
    if validate.get("binding_required_joint_independent_bet_equivalents") != max(expected.values()):
        blockers.append("MinTRL_validate_binding_mismatch")
    return blockers


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
