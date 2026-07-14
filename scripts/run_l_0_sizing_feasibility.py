from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json
from lib.provenance import git_commit, payload_sha256
from lib.report import render_markdown_report, write_report_pair
from lib.sizing import futures_minimum_capital, inverse_volatility_scenario


DEFAULT_PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_0_sizing_feasibility_preregistration.json"
DEFAULT_INPUTS = PROJECT_ROOT / "experiments" / "inputs" / "l_0_public_inputs.json"
DEFAULT_JSON = PROJECT_ROOT / "reports" / "feasibility" / "l_0_sizing_feasibility.json"
DEFAULT_MARKDOWN = PROJECT_ROOT / "reports" / "feasibility" / "l_0_sizing_feasibility.md"


def build_report_payload(
    preregistration: dict[str, Any],
    inputs: dict[str, Any],
    *,
    producing_commit: str,
) -> dict[str, Any]:
    etf_gate = preregistration["etf_branch"]
    limits = etf_gate["capital_and_trade_limits"]
    risk_budget = etf_gate["risk_budget"]
    cost_grid = etf_gate["cost_grid"]
    sleeves = inputs["etf"]["sleeves"]

    economic_scenarios: list[dict[str, Any]] = []
    for capital in preregistration["capital_scenarios_usd"]:
        for breadth in etf_gate["breadth_scenarios"]:
            scenario = inverse_volatility_scenario(
                sleeves,
                breadth=breadth,
                capital_usd=capital,
                gross_exposure=limits["maximum_gross_exposure"],
                minimum_trade_usd=limits["minimum_trade_usd"],
                maximum_weight=risk_budget["maximum_notional_weight"],
                maximum_standalone_risk_contribution=risk_budget[
                    "maximum_standalone_risk_contribution"
                ],
            )
            expense_fraction = sum(
                row["weight"] * sleeves[index]["expense_ratio"]
                for index, row in enumerate(scenario["allocations"])
            ) / scenario["gross_exposure"]
            webull_one_way = inputs["etf"]["broker_facts"][
                "Webull_Thailand_manual_fractional"
            ]["commission_one_way_fraction_including_vat"]
            cost_rows = []
            for turnover in cost_grid["annual_one_way_turnover_multiples"]:
                trading_cost = turnover * (webull_one_way + 25.0 / 10_000.0)
                cost_rows.append(
                    {
                        "annual_one_way_turnover_multiple": turnover,
                        "commission_plus_25bps_spread_fraction": round(trading_cost, 8),
                        "weighted_expense_fraction": round(expense_fraction, 8),
                        "total_recurring_cost_fraction": round(trading_cost + expense_fraction, 8),
                    }
                )
            primary = next(
                row
                for row in cost_rows
                if row["annual_one_way_turnover_multiple"]
                == cost_grid["primary_cost_gate_turnover_multiple"]
            )
            scenario["webull_cost_grid"] = cost_rows
            scenario["gates"]["primary_stressed_recurring_cost_met"] = (
                primary["total_recurring_cost_fraction"]
                <= cost_grid["maximum_recurring_cost_fraction_of_capital"]
            )
            scenario["economic_classification"] = (
                "feasible" if all(scenario["gates"].values()) else "infeasible"
            )
            economic_scenarios.append(scenario)

    broker_blockers = {
        "Webull_Thailand_manual_fractional": [
            "exact_candidate_green_diamond_eligibility_unverified",
            "public_minimum_fractional_order_unverified",
            "funding_FX_cost_unverified",
            "sell_side_regulatory_fees_not_quantified",
        ],
        "Webull_Thailand_OpenAPI_fractional": [
            "Thailand_OpenAPI_fractional_order_support_unverified",
            "exact_candidate_API_eligibility_unverified",
            "public_minimum_fractional_order_unverified",
            "funding_FX_cost_unverified",
            "sell_side_regulatory_fees_not_quantified",
        ],
        "IBKR_fractional_reference": [
            "exact_candidate_fractional_eligibility_unverified",
            "Thailand_account_permission_unverified",
            "minimum_commission_requires_unlocked_order_count_sensitivity",
            "funding_FX_cost_unverified",
        ],
    }
    broker_results = []
    for capital in preregistration["capital_scenarios_usd"]:
        feasible_breadths = [
            row["breadth"]
            for row in economic_scenarios
            if row["capital_usd"] == capital and row["economic_classification"] == "feasible"
        ]
        for broker_path in etf_gate["broker_paths"]:
            broker_results.append(
                {
                    "capital_usd": capital,
                    "broker_path": broker_path,
                    "classification": "scope_restricted",
                    "allocation_feasible_breadths_under_recorded_cost_model": feasible_breadths,
                    "fully_verified_feasible": False,
                    "blockers": broker_blockers[broker_path],
                }
            )

    futures_gate = preregistration["futures_branch"]
    concentration_limits = futures_gate["stress_concentration_limits"][
        "per_market_max_fraction_by_breadth"
    ]
    futures_results: dict[str, list[dict[str, Any]]] = {}
    for contract_size in ("micro", "full"):
        futures_results[contract_size] = [
            futures_minimum_capital(
                inputs["futures"][contract_size],
                breadth=breadth,
                per_market_stress_limit=concentration_limits[str(breadth)],
            )
            for breadth in futures_gate["breadth_scenarios"]
        ]
        for row in futures_results[contract_size]:
            minimum_capital = row["minimum_capital_usd"]
            row["diagnostics_at_minimum_capital"] = {
                "initial_margin_fraction": round(row["initial_margin_sum_usd"] / minimum_capital, 8),
                "stressed_margin_fraction": round(row["stressed_margin_sum_usd"] / minimum_capital, 8),
                "cash_after_initial_margin_fraction": round(
                    1.0 - row["initial_margin_sum_usd"] / minimum_capital,
                    8,
                ),
                "aggregate_stress_loss_fraction": round(
                    row["aggregate_stress_loss_usd"] / minimum_capital,
                    8,
                ),
                "maximum_single_market_stress_fraction": round(
                    row["maximum_single_market_stress_loss_usd"] / minimum_capital,
                    8,
                ),
                "portfolio_round_turn_broker_commission_floor_usd": round(
                    row["breadth"] * 1.70,
                    2,
                ),
                "round_turn_total_cost_status": "unverified_exchange_and_regulatory_fees",
            }

    payload: dict[str, Any] = {
        "schema_version": "lily_l0_sizing_feasibility_report_v1",
        "hypothesis_id": "L-0",
        "measurement_date": inputs["as_of"],
        "producing_git_commit": producing_commit,
        "evidence_tier": "E0",
        "edge_claim": "none",
        "decision": "scope_restricted",
        "claims": {
            "fact": "Public broker terms establish general fractional availability and published fees, but not a fully verified exact Thailand implementation path.",
            "locked_assumption": "Capital, breadth, inverse-volatility inputs, cash, concentration, turnover, spread, margin, and stress gates are copied from the locked preregistration.",
            "calculation": "ETF 8- and 10-sleeve economic sizing passes at USD 1,000 and USD 2,000; the 12-sleeve case breaches the 25% weight cap because the locked 3% volatility for SGOV creates a 29.67% target weight.",
            "inference": "Fractional ETFs are the only economically plausible current-capital branch, while micro futures require capital far above USD 2,000.",
            "recommendation": "Carry a scope restriction into B3 and verify exact Webull Thailand ticker/minimum/FX and OpenAPI fractional capability before any implementation study.",
            "caveat": "This is deterministic E0 feasibility evidence, not evidence of trend-following returns, edge, broker approval, or deployment readiness."
        },
        "guardrails": {
            "paid_data_used": False,
            "credentialed_broker_request_used": False,
            "orders_sent": False,
            "paper_trades_sent": False,
            "return_backtest_run": False,
        },
        "tier_blockers": [
            "no_strategy_return_evidence",
            "no_account_reported_permissions",
            "no_exact_Webull_Thailand_fractional_ticker_check",
            "no_Webull_Thailand_fractional_OpenAPI_confirmation",
            "funding_FX_cost_unverified",
            "Webull_sell_side_regulatory_fees_not_quantified",
            "futures_margin_uses_Hong_Kong_public_proxy_not_Thailand_account",
            "futures_total_round_turn_cost_and_expiry_rules_incomplete",
        ],
        "etf": {
            "candidate_sleeves": sleeves,
            "economic_scenarios": economic_scenarios,
            "broker_results": broker_results,
            "overall_current_capital_result": {
                "classification": "scope_restricted",
                "fully_verified_broker_path_exists": False,
                "economic_sizing_passes_for_breadths": [8, 10],
                "capital_scenarios_usd": preregistration["capital_scenarios_usd"],
            },
        },
        "futures": {
            "micro": futures_results["micro"],
            "full_size_comparator": futures_results["full"],
            "operational_classification": "minimum_capital_only",
            "current_capital_feasible": False,
            "limitations": inputs["futures"]["shared_limitations"],
        },
        "source_inventory": inputs["sources"],
        "methodology_sources": preregistration["wiki_sources"],
    }
    payload["report_digest_sha256"] = payload_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    etf_rows = [
        "| Capital | Breadth | Economic result | Max weight | Min trade |",
        "|---:|---:|:---|---:|---:|",
    ]
    for row in payload["etf"]["economic_scenarios"]:
        etf_rows.append(
            f"| ${row['capital_usd']:,} | {row['breadth']} | {row['economic_classification']} | "
            f"{row['maximum_observed_weight']:.2%} | ${row['minimum_observed_trade_usd']:.2f} |"
        )
    broker_rows = [
        "| Capital | Path | Classification | Verified feasible |",
        "|---:|:---|:---|:---|",
    ]
    for row in payload["etf"]["broker_results"]:
        broker_rows.append(
            f"| ${row['capital_usd']:,} | {row['broker_path']} | {row['classification']} | "
            f"{str(row['fully_verified_feasible']).lower()} |"
        )
    futures_rows = [
        "| Contract set | Markets | Minimum capital | Binding gate |",
        "|:---|---:|---:|:---|",
    ]
    for label, key in (("Micro", "micro"), ("Full-size comparator", "full_size_comparator")):
        for row in payload["futures"][key]:
            futures_rows.append(
                f"| {label} | {row['breadth']} | ${row['minimum_capital_usd']:,} | {row['binding_component']} |"
            )
    blockers = "\n".join(f"- `{item}`" for item in payload["tier_blockers"])
    sources = "\n".join(
        f"- [{row['publisher']}]({row['url']}) — {row['claim_supported']} Caveat: {row['staleness_or_scope_note']}"
        for row in payload["source_inventory"]
    )
    return render_markdown_report(
        "L-0 Sizing Feasibility — E0",
        [
            ("Decision", f"**scope_restricted**. {payload['claims']['recommendation']}\n\nNo edge or deployment claim is made."),
            ("What the evidence says", "\n".join(f"- **{key}**: {value}" for key, value in payload["claims"].items())),
            ("ETF economic sizing", "\n".join(etf_rows)),
            ("Broker-path classification", "\n".join(broker_rows)),
            ("Futures minimum capital", "\n".join(futures_rows)),
            ("E0 blockers", blockers),
            ("Sources", sources),
            ("Integrity", f"Producing commit: `{payload['producing_git_commit']}`\n\nMachine report digest: `{payload['report_digest_sha256']}`"),
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the locked L-0 deterministic sizing study.")
    parser.add_argument("--preregistration", type=Path, default=DEFAULT_PREREGISTRATION)
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    payload = build_report_payload(
        load_json(args.preregistration),
        load_json(args.inputs),
        producing_commit=git_commit(PROJECT_ROOT),
    )
    write_report_pair(
        payload,
        args.json,
        args.markdown,
        render_markdown(payload),
        project_root=PROJECT_ROOT,
    )
    print(f"wrote {args.json.relative_to(PROJECT_ROOT)} and {args.markdown.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
