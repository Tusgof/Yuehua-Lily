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


DEFAULT_PREREGISTRATION = PROJECT_ROOT / "experiments" / "core_1_stable_baseline_preregistration_v1.json"
EXPECTED_CONTRACT_SHA256 = "5003d2360bb8729bcd91a39da34ff2e28c92ad2eb75c9b632c3ee85bcda7682f"

EXPECTED_TOP_LEVEL_KEYS = {
    "schema_version",
    "gate_id",
    "workstream",
    "hypothesis_id",
    "status",
    "evidence_tier",
    "edge_claim",
    "research_question",
    "rationale",
    "development_candidates_in_locked_order",
    "candidate_constraints",
    "universe",
    "portfolio_construction",
    "timing",
    "costs",
    "windows",
    "search_accounting_and_inference",
    "matched_benchmark",
    "development_eligibility_gates",
    "selection_rule",
    "stop_rule",
    "authorizations",
    "claim_ceiling",
    "exact_next_safe_action",
    "source_provenance",
}

EXPECTED_IDENTITY = {
    "schema_version": "lily_core_1_stable_baseline_preregistration_v1",
    "gate_id": "core_1_stable_baseline_preregistration_v1",
    "workstream": "CORE-1P",
    "hypothesis_id": "L-1",
    "status": "locked_before_execution",
    "evidence_tier": "E0",
    "edge_claim": "none",
}

EXPECTED_QUESTION_AND_RATIONALE = {
    "research_question": "Can a low-turnover long/cash trend-following system produce positive net return and positive net Sharpe after realistic costs on globally diversified ETFs?",
    "rationale": [
        "Existing L-1 is real E1 evidence, not an empty project: gross annual arithmetic return +3.6674479855%, gross Sharpe 0.4934695406, net annual arithmetic return -2.7427845464%, net Sharpe -0.3681760727, maximum drawdown -29.6729404515%, and 3,224 executed asset trades over 2007-02-05..2015-12-31.",
        "Existing continuous signed q/vol portfolio therefore shows a cost/turnover failure. CORE-1 replaces neither its locked bytes nor history. It tests a simpler long/cash implementation designed to reduce turnover.",
        "L-2, L-3, and L-4 enhancement execution is prospectively paused while CORE-1 is active. Preserve all statuses, evidence tiers, locked artifacts, and history. B8.9-D commit e76a2ec on its unmerged milestone branch is paused and non-authoritative; it must not be merged or edited in this order.",
    ],
}

EXPECTED_VARIANTS = {
    "development_candidates_in_locked_order": [
        {
            "id": "CORE1_DC60",
            "signal": "For each asset, use daily total-return direction over the prior 60 complete sessions; zero return contributes 0; long iff sum(direction)>0, otherwise cash.",
            "lookback_complete_sessions": 60,
        },
        {
            "id": "CORE1_DC120",
            "signal": "For each asset, use daily total-return direction over the prior 120 complete sessions; zero return contributes 0; long iff sum(direction)>0, otherwise cash.",
            "lookback_complete_sessions": 120,
        },
        {
            "id": "CORE1_SMA200",
            "signal": "Long iff the current corporate-action-aware total-return close is strictly above its simple moving average over the current and prior 199 complete sessions; otherwise cash.",
            "lookback_complete_sessions": 200,
        },
    ],
    "candidate_constraints": {
        "missing_required_observation": "asset_cash_until_complete",
        "continuous_q_magnitude": False,
        "shorting": False,
        "inverse_volatility_division": False,
        "target_volatility_scaling": False,
        "leverage": False,
        "regime_filter": False,
        "ensemble": False,
        "parameter_variation": False,
        "candidate_count": 3,
    },
}

EXPECTED_UNIVERSE = {
    "symbols_in_order": ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"],
    "rationale": "US-listed fractional implementation proxies with global countries and asset classes; do not claim point-in-time opportunity-set generality.",
}

EXPECTED_PORTFOLIO = {
    "fixed_sleeve_budget_per_asset": 0.125,
    "long_target_weight": 0.125,
    "inactive_asset_target_weight": 0.0,
    "inactive_sleeve": "cash",
    "renormalize_active_sleeves": False,
    "gross_exposure_range": [0.0, 1.0],
    "cash_weight": "1-gross_exposure",
    "borrowing": False,
    "no_trade_band": {
        "comparison": "target versus drifted pre-trade portfolio weight at an execution opportunity",
        "trade_when_absolute_difference_at_least": 0.02,
        "otherwise": "retain drifted weight",
        "opening_and_closing_0_125_sleeves": "subject to the same rule and normally pass",
        "fixed_dollar_floor_in_research_accounting": False,
        "current_capital_feasibility": "later separate study",
    },
}

EXPECTED_TIMING = {
    "decision": "Weekly after official close of actual last NYSE session of each ISO week using only available data.",
    "execution": "Official close of next actual NYSE session.",
    "pnl_start": "after_that_execution_close",
    "same_close_execution": False,
    "manufactured_sessions": False,
}

