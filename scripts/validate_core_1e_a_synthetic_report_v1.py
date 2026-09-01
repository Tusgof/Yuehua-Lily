"""Closed-world semantic validation for the CORE-1E-A synthetic report."""

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

from lib.core_1e_a_synthetic_engine import (
    ATTRIBUTION_COMPONENTS,
    ATTRIBUTION_TOLERANCE,
    REPORT_SCHEMA_VERSION,
    build_report,
)
from lib.io import load_json, relative_to_root
from lib.provenance import file_sha256, git_commit


CONTRACT = PROJECT_ROOT / "experiments" / "core_1e_a_phase_a_execution_contract_v1.json"
FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "core1e_a" / "synthetic_market_v1.json"
ENGINE = PROJECT_ROOT / "lib" / "core_1e_a_synthetic_engine.py"
DEFAULT_REPORT = PROJECT_ROOT / "tests" / "fixtures" / "core1e_a" / "synthetic_report_v1.json"

TOP_LEVEL = {
    "schema_version",
    "report_type",
    "outcome",
    "evidence_tier",
    "edge_claim",
    "contract_sha256",
    "fixture",
    "windows",
    "timing_attestation",
    "calculation_attestation",
    "trial_inventory",
    "trial_statistics",
    "candidates",
    "benchmark",
    "selection",
    "access_counts",
    "validation_seal",
    "provenance",
}
METRIC_KEYS = {
    "calendar_count",
    "annual_arithmetic_return",
    "annual_geometric_return",
    "annualized_volatility",
    "annualized_sharpe",
    "maximum_drawdown",
    "one_way_turnover",
    "annualized_one_way_turnover",
    "trade_count",
    "average_exposure",
    "minimum_exposure",
    "maximum_exposure",
    "psr",
    "dsr",
    "autocorrelation_adjusted_sharpe_variance",
    "autocorrelation_lags",
    "hac_newey_west",
    "independent_bet_equivalents",
    "daily_sharpe_for_inference",
    "skewness_population",
    "raw_kurtosis_population",
}
ASSET_KEYS = {"VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_keys(value: Any, expected: set[str], label: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        blockers.append(f"{label}_must_be_object")
        return
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        if missing:
            blockers.append(f"{label}_missing:{','.join(missing)}")
        if unknown:
            blockers.append(f"{label}_unknown:{','.join(unknown)}")


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _finite_numbers(value: Any, label: str, blockers: list[str]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)) and not math.isfinite(value):
        blockers.append(f"nonfinite_number:{label}")
    elif isinstance(value, dict):
        for key, child in value.items():
            _finite_numbers(child, f"{label}.{key}", blockers)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _finite_numbers(child, f"{label}[{index}]", blockers)


