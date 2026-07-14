from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.environment import interpreter_metadata, require_configured_path
from lib.io import load_json, write_json
from lib.provenance import file_sha256, git_commit, payload_sha256
from lib.remediation import audit_corporate_actions, fee_coverage
from lib.report import render_markdown_report


CONTRACT = PROJECT_ROOT / "experiments" / "l_1_data_quality_remediation.json"
B4_REPORT = PROJECT_ROOT / "reports" / "experiments" / "l_1_baseline_summary.json"
CASH_REPORT = PROJECT_ROOT / "reports" / "data_quality" / "l_1_cash_remediation.json"
MAIN_JSON = PROJECT_ROOT / "reports" / "data_quality" / "l_1_data_quality_remediation.json"
MAIN_MARKDOWN = PROJECT_ROOT / "reports" / "data_quality" / "l_1_data_quality_remediation.md"
WEBULL_REPORT = PROJECT_ROOT / "reports" / "feasibility" / "webull_th_capability.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the B4.1 data-quality remediation reports.")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    data_root = args.data_root.resolve() if args.data_root else require_configured_path("LILY_DATA_ROOT")
    produced_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    fees = load_json(data_root / "normalized" / "official_fee_history_v1.json")
    cash = load_json(data_root / "normalized" / "treasury_13week_cash_v1.json")
    webull = load_json(data_root / "normalized" / "webull_th_public_capability_v1.json")
    b4 = load_json(B4_REPORT)
    cash_report = load_json(CASH_REPORT)
    corporate = audit_corporate_actions(data_root)
    fee_status = fee_coverage(fees)
    expense_units = float(b4["primary"]["cost_decomposition_return_units"]["expense_ratio"])
    observations = int(b4["primary"]["net"]["observations"])
    annualized_full_expense_credit = (1.0 + expense_units) ** (252.0 / observations) - 1.0
    optimistic_cagr = cash_report["remediated_primary"]["net"]["annual_geometric_return"] + annualized_full_expense_credit
    fee_decision_bound = {
        "method": "Optimistic additive bound: return 100% of all B4 booked ETF expense drag, annualized over the opened observations, on top of the cash-remediated CAGR.",
        "booked_expense_return_units": expense_units,
        "annualized_full_expense_credit": annualized_full_expense_credit,
        "cash_remediated_net_geometric_return": cash_report["remediated_primary"]["net"]["annual_geometric_return"],
        "optimistic_net_geometric_return_after_full_credit": optimistic_cagr,
        "can_turn_primary_positive": optimistic_cagr > 0.0,
        "interpretation": "decision_bounded_not_exact_path_reconstruction",
    }
    webull_report = _webull_report(webull, produced_at)
    write_json(WEBULL_REPORT, webull_report)
    workstreams = {
        "corporate_actions": {
            "outcome": "partially_resolved_within_provider",
            "locked_tolerance_status": corporate["status"],
            "passed_symbols": [row["symbol"] for row in corporate["rows"] if row["pass"]],
            "failed_symbols": [row["symbol"] for row in corporate["rows"] if not row["pass"]],
            "rows": corporate["rows"],
            "decision": "Arithmetic is reconciled within the cumulative tolerance for all symbols, but VGK and VWO fail the stricter daily tolerance and no point-in-time revision archive exists.",
        },
        "historical_expense_ratios": {
            "outcome": "partially_resolved_decision_bounded",
            "official_record_count": len(fees["records"]),
            "coverage": fee_status,
            "decision_bound": fee_decision_bound,
            "decision": "Official dated fees replace unsupported current-only assumptions as evidence, but gaps over 18 months remain. Even a full credit of all booked ETF expense drag leaves the cash-remediated primary CAGR negative.",
        },
        "cash_series": {
            "outcome": "resolved_E1",
            "source": "U.S. Treasury 13 WEEKS COUPON EQUIVALENT",
            "source_observations": len(cash["observations"]),
            "source_coverage": cash["coverage"],
            "cash_report_path": "reports/data_quality/l_1_cash_remediation.json",
            "original_net_geometric_return": cash_report["original_B4_primary"]["annual_net_geometric_return"],
            "remediated_net_geometric_return": cash_report["remediated_primary"]["net"]["annual_geometric_return"],
            "annual_net_geometric_return_change": cash_report["comparison"]["annual_net_geometric_return_change"],
            "decision": "The zero-cash blocker is removed for the opened window; the remediated result remains negative and E1.",
        },
        "webull_thailand": {
            "outcome": "public_capability_partially_resolved_account_scope_restricted",
            "report_path": "reports/feasibility/webull_th_capability.json",
            "manual_fractional_general": "verified_public",
            "candidate_ticker_green_diamond": "requires_account_observation",
            "openapi_fractional": "not_documented",
            "decision": "Manual fractional trading exists generally in Thailand, but exact candidate eligibility and fractional OpenAPI orders cannot be inferred from public documentation.",
        },
    }
    tier_blockers = [
        "Corporate-action point-in-time revision provenance is unavailable and VGK/VWO exceed the locked daily reconciliation tolerance.",
        "Six of eight historical fee series have at least one uncovered interval under the locked 18-month rule; DBC lacks a pre-2007 filing even though operations began in 2006.",
        "Webull Thailand green-diamond eligibility for the candidate tickers requires an account/app observation.",
        "Webull Thailand OpenAPI documentation does not explicitly support fractional quantity or notional orders.",
        "No adversarial review or E2 promotion was attempted.",
    ]
    payload = {
        "schema_version": "lily_l1_data_quality_remediation_report_v1",
        "order_id": "B4.1",
        "hypothesis_id": "L-1",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "decision": "scope_restricted_public_remediation_complete",
        "produced_at": produced_at,
        "producing_git_commit": git_commit(PROJECT_ROOT),
        "contract_sha256": file_sha256(CONTRACT),
        "environment": interpreter_metadata(),
        "source_datasets": {
            "treasury": {
                "storage_reference": "${LILY_DATA_ROOT}/normalized/treasury_13week_cash_v1.json",
                "sha256": file_sha256(data_root / "normalized" / "treasury_13week_cash_v1.json"),
            },
            "official_fees": {
                "storage_reference": "${LILY_DATA_ROOT}/normalized/official_fee_history_v1.json",
                "sha256": file_sha256(data_root / "normalized" / "official_fee_history_v1.json"),
            },
            "webull_public": {
                "storage_reference": "${LILY_DATA_ROOT}/normalized/webull_th_public_capability_v1.json",
                "sha256": file_sha256(data_root / "normalized" / "webull_th_public_capability_v1.json"),
            },
        },
        "workstreams": workstreams,
        "cash_remediation_digest": cash_report["report_digest_sha256"],
        "tier_blockers": tier_blockers,
        "guardrails": {
            "maximum_market_or_cash_date_accessed": "2015-12-31",
            "validation_data_opened": False,
            "credentials_used": False,
            "account_queried": False,
            "external_message_sent": False,
            "orders_sent": False,
            "paid_data_used": False,
        },
        "exact_next_safe_action": "Keep validation sealed. In the owner's Webull Thailand mobile app, record the green-diamond status for the ten current-capital candidates without placing or previewing an order, and request written broker confirmation of fractional OpenAPI support before any implementation study. Independent point-in-time corporate-action data remains an E2 prerequisite, not a reason to open validation now.",
    }
    payload["report_digest_sha256"] = payload_sha256(payload)
    write_json(MAIN_JSON, payload)
    MAIN_MARKDOWN.parent.mkdir(parents=True, exist_ok=True)
    MAIN_MARKDOWN.write_text(_markdown(payload), encoding="utf-8", newline="\n")
    print(json.dumps({"status": "completed_E1", "digest": payload["report_digest_sha256"]}, indent=2))
    return 0


