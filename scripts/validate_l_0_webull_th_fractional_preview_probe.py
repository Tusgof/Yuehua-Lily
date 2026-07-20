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
from scripts.validate_l_0_webull_th_fractional_preview_report import validate_report


DEFAULT_PATH = PROJECT_ROOT / "experiments" / "l_0_webull_th_fractional_preview_probe.json"
MANIFEST_PATH = PROJECT_ROOT / "experiments" / "locked_gates.jsonl"
GATE_ID = "l_0_webull_th_fractional_preview_probe_v1"
SOURCE_GATE_PATH = "experiments/l_1_shadow_accounting_activation_contract.json"
SOURCE_GATE_HASH = "e23a86840b7b2572abba16798d66914ddf2a734658a904493aa863fa23aaca8c"
QUANTITY_GRID = ["1", "0.1", "0.01", "0.001", "0.0001", "0.00001", "0.000001", "0.0000001"]
AUTH_PATHS = [
    "/openapi/auth/token/create",
    "/openapi/auth/token/check",
    "/openapi/auth/token/refresh",
]
REQUEST_TEMPLATE = {
    "combo_type": "NORMAL",
    "instrument_type": "EQUITY",
    "market": "US",
    "symbol": "VTI",
    "order_type": "MARKET",
    "entrust_type": "QTY",
    "support_trading_session": "CORE",
    "time_in_force": "DAY",
    "side": "BUY",
}
EXPECTED_ARTIFACT_HASHES = {
    "scripts/run_l_0_webull_th_fractional_preview_probe.py": "edec1e1658c74abb87d116b2680d4a292481bbce3eec6d18984634f2369aa06a",
    "scripts/validate_l_0_webull_th_fractional_preview_report.py": "a9c315e759556b38c62878cab8733398a184c8767387660b201a3fb91538d28e",
    "schemas/l_0_webull_th_fractional_preview_report.schema.json": "e803eef1b84a52a0fd36d51d83aef86420e63b490239dd2a5d2af2e47d8a33c5",
    "tests/fixtures/webull_fractional_preview/report_all_accepted.json": "154207a3e8acb0e2d1c625ee0960da732cca4478cc13a7b0212aebf648dcb88e",
    "tests/fixtures/webull_fractional_preview/report_mixed.json": "d57611471f78770026d58cea02938de4259f3617f891dfdf411eb775043113b6",
    "tests/fixtures/webull_fractional_preview/report_blocked.json": "d61f4e1c9f461b6c45c65957e7b83a20a34f9600bef075bfafa6057e28913191",
}
FIXTURE_DECISIONS = {
    "tests/fixtures/webull_fractional_preview/report_all_accepted.json": "all_tested_quantities_accepted",
    "tests/fixtures/webull_fractional_preview/report_mixed.json": "mixed_tested_quantity_acceptance",
    "tests/fixtures/webull_fractional_preview/report_blocked.json": "blocked_before_preview",
}