def _shape_blockers(report: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    _check_keys(report, TOP_LEVEL, "report", blockers)
    _check_keys(report.get("fixture"), {"path", "sha256", "fixture_id"}, "fixture", blockers)
    windows = _mapping(report.get("windows"))
    _check_keys(windows, {"warmup_qa", "development", "validation"}, "windows", blockers)
    _check_keys(_mapping(windows.get("warmup_qa")), {"start", "end", "performance_claim"}, "warmup", blockers)
    _check_keys(_mapping(windows.get("development")), {"start", "end"}, "development", blockers)
    _check_keys(_mapping(windows.get("validation")), {"start", "end", "status", "accessed"}, "validation_window", blockers)
    _check_keys(report.get("timing_attestation"), {"weekly_decisions", "all_execution_dates_after_decisions", "same_close_execution", "manufactured_sessions", "lookahead_detected"}, "timing", blockers)
    _check_keys(report.get("calculation_attestation"), {"fixed_sleeve_weight", "no_trade_band", "expense_accrual_basis", "primary_execution_cost_multiplier", "two_x_execution_cost_multiplier", "two_x_expense_multiplier"}, "calculation", blockers)
    _check_keys(report.get("trial_inventory"), {"count", "candidate_ids", "effective_rank_convention"}, "trial_inventory", blockers)
    _check_keys(report.get("access_counts"), {"real_dataset_access", "real_container_access", "real_return_decode", "validation_access", "provider_calls", "credential_reads", "broker_actions", "paid_actions"}, "access_counts", blockers)
    _check_keys(report.get("validation_seal"), {"status", "accessed"}, "validation_seal", blockers)
    _check_keys(report.get("provenance"), {"producing_commit", "engine_sha256", "source_kind"}, "provenance", blockers)
    trial_statistics = report.get("trial_statistics", [])
    if not isinstance(trial_statistics, list):
        trial_statistics = []
    for index, trial in enumerate(trial_statistics):
        _check_keys(trial, {"candidate_id", "annualized_sharpe", "dsr", "effective_trial_count"}, f"trial_{index}", blockers)
    candidates = report.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    for index, candidate in enumerate(candidates):
        label = f"candidate_{index}"
        _check_keys(candidate, {"id", "metrics", "costs", "asset_contributions", "attribution", "largest_positive_contribution_share", "positive_contribution_hhi", "best_episode_concentration", "leave_one_out", "subperiods", "regime_diagnostics", "critical_blockers", "gates", "all_gates_pass"}, label, blockers)
        candidate_map = _mapping(candidate)
        metrics = _mapping(candidate_map.get("metrics"))
        _check_keys(metrics, {"gross", "primary_net", "two_x_execution_cost_net"}, f"{label}_paths", blockers)
        for path in ("gross", "primary_net", "two_x_execution_cost_net"):
            path_metrics = _mapping(metrics.get(path))
            _check_keys(path_metrics, METRIC_KEYS, f"{label}_{path}", blockers)
            _check_keys(_mapping(path_metrics.get("autocorrelation_lags")), {"lags", "values"}, f"{label}_{path}_autocorrelation_lags", blockers)
            _check_keys(_mapping(path_metrics.get("hac_newey_west")), {"lags", "variance_of_mean", "t_statistic"}, f"{label}_{path}_hac_newey_west", blockers)
            _check_keys(_mapping(path_metrics.get("independent_bet_equivalents")), {"effective_time_count", "cross_section_count", "joint_count", "cross_section_eigenvalues"}, f"{label}_{path}_independent_bet_equivalents", blockers)
        _check_keys(candidate_map.get("costs"), {"commission", "spread_slippage", "sell_surcharge", "execution_cost_primary", "execution_cost_two_x", "etf_expense_accrual", "primary_total_cost_drag", "two_x_total_cost_drag"}, f"{label}_costs", blockers)
        _check_keys(candidate_map.get("asset_contributions"), ASSET_KEYS, f"{label}_asset_contributions", blockers)
        attribution = _mapping(candidate_map.get("attribution"))
        _check_keys(attribution, {"units", "tolerance", "daily", "full_window"}, f"{label}_attribution", blockers)
        daily = attribution.get("daily", [])
        if not isinstance(daily, list):
            daily = []
        for daily_index, daily_row in enumerate(daily):
            daily_label = f"{label}_attribution_daily_{daily_index}"
            _check_keys(daily_row, {"date", "primary_net_return", "asset_components", "asset_total"}, daily_label, blockers)
            daily_assets = _mapping(daily_row.get("asset_components"))
            _check_keys(daily_assets, ASSET_KEYS, f"{daily_label}_assets", blockers)
            for symbol in ASSET_KEYS:
                _check_keys(_mapping(daily_assets.get(symbol)), set(ATTRIBUTION_COMPONENTS), f"{daily_label}_{symbol}", blockers)
        full_window = _mapping(attribution.get("full_window"))
        _check_keys(full_window, {"asset_components", "primary_net_return_sum", "asset_total"}, f"{label}_attribution_full_window", blockers)
        full_assets = _mapping(full_window.get("asset_components"))
        _check_keys(full_assets, ASSET_KEYS, f"{label}_attribution_full_window_assets", blockers)
        for symbol in ASSET_KEYS:
            _check_keys(_mapping(full_assets.get(symbol)), set(ATTRIBUTION_COMPONENTS), f"{label}_attribution_full_window_{symbol}", blockers)
        if candidate_map.get("leave_one_out") is not None:
            _check_keys(candidate_map.get("leave_one_out"), {"removed_asset", "annual_geometric_return"}, f"{label}_leave_one_out", blockers)
        subperiod_map = _mapping(candidate_map.get("subperiods"))
        _check_keys(subperiod_map, {"2007_2009", "2010_2012", "2013_2015"}, f"{label}_subperiods", blockers)
        for period in ("2007_2009", "2010_2012", "2013_2015"):
            _check_keys(subperiod_map.get(period), {"observations", "annual_geometric_return", "annualized_sharpe"}, f"{label}_{period}", blockers)
        regimes = _mapping(candidate_map.get("regime_diagnostics"))
        _check_keys(regimes, {"gfc", "prior_only_global_state_whipsaw"}, f"{label}_regimes", blockers)
        _check_keys(_mapping(regimes.get("gfc")), {"status", "funded", "claim"}, f"{label}_gfc", blockers)
        _check_keys(_mapping(regimes.get("prior_only_global_state_whipsaw")), {"status", "lookahead_free", "claim"}, f"{label}_prior_only_regime", blockers)
        _check_keys(candidate_map.get("gates"), set("ABCDEFGH"), f"{label}_gates", blockers)
    benchmark = _mapping(report.get("benchmark"))
    _check_keys(benchmark, {"id", "metrics", "costs"}, "benchmark", blockers)
    benchmark_metrics = _mapping(benchmark.get("metrics"))
    _check_keys(benchmark_metrics, {"gross", "primary_net", "two_x_execution_cost_net"}, "benchmark_paths", blockers)
    for path in ("gross", "primary_net", "two_x_execution_cost_net"):
        path_metrics = _mapping(benchmark_metrics.get(path))
        _check_keys(path_metrics, METRIC_KEYS, f"benchmark_{path}", blockers)
        _check_keys(_mapping(path_metrics.get("autocorrelation_lags")), {"lags", "values"}, f"benchmark_{path}_autocorrelation_lags", blockers)
        _check_keys(_mapping(path_metrics.get("hac_newey_west")), {"lags", "variance_of_mean", "t_statistic"}, f"benchmark_{path}_hac_newey_west", blockers)
        _check_keys(_mapping(path_metrics.get("independent_bet_equivalents")), {"effective_time_count", "cross_section_count", "joint_count", "cross_section_eigenvalues"}, f"benchmark_{path}_independent_bet_equivalents", blockers)
    _check_keys(benchmark.get("costs"), {"commission", "spread_slippage", "sell_surcharge", "execution_cost_primary", "execution_cost_two_x", "etf_expense_accrual", "primary_total_cost_drag", "two_x_total_cost_drag"}, "benchmark_costs", blockers)
    selection = _mapping(report.get("selection"))
    _check_keys(selection, {"outcome", "winner", "eligible_candidates", "discarded_candidates", "ranking", "stop_rule", "tie_break"}, "selection", blockers)
    ranking = selection.get("ranking", [])
    if not isinstance(ranking, list):
        ranking = []
    for index, item in enumerate(ranking):
        _check_keys(item, {"candidate_id", "eligible", "worst_subperiod_annualized_sharpe", "one_way_turnover"}, f"selection_ranking_{index}", blockers)
    return sorted(set(blockers))


def _attribution_blockers(candidate: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    attribution = candidate.get("attribution")
    if not isinstance(attribution, dict) or attribution.get("tolerance") != ATTRIBUTION_TOLERANCE:
        return ["attribution_tolerance_changed"]
    tolerance = attribution["tolerance"]
    daily = attribution.get("daily")
    full_window = attribution.get("full_window")
    if not isinstance(daily, list) or not isinstance(full_window, dict):
        return ["attribution_reconciliation_not_evaluable"]
    daily_primary_sum = 0.0
    def number(value: Any) -> float:
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else math.nan

    for index, row in enumerate(daily):
        assets = row.get("asset_components") if isinstance(row, dict) else None
        if not isinstance(assets, dict):
            continue
        component_sum = 0.0
        for symbol in ASSET_KEYS:
            components = assets.get(symbol)
            if not isinstance(components, dict):
                continue
            component_total = sum(number(components.get(key, 0.0)) for key in ATTRIBUTION_COMPONENTS[:-1])
            if not math.isclose(component_total, number(components.get("primary_net")), abs_tol=tolerance, rel_tol=0.0):
                blockers.append(f"attribution_daily_component_mismatch:{index}:{symbol}")
            component_sum += number(components.get("primary_net"))
        if isinstance(row.get("primary_net_return"), (int, float)) and not isinstance(row.get("primary_net_return"), bool):
            daily_primary_sum += float(row["primary_net_return"])
            if not math.isclose(component_sum, number(row["primary_net_return"]), abs_tol=tolerance, rel_tol=0.0):
                blockers.append(f"attribution_daily_return_mismatch:{index}")
        if not math.isclose(component_sum, number(row.get("asset_total")), abs_tol=tolerance, rel_tol=0.0):
            blockers.append(f"attribution_daily_total_mismatch:{index}")
    full_assets = full_window.get("asset_components")
    if not isinstance(full_assets, dict):
        return sorted(set(blockers + ["attribution_full_window_not_evaluable"]))
    full_primary_sum = 0.0
    for symbol in ASSET_KEYS:
        components = full_assets.get(symbol)
        if not isinstance(components, dict):
            continue
        component_total = sum(number(components.get(key, 0.0)) for key in ATTRIBUTION_COMPONENTS[:-1])
        if not math.isclose(component_total, number(components.get("primary_net")), abs_tol=tolerance, rel_tol=0.0):
            blockers.append(f"attribution_full_component_mismatch:{symbol}")
        full_primary_sum += number(components.get("primary_net"))
        candidate_assets = _mapping(candidate.get("asset_contributions"))
        if not math.isclose(number(components.get("primary_net")), number(candidate_assets.get(symbol)), abs_tol=tolerance, rel_tol=0.0):
            blockers.append(f"attribution_asset_contribution_mismatch:{symbol}")
    if not math.isclose(full_primary_sum, number(full_window.get("asset_total")), abs_tol=tolerance, rel_tol=0.0):
        blockers.append("attribution_full_total_mismatch")
    if not math.isclose(full_primary_sum, number(full_window.get("primary_net_return_sum")), abs_tol=tolerance, rel_tol=0.0):
        blockers.append("attribution_full_return_mismatch")
    if not math.isclose(full_primary_sum, daily_primary_sum, abs_tol=tolerance, rel_tol=0.0):
        blockers.append("attribution_daily_full_window_mismatch")
    return sorted(set(blockers))


def validate_report(
    report_path: Path | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Validate a report against a freshly recomputed synthetic result."""

    contract_path = project_root / "experiments" / "core_1e_a_phase_a_execution_contract_v1.json"
    fixture_path = project_root / "tests" / "fixtures" / "core1e_a" / "synthetic_market_v1.json"
    engine_path = project_root / "lib" / "core_1e_a_synthetic_engine.py"
    blockers: list[str] = []
    try:
        contract = load_json(contract_path)
        fixture = load_json(fixture_path)
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [f"input_unreadable:{exc.__class__.__name__}"]}
    expected = build_report(
        fixture,
        contract_sha256=file_sha256(contract_path),
        fixture_sha256=file_sha256(fixture_path),
        producing_commit=git_commit(project_root),
        engine_sha256=file_sha256(engine_path),
        stop_rule=contract["locked_science"]["stop_rule"],
    )
    if report_path is None:
        report = expected
        report_identity = "in_memory_synthetic_fixture_report"
    else:
        try:
            report = load_json(report_path)
        except (OSError, json.JSONDecodeError) as exc:
            return {"status": "blocked", "blockers": [f"report_unreadable:{exc.__class__.__name__}"]}
        report_identity = relative_to_root(report_path, project_root)
    if not isinstance(report, dict):
        blockers.append("report_must_be_object")
    else:
        blockers.extend(_shape_blockers(report))
        for candidate in report.get("candidates", []):
            if isinstance(candidate, dict):
                blockers.extend(_attribution_blockers(candidate))
        _finite_numbers(report, "report", blockers)
        if report.get("schema_version") != REPORT_SCHEMA_VERSION:
            blockers.append("schema_version_changed")
        if report != expected:
            blockers.append("recomputed_material_decisions_mismatch")
        if report.get("fixture", {}).get("path") != "tests/fixtures/core1e_a/synthetic_market_v1.json":
            blockers.append("fixture_path_changed")
        if report.get("contract_sha256") != file_sha256(contract_path):
            blockers.append("contract_provenance_drift")
        if report.get("fixture", {}).get("sha256") != file_sha256(fixture_path):
            blockers.append("fixture_provenance_drift")
        if report.get("provenance", {}).get("producing_commit") != git_commit(project_root):
            blockers.append("producing_commit_drift")
        if report.get("provenance", {}).get("engine_sha256") != file_sha256(engine_path):
            blockers.append("engine_provenance_drift")
        if report.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}:
            blockers.append("validation_access_not_sealed")
        access = report.get("access_counts")
        if isinstance(access, dict) and any(value != 0 for value in access.values()):
            blockers.append("nonzero_forbidden_access_count")
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "report_path": report_identity,
        "contract_sha256": _sha(contract_path),
        "fixture_sha256": _sha(fixture_path),
        "validation_accessed": False,
        "real_data_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CORE-1E-A synthetic report semantics.")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    result = validate_report(args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
