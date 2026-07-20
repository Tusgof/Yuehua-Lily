from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, load_jsonl, relative_to_root
from lib.provenance import file_sha256


DEFAULT_PATH = PROJECT_ROOT / "experiments" / "l_1_shadow_accounting_activation_contract.json"
MANIFEST_PATH = PROJECT_ROOT / "experiments" / "locked_gates.jsonl"
PREDECESSOR_GATE_ID = "l_1_shadow_accounting_activation_v1"
ACTIVE_GATE_ID = "l_1_shadow_accounting_activation_v2"
EXPECTED_SOURCE_HASHES = {
    "experiments/l_1_prospective_shadow_accounting_preregistration.json": "ee17ecc385c0fadd808d7c5e5a5af0ab426c133994ff54ef4071e9a242c45d88",
    "experiments/inputs/b4_8_webull_shadow_accounting_capability_inventory.json": "61ec6cb110adb5246a3e6e31540b1685f2a4a31aea1a7925bbb088a6d3d7156c",
    "experiments/l_0_webull_th_read_only_capability_probe.json": "7307f6faf1fcbefa6f0e803311ac624901ed01cebb2d2d347c52d6186dfbbf82",
    "reports/feasibility/l_0_webull_th_read_only_capability.json": "365f0d4ce5db85cc9356f11457ac9776a79fc2ca290c85813f9428c89815f630",
}
EXPECTED_QUANTITIES = [
    "1",
    "0.1",
    "0.01",
    "0.001",
    "0.0001",
    "0.00001",
    "0.000001",
    "0.0000001",
]