EXPECTED_COSTS = {
    "primary": {
        "commission_one_way_traded_notional": 0.00107,
        "commission_source": "Webull Thailand commission including VAT",
        "spread_slippage_one_way": 0.0025,
        "sell_surcharge": 0.0001,
        "etf_expense_ratios": "then-current locked ETF expense ratios accrued daily on held notional",
        "short_borrow": "not_applicable_long_cash",
        "cash_yield": 0.0,
        "cash_yield_limitation": "Cash yield is 0 until an approved, timestamp-valid cash series exists.",
        "funding_fx": "excluded_from_recurring_pnl_report_separately_later",
        "booking_rule": "Book commission, spread-slippage, and sell surcharge only on executed notional changes; accrue ETF expense ratios daily on held notional.",
    },
    "stress": {
        "name": "2x_execution_costs",
        "double": ["commission", "spread_slippage", "sell_surcharge"],
        "do_not_double": ["ETF expenses"],
    },
    "reported_paths": ["gross", "primary_net", "two_x_execution_cost_net"],
}

EXPECTED_WINDOWS = {
    "warmup_qa": {"start": "2006-02-03", "end": "2007-02-02", "performance_claim": False},
    "opened_development_falsification": {"start": "2007-02-05", "end": "2015-12-31"},
    "final_validation": {
        "start": "2016-01-04",
        "end": "2026-06-30",
        "status": "sealed_not_accessed",
        "forbidden": ["read", "scan", "hash", "count", "infer"],
    },
}

EXPECTED_SEARCH = {
    "search_inventory_exact_trials": 3,
    "attempted_real_return_run_counts_as_trial": True,
    "extra_debug_variant": False,
    "DSR": "use all three trials/effective-rank conventions",
    "required_reporting": [
        "PSR",
        "HAC/Newey-West inference",
        "autocorrelation-adjusted Sharpe variance",
        "calendar count",
        "trades",
        "turnover",
        "independent-bet equivalents",
    ],
}

EXPECTED_BENCHMARK = {
    "name": "equal_weight_always_long_fixed_sleeves",
    "target_weight_per_asset": 0.125,
    "same_dates": True,
    "same_one_session_delay": True,
    "same_drift": True,
    "same_no_trade_band": 0.02,
    "same_costs": True,
    "same_expenses": True,
    "same_cash_conventions": True,
    "switch_after_results": False,
}

EXPECTED_GATES = {
    "A": "Primary net annual geometric return > 0 and primary net annual Sharpe > 0.",
    "B": "PSR versus annual Sharpe 0 is >= 0.90; report HAC/Newey-West mean-return evidence and DSR for all three trials.",
    "C": "Under 2x execution costs, net annual geometric return > 0 and net annual Sharpe > 0.",
    "D": "Primary maximum drawdown is at least 5 percentage points less severe than the matched benchmark (strategy MDD - benchmark MDD >= 0.05, where both are negative or zero).",
    "E": "Remove the single asset with greatest full-window positive net contribution, hold its sleeve as cash without re-optimization, and primary net annual geometric return remains > 0.",
    "F": "Contribution concentration: largest positive asset share <= 0.50; also report positive-contribution HHI and best-episode concentration.",
    "G": "Fixed subperiods 2007-2009, 2010-2012, 2013-2015: at least 2 of 3 have positive net annual geometric return, and no subperiod is below -5% net annual geometric return. Report the locked GFC diagnostic and prior-only global-state/whipsaw diagnostics, but never manufacture a funded regime claim.",
    "H": "No critical timestamp, corporate-action, survivorship/inception, missingness, or accounting blocker.",
}

EXPECTED_SELECTION = {
    "discard_first": "Discard any candidate failing any A-H gate.",
    "primary": "Among eligible candidates, choose the one with highest worst-subperiod net Sharpe.",
    "near_tie": "If the top two are within 0.02 annual Sharpe on that criterion, choose lower one-way turnover.",
    "final_tie": "If still tied within 1e-12, order is CORE1_DC60, CORE1_DC120, CORE1_SMA200.",
    "claim_limit": "Selection is E1 development evidence only and does not open validation or claim an edge.",
}

EXPECTED_STOP_RULE = "If no candidate passes every A-H gate, stop CORE-1 after CORE-1E, keep validation sealed, and require an owner/Inspector decision to reformulate or close this ETF trend family. No fourth candidate, parameter rescue, universe/date/cost change, or remediation layering. If one candidate passes, lock that single candidate in a separate future order before any request to open final validation."

EXPECTED_AUTHORIZATIONS = {
    "backtest": False,
    "return_reading_or_parsing": False,
    "dataset_access": False,
    "container_access": False,
    "dataset_hash_or_scan": False,
    "validation_access": False,
    "provider_or_network_data_call": False,
    "credential_access": False,
    "broker_or_account_action": False,
    "paid_action": False,
    "paper_trading": False,
    "real_money_action": False,
    "research_log_edit": False,
}

