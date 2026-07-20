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
from scripts.validate_l_0_webull_th_fractional_preview_probe import validate_contract


DEFAULT_PATH = PROJECT_ROOT / "experiments" / "l_0_webull_th_fractional_preview_activation.json"
MANIFEST_PATH = PROJECT_ROOT / "experiments" / "locked_gates.jsonl"
GATE_ID = "l_0_webull_th_fractional_preview_activation_v1"
MACHINERY_PATH = PROJECT_ROOT / "experiments" / "l_0_webull_th_fractional_preview_probe.json"
RUNNER_PATH = PROJECT_ROOT / "scripts" / "run_l_0_webull_th_fractional_preview_probe.py"
MACHINERY_HASH = "4bfee4a8cd69b069988913121898fd6affd8642380b0ed877f377872bef3c77e"
RUNNER_HASH = "edec1e1658c74abb87d116b2680d4a292481bbce3eec6d18984634f2369aa06a"
QUANTITY_GRID = ["1", "0.1", "0.01", "0.001", "0.0001", "0.00001", "0.000001", "0.0000001"]


def validate_activation(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        activation = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"activation_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l0_webull_th_fractional_preview_activation_v1",
        "order_id": "B4.11",
        "gate_id": GATE_ID,
        "hypothesis_id": "L-0",
        "linked_hypothesis_id": "L-1",
        "status": "locked_execution_authorized",
        "evidence_ceiling": "E0",
        "edge_claim": "none",
        "execution_authorized": True,
        "machinery_gate_id": "l_0_webull_th_fractional_preview_probe_v1",
        "contract_sha256": MACHINERY_HASH,
        "runner_sha256": RUNNER_HASH,
        "maximum_preview_requests": 8,
        "production_allowed": False,
        "orders_allowed": False,
    }
    for field, value in expected.items():
        if activation.get(field) != value:
            blockers.append(f"field_mismatch:{field}")
    if not isinstance(activation.get("owner_authorization"), str) or "explicitly authorized" not in activation["owner_authorization"]:
        blockers.append("owner_authorization_missing")

    machinery_result = validate_contract()
    if machinery_result["status"] != "pass":
        blockers.append("machinery_gate_invalid")
    if not MACHINERY_PATH.is_file() or file_sha256(MACHINERY_PATH) != MACHINERY_HASH:
        blockers.append("machinery_contract_hash_mismatch")
    if not RUNNER_PATH.is_file() or file_sha256(RUNNER_PATH) != RUNNER_HASH:
        blockers.append("runner_hash_mismatch")

    scope = activation.get("execution_scope", {})
    expected_scope = {
        "environment": "webull_thailand_uat",
        "host": "th-api.uat.webullbroker.com",
        "credential_environment_names": ["WEBULL_UAT_APP_KEY", "WEBULL_UAT_APP_SECRET", "WEBULL_UAT_ACCOUNT_ID"],
        "credential_values_may_be_persisted_or_logged": False,
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
        "one_run_only": True,
        "report_path": "reports/feasibility/l_0_webull_th_fractional_preview.json",
        "paid_spend_cap_usd": 0,
    }
    if scope != expected_scope:
        blockers.append("execution_scope_mismatch")

    if len(activation.get("preflight_order", [])) != 7:
        blockers.append("preflight_inventory_mismatch")
    attestation = activation.get("request_attestation_before_execution", {})
    expected_zero_fields = {
        "broker_api_calls", "authentication_calls", "preview_calls", "order_endpoint_calls",
        "orders_sent", "provider_api_calls", "validation_observations_opened", "paid_spend_usd",
    }
    if set(attestation) != expected_zero_fields:
        blockers.append("request_attestation_inventory_mismatch")
    for field in expected_zero_fields:
        if attestation.get(field) != 0:
            blockers.append(f"pre_execution_attestation_nonzero:{field}")

    _validate_seal(activation.get("validation_return_seal", {}), blockers)
    if len(activation.get("claim_limits", [])) != 3:
        blockers.append("claim_limit_inventory_mismatch")
    hard_stops = " ".join(str(value) for value in activation.get("hard_stops", []))
    for required in ("UAT credential", "production", "POST /openapi/trade/order/preview", "ninth preview", "validation return", "order submission"):
        if required not in hard_stops:
            blockers.append(f"hard_stop_missing:{required}")
    if "Commit and push" not in str(activation.get("next_safe_action", "")):
        blockers.append("commit_before_execution_rule_missing")

    serialized = json.dumps(activation, ensure_ascii=False)
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
    if row.get("artifact_path") != "experiments/l_0_webull_th_fractional_preview_activation.json":
        blockers.append("active_gate_artifact_path_mismatch")
    if row.get("validator_path") != "scripts/validate_l_0_webull_th_fractional_preview_activation.py":
        blockers.append("active_gate_validator_path_mismatch")
    if row.get("artifact_sha256") != file_sha256(path):
        blockers.append("active_gate_artifact_hash_mismatch")
    if row.get("validator_sha256") != file_sha256(Path(__file__)):
        blockers.append("active_gate_validator_hash_mismatch")


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "activation_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the locked B4.11 Webull Thailand UAT preview activation gate.")
    parser.add_argument("--activation", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    result = validate_activation(args.activation)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
