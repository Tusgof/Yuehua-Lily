from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root


QUANTITY_GRID = ["1", "0.1", "0.01", "0.001", "0.0001", "0.00001", "0.000001", "0.0000001"]
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
AUTH_PATHS = {
    "/openapi/auth/token/create",
    "/openapi/auth/token/check",
    "/openapi/auth/token/refresh",
}
CLAIM_LIMITS = [
    "The report measures tested UAT preview acceptance only; it does not prove an order was placed or filled.",
    "The result may not be generalized from VTI UAT to all symbols or production.",
    "The report provides no execution-quality, strategy-edge, E2, deployment, or real-money evidence.",
]


def validate_report(path: Path) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        report = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"report_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l0_webull_th_fractional_preview_report_v1",
        "order_id": "B4.10",
        "hypothesis_id": "L-0",
        "linked_hypothesis_id": "L-1",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "environment": "webull_thailand_uat",
        "host": "th-api.uat.webullbroker.com",
    }
    for field, value in expected.items():
        if report.get(field) != value:
            blockers.append(f"field_mismatch:{field}")
    mode = report.get("report_mode")
    if mode not in {"synthetic_fixture", "uat_preview"}:
        blockers.append("invalid_report_mode")
    if not COMMIT_PATTERN.fullmatch(str(report.get("producing_git_commit", ""))):
        blockers.append("invalid_producing_git_commit")
    if not HASH_PATTERN.fullmatch(str(report.get("contract_sha256", ""))):
        blockers.append("invalid_contract_sha256")
    if mode == "synthetic_fixture" and report.get("activation_gate_id") is not None:
        blockers.append("synthetic_activation_gate_must_be_null")
    if mode == "uat_preview" and report.get("activation_gate_id") != "l_0_webull_th_fractional_preview_activation_v1":
        blockers.append("uat_activation_gate_mismatch")

    rows = report.get("rows", [])
    if not isinstance(rows, list):
        blockers.append("rows_must_be_list")
        rows = []
    if len(rows) > len(QUANTITY_GRID):
        blockers.append("row_count_exceeds_locked_grid")
    accepted: list[Decimal] = []
    rejected: list[Decimal] = []
    for index, row in enumerate(rows):
        label = f"row_{index + 1}"
        if not isinstance(row, dict):
            blockers.append(f"{label}:must_be_object")
            continue
        expected_quantity = QUANTITY_GRID[index]
        if row.get("quantity") != expected_quantity:
            blockers.append(f"{label}:quantity_order_mismatch")
        outcome = row.get("outcome")
        response_class = row.get("response_class")
        error_code = row.get("documented_error_code")
        if outcome == "accepted":
            if response_class != "success" or error_code is not None:
                blockers.append(f"{label}:accepted_shape_mismatch")
            accepted.append(Decimal(expected_quantity))
        elif outcome == "rejected":
            if response_class != "business_error" or not isinstance(error_code, str) or not error_code:
                blockers.append(f"{label}:rejected_shape_mismatch")
            rejected.append(Decimal(expected_quantity))
        else:
            blockers.append(f"{label}:invalid_outcome")
        if not HASH_PATTERN.fullmatch(str(row.get("response_sha256", ""))):
            blockers.append(f"{label}:invalid_response_sha256")

    expected_summary = {
        "tested_quantity_count": len(rows),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "smallest_accepted_tested_quantity": _decimal_string(min(accepted)) if accepted else None,
        "largest_rejected_tested_quantity": _decimal_string(max(rejected)) if rejected else None,
        "exact_broker_minimum_known": False,
    }
    if report.get("summary") != expected_summary:
        blockers.append("summary_mismatch")

    decision = report.get("decision")
    declared_blockers = report.get("blockers")
    if not isinstance(declared_blockers, list):
        blockers.append("blockers_must_be_list")
        declared_blockers = []
    if len(rows) == len(QUANTITY_GRID):
        expected_decision = (
            "all_tested_quantities_accepted"
            if len(accepted) == len(rows)
            else "all_tested_quantities_rejected"
            if len(rejected) == len(rows)
            else "mixed_tested_quantity_acceptance"
        )
        if declared_blockers:
            blockers.append("completed_grid_cannot_have_blockers")
    else:
        expected_decision = "blocked_before_preview" if not rows else "blocked_after_partial_preview"
        if not declared_blockers:
            blockers.append("blocked_report_requires_blocker")
    if decision != expected_decision:
        blockers.append(f"decision_mismatch:expected_{expected_decision}")

    _validate_attestation(
        report.get("request_attestation", {}),
        mode,
        len(rows),
        bool(declared_blockers),
        blockers,
    )
    _validate_seal(report.get("validation_return_seal", {}), blockers)
    if report.get("claim_limits") != CLAIM_LIMITS:
        blockers.append("claim_limits_mismatch")
    return _result(path, blockers)


def _validate_attestation(
    attestation: Any,
    mode: Any,
    row_count: int,
    has_blockers: bool,
    blockers: list[str],
) -> None:
    if not isinstance(attestation, dict):
        blockers.append("request_attestation_must_be_object")
        return
    paths = attestation.get("authentication_paths", [])
    if not isinstance(paths, list) or any(path not in AUTH_PATHS for path in paths):
        blockers.append("authentication_path_inventory_invalid")
        paths = []
    preview_calls = attestation.get("preview_request_count")
    if mode == "uat_preview":
        if not isinstance(preview_calls, int) or preview_calls < row_count or preview_calls > row_count + 1:
            blockers.append("request_attestation_mismatch:preview_request_count")
        elif preview_calls != row_count and not has_blockers:
            blockers.append("unclassified_preview_request_requires_blocker")
    elif preview_calls != 0:
        blockers.append("request_attestation_mismatch:preview_request_count")
    expected_preview_calls = preview_calls if isinstance(preview_calls, int) else 0
    expected_auth_calls = len(paths) if mode == "uat_preview" else 0
    if mode == "synthetic_fixture" and paths:
        blockers.append("synthetic_fixture_must_have_no_authentication_paths")
    expected = {
        "authentication_request_count": expected_auth_calls,
        "preview_path": "/openapi/trade/order/preview",
        "synthetic_preview_row_count": row_count if mode == "synthetic_fixture" else 0,
        "total_broker_request_count": expected_auth_calls + expected_preview_calls,
        "forbidden_request_count": 0,
        "production_request_count": 0,
        "order_mutation_or_query_count": 0,
        "orders_sent": 0,
        "raw_response_persisted": False,
        "credential_or_account_\u0069dentifier_persisted": False,
        "paid_spend_usd": 0,
    }
    for field, value in expected.items():
        if attestation.get(field) != value:
            blockers.append(f"request_attestation_mismatch:{field}")
    if expected_auth_calls > 3 or expected_preview_calls > 8 or expected_auth_calls + expected_preview_calls > 11:
        blockers.append("request_cap_exceeded")


def _validate_seal(seal: Any, blockers: list[str]) -> None:
    if not isinstance(seal, dict) or seal.get("status") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
        return
    for field in (
        "prices_opened",
        "adjusted_prices_opened",
        "returns_opened",
        "signals_opened",
        "positions_opened",
        "regimes_opened",
        "benchmarks_opened",
        "pnl_opened",
    ):
        if seal.get(field) is not False:
            blockers.append(f"validation_seal_false_field_mismatch:{field}")


def _decimal_string(value: Decimal) -> str:
    try:
        rendered = format(value, "f")
    except InvalidOperation:
        return "invalid"
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "report_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Lily Webull Thailand fractional-preview report.")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate_report(args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
