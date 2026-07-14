from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root
from lib.statistics import minimum_track_record_length_falsify, minimum_track_record_length_validate


DEFAULT_PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_1_baseline_preregistration.json"
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def validate_preregistration(path: Path = DEFAULT_PREREGISTRATION) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        payload = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"preregistration_unreadable:{exc.__class__.__name__}"])
    if not isinstance(payload, dict):
        return _result(path, ["preregistration_must_be_object"])

    expected_root = {
        "schema_version": "lily_l1_baseline_preregistration_v1",
        "hypothesis_id": "L-1",
        "status": "locked_before_execution",
        "evidence_ceiling_without_adversarial_review": "E1",
        "edge_claim_before_execution": "none",
    }
    for field, expected in expected_root.items():
        if payload.get(field) != expected:
            blockers.append(f"invalid_locked_field:{field}")

    pre = payload.get("pre_measurement_state")
    if not isinstance(pre, dict) or not pre:
        blockers.append("pre_measurement_state_missing")
    else:
        blockers.extend(
            f"pre_measurement_state_must_be_false:{field}"
            for field, value in pre.items()
            if value is not False
        )

    scope = payload.get("scope_decisions", {})
    if scope.get("primary_inference_branch") != "research_signed":
        blockers.append("primary_branch_must_be_research_signed")
    if scope.get("current_capital_branch") != "implementable_long_or_cash":
        blockers.append("current_capital_branch_changed")
    if scope.get("capital_scenarios_usd") != [1000, 2000]:
        blockers.append("capital_scenarios_must_be_1000_and_2000")
    if scope.get("data_cutoff_inclusive") != "2026-06-30":
        blockers.append("data_cutoff_changed")
    if scope.get("paid_data_guard_usd_cumulative_through_L1") != 50:
        blockers.append("paid_data_guard_must_be_USD50")
    if "excluded" not in str(scope.get("futures", "")):
        blockers.append("futures_must_be_excluded_from_L1")

    signal = payload.get("signal", {})
    expected_signal = {
        "name": "60_day_directional_count_raw",
        "minimum_complete_observations": 60,
        "scaling": "none; do not apply the source paper's rolling three-year extreme scaling",
        "research_exposure": "signed q in [-1,1]",
        "current_capital_exposure": "max(q,0) in [0,1]",
        "no_stop_loss_or_take_profit": True,
    }
    for field, expected in expected_signal.items():
        if signal.get(field) != expected:
            blockers.append(f"signal_rule_changed:{field}")
    formula = str(signal.get("formula", ""))
    if "k=0..59" not in formula or "/ 60" not in formula:
        blockers.append("signal_formula_must_lock_60_directional_observations")
    if "0 if r[i,t] = 0" not in str(signal.get("direction", "")):
        blockers.append("zero_return_rule_missing")

    universes = payload.get("universes", {})
    research = universes.get("research_signed", {})
    research_tickers = [row.get("ticker") for row in research.get("instruments", [])]
    if research_tickers != ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]:
        blockers.append("research_universe_or_order_changed")
    if "No performance-driven replacement" not in str(research.get("replacement_rule", "")):
        blockers.append("research_universe_replacement_rule_missing")
    implementation = universes.get("implementable_long_or_cash", {})
    if implementation.get("candidate_tickers_in_order") != [
        "VTI", "VGK", "EWJ", "IPAC", "VWO", "IEF", "SCHP", "GLDM", "PDBC", "VNQI"
    ]:
        blockers.append("implementable_universe_or_order_changed")
    if implementation.get("minimum_breadth") != 8 or implementation.get("primary_breadth") != 10:
        blockers.append("implementable_breadth_changed")
    if implementation.get("shorting") is not False or implementation.get("leverage") is not False:
        blockers.append("current_capital_must_be_long_cash_without_leverage")

    timing = payload.get("timing_and_calendar", {})
    if timing.get("execution_delay_sessions") != 1 or timing.get("same_close_execution_forbidden") is not True:
        blockers.append("execution_delay_or_same_close_rule_changed")
    if timing.get("timezone") != "America/New_York":
        blockers.append("execution_timezone_changed")

    portfolio = payload.get("portfolio_construction", {})
    asset_vol = portfolio.get("asset_volatility", {})
    if asset_vol.get("span_sessions") != 60 or asset_vol.get("annualized_floor") != 0.05:
        blockers.append("asset_volatility_rule_changed")
    covariance = portfolio.get("covariance", {})
    if covariance.get("span_sessions") != 60 or covariance.get("minimum_complete_pair_observations") != 60:
        blockers.append("covariance_rule_changed")
    locked_portfolio_values = {
        "portfolio_target_volatility": 0.10,
        "maximum_gross_exposure": 0.90,
        "minimum_cash_fraction": 0.10,
        "maximum_absolute_asset_weight": 0.25,
        "maximum_leverage": 1.0,
        "rebalance": "weekly",
        "fractional_precision_usd": 0.01,
    }
    for field, expected in locked_portfolio_values.items():
        if portfolio.get(field) != expected:
            blockers.append(f"portfolio_rule_changed:{field}")
    if "USD 5" not in str(portfolio.get("current_capital_trade_floor", "")):
        blockers.append("current_capital_trade_floor_missing")

    costs = payload.get("costs", {})
    primary_cost = costs.get("primary_model", {})
    expected_costs = {
        "Webull_Thailand_commission_one_way_fraction_including_VAT": 0.00107,
        "spread_and_slippage_one_way_bps": 25.0,
        "sell_regulatory_surcharge_bps": 1.0,
        "research_short_borrow_annual_fraction": 0.03,
    }
    for field, expected in expected_costs.items():
        if primary_cost.get(field) != expected:
            blockers.append(f"primary_cost_changed:{field}")
    sensitivities = costs.get("locked_sensitivities", [])
    if [row.get("id") for row in sensitivities] != ["lower_spread", "severe_cost"]:
        blockers.append("cost_sensitivity_inventory_changed")
    if costs.get("zero_cost_result_may_not_support_a_claim") is not True:
        blockers.append("zero_cost_claim_guard_missing")

    returns = payload.get("return_accounting", {})
    if "raw close" not in str(returns.get("economic_return", "")):
        blockers.append("corporate_action_return_accounting_missing")
    if returns.get("annualization_sessions") != 252 or returns.get("bankruptcy_rule") is None:
        blockers.append("return_annualization_or_bankruptcy_rule_missing")

    benchmarks = payload.get("benchmarks", {})
    for field in ("matched_implementable", "cash", "active_return"):
        if not benchmarks.get(field):
            blockers.append(f"benchmark_missing:{field}")
    if benchmarks.get("benchmark_selection_after_results_forbidden") is not True:
        blockers.append("benchmark_selection_guard_missing")

    sample = payload.get("sample_and_unlock_order", {})
    if sample.get("falsification_window") != {
        "start": "2007-02-05", "end": "2015-12-31", "opened_first": True
    }:
        blockers.append("falsification_window_changed")
    if sample.get("untouched_validation_window") != {
        "start": "2016-01-04", "end": "2026-06-30", "initially_sealed": True
    }:
        blockers.append("untouched_validation_window_changed")
    unlock_text = str(sample.get("unlock_rule", ""))
    for required in ("falsification window", "MinTRL_falsify", "validation window", "MinTRL_validate"):
        if required not in unlock_text:
            blockers.append(f"sequential_unlock_rule_missing:{required}")

    blockers.extend(_validate_dual_mintrl(payload.get("dual_MinTRL", {})))

    regimes = payload.get("regime_matrix", {})
    if set(regimes.get("global_state", {})) != {"broad_uptrend", "broad_downtrend", "whipsaw", "mixed"}:
        blockers.append("global_regime_matrix_incomplete")
    required_breakdowns = set(regimes.get("required_breakdowns", []))
    if required_breakdowns != {
        "global_state", "volatility_state", "asset_sleeve", "country_or_region", "calendar_subperiod", "fixed_crisis_window"
    }:
        blockers.append("required_regime_breakdowns_changed")

    payoff = payload.get("payoff_and_concentration_tests", {})
    for field in (
        "right_tail_ratio", "return_skewness", "quadratic_convexity", "convex_payoff_gate",
        "asset_contribution_concentration", "largest_episode_concentration",
        "best_market_removal", "best_trend_removal", "removal_pass",
    ):
        if not payoff.get(field):
            blockers.append(f"payoff_or_concentration_test_missing:{field}")

    decisions = payload.get("decision_rules", {})
    if len(decisions.get("falsified", [])) != 4:
        blockers.append("falsification_rule_incomplete")
    if len(decisions.get("validation_grade_candidate", [])) != 5:
        blockers.append("validation_rule_incomplete")
    if "separate adversarial review" not in str(decisions.get("E2_promotion", "")):
        blockers.append("E2_adversarial_review_gate_missing")

    search = payload.get("search_and_robustness", {})
    trials = search.get("locked_trial_inventory", [])
    if [row.get("trial_id") for row in trials] != [
        "primary_60", "sensitivity_40", "sensitivity_80", "sensitivity_low_cost", "sensitivity_severe_cost"
    ]:
        blockers.append("locked_trial_inventory_changed")
    if sum(row.get("claim_eligible") is True for row in trials) != 1:
        blockers.append("exactly_one_trial_must_be_claim_eligible")
    if "maximum of 5" not in str(search.get("effective_trials_for_DSR", "")):
        blockers.append("DSR_effective_trial_floor_missing")
    if not search.get("additional_search_forbidden"):
        blockers.append("forbidden_search_inventory_missing")

    integrity = payload.get("data_integrity", {})
    required_integrity_terms = {
        "point_in_time_rule": "fixed preregistered proxies",
        "delisting_rule": "delisting",
        "backfill_rule": "legal inception",
        "corporate_action_rule": "splits",
        "FX_rule": "USD listing",
        "futures_roll_rule": "futures are excluded",
        "provider_drift_rule": "blocks execution",
        "hash_rule": "hash",
        "missingness_rule": "No price forward fill",
    }
    for field, phrase in required_integrity_terms.items():
        if phrase not in str(integrity.get(field, "")):
            blockers.append(f"data_integrity_rule_missing:{field}")

    sources = payload.get("wiki_sources")
    if not isinstance(sources, list) or len(sources) < 10:
        blockers.append("wiki_source_hashes_missing")
    else:
        for index, source in enumerate(sources):
            if not isinstance(source, dict) or not str(source.get("path", "")).startswith("wiki/"):
                blockers.append(f"wiki_source_path_invalid:{index}")
            if not HASH_PATTERN.fullmatch(str(source.get("sha256", ""))):
                blockers.append(f"wiki_source_hash_invalid:{index}")
    if len(payload.get("B4_report_requirements", [])) < 8:
        blockers.append("B4_report_requirements_incomplete")
    hard_stops = " ".join(payload.get("hard_stops", [])).lower()
    for term in ("backtest execution during b3", "untouched validation", "credential", "same-close", "in-place change", "edge"):
        if term not in hard_stops:
            blockers.append(f"hard_stop_missing:{term}")
    return _result(path, blockers)