def _webull_report(webull: dict[str, object], produced_at: str) -> dict[str, object]:
    findings = webull["findings"]
    assert isinstance(findings, dict)
    payload: dict[str, object] = {
        "schema_version": "lily_webull_th_capability_report_v1",
        "order_id": "B4.1",
        "hypothesis_id": "L-1",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "decision": "scope_restricted",
        "produced_at": produced_at,
        "producing_git_commit": git_commit(PROJECT_ROOT),
        "sources": webull["sources"],
        "facts": findings,
        "classifications": {
            "manual_mobile_fractional_general": "verified_public",
            "manual_market_order_regular_hours_only": "verified_public",
            "manual_four_decimal_precision": "verified_public",
            "candidate_ticker_green_diamond": "requires_account_observation",
            "openapi_us_stock_etf_general": "verified_public",
            "openapi_quantity_order": "verified_public",
            "openapi_fractional_or_notional": "not_documented",
        },
        "candidate_tickers": ["VTI", "VGK", "EWJ", "IPAC", "VWO", "IEF", "SCHP", "GLDM", "PDBC", "VNQI"],
        "tier_blockers": [
            "Public pages do not expose green-diamond eligibility by ticker.",
            "OpenAPI documentation uses QTY/number-of-shares orders and does not explicitly document fractional or notional orders.",
            "No account/app capability observation or broker confirmation was authorized.",
        ],
        "guardrails": {"credentials_used": False, "account_queried": False, "order_previewed": False, "orders_sent": False},
    }
    payload["report_digest_sha256"] = payload_sha256(payload)
    return payload


