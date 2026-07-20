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
from lib.provenance import file_sha256
from scripts.validate_l_1_shadow_accounting_report import validate_report


DEFAULT_PATH = PROJECT_ROOT / "experiments" / "l_1_shadow_accounting_activation_contract.json"
EXPECTED_BLOCKERS = [
    "dedicated_owner_controlled_thailand_test_account_not_verified",
    "auditable_thailand_account_corporate_action_cash_ledger_not_documented",
    "auditable_thailand_account_corporate_action_unit_ledger_not_documented",
    "broker_minimum_fractional_share_quantum_not_documented",
]
EXPECTED_FILE_HASHES = {
    "experiments/l_1_prospective_shadow_accounting_preregistration.json": "ee17ecc385c0fadd808d7c5e5a5af0ab426c133994ff54ef4071e9a242c45d88",
    "scripts/validate_l_1_prospective_shadow_accounting_preregistration.py": "e42631efac2d6a64bb74df98ba35653a7f5b15558e69415954843fc4fbbd3a4a",
    "experiments/inputs/b4_8_webull_shadow_accounting_capability_inventory.json": "61ec6cb110adb5246a3e6e31540b1685f2a4a31aea1a7925bbb088a6d3d7156c",
    "schemas/l_1_shadow_accounting_event.schema.json": "6b91b968e7b3f56e01c825ddb4d7a7c75095b3e958eb70b707379888f1311ac6",
    "schemas/l_1_shadow_accounting_report.schema.json": "df78ea1a3c4c345b55b13978f02d2611a9a75ff2d8d39f7cf36841fbfd525032",
    "scripts/validate_l_1_shadow_accounting_report.py": "5694524275119242acd40e69f74606006ae4317be733fcef42086aedb3ab4de1",
    "tests/fixtures/shadow_accounting/report_no_material.json": "979e1d18e7b14f54b2945cc6811bb7635bf97144afd54084e1c458e4109e1d58",
    "tests/fixtures/shadow_accounting/report_material_breach.json": "da1029e7f5683636756db71f3c3fd91fc63be933e0790448cbd4e5848bf79959",
    "tests/fixtures/shadow_accounting/report_activation_blocked.json": "77d02eeec175d6e0e375bf5e5f93be135f4d169639cc0622d3bc7ba741d37852",
}