EXPECTED_SOURCE_PROVENANCE = {
    "start_commit": "086c445e6ef711d1d553a121c2c80577afa86f99",
    "l1_summary": {
        "path": "reports/experiments/l_1_baseline_summary.json",
        "sha256": "f6c4e14c71a4914371e6078f16351905f38cfb7420526d01238bad770cb6e71c",
    },
    "wiki": [
        {
            "path": "wiki/concepts/directional-count-trend-signal.md",
            "sha256": "0eb4e3cbd6eceab838d5fc88c0500bedfbe345389eb3646fb19200b6b97b7490",
        },
        {
            "path": "wiki/concepts/long-only-trend-following.md",
            "sha256": "a80ab0cc6e9ec2807197a700ef4bfa560ed2ec3ec46e02dc88367724eac3d37f",
        },
        {
            "path": "wiki/concepts/trend-following-transaction-cost-control.md",
            "sha256": "f92fb361bfcc89e4e65dce958ca63447d3563e04fc77332187d8a3f68322631a",
        },
        {
            "path": "wiki/concepts/backtest-validation-protocol.md",
            "sha256": "c7f843310706d902120651e677429e66cbde9ce96ee526544de5419ee99aefa0",
        },
    ],
}

EXPECTED_CLAIM_CEILING = "E0 planning/governance only; no empirical result, validation opening, or edge claim."
EXPECTED_NEXT_ACTION = "CORE-1E only after Inspector acceptance + user integration."
EXPECTED_LOCK_SCOPE = [
    "question",
    "variants",
    "universe_order",
    "timing",
    "portfolio_and_band",
    "costs_and_stress",
    "windows_and_seal",
    "benchmark",
    "A_H_gates",
    "selection",
    "stop_rule",
    "claim_ceiling",
    "authorizations",
    "source_identity_and_hash",
    "next_action",
]


def validate_preregistration(path: Path = DEFAULT_PREREGISTRATION) -> dict[str, Any]:
    try:
        payload = load_json(path)
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        return _result(path, [f"preregistration_unreadable:{exc.__class__.__name__}"])
    blockers: list[str] = []
    if not isinstance(payload, dict):
        blockers.append("preregistration_must_be_object")
    else:
        if set(payload) != EXPECTED_TOP_LEVEL_KEYS:
            blockers.append("top_level_structure_changed")
        _check(blockers, "identity", {key: payload.get(key) for key in EXPECTED_IDENTITY}, EXPECTED_IDENTITY)
        _check(
            blockers,
            "question",
            {key: payload.get(key) for key in EXPECTED_QUESTION_AND_RATIONALE},
            EXPECTED_QUESTION_AND_RATIONALE,
        )
        _check(
            blockers,
            "variants",
            {key: payload.get(key) for key in EXPECTED_VARIANTS},
            EXPECTED_VARIANTS,
        )
        _check(blockers, "universe_order", payload.get("universe"), EXPECTED_UNIVERSE)
        _check(blockers, "portfolio_and_band", payload.get("portfolio_construction"), EXPECTED_PORTFOLIO)
        _check(blockers, "timing", payload.get("timing"), EXPECTED_TIMING)
        _check(blockers, "costs_and_stress", payload.get("costs"), EXPECTED_COSTS)
        _check(blockers, "windows_and_seal", payload.get("windows"), EXPECTED_WINDOWS)
        _check(
            blockers,
            "search_and_inference",
            payload.get("search_accounting_and_inference"),
            EXPECTED_SEARCH,
        )
        _check(blockers, "benchmark", payload.get("matched_benchmark"), EXPECTED_BENCHMARK)
        _check(blockers, "A_H_gates", payload.get("development_eligibility_gates"), EXPECTED_GATES)
        _check(blockers, "selection", payload.get("selection_rule"), EXPECTED_SELECTION)
        _check(blockers, "stop_rule", payload.get("stop_rule"), EXPECTED_STOP_RULE)
        _check(blockers, "claim_ceiling", payload.get("claim_ceiling"), EXPECTED_CLAIM_CEILING)
        _check(blockers, "authorizations", payload.get("authorizations"), EXPECTED_AUTHORIZATIONS)
        _check(blockers, "source_identity_and_hash", payload.get("source_provenance"), EXPECTED_SOURCE_PROVENANCE)
        _check(blockers, "next_action", payload.get("exact_next_safe_action"), EXPECTED_NEXT_ACTION)
    if _sha256(path) != EXPECTED_CONTRACT_SHA256:
        blockers.append("locked_contract_sha256_changed")
    return _result(path, blockers)


def _check(blockers: list[str], label: str, actual: Any, expected: Any) -> None:
    if not _exact_equal(actual, expected):
        blockers.append(f"{label}_changed")


def _exact_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _exact_equal(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _exact_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected)
        )
    return actual == expected


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "fail" if blockers else "pass",
        "path": relative_to_root(path, PROJECT_ROOT),
        "blockers": blockers,
        "lock_scope": EXPECTED_LOCK_SCOPE,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail closed on CORE-1P preregistration drift.")
    parser.add_argument("--path", type=Path, default=DEFAULT_PREREGISTRATION)
    args = parser.parse_args()
    result = validate_preregistration(args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