def validate_contract(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        contract = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"contract_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l0_webull_th_fractional_preview_probe_v1",
        "order_id": "B4.10",
        "hypothesis_id": "L-0",
        "linked_hypothesis_id": "L-1",
        "status": "locked_machinery_ready_execution_not_authorized",
        "evidence_ceiling": "E0",
        "edge_claim": "none",
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            blockers.append(f"field_mismatch:{field}")

    source = contract.get("source_gate", {})
    if source != {
        "gate_id": "l_1_shadow_accounting_activation_v2",
        "path": SOURCE_GATE_PATH,
        "sha256": SOURCE_GATE_HASH,
    }:
        blockers.append("source_gate_declaration_mismatch")
    source_path = PROJECT_ROOT / SOURCE_GATE_PATH
    if not source_path.is_file() or file_sha256(source_path) != SOURCE_GATE_HASH:
        blockers.append("source_gate_hash_mismatch")

    machinery = contract.get("machinery_state", {})
    expected_machinery = {
        "runner_hash_locked": True,
        "report_schema_and_validator_hash_locked": True,
        "fixtures_hash_locked": True,
        "execution_authorized_by_B4_10": False,
        "authentication_authorized_by_B4_10": False,
        "preview_authorized_by_B4_10": False,
        "activation_gate_required": "l_0_webull_th_fractional_preview_activation_v1",
        "activation_artifact_required": "experiments/l_0_webull_th_fractional_preview_activation.json",
        "activation_order_planned": "B4.11",
    }
    if machinery != expected_machinery:
        blockers.append("machinery_state_mismatch")

    environment = contract.get("environment", {})
    expected_environment = {
        "region": "th",
        "environment": "Webull Thailand UAT only",
        "host": "th-api.uat.webullbroker.com",
        "production_allowed": False,
        "sdk_package": "webull-openapi-python-sdk",
        "sdk_version_required": "2.0.13",
        "sdk_source_commit": "10889b59ae98a70ba03c5d6c6113709b8c05afb0",
        "python_runtime": "3.11",
        "credential_environment_names": ["WEBULL_UAT_APP_KEY", "WEBULL_UAT_APP_SECRET", "WEBULL_UAT_ACCOUNT_ID"],
        "credential_values_may_be_persisted_or_logged": False,
        "token_storage_reference": "${LOCALAPPDATA}/Yuehua-Lily/webull-uat-token",
    }
    if environment != expected_environment:
        blockers.append("uat_environment_mismatch")

    request = contract.get("request_boundary", {})
    expected_request = {
        "authentication_paths": AUTH_PATHS,
        "only_non_auth_request": {"method": "POST", "path": "/openapi/trade/order/preview"},
        "symbol": "VTI",
        "quantity_grid_in_request_order": QUANTITY_GRID,
        "maximum_authentication_requests": 3,
        "maximum_preview_requests": 8,
        "maximum_total_requests": 11,
        "automatic_retry": False,
        "amount_mode_allowed": False,
        "balance_or_positions_allowed": False,
        "place_replace_cancel_allowed": False,
        "order_history_open_detail_allowed": False,
        "paid_spend_cap_usd": 0,
        "request_template": REQUEST_TEMPLATE,
    }
    if request != expected_request:
        blockers.append("request_boundary_mismatch")

    sdk_path = contract.get("sdk_path_decision", {})
    if sdk_path.get("official_thailand_path") != "/openapi/trade/order/preview":
        blockers.append("official_thailand_path_mismatch")
    if sdk_path.get("pinned_sdk_preview_helper_path") != "/openapi/trade/stock/order/preview":
        blockers.append("sdk_helper_path_finding_mismatch")
    if "generic ApiRequest" not in str(sdk_path.get("runner_choice", "")):
        blockers.append("generic_request_choice_missing")

    declared_artifacts = {
        str(row.get("path", "")): str(row.get("sha256", ""))
        for row in contract.get("machine_artifacts", [])
        if isinstance(row, dict)
    }
    if declared_artifacts != EXPECTED_ARTIFACT_HASHES:
        blockers.append("machine_artifact_declaration_mismatch")
    for relative, expected_hash in EXPECTED_ARTIFACT_HASHES.items():
        target = PROJECT_ROOT / relative
        if not target.is_file() or file_sha256(target) != expected_hash:
            blockers.append(f"machine_artifact_hash_mismatch:{relative}")

    fixture_expectations = {
        str(row.get("path", "")): str(row.get("expected_decision", ""))
        for row in contract.get("fixture_expectations", [])
        if isinstance(row, dict)
    }
    if fixture_expectations != FIXTURE_DECISIONS:
        blockers.append("fixture_expectation_inventory_mismatch")
    for relative, decision in FIXTURE_DECISIONS.items():
        fixture_path = PROJECT_ROOT / relative
        fixture_result = validate_report(fixture_path)
        if fixture_result["status"] != "pass":
            blockers.append(f"fixture_validation_failed:{relative}")
            continue
        if load_json(fixture_path).get("decision") != decision:
            blockers.append(f"fixture_decision_mismatch:{relative}")

    attestation = contract.get("B4_10_request_attestation", {})
    expected_zero_fields = {
        "broker_api_calls", "authentication_calls", "preview_calls", "order_endpoint_calls",
        "orders_sent", "provider_api_calls", "validation_observations_opened", "paid_spend_usd",
    }
    if set(attestation) != expected_zero_fields:
        blockers.append("request_attestation_inventory_mismatch")
    for field in expected_zero_fields:
        if attestation.get(field) != 0:
            blockers.append(f"B4_10_request_attestation_nonzero:{field}")

    _validate_seal(contract.get("validation_return_seal", {}), blockers)
    if len(contract.get("claim_limits", [])) != 3:
        blockers.append("claim_limit_inventory_mismatch")
    hard_stops = " ".join(str(value) for value in contract.get("hard_stops", []))
    for required in ("B4.11", "credential", "th-api.uat.webullbroker.com", "POST /openapi/trade/order/preview", "ninth preview", "validation return", "real-money"):
        if required not in hard_stops:
            blockers.append(f"hard_stop_missing:{required}")
    if "separate B4.11 activation gate" not in str(contract.get("next_safe_action", "")):
        blockers.append("next_safe_action_mismatch")

    serialized = json.dumps(contract, ensure_ascii=False)
    for assignment in ("WEBULL_UAT_APP_KEY=", "WEBULL_UAT_APP_SECRET=", "WEBULL_UAT_ACCOUNT_ID="):
        if assignment in serialized:
            blockers.append("credential_assignment_forbidden")

    if path.resolve() == DEFAULT_PATH.resolve():
        _validate_active_manifest(path, blockers)
    return _result(path, blockers)


def _validate_seal(seal: Any, blockers: list[str]) -> None:
    if not isinstance(seal, dict):
        blockers.append("validation_seal_must_be_object")
        return
    if seal.get("untouched_start") != "2016-01-04" or seal.get("untouched_end") != "2026-06-30":
        blockers.append("validation_window_mismatch")
    if seal.get("status") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
    for field in ("prices_opened", "adjusted_prices_opened", "returns_opened", "signals_opened", "positions_opened", "regimes_opened", "benchmarks_opened", "pnl_opened"):
        if seal.get(field) is not False:
            blockers.append(f"validation_seal_false_field_mismatch:{field}")


def _validate_active_manifest(path: Path, blockers: list[str]) -> None:
    try:
        rows = load_jsonl(MANIFEST_PATH)
    except (FileNotFoundError, ValueError):
        blockers.append("locked_gate_manifest_unreadable")
        return
    matching = [row for row in rows if row.get("gate_id") == GATE_ID]
    if len(matching) != 1:
        blockers.append("active_gate_entry_mismatch")
        return
    row = matching[0]
    if row.get("artifact_path") != "experiments/l_0_webull_th_fractional_preview_probe.json":
        blockers.append("active_gate_artifact_path_mismatch")
    if row.get("validator_path") != "scripts/validate_l_0_webull_th_fractional_preview_probe.py":
        blockers.append("active_gate_validator_path_mismatch")
    if row.get("artifact_sha256") != file_sha256(path):
        blockers.append("active_gate_artifact_hash_mismatch")
    if row.get("validator_sha256") != file_sha256(Path(__file__)):
        blockers.append("active_gate_validator_hash_mismatch")


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "contract_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the locked B4.10 Webull Thailand fractional-preview machinery gate.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    result = validate_contract(args.contract)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
