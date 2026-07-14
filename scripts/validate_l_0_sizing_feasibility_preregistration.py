from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root


DEFAULT_PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_0_sizing_feasibility_preregistration.json"


def validate_preregistration(path: Path = DEFAULT_PREREGISTRATION) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        payload = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"preregistration_unreadable:{exc.__class__.__name__}"])
    if not isinstance(payload, dict):
        return _result(path, ["preregistration_must_be_object"])

    expected = {
        "schema_version": "lily_l0_sizing_feasibility_preregistration_v1",
        "hypothesis_id": "L-0",
        "status": "locked_before_measurement",
        "evidence_tier": "E0",
        "edge_claim": "none",
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            blockers.append(f"invalid_locked_field:{field}")
    if payload.get("capital_scenarios_usd") != [1000, 2000]:
        blockers.append("capital_scenarios_must_be_1000_and_2000")

    pre = payload.get("pre_measurement_state")
    required_false = {
        "analysis_code_written",
        "broker_account_queried",
        "credentials_used",
        "orders_sent",
        "paid_data_used",
        "return_backtest_run",
    }
    if not isinstance(pre, dict):
        blockers.append("pre_measurement_state_missing")
    else:
        blockers.extend(f"pre_measurement_state_must_be_false:{field}" for field in required_false if pre.get(field) is not False)

    etf = payload.get("etf_branch")
    if not isinstance(etf, dict):
        blockers.append("etf_branch_missing")
    else:
        if etf.get("breadth_scenarios") != [8, 10, 12]:
            blockers.append("ETF_breadth_must_be_8_10_12")
        limits = etf.get("capital_and_trade_limits", {})
        if limits.get("minimum_cash_buffer") != 0.10:
            blockers.append("ETF_cash_buffer_must_be_10_percent")
        if limits.get("maximum_gross_exposure") != 0.90 or limits.get("maximum_leverage") != 1.0:
            blockers.append("ETF_gross_and_leverage_limits_changed")
        if limits.get("minimum_trade_usd") != 5.0:
            blockers.append("ETF_minimum_trade_must_be_USD5")
        risk = etf.get("risk_budget", {})
        if risk.get("maximum_standalone_risk_contribution") != 0.16:
            blockers.append("ETF_risk_concentration_limit_changed")
        cost = etf.get("cost_grid", {})
        if cost.get("maximum_recurring_cost_fraction_of_capital") != 0.015:
            blockers.append("ETF_cost_gate_must_be_1_5_percent")
        if len(etf.get("candidate_sleeves", [])) != 12:
            blockers.append("ETF_candidate_sleeves_must_contain_12_locked_slots")

    futures = payload.get("futures_branch")
    if not isinstance(futures, dict):
        blockers.append("futures_branch_missing")
    else:
        if futures.get("breadth_scenarios") != [4, 8, 12]:
            blockers.append("futures_breadth_must_be_4_8_12")
        if len(futures.get("nested_candidate_markets", [])) != 12:
            blockers.append("futures_candidate_markets_must_contain_12_locked_slots")
        margin = futures.get("margin_and_cash_limits", {})
        expected_margin = {
            "base_initial_margin_max_fraction_of_capital": 0.40,
            "margin_stress_multiplier": 1.50,
            "stressed_margin_max_fraction_of_capital": 0.60,
            "minimum_cash_buffer_after_initial_margin": 0.40,
        }
        for field, value in expected_margin.items():
            if margin.get(field) != value:
                blockers.append(f"futures_margin_limit_changed:{field}")
        concentration = futures.get("stress_concentration_limits", {})
        if concentration.get("aggregate_stress_loss_max_fraction_of_capital") != 0.30:
            blockers.append("futures_aggregate_stress_limit_changed")
        if concentration.get("per_market_max_fraction_by_breadth") != {"4": 0.10, "8": 0.075, "12": 0.05}:
            blockers.append("futures_per_market_stress_limits_changed")
        if "initial_margin_sum/0.40" not in str(futures.get("minimum_capital_formula")):
            blockers.append("futures_minimum_capital_formula_missing")

    data_rules = payload.get("data_rules", {})
    forbidden_text = " ".join(data_rules.get("forbidden", [])).lower() if isinstance(data_rules, dict) else ""
    for term in ("paid data", "credentialed broker request", "order transmission", "strategy return history"):
        if term not in forbidden_text:
            blockers.append(f"missing_data_guard:{term}")
    if len(payload.get("wiki_sources", [])) < 5:
        blockers.append("wiki_source_hashes_missing")
    if not payload.get("report_requirements"):
        blockers.append("report_requirements_missing")
    return _result(path, blockers)


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "preregistration_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the locked L-0 sizing-feasibility preregistration.")
    parser.add_argument("--preregistration", type=Path, default=DEFAULT_PREREGISTRATION)
    args = parser.parse_args()
    result = validate_preregistration(args.preregistration)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
