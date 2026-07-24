from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root
from lib.provenance import file_sha256, git_commit


CONTRACT = PROJECT_ROOT / "experiments" / "l_2_falsification_execution_contract_v2.json"
V2 = "84a7bb45070b54846a709573506c8213a3bc62d28cfa25f4982415d40d94e1f3"
V3 = "507bf40a0a6ac1690ff0c6898bf20dc79c3b8dee78d18251c5835e45d7b60afc"
WINDOW = {"start": "2007-02-05", "end": "2015-12-31"}
SEALED = {"status": "sealed_not_accessed", "prices_opened": False, "returns_opened": False, "signals_opened": False, "positions_opened": False, "regimes_opened": False, "benchmarks_opened": False, "PnL_opened": False}
COMMON = {"schema_version", "order_id", "hypothesis_id", "evidence_tier", "edge_claim", "report_mode", "execution_status", "producing_git_commit", "contract_sha256", "v2_sha256", "v3_sha256", "falsification_window", "validation_return_seal", "market_returns_read", "decision", "blockers", "claim_limits"}
TRIAL_IDS = {"primary_32_64_126_252", "leave_out_32", "leave_out_64", "leave_out_126", "leave_out_252"}
REQUIRED_EXECUTION_BLOCKERS = {"validation_remains_sealed", "edge_claim_none", "validation_not_opened"}
CLAIM_LIMITS = [
    "E1 falsification-stage evidence only; no edge, E2, deployment, paper-trading, or real-money claim.",
    "The paired daily active-return inference is limited to the locked falsification window and does not open validation.",
    "A not_falsified_not_validated result is not validation-grade evidence or permission to deploy.",
]


def validate_report(path: Path) -> dict[str, Any]:
    try:
        report = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"report_unreadable:{exc.__class__.__name__}"])
    if not isinstance(report, dict):
        return _result(path, ["report_must_be_object"])
    blockers: list[str] = []
    expected = {
        "schema_version": "lily_l2_falsification_report_v2",
        "order_id": "B6.1",
        "hypothesis_id": "L-2",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "v2_sha256": V2,
        "v3_sha256": V3,
        "falsification_window": WINDOW,
        "validation_return_seal": SEALED,
        "claim_limits": CLAIM_LIMITS,
    }
    for field, value in expected.items():
        if report.get(field) != value:
            blockers.append(f"field_mismatch:{field}")
    if report.get("contract_sha256") != file_sha256(CONTRACT):
        blockers.append("contract_sha256_not_active_contract")
    actual_commit = git_commit(PROJECT_ROOT)
    if actual_commit == "unavailable" or report.get("producing_git_commit") != actual_commit:
        blockers.append("producing_git_commit_not_current_checkout")
    mode = report.get("report_mode")
    if mode == "synthetic_fixture":
        _validate_synthetic(report, blockers)
    elif mode == "preflight_failure":
        _validate_preflight_failure(report, blockers)
    elif mode == "falsification_execution":
        _validate_execution(report, blockers)
    else:
        blockers.append("invalid_report_mode")
    return _result(path, blockers)


def _validate_synthetic(report: dict[str, Any], blockers: list[str]) -> None:
    _validate_field_set(report, COMMON, blockers, "synthetic")
    if report.get("execution_status") != "not_run" or report.get("decision") != "not_run":
        blockers.append("synthetic_status_or_decision_invalid")
    if report.get("market_returns_read") is not False:
        blockers.append("synthetic_must_not_read_market_returns")
    if report.get("blockers") != ["synthetic_fixture_no_market_data", "validation_remains_sealed", "edge_claim_none"]:
        blockers.append("synthetic_blockers_mismatch")


def _validate_preflight_failure(report: dict[str, Any], blockers: list[str]) -> None:
    allowed = COMMON | {"preflight_attestation"}
    _validate_field_set(report, allowed, blockers, "preflight")
    if report.get("execution_status") != "scope_restricted" or report.get("decision") != "scope_restricted":
        blockers.append("preflight_status_or_decision_invalid")
    if report.get("market_returns_read") is not False:
        blockers.append("preflight_must_not_read_market_returns")
    attestation = report.get("preflight_attestation")
    required = {"container_metadata_read", "return_rows_parsed", "validation_return_opened", "reason"}
    if not isinstance(attestation, dict) or set(attestation) != required:
        blockers.append("preflight_attestation_shape_invalid")
    elif attestation.get("container_metadata_read") is not True or attestation.get("return_rows_parsed") is not False or attestation.get("validation_return_opened") is not False or attestation.get("reason") not in {"container_metadata_missing", "container_max_date_after_falsification_window", "activation_gate_invalid"}:
        blockers.append("preflight_attestation_values_invalid")
    _validate_execution_blockers(report, blockers)