def _validate_dual_mintrl(plan: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if plan.get("observation_frequency") != "daily" or plan.get("annualization_sessions") != 252:
        blockers.append("MinTRL_frequency_or_annualization_changed")
    autocorrelations = plan.get("planning_autocorrelations_lags_1_to_5")
    if autocorrelations != [0.10, 0.05, 0.025, 0.0125, 0.00625]:
        blockers.append("MinTRL_autocorrelation_plan_changed")
        return blockers
    common = {
        "skewness": plan.get("planning_skewness"),
        "raw_kurtosis": plan.get("planning_raw_Pearson_kurtosis"),
        "autocorrelations": autocorrelations,
        "significance": plan.get("one_sided_significance"),
        "power": plan.get("power"),
    }
    falsify = plan.get("falsify", {})
    computed_falsify = minimum_track_record_length_falsify(
        claimed_minimum_sharpe=falsify.get("claimed_minimum_annual_Sharpe", 0) / math.sqrt(252),
        adverse_true_sharpe=falsify.get("adverse_true_annual_Sharpe", 0) / math.sqrt(252),
        **common,
    )
    if computed_falsify != 3850 or falsify.get("required_joint_independent_bet_equivalents") != 3850:
        blockers.append("MinTRL_falsify_recalculation_mismatch")
    if falsify.get("sequence") != 1 or falsify.get("planning_minimum_calendar_observations_at_dimension_4") != 963:
        blockers.append("MinTRL_falsify_sequence_or_funding_changed")

    validate = plan.get("validate", {})
    expected_plans = [
        ("portfolio_excess_zero", 0.75, 0.0, 3856),
        ("minimum_acceptable_Sharpe", 0.75, 0.25, 8673),
        ("active_vs_matched_benchmark", 0.50, 0.0, 8660),
    ]
    actual_plans = validate.get("null_plans", [])
    if len(actual_plans) != len(expected_plans):
        blockers.append("MinTRL_validate_null_inventory_changed")
    else:
        for row, (plan_id, expected_annual, null_annual, required) in zip(actual_plans, expected_plans, strict=True):
            computed = minimum_track_record_length_validate(
                expected_sharpe=expected_annual / math.sqrt(252),
                null_sharpe=null_annual / math.sqrt(252),
                **common,
            )
            if row != {
                "id": plan_id,
                "expected_annual_Sharpe": expected_annual,
                "null_annual_Sharpe": null_annual,
                "required_joint_independent_bet_equivalents": required,
            } or computed != required:
                blockers.append(f"MinTRL_validate_recalculation_mismatch:{plan_id}")
    if validate.get("sequence") != 2:
        blockers.append("MinTRL_validate_must_follow_falsify")
    if validate.get("binding_required_joint_independent_bet_equivalents") != 8673:
        blockers.append("MinTRL_validate_binding_requirement_changed")
    if validate.get("planning_minimum_calendar_observations_at_dimension_4") != 2169:
        blockers.append("MinTRL_validate_calendar_funding_changed")
    if plan.get("planning_cross_sectional_effective_dimensions") != 4.0:
        blockers.append("MinTRL_planning_effective_dimensions_changed")
    if plan.get("raw_trade_count_never_substitutes_for_effective_observations") is not True:
        blockers.append("MinTRL_trade_count_guard_missing")
    return blockers


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "preregistration_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the locked L-1 baseline preregistration.")
    parser.add_argument("--preregistration", type=Path, default=DEFAULT_PREREGISTRATION)
    args = parser.parse_args()
    result = validate_preregistration(args.preregistration)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