def validate_contract(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        contract = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"artifact_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l1_webull_api_scope_and_fractional_preview_v2",
        "order_id": "B4.9",
        "hypothesis_id": "L-1",
        "linked_hypothesis_id": "L-0",
        "status": "locked_scope_decision_and_preview_probe",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "supersedes_gate_id": PREDECESSOR_GATE_ID,
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            blockers.append(f"field_mismatch:{field}")

    decision = contract.get("decision", {})
    expected_decision = {
        "published_thailand_api_inventory_accepted_as_current_scope": True,
        "webull_account_corporate_action_ledger_classification": "unavailable_under_published_thailand_api",
        "b4_7_three_stream_dry_run_status": "closed_not_started_due_unavailable_broker_ledger",
        "written_webull_confirmation_required_before_next_step": False,
        "fractional_preview_probe_status": "designed_not_executed",
        "validation_unlock_authorized": False,
        "paper_or_real_order_authorized": False,
        "real_money_authorized": False,
    }
    if decision != expected_decision:
        blockers.append("scope_decision_mismatch")

    role = contract.get("webull_role_boundary", {})
    if "corporate-action" not in str(role.get("forbidden_role", "")):
        blockers.append("webull_forbidden_role_missing")
    if "shared UAT" not in str(role.get("paper_ledger_substitution_rule", "")):
        blockers.append("shared_uat_not_rejected_as_ledger")

    accounting = contract.get("corporate_action_accounting_scope", {})
    if accounting.get("research_streams") != [
        "alpha_vantage_current_snapshot_shadow_ledger",
        "lily_yahoo_event_strategy_accounting",
    ]:
        blockers.append("two_source_inventory_mismatch")
    if accounting.get("classification") != "two_source_shadow_accounting_with_explicit_E1_limit":
        blockers.append("accounting_scope_classification_mismatch")
    if accounting.get("collection_authorized_by_B4_9") is not False:
        blockers.append("B4_9_must_not_authorize_collection")

    preview = contract.get("fractional_preview_probe", {})
    if preview.get("execution_authorized_by_B4_9") is not False:
        blockers.append("B4_9_must_not_authorize_preview_execution")
    if preview.get("host") != "th-api.uat.webullbroker.com":
        blockers.append("preview_host_mismatch")
    if preview.get("production_host_or_account_allowed") is not False:
        blockers.append("production_preview_must_be_forbidden")
    if preview.get("shared_uat_account_allowed_for_stateless_preview_only") is not True:
        blockers.append("shared_uat_preview_scope_mismatch")
    if preview.get("shared_uat_balance_positions_or_orders_allowed") is not False:
        blockers.append("shared_uat_state_access_must_be_forbidden")
    if preview.get("only_non_auth_path") != {
        "method": "POST",
        "path": "/openapi/trade/order/preview",
    }:
        blockers.append("preview_path_mismatch")
    if preview.get("quantity_grid_in_request_order") != EXPECTED_QUANTITIES:
        blockers.append("quantity_grid_mismatch")
    if preview.get("maximum_authentication_requests") != 3:
        blockers.append("authentication_request_cap_mismatch")
    if preview.get("maximum_preview_requests") != len(EXPECTED_QUANTITIES):
        blockers.append("preview_request_cap_mismatch")
    if preview.get("maximum_total_requests") != 11:
        blockers.append("total_request_cap_mismatch")
    if preview.get("automatic_retry") is not False or preview.get("paid_spend_cap_usd") != 0:
        blockers.append("retry_or_spend_boundary_mismatch")
    template = preview.get("request_template", {})
    if template != {
        "combo_type": "NORMAL",
        "instrument_type": "EQUITY",
        "market": "US",
        "symbol": "VTI",
        "order_type": "MARKET",
        "entrust_type": "QTY",
        "support_trading_session": "CORE",
        "time_in_force": "DAY",
        "side": "BUY",
    }:
        blockers.append("preview_request_template_mismatch")
    if "Do not test AMOUNT" not in str(preview.get("amount_mode_rule", "")):
        blockers.append("amount_mode_exclusion_missing")
    if "may not be generalized" not in str(preview.get("scope_rule", "")):
        blockers.append("preview_scope_limit_missing")

    attestation = contract.get("B4_9_request_attestation", {})
    for field in (
        "broker_api_calls",
        "authentication_calls",
        "preview_calls",
        "order_endpoint_calls",
        "orders_sent",
        "provider_api_calls",
        "validation_observations_opened",
        "paid_spend_usd",
    ):
        if attestation.get(field) != 0:
            blockers.append(f"B4_9_request_attestation_nonzero:{field}")
    if attestation.get("public_document_requests") != 3:
        blockers.append("public_document_request_attestation_mismatch")

    if len(contract.get("future_execution_requirements", [])) != 5:
        blockers.append("future_execution_requirement_inventory_mismatch")
    if len(contract.get("hard_stops", [])) != 8:
        blockers.append("hard_stop_inventory_mismatch")
    _validate_seal(contract.get("validation_return_seal", {}), blockers)
    if len(contract.get("claim_limits", [])) != 4:
        blockers.append("claim_limit_inventory_mismatch")
    if "Implement and lock B4.10" not in str(contract.get("next_safe_action", "")):
        blockers.append("next_safe_action_mismatch")

    declared_sources = {
        str(row.get("path", "")): str(row.get("sha256", ""))
        for row in contract.get("source_lineage", [])
        if isinstance(row, dict)
    }
    for relative, expected_hash in EXPECTED_SOURCE_HASHES.items():
        target = PROJECT_ROOT / relative
        if not target.is_file() or file_sha256(target) != expected_hash:
            blockers.append(f"source_hash_mismatch:{relative}")
        if declared_sources.get(relative) != expected_hash:
            blockers.append(f"declared_source_hash_mismatch:{relative}")

    if path.resolve() == DEFAULT_PATH.resolve():
        _validate_active_manifest(path, blockers)
    return _result(path, blockers)


def _validate_active_manifest(path: Path, blockers: list[str]) -> None:
    try:
        rows = load_jsonl(MANIFEST_PATH)
    except (FileNotFoundError, ValueError):
        blockers.append("locked_gate_manifest_unreadable")
        return
    predecessor = [row for row in rows if row.get("gate_id") == PREDECESSOR_GATE_ID]
    active = [row for row in rows if row.get("gate_id") == ACTIVE_GATE_ID]
    if len(predecessor) != 1:
        blockers.append("predecessor_gate_entry_mismatch")
    if len(active) != 1:
        blockers.append("active_gate_entry_mismatch")
        return
    row = active[0]
    if row.get("supersedes_gate_id") != PREDECESSOR_GATE_ID:
        blockers.append("active_gate_supersession_mismatch")
    if row.get("artifact_path") != "experiments/l_1_shadow_accounting_activation_contract.json":
        blockers.append("active_gate_artifact_path_mismatch")
    if row.get("validator_path") != "scripts/validate_l_1_shadow_accounting_activation_contract.py":
        blockers.append("active_gate_validator_path_mismatch")
    if row.get("artifact_sha256") != file_sha256(path):
        blockers.append("active_gate_artifact_hash_mismatch")
    validator = PROJECT_ROOT / "scripts" / "validate_l_1_shadow_accounting_activation_contract.py"
    if row.get("validator_sha256") != file_sha256(validator):
        blockers.append("active_gate_validator_hash_mismatch")


def _validate_seal(seal: dict[str, Any], blockers: list[str]) -> None:
    if seal.get("untouched_start") != "2016-01-04" or seal.get("untouched_end") != "2026-06-30":
        blockers.append("validation_window_mismatch")
    if seal.get("status") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
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


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "contract_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Lily B4.9 Webull API scope and fractional-preview gate.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    result = validate_contract(args.contract)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
