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
from lib.report import render_markdown_report
from lib.search_log import append_search_log
from lib.trend_baseline import CostModel, add_dsr, load_market, run_trial, trial_summary


PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_1_baseline_preregistration.json"
PREREGISTRATION_VALIDATOR = PROJECT_ROOT / "scripts" / "validate_l_1_baseline_preregistration.py"
DATA_REGISTRY = PROJECT_ROOT / "datasets" / "registry.json"
SEARCH_LOG = PROJECT_ROOT / "reports" / "experiments" / "l_1_search_log.jsonl"
SUMMARY_JSON = PROJECT_ROOT / "reports" / "experiments" / "l_1_baseline_summary.json"
SUMMARY_MARKDOWN = PROJECT_ROOT / "reports" / "experiments" / "l_1_baseline_summary.md"
ADVERSARIAL = PROJECT_ROOT / "reports" / "adversarial" / "l_1_baseline_review.json"


LOCKED_TRIALS = (
    ("primary_60", 60, CostModel(spread_bps=25.0, borrow_annual=0.03), True),
    ("sensitivity_40", 40, CostModel(spread_bps=25.0, borrow_annual=0.03), False),
    ("sensitivity_80", 80, CostModel(spread_bps=25.0, borrow_annual=0.03), False),
    ("sensitivity_low_cost", 60, CostModel(spread_bps=12.5, borrow_annual=0.03), False),
    ("sensitivity_severe_cost", 60, CostModel(spread_bps=50.0, borrow_annual=0.06), False),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the locked L-1 falsification-window baseline.")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    data_root = args.data_root.resolve() if args.data_root else require_configured_path("LILY_DATA_ROOT")
    dataset_path = data_root / "normalized" / "l1_yahoo_daily_v1.json"
    run_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    run_id = "l1-falsification-" + run_at.replace(":", "").replace("-", "")
    append_search_log(
        SEARCH_LOG,
        [{
            "event": "run_started", "run_id": run_id, "timestamp_utc": run_at,
            "hypothesis_id": "L-1", "opened_window": "falsification_2007-02-05_to_2015-12-31",
            "untouched_validation_status": "sealed_not_accessed", "dataset_sha256": file_sha256(dataset_path),
        }],
    )
    market = load_market(load_json(dataset_path))
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
                "event": "trial_completed", "run_id": run_id, "timestamp_utc": run_at,
                "trial_id": trial_id, "lookback_sessions": lookback,
                "cost_model": {"spread_bps": cost.spread_bps, "borrow_annual": cost.borrow_annual},
                "claim_eligible": claim_eligible, "annual_net_geometric_return": summary["net"]["annual_geometric_return"],
                "annual_net_sharpe": summary["net"]["annual_sharpe"],
                "joint_independent_bet_equivalents": summary["joint_independent_bet_equivalents"],
                "selected_as_result": claim_eligible,
            }],
        )
    primary = add_dsr(summaries[0], trials)
    registry = load_json(DATA_REGISTRY)
    datasets = [row for row in registry["datasets"] if "L-1" in row.get("hypothesis_ids", [])]
    tier_blockers = [
        "Yahoo public chart data is not a point-in-time revision archive and provider close is split-normalized.",
        "The fixed universe contains surviving proxies and does not represent the historical ETF opportunity set.",
        "Current expense-ratio proxies replace unavailable then-current fee histories.",
        "Cash return is set to zero because a matched point-in-time public cash series was not acquired.",
        "Market impact is not modeled.",
        "Webull Thailand fractional eligibility and OpenAPI capability remain unverified, so the current-capital branch was not run.",
        "No independent adversarial review has been performed; E2 promotion is forbidden.",
    ]
    funded = bool(primary["MinTRL_falsify_funded"])
    decision = "not_falsified_but_not_validated" if funded else "underfunded_scope_restricted"
    payload = {
        "schema_version": "lily_l1_baseline_summary_v1",
        "hypothesis_id": "L-1",
        "experiment_id": "L1-BASELINE",
        "run_id": run_id,
        "produced_at": run_at,
        "producing_git_commit": git_commit(PROJECT_ROOT),
        "evidence_tier": "E1",
        "edge_claim": "none",
        "decision": decision,
        "tier_blockers": tier_blockers,
        "locked_gate": {
            "preregistration_sha256": file_sha256(PREREGISTRATION),
            "validator_sha256": file_sha256(PREREGISTRATION_VALIDATOR),
            "expected_preregistration_sha256": "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29",
            "expected_validator_sha256": "c568f5db8236e253e63056ed2797ead9259397d293c478e7f0abf53bfda70232",
        },
        "environment": interpreter_metadata(),
        "data": {
            "dataset_ids": [row["dataset_id"] for row in datasets],
            "dataset_hashes": {row["dataset_id"]: row["hashes"] for row in datasets},
            "opened_coverage": {"warmup_start": "2006-02-03", "falsification_start": "2007-02-05", "falsification_end": "2015-12-31"},
            "maximum_session_accessed": max(trials[0].dates),
            "untouched_validation": {"start": "2016-01-04", "end": "2026-06-30", "status": "sealed_not_accessed"},
            "integrity_status": "scope_restricted",
            "paid_amount_usd": 0,
            "credentials_used": False,
            "network_used_for_acquisition": True,
        },
        "search": {
            "log_path": "reports/experiments/l_1_search_log.jsonl",
            "locked_trial_count": 5,
            "completed_trial_count_this_run": 5,
            "primary_trial_id": "primary_60",
            "selection_rule_respected": True,
        },
        "trials": summaries,
        "primary": primary,
        "dual_MinTRL_and_unlock": {
            "falsification_required_joint_independent_bet_equivalents": 3850,
            "falsification_actual_joint_independent_bet_equivalents": primary["joint_independent_bet_equivalents"],
            "falsification_funded": funded,
            "validation_binding_required_joint_independent_bet_equivalents": 8673,
            "validation_capacity_verified": False,
            "unlock_decision": "remain_sealed",
            "unlock_reason": "Data-integrity and implementability blockers remain, validation capacity was not verified without opening data, and no E2 review was attempted.",
        },
        "current_capital_branch": {
            "status": "scope_restricted_not_run",
            "capital_scenarios_usd": [1000, 2000],
            "reason": "Locked broker eligibility snapshot is incomplete; fewer than eight verified sleeves cannot be assumed.",
        },
        "limitations": {
            "survivorship": "Fixed surviving-proxy study only.",
            "inception_and_backfill": "No pre-inception rows were accepted; provider revision history is unavailable.",
            "corporate_actions": "Cash distributions were reconstructed from events; provider close is already split-normalized.",
            "currency": "All instruments trade in USD, but non-US underlying FX exposure remains economic exposure.",
            "futures_roll": "Not applicable; futures were excluded and no futures rows were read.",
            "broker": "No account, permission, credential, paper order, or real order was accessed.",
        },
        "source_inventory": {
            "market_data": {
                "provider": "Yahoo Finance chart API",
                "endpoint_pattern": "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                "license_note": "Publicly accessible endpoint; provider terms apply and redistribution rights are not asserted.",
            },
            "methodology": load_json(PREREGISTRATION)["wiki_sources"],
        },
        "adversarial_review": {"status": "not_started_E1_no_promotion", "reviewer_is_independent": False},
        "guardrails": {
            "validation_data_opened": False, "broker_credentials_used": False, "account_queried": False,
            "orders_sent": False, "paper_trades_sent": False, "paid_data_used": False,
        },
        "exact_next_safe_action": "Keep validation sealed. Resolve the corporate-action, historical fee, cash-series, and broker-eligibility gaps under a new bounded data-quality order; then independently verify whether the sealed window can fund all validation nulls before any unlock request.",
    }
    payload["report_digest_sha256"] = payload_sha256(payload)
    write_json(SUMMARY_JSON, payload)
    SUMMARY_MARKDOWN.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MARKDOWN.write_text(_markdown(payload), encoding="utf-8", newline="\n")
    write_json(
        ADVERSARIAL,
        {
            "schema_version": "lily_adversarial_review_status_v1",
            "hypothesis_id": "L-1",
            "evidence_tier": "E1",
            "promotion_requested": False,
            "status": "not_started_E1_no_promotion",
            "reviewer_is_independent": False,
            "unresolved_critical_issues": tier_blockers,
            "note": "This is an honest status artifact, not an adversarial review.",
            "producing_git_commit": payload["producing_git_commit"],
        },
    )
    print(json.dumps({"status": "completed_E1", "decision": decision, "report": str(SUMMARY_JSON.name), "digest": payload["report_digest_sha256"]}, indent=2))
    return 0