def _validate_execution(report: dict[str, Any], blockers: list[str]) -> None:
    allowed = COMMON | {"falsification_container", "observation_counts", "primary_statistics", "costs_and_turnover", "trial_inventory", "decision_matrix_trace", "v3_timing_attestation", "mechanism_autopsy"}
    _validate_field_set(report, allowed, blockers, "execution")
    status = report.get("execution_status")
    if status not in {"falsified", "not_falsified_not_validated"} or report.get("decision") != status:
        blockers.append("execution_status_or_decision_invalid")
    if report.get("market_returns_read") is not True:
        blockers.append("execution_requires_market_return_read")
    _validate_container(report.get("falsification_container"), blockers)
    counts = _validate_counts(report.get("observation_counts"), blockers)
    statistics = _validate_statistics(report.get("primary_statistics"), blockers)
    _validate_costs(report.get("costs_and_turnover"), blockers)
    _validate_trials(report.get("trial_inventory"), blockers)
    _validate_timing(report.get("v3_timing_attestation"), blockers)
    _validate_execution_blockers(report, blockers)
    _validate_decision_trace(report.get("decision_matrix_trace"), status, counts, statistics, blockers)
    if status == "falsified":
        _validate_autopsy(report.get("mechanism_autopsy"), blockers)
    elif "mechanism_autopsy" in report:
        blockers.append("autopsy_only_allowed_for_falsified")


def _validate_field_set(report: dict[str, Any], allowed: set[str], blockers: list[str], label: str) -> None:
    unknown = sorted(set(report) - allowed)
    missing = sorted(COMMON - set(report))
    if unknown:
        blockers.append(f"{label}_unexpected_fields:{','.join(unknown)}")
    if missing:
        blockers.append(f"{label}_missing_common_fields:{','.join(missing)}")


def _validate_container(value: Any, blockers: list[str]) -> None:
    expected = {"container_id", "container_sha256", "max_date"}
    if not isinstance(value, dict) or set(value) != expected:
        blockers.append("falsification_container_shape_invalid")
        return
    if not isinstance(value["container_id"], str) or not value["container_id"] or not _is_hash(value["container_sha256"]):
        blockers.append("falsification_container_identity_invalid")
    try:
        if date.fromisoformat(str(value["max_date"])) > date(2015, 12, 31):
            blockers.append("falsification_container_opens_validation")
    except ValueError:
        blockers.append("falsification_container_max_date_invalid")


def _validate_counts(value: Any, blockers: list[str]) -> dict[str, float] | None:
    expected = {"calendar_observations", "paired_date_count", "time_effective_observations", "joint_independent_bet_equivalents"}
    if not isinstance(value, dict) or set(value) != expected:
        blockers.append("observation_counts_shape_invalid")
        return None
    if not isinstance(value["calendar_observations"], int) or value["calendar_observations"] <= 0 or not isinstance(value["paired_date_count"], int) or value["paired_date_count"] <= 0:
        blockers.append("calendar_or_paired_observation_count_invalid")
    numeric = {key: _finite_number(value[key]) for key in ("time_effective_observations", "joint_independent_bet_equivalents")}
    if any(item is None or item <= 0 for item in numeric.values()):
        blockers.append("effective_observation_or_ibe_invalid")
        return None
    return {key: float(item) for key, item in numeric.items() if item is not None}


def _validate_statistics(value: Any, blockers: list[str]) -> dict[str, float] | None:
    expected = {"paired_daily_active_return_sha256", "annualized_active_sharpe", "per_period_active_sharpe", "annual_to_daily_conversion", "minimum_useful_per_period_sharpe", "primary_margin_psr", "dsr", "dsr_trial_count"}
    if not isinstance(value, dict) or set(value) != expected:
        blockers.append("primary_statistics_shape_invalid")
        return None
    if not _is_hash(value["paired_daily_active_return_sha256"]) or value["annual_to_daily_conversion"] != "annualized_sharpe / sqrt(252)" or value["dsr_trial_count"] != 5:
        blockers.append("primary_statistics_provenance_or_conversion_invalid")
    numbers = {key: _finite_number(value[key]) for key in ("annualized_active_sharpe", "per_period_active_sharpe", "minimum_useful_per_period_sharpe", "primary_margin_psr", "dsr")}
    if any(item is None for item in numbers.values()):
        blockers.append("primary_statistics_numeric_invalid")
        return None
    annual = float(numbers["annualized_active_sharpe"])
    per_period = float(numbers["per_period_active_sharpe"])
    if not math.isclose(per_period, annual / math.sqrt(252), rel_tol=0.0, abs_tol=1e-12):
        blockers.append("annual_to_daily_sharpe_mismatch")
    if not math.isclose(float(numbers["minimum_useful_per_period_sharpe"]), 0.1 / math.sqrt(252), rel_tol=0.0, abs_tol=1e-12):
        blockers.append("minimum_useful_sharpe_mismatch")
    if not 0 <= float(numbers["primary_margin_psr"]) <= 1 or not 0 <= float(numbers["dsr"]) <= 1:
        blockers.append("probability_metric_out_of_range")
    return {key: float(item) for key, item in numbers.items() if item is not None}


