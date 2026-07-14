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


DEFAULT_PATH = PROJECT_ROOT / "experiments" / "l_1_data_quality_remediation.json"


def validate_contract(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        payload = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"contract_unreadable:{exc.__class__.__name__}"])
    expected = {
        "schema_version": "lily_l1_data_quality_remediation_v1",
        "order_id": "B4.1",
        "hypothesis_id": "L-1",
        "status": "locked_before_remediation_measurement",
        "evidence_ceiling": "E1",
        "edge_claim": "none",
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            blockers.append(f"field_mismatch:{field}")
    boundary = payload.get("data_boundary", {})
    if boundary.get("maximum_market_or_cash_date_inclusive") != "2015-12-31":
        blockers.append("maximum_data_date_mismatch")
    if boundary.get("validation_status_required") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
    workstreams = payload.get("workstreams", {})
    if set(workstreams) != {"corporate_actions", "historical_expense_ratios", "cash_series", "webull_thailand"}:
        blockers.append("workstream_inventory_mismatch")
    corporate = workstreams.get("corporate_actions", {})
    if "0.002" not in str(corporate.get("pass_rule")) or "0.0005" not in str(corporate.get("pass_rule")):
        blockers.append("corporate_action_tolerances_not_locked")
    fee = workstreams.get("historical_expense_ratios", {})
    if "18 months" not in str(fee.get("full_resolution_rule")) or "removing 100%" not in str(fee.get("decision_bound_rule")):
        blockers.append("fee_resolution_rules_not_locked")
    cash = workstreams.get("cash_series", {})
    if cash.get("field") != "13 WEEKS COUPON EQUIVALENT" or cash.get("source_years") != list(range(2006, 2016)):
        blockers.append("cash_source_not_locked")
    if "next NYSE session" not in str(cash.get("availability_rule")):
        blockers.append("cash_lag_not_locked")
    webull = workstreams.get("webull_thailand", {})
    if len(webull.get("official_sources", [])) != 5:
        blockers.append("webull_source_inventory_mismatch")
    if "notional orders or fractional quantity" not in str(webull.get("openapi_capability_rule")):
        blockers.append("webull_fractional_proof_rule_not_locked")
    if len(payload.get("hard_stops", [])) < 5 or len(payload.get("required_outputs", [])) < 6:
        blockers.append("outputs_or_hard_stops_incomplete")
    return _result(path, blockers)


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "contract_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the locked L-1 data-quality remediation contract.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    result = validate_contract(args.contract)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