def validate_contract(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        contract = load_json(path)
        inventory = load_json(PROJECT_ROOT / "experiments" / "inputs" / "b4_8_webull_shadow_accounting_capability_inventory.json")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"artifact_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l1_shadow_accounting_activation_contract_v1",
        "order_id": "B4.8",
        "hypothesis_id": "L-1",
        "status": "locked_activation_blocked",
        "evidence_tier": "E0",
        "edge_claim": "none",
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            blockers.append(f"field_mismatch:{field}")

    decision = contract.get("decision", {})
    expected_decision = {
        "activation_status": "activation_blocked_before_observation",
        "dry_run_started": False,
        "forward_start_marker_committed": False,
        "paper_or_test_order_authorized": False,
        "production_account_authorized": False,
        "provider_acquisition_authorized": False,
        "validation_unlock_authorized": False,
        "real_money_authorized": False,
    }
    if decision != expected_decision:
        blockers.append("decision_boundary_mismatch")
    if contract.get("activation_blockers") != EXPECTED_BLOCKERS:
        blockers.append("activation_blocker_inventory_mismatch")
    if inventory.get("decision") != "activation_blocked_before_observation" or inventory.get("activation_blockers") != EXPECTED_BLOCKERS:
        blockers.append("capability_inventory_decision_mismatch")
    attestation = inventory.get("request_attestation", {})
    if any(value != 0 for value in attestation.values()):
        blockers.append("capability_inventory_request_attestation_nonzero")

    environment = contract.get("environment_contract", {})
    if environment.get("required_environment") != "dedicated_owner_controlled_webull_thailand_test_account":
        blockers.append("required_environment_mismatch")
    for field in ("shared_test_account_allowed", "production_host_allowed", "production_account_fallback_allowed"):
        if environment.get(field) is not False:
            blockers.append(f"environment_false_field_mismatch:{field}")
    if environment.get("runtime_network_allowlist") != [] or environment.get("runtime_order_path_allowlist") != []:
        blockers.append("runtime_allowlist_must_be_empty")
    if environment.get("candidate_read_only_paths_for_a_future_separately_locked_probe") != [
        "/openapi/account/list",
        "/openapi/assets/balance",
        "/openapi/assets/positions",
        "/openapi/instrument/stock/list",
    ]:
        blockers.append("future_read_only_path_inventory_mismatch")
    if len(environment.get("required_but_undocumented_thailand_paths", [])) != 3:
        blockers.append("undocumented_path_inventory_mismatch")

    marker = contract.get("forward_marker_contract", {})
    for field in ("activation_timestamp", "observation_start_date", "observation_stop_date"):
        if marker.get(field) is not None:
            blockers.append(f"blocked_marker_must_be_null:{field}")
    if marker.get("minimum_calendar_days") != 180 or marker.get("maximum_calendar_days") != 365:
        blockers.append("observation_duration_mismatch")

    request_contract = contract.get("provider_request_contract", {})
    expected_request = {
        "webull_request_cap": 0,
        "alpha_vantage_request_cap": 0,
        "yahoo_request_cap": 0,
        "paid_spend_cap_usd": 0,
        "provider_calls_authorized": False,
    }
    for field, value in expected_request.items():
        if request_contract.get(field) != value:
            blockers.append(f"provider_request_boundary_mismatch:{field}")

    machine = contract.get("machine_contracts", {})
    declared: dict[str, str] = {}
    for key in ("event_schema", "report_schema", "report_validator"):
        row = machine.get(key, {})
        declared[str(row.get("path", ""))] = str(row.get("sha256", ""))
    fixtures = machine.get("synthetic_fixtures", [])
    for row in fixtures if isinstance(fixtures, list) else []:
        if isinstance(row, dict):
            declared[str(row.get("path", ""))] = str(row.get("sha256", ""))
    for relative, expected_hash in EXPECTED_FILE_HASHES.items():
        target = PROJECT_ROOT / relative
        if not target.is_file() or file_sha256(target) != expected_hash:
            blockers.append(f"file_hash_mismatch:{relative}")
        if relative in {
            "schemas/l_1_shadow_accounting_event.schema.json",
            "schemas/l_1_shadow_accounting_report.schema.json",
            "scripts/validate_l_1_shadow_accounting_report.py",
            "tests/fixtures/shadow_accounting/report_no_material.json",
            "tests/fixtures/shadow_accounting/report_material_breach.json",
            "tests/fixtures/shadow_accounting/report_activation_blocked.json",
        } and declared.get(relative) != expected_hash:
            blockers.append(f"machine_contract_hash_mismatch:{relative}")

    expected_fixture_decisions = {
        "tests/fixtures/shadow_accounting/report_no_material.json": "no_material_operational_discrepancy_observed_within_preregistered_scope",
        "tests/fixtures/shadow_accounting/report_material_breach.json": "material_operational_discrepancy_observed",
        "tests/fixtures/shadow_accounting/report_activation_blocked.json": "activation_blocked_before_observation",
    }
    if len(fixtures) != 3:
        blockers.append("synthetic_fixture_inventory_mismatch")
    for fixture in fixtures if isinstance(fixtures, list) else []:
        if not isinstance(fixture, dict):
            continue
        relative = str(fixture.get("path", ""))
        result = validate_report(PROJECT_ROOT / relative)
        if result["status"] != "pass":
            blockers.append(f"synthetic_fixture_validation_failed:{relative}")
        if fixture.get("expected_decision") != expected_fixture_decisions.get(relative):
            blockers.append(f"synthetic_fixture_decision_mismatch:{relative}")

    if len(contract.get("future_activation_requirements", [])) != 6:
        blockers.append("future_activation_requirement_inventory_mismatch")
    if len(contract.get("hard_stops", [])) != 8:
        blockers.append("hard_stop_inventory_mismatch")
    _validate_seal(contract.get("validation_return_seal", {}), blockers)
    claim_text = json.dumps(contract.get("claim_limits", []), ensure_ascii=False)
    for required in ("does not prove", "Synthetic fixtures do not provide", "No edge", "real-money"):
        if required not in claim_text:
            blockers.append(f"claim_limit_missing:{required}")
    if "Obtain written Webull Thailand confirmation" not in str(contract.get("next_safe_action", "")):
        blockers.append("next_safe_action_mismatch")
    return _result(path, blockers)


def _validate_seal(seal: dict[str, Any], blockers: list[str]) -> None:
    if seal.get("untouched_start") != "2016-01-04" or seal.get("untouched_end") != "2026-06-30":
        blockers.append("validation_window_mismatch")
    if seal.get("status") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
    for field in ("prices_opened", "adjusted_prices_opened", "returns_opened", "signals_opened", "positions_opened", "regimes_opened", "benchmarks_opened", "pnl_opened"):
        if seal.get(field) is not False:
            blockers.append(f"validation_seal_false_field_mismatch:{field}")


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "contract_path": relative_to_root(path, PROJECT_ROOT)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Lily B4.8 shadow-accounting activation contract.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    result = validate_contract(args.contract)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