def _markdown(payload: dict[str, object]) -> str:
    primary = payload["primary"]
    assert isinstance(primary, dict)
    net = primary["net"]
    assert isinstance(net, dict)
    unlock = payload["dual_MinTRL_and_unlock"]
    assert isinstance(unlock, dict)
    sections = [
        ("สถานะหลักฐาน", f"- Hypothesis: `L-1`\n- ระดับ: `E1`\n- Edge claim: `none`\n- ข้อสรุป: `{payload['decision']}`\n- Producing commit: `{payload['producing_git_commit']}`\n- Machine digest: `{payload['report_digest_sha256']}`"),
        ("ผลของ primary_60", f"ผลตอบแทนเรขาคณิตสุทธิต่อปี: {net['annual_geometric_return']:.4%}\n\nSharpe สุทธิต่อปี: {net['annual_sharpe']:.4f}\n\nMaximum drawdown: {net['maximum_drawdown']:.4%}\n\nจำนวน joint independent-bet equivalents: {primary['joint_independent_bet_equivalents']:.2f}"),
        ("MinTRL และข้อมูลที่ปิดผนึก", f"ต้องการฝั่ง falsification: {unlock['falsification_required_joint_independent_bet_equivalents']:,}\n\nได้จริง: {unlock['falsification_actual_joint_independent_bet_equivalents']:.2f}\n\nสถานะ validation: `sealed_not_accessed`\n\nคำตัดสินการเปิดข้อมูล: `remain_sealed`"),
        ("ข้อจำกัดสำคัญ", "\n".join(f"- {item}" for item in payload["tier_blockers"])),
        ("สิ่งที่ยังห้ามสรุป", "ผลนี้ไม่ใช่หลักฐานระดับ E2 ไม่ยืนยันว่ามี edge ไม่อนุมัติ paper trading และไม่อนุมัติเงินจริง"),
        ("ขั้นต่อไปที่ปลอดภัย", str(payload["exact_next_safe_action"])),
    ]
    return render_markdown_report("Lily L-1 Baseline — Falsification Window", sections)


if __name__ == "__main__":
    raise SystemExit(main())