def _markdown(payload: dict[str, object]) -> str:
    workstreams = payload["workstreams"]
    assert isinstance(workstreams, dict)
    cash = workstreams["cash_series"]
    fees = workstreams["historical_expense_ratios"]
    corporate = workstreams["corporate_actions"]
    webull = workstreams["webull_thailand"]
    assert all(isinstance(value, dict) for value in (cash, fees, corporate, webull))
    sections = [
        ("สถานะ", f"- Order: `B4.1`\n- Evidence: `E1`\n- Edge claim: `none`\n- Decision: `{payload['decision']}`\n- Producing commit: `{payload['producing_git_commit']}`\n- Machine digest: `{payload['report_digest_sha256']}`"),
        ("Corporate actions", f"ผล: `{corporate['outcome']}`\n\nผ่าน tolerance รายวัน: {', '.join(corporate['passed_symbols'])}\n\nไม่ผ่าน tolerance รายวัน: {', '.join(corporate['failed_symbols'])}"),
        ("Historical expense ratios", f"ผล: `{fees['outcome']}`\n\nเอกสารทางการ: {fees['official_record_count']} รายการ\n\nผลตอบแทนสุทธิแบบ cash-remediated หลังคืน expense drag ทั้งหมดอย่างมองโลกดีที่สุด: {fees['decision_bound']['optimistic_net_geometric_return_after_full_credit']:.4%} ต่อปี"),
        ("Cash benchmark", f"ผล: `{cash['outcome']}`\n\nNet CAGR เดิม: {cash['original_net_geometric_return']:.4%}\n\nNet CAGR หลังใช้ Treasury cash: {cash['remediated_net_geometric_return']:.4%}\n\nเปลี่ยนแปลง: {cash['annual_net_geometric_return_change']:.4%} ต่อปี"),
        ("Webull Thailand", f"ผล: `{webull['outcome']}`\n\nManual fractional โดยทั่วไป: `verified_public`\n\nGreen diamond ราย ticker: `requires_account_observation`\n\nFractional OpenAPI: `not_documented`"),
        ("ข้อจำกัด", "\n".join(f"- {item}" for item in payload["tier_blockers"])),
        ("ขั้นต่อไปที่ปลอดภัย", str(payload["exact_next_safe_action"])),
    ]
    return render_markdown_report("Lily L-1 Data-Quality Remediation", sections)


if __name__ == "__main__":
    raise SystemExit(main())
