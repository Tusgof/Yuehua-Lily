from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root
from lib.provenance import file_sha256, payload_sha256


DEFAULT_JSON = PROJECT_ROOT / "reports" / "data_quality" / "l_1_data_quality_remediation.json"
DEFAULT_MARKDOWN = PROJECT_ROOT / "reports" / "data_quality" / "l_1_data_quality_remediation.md"
CONTRACT = PROJECT_ROOT / "experiments" / "l_1_data_quality_remediation.json"
CASH = PROJECT_ROOT / "reports" / "data_quality" / "l_1_cash_remediation.json"
WEBULL = PROJECT_ROOT / "reports" / "feasibility" / "webull_th_capability.json"
EXPECTED_CONTRACT_HASH = "1fe4957f667bdf367d230048ac279fbdf9b4b2b109540dcdf5a54900e1c7cdb9"


def validate_report(
    report_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MARKDOWN,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        report = load_json(report_path)
        markdown = markdown_path.read_text(encoding="utf-8")
        cash = load_json(CASH)
        webull = load_json(WEBULL)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result([f"artifact_unreadable:{exc.__class__.__name__}"], report_path)
    expected = {
        "schema_version": "lily_l1_data_quality_remediation_report_v1",
        "order_id": "B4.1",
        "hypothesis_id": "L-1",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "decision": "scope_restricted_public_remediation_complete",
    }
    for field, value in expected.items():
        if report.get(field) != value:
            blockers.append(f"field_mismatch:{field}")
    if file_sha256(CONTRACT) != EXPECTED_CONTRACT_HASH or report.get("contract_sha256") != EXPECTED_CONTRACT_HASH:
        blockers.append("locked_contract_hash_mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", str(report.get("producing_git_commit", ""))):
        blockers.append("producing_git_commit_invalid")
    workstreams = report.get("workstreams", {})
    if set(workstreams) != {"corporate_actions", "historical_expense_ratios", "cash_series", "webull_thailand"}:
        blockers.append("workstream_inventory_mismatch")
    else:
        corporate = workstreams["corporate_actions"]
        if corporate.get("failed_symbols") != ["VGK", "VWO"] or len(corporate.get("rows", [])) != 8:
            blockers.append("corporate_action_result_mismatch")
        fees = workstreams["historical_expense_ratios"]
        if fees.get("official_record_count") != 60 or fees.get("decision_bound", {}).get("can_turn_primary_positive") is not False:
            blockers.append("fee_decision_bound_mismatch")
        cash_result = workstreams["cash_series"]
        if cash_result.get("outcome") != "resolved_E1" or cash_result.get("remediated_net_geometric_return", 1.0) >= 0.0:
            blockers.append("cash_remediation_result_mismatch")
        webull_result = workstreams["webull_thailand"]
        if webull_result.get("candidate_ticker_green_diamond") != "requires_account_observation" or webull_result.get("openapi_fractional") != "not_documented":
            blockers.append("webull_classification_mismatch")
    guardrails = report.get("guardrails", {})
    if guardrails.get("maximum_market_or_cash_date_accessed") != "2015-12-31":
        blockers.append("maximum_data_date_mismatch")
    if any(value for key, value in guardrails.items() if key != "maximum_market_or_cash_date_accessed"):
        blockers.append("forbidden_activity_recorded")
    if cash.get("data", {}).get("untouched_validation_status") != "sealed_not_accessed":
        blockers.append("cash_validation_status_mismatch")
    if [row.get("trial_id") for row in cash.get("trials", [])] != ["primary_60", "sensitivity_40", "sensitivity_80", "sensitivity_low_cost", "sensitivity_severe_cost"]:
        blockers.append("cash_trial_inventory_mismatch")
    if webull.get("classifications", {}).get("openapi_fractional_or_notional") != "not_documented":
        blockers.append("webull_machine_report_mismatch")
    if not report.get("tier_blockers") or not report.get("exact_next_safe_action"):
        blockers.append("blockers_or_next_action_missing")
    digest = report.get("report_digest_sha256")
    digest_payload = dict(report)
    digest_payload.pop("report_digest_sha256", None)
    if digest != payload_sha256(digest_payload):
        blockers.append("report_digest_mismatch")
    for required in (str(digest), str(report.get("producing_git_commit")), "E1", "requires_account_observation", "not_documented"):
        if not required or required not in markdown:
            blockers.append(f"markdown_missing_machine_value:{required}")
    return _result(blockers, report_path)


def _result(blockers: list[str], report_path: Path) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "report_path": relative_to_root(report_path, PROJECT_ROOT)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the B4.1 remediation report pack.")
    parser.add_argument("--report", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    result = validate_report(args.report, args.markdown)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
