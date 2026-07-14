from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.environment import interpreter_metadata, require_configured_path
from lib.io import load_json, write_json
from lib.provenance import file_sha256, git_commit, payload_sha256
from lib.remediation import cash_returns_for_sessions
from lib.search_log import append_search_log
from lib.trend_baseline import CostModel, add_dsr, load_market, run_trial, trial_summary


MARKET_RELATIVE = Path("normalized/l1_yahoo_daily_v1.json")
CASH_RELATIVE = Path("normalized/treasury_13week_cash_v1.json")
ORIGINAL_REPORT = PROJECT_ROOT / "reports" / "experiments" / "l_1_baseline_summary.json"
SEARCH_LOG = PROJECT_ROOT / "reports" / "experiments" / "l_1_search_log.jsonl"
OUTPUT = PROJECT_ROOT / "reports" / "data_quality" / "l_1_cash_remediation.json"
CONTRACT = PROJECT_ROOT / "experiments" / "l_1_data_quality_remediation.json"


LOCKED_TRIALS = (
    ("primary_60", 60, CostModel(spread_bps=25.0, borrow_annual=0.03), True),
    ("sensitivity_40", 40, CostModel(spread_bps=25.0, borrow_annual=0.03), False),
    ("sensitivity_80", 80, CostModel(spread_bps=25.0, borrow_annual=0.03), False),
    ("sensitivity_low_cost", 60, CostModel(spread_bps=12.5, borrow_annual=0.03), False),
    ("sensitivity_severe_cost", 60, CostModel(spread_bps=50.0, borrow_annual=0.06), False),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the locked cash-only L-1 remediation.")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    data_root = args.data_root.resolve() if args.data_root else require_configured_path("LILY_DATA_ROOT")
    market_payload = load_json(data_root / MARKET_RELATIVE)
    sessions = sorted(
        set.intersection(
            *[{record["session_date"] for record in symbol["records"]} for symbol in market_payload["symbols"]]
        )
    )
    cash_payload = load_json(data_root / CASH_RELATIVE)
    cash_returns = cash_returns_for_sessions(cash_payload, sessions)
    market = load_market(market_payload, cash_returns=cash_returns)
    run_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    run_id = "l1-cash-remediation-" + run_at.replace(":", "").replace("-", "")
    append_search_log(
        SEARCH_LOG,
        [{
            "event": "run_started",
            "run_id": run_id,
            "timestamp_utc": run_at,
            "hypothesis_id": "L-1",
            "order_id": "B4.1",
            "change_from_B4": "lagged_13_week_Treasury_cash_only",
            "opened_window": "falsification_2007-02-05_to_2015-12-31",
            "untouched_validation_status": "sealed_not_accessed",
            "market_dataset_sha256": file_sha256(data_root / MARKET_RELATIVE),
            "cash_dataset_sha256": file_sha256(data_root / CASH_RELATIVE),
        }],
    )
    trials = []
    summaries = []
    for trial_id, lookback, cost, claim_eligible in LOCKED_TRIALS:
        trial = run_trial(market, trial_id=trial_id, lookback=lookback, cost_model=cost)
        summary = trial_summary(trial)
        summary["claim_eligible"] = claim_eligible
        trials.append(trial)
        summaries.append(summary)
        append_search_log(
            SEARCH_LOG,
            [{
                "event": "trial_completed",
                "run_id": run_id,
                "timestamp_utc": run_at,
                "order_id": "B4.1",
                "trial_id": trial_id,
                "lookback_sessions": lookback,
                "cost_model": {"spread_bps": cost.spread_bps, "borrow_annual": cost.borrow_annual},
                "cash_model": "lagged_13_week_Treasury_coupon_equivalent",
                "claim_eligible": claim_eligible,
                "selected_as_result": claim_eligible,
                "annual_net_geometric_return": summary["net"]["annual_geometric_return"],
                "annual_net_sharpe": summary["net"]["annual_sharpe"],
                "joint_independent_bet_equivalents": summary["joint_independent_bet_equivalents"],
            }],
        )
    primary = add_dsr(summaries[0], trials)
    original = load_json(ORIGINAL_REPORT)
    opened_sessions = [session for session in sessions if "2007-02-05" <= session <= "2015-12-31"]
    payload = {
        "schema_version": "lily_l1_cash_remediation_v1",
        "order_id": "B4.1",
        "hypothesis_id": "L-1",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "decision": "cash_gap_resolved_result_remains_scope_restricted",
        "produced_at": run_at,
        "producing_git_commit": git_commit(PROJECT_ROOT),
        "run_id": run_id,
        "contract_sha256": file_sha256(CONTRACT),
        "environment": interpreter_metadata(),
        "data": {
            "market_dataset_sha256": file_sha256(data_root / MARKET_RELATIVE),
            "cash_dataset_sha256": file_sha256(data_root / CASH_RELATIVE),
            "cash_source": "U.S. Treasury 13 WEEKS COUPON EQUIVALENT",
            "cash_source_coverage": cash_payload["coverage"],
            "opened_session_count": len(opened_sessions),
            "opened_sessions_with_nonzero_cash_return": sum(cash_returns[session] != 0.0 for session in opened_sessions),
            "maximum_session_accessed": max(opened_sessions),
            "untouched_validation_status": "sealed_not_accessed",
        },
        "original_B4_primary": {
            "producing_git_commit": original["producing_git_commit"],
            "report_digest_sha256": original["report_digest_sha256"],
            "annual_net_geometric_return": original["primary"]["net"]["annual_geometric_return"],
            "annual_net_sharpe": original["primary"]["net"]["annual_sharpe"],
            "cash_yield_return_units": original["primary"]["cost_decomposition_return_units"]["cash_yield"],
        },
        "remediated_primary": primary,
        "trials": summaries,
        "comparison": {
            "annual_net_geometric_return_change": primary["net"]["annual_geometric_return"] - original["primary"]["net"]["annual_geometric_return"],
            "annual_net_sharpe_change": primary["net"]["annual_sharpe"] - original["primary"]["net"]["annual_sharpe"],
            "cash_yield_return_units": primary["cost_decomposition_return_units"]["cash_yield"],
            "primary_selection_unchanged": True,
        },
        "tier_blockers": [
            "Corporate-action provenance is not an independent point-in-time archive.",
            "Historical expense coverage is not complete for every ETF session.",
            "Webull Thailand per-symbol fractional eligibility and OpenAPI fractional orders remain unverified.",
            "No adversarial review or E2 promotion was requested.",
        ],
        "guardrails": {
            "validation_data_opened": False,
            "credentials_used": False,
            "account_queried": False,
            "orders_sent": False,
            "paid_data_used": False,
        },
    }
    payload["report_digest_sha256"] = payload_sha256(payload)
    write_json(OUTPUT, payload)
    print(json.dumps({"status": "completed_E1", "run_id": run_id, "digest": payload["report_digest_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