def _validate_costs(value: Any, blockers: list[str]) -> None:
    expected = {"cost_model_attested", "candidate_turnover_bps", "comparator_turnover_bps", "candidate_cost_bps", "comparator_cost_bps"}
    if not isinstance(value, dict) or set(value) != expected:
        blockers.append("costs_and_turnover_shape_invalid")
        return
    if value["cost_model_attested"] is not True or any(_finite_number(value[key]) is None or _finite_number(value[key]) < 0 for key in expected - {"cost_model_attested"}):
        blockers.append("costs_and_turnover_values_invalid")


def _validate_trials(value: Any, blockers: list[str]) -> None:
    expected = {"trial_id", "paired_daily_active_return_sha256", "per_period_sharpe"}
    if not isinstance(value, list) or len(value) != 5:
        blockers.append("trial_inventory_count_invalid")
        return
    ids: set[str] = set()
    for row in value:
        if not isinstance(row, dict) or set(row) != expected or not isinstance(row.get("trial_id"), str) or not _is_hash(row.get("paired_daily_active_return_sha256")) or _finite_number(row.get("per_period_sharpe")) is None:
            blockers.append("trial_inventory_row_invalid")
            continue
        ids.add(row["trial_id"])
    if ids != TRIAL_IDS:
        blockers.append("trial_inventory_incomplete_or_mismatched")


def _validate_timing(value: Any, blockers: list[str]) -> None:
    expected = {"shared_decision_index_r_t_minus_k", "no_future_returns", "next_actual_nyse_close_t_plus_1", "identical_post_execution_windows"}
    if not isinstance(value, dict) or set(value) != expected or any(value.get(key) is not True for key in expected):
        blockers.append("v3_timing_attestation_invalid")


def _validate_execution_blockers(report: dict[str, Any], blockers: list[str]) -> None:
    declared = report.get("blockers")
    if not isinstance(declared, list) or any(not isinstance(item, str) for item in declared) or len(declared) != len(set(declared)):
        blockers.append("blockers_shape_invalid")
    elif not REQUIRED_EXECUTION_BLOCKERS.issubset(declared):
        blockers.append("required_execution_claim_limits_missing")


def _validate_decision_trace(value: Any, status: Any, counts: dict[str, float] | None, statistics: dict[str, float] | None, blockers: list[str]) -> None:
    expected = {"outcome", "minimum_required_joint_independent_bet_equivalents", "annualized_active_sharpe_threshold", "primary_margin_psr_max_for_falsification"}
    if not isinstance(value, dict) or set(value) != expected:
        blockers.append("decision_matrix_trace_shape_invalid")
        return
    if value.get("outcome") != status or value.get("minimum_required_joint_independent_bet_equivalents") != 54048 or value.get("annualized_active_sharpe_threshold") != 0.1 or value.get("primary_margin_psr_max_for_falsification") != 0.05:
        blockers.append("decision_matrix_trace_mismatch")
    if counts is None or statistics is None:
        return
    falsified = counts["joint_independent_bet_equivalents"] >= 54048 and statistics["annualized_active_sharpe"] < 0.1 and statistics["primary_margin_psr"] <= 0.05
    if (status == "falsified") != falsified:
        blockers.append("decision_does_not_follow_locked_matrix")


def _validate_autopsy(value: Any, blockers: list[str]) -> None:
    expected = {"horizon_diversification", "signal_transform", "lag", "noise", "cost"}
    if not isinstance(value, dict) or set(value) != expected or any(not isinstance(value[key], str) or not value[key].strip() for key in expected):
        blockers.append("mechanism_autopsy_incomplete")


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "report_path": relative_to_root(path, PROJECT_ROOT)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate_report(args.report)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
