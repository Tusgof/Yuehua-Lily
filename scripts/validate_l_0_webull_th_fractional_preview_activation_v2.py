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

from lib.io import load_json, load_jsonl, relative_to_root
from lib.provenance import file_sha256


DEFAULT_PATH = PROJECT_ROOT / "experiments" / "l_0_webull_th_fractional_preview_activation_v2.json"
MANIFEST_PATH = PROJECT_ROOT / "experiments" / "locked_gates.jsonl"
GATE_ID = "l_0_webull_th_fractional_preview_activation_v2"
PREDECESSOR_GATE_ID = "l_0_webull_th_fractional_preview_activation_v1"
PREDECESSOR_ARTIFACT = PROJECT_ROOT / "experiments" / "l_0_webull_th_fractional_preview_activation.json"
PREDECESSOR_VALIDATOR = PROJECT_ROOT / "scripts" / "validate_l_0_webull_th_fractional_preview_activation.py"
PREDECESSOR_ARTIFACT_HASH = "ba830811cf2caeac9f9a265a2428b5afb96c514ed076ceba94680846793deed0"
PREDECESSOR_VALIDATOR_HASH = "04ee22bd745b4fd1f1a23012d9547ee5d747f737ec174b5cfbe43edc0bd00e52"
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
QUANTITY_GRID = ["1", "0.1", "0.01", "0.001", "0.0001", "0.00001", "0.000001", "0.0000001"]
MACHINE_PATHS = {
    "scripts/run_l_0_webull_th_fractional_preview_probe_v2.py",
    "scripts/validate_l_0_webull_th_fractional_preview_report_v2.py",
    "schemas/l_0_webull_th_fractional_preview_report_v2.schema.json",
    "tests/test_run_l_0_webull_th_fractional_preview_probe_v2.py",
    "tests/test_validate_l_0_webull_th_fractional_preview_report_v2.py",
    "tests/test_validate_l_0_webull_th_fractional_preview_activation_v2.py",
}


def validate_activation(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        activation = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"activation_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l0_webull_th_fractional_preview_activation_v2",
        "order_id": "B4.12",
        "gate_id": GATE_ID,
        "supersedes_gate_id": PREDECESSOR_GATE_ID,
        "hypothesis_id": "L-0",
        "linked_hypothesis_id": "L-1",
        "status": "locked_execution_authorized",
        "evidence_ceiling": "E0",
        "edge_claim": "none",
        "execution_authorized": True,
        "maximum_authentication_requests": 8,
        "maximum_preview_requests": 8,
        "maximum_total_requests": 16,
        "production_allowed": False,
        "orders_allowed": False,
    }
    for field, value in expected.items():
        if activation.get(field) != value:
            blockers.append(f"field_mismatch:{field}")
    if not isinstance(activation.get("owner_authorization"), str) or "authorized" not in activation["owner_authorization"]:
        blockers.append("owner_authorization_missing")
    if activation.get("predecessor_hashes") != {
        "artifact_sha256": PREDECESSOR_ARTIFACT_HASH,
        "validator_sha256": PREDECESSOR_VALIDATOR_HASH,
    }:
        blockers.append("predecessor_hash_inventory_mismatch")
    if file_sha256(PREDECESSOR_ARTIFACT) != PREDECESSOR_ARTIFACT_HASH:
        blockers.append("immutable_predecessor_artifact_hash_mismatch")
    if file_sha256(PREDECESSOR_VALIDATOR) != PREDECESSOR_VALIDATOR_HASH:
        blockers.append("immutable_predecessor_validator_hash_mismatch")

    expected_scope = {
        "environment": "webull_thailand_uat",
        "host": "th-api.uat.webullbroker.com",
        "sdk_package": "webull-openapi-python-sdk",
        "sdk_version_required": "2.0.13",
        "python_runtime": "3.11",
        "credential_environment_names": ["WEBULL_UAT_APP_KEY", "WEBULL_UAT_APP_SECRET", "WEBULL_UAT_ACCOUNT_ID"],
        "credential_token_or_account_identifier_may_be_persisted_or_logged": False,
        "only_authentication_requests": [
            {"method": "POST", "path": "/openapi/auth/token/create", "maximum_requests": 1},
            {"method": "POST", "path": "/openapi/auth/token/check", "maximum_requests": 7},
        ],
        "only_non_auth_request": {"method": "POST", "path": "/openapi/trade/order/preview"},
        "symbol": "VTI",
        "quantity_grid_in_request_order": QUANTITY_GRID,
        "authentication_polling_duration_seconds": 30,
        "authentication_polling_interval_seconds": 5,
        "maximum_authentication_requests": 8,
        "maximum_preview_requests": 8,
        "maximum_total_requests": 16,
        "automatic_retry": False,
        "automatic_polling_extension": False,
        "amount_mode_allowed": False,
        "balance_or_positions_allowed": False,
        "place_replace_cancel_allowed": False,
        "order_history_open_detail_allowed": False,
        "one_run_only": True,
        "report_path": "reports/feasibility/l_0_webull_th_fractional_preview_v2.json",
        "paid_spend_cap_usd": 0,
    }
    if activation.get("execution_scope") != expected_scope:
        blockers.append("execution_scope_mismatch")

    artifacts = activation.get("machine_artifacts")
    if not isinstance(artifacts, list):
        blockers.append("machine_artifacts_must_be_list")
        artifacts = []
    paths = {row.get("path") for row in artifacts if isinstance(row, dict)}
    if paths != MACHINE_PATHS or len(artifacts) != len(MACHINE_PATHS):
        blockers.append("machine_artifact_inventory_mismatch")
    for row in artifacts:
        if not isinstance(row, dict):
            continue
        artifact_path = row.get("path")
        digest = str(row.get("sha256", ""))
        if artifact_path not in MACHINE_PATHS or not HASH_PATTERN.fullmatch(digest):
            blockers.append(f"invalid_machine_artifact:{artifact_path}")
            continue
        target = PROJECT_ROOT / str(artifact_path)
        if not target.is_file() or file_sha256(target) != digest:
            blockers.append(f"machine_artifact_hash_mismatch:{artifact_path}")

    attestation = activation.get("request_attestation_before_execution", {})
    zero_fields = {
        "broker_api_calls", "authentication_calls", "preview_calls", "order_endpoint_calls",
        "orders_sent", "provider_api_calls", "validation_observations_opened", "paid_spend_usd",
    }
    if set(attestation) != zero_fields:
        blockers.append("request_attestation_inventory_mismatch")
    for field in zero_fields:
        if attestation.get(field) != 0:
            blockers.append(f"pre_execution_attestation_nonzero:{field}")
    _validate_seal(activation.get("validation_return_seal"), blockers)
    if len(activation.get("claim_limits", [])) != 3:
        blockers.append("claim_limit_inventory_mismatch")
    hard_stops = " ".join(str(value) for value in activation.get("hard_stops", []))
    for required in (
        "production", "balance", "POST /openapi/trade/order/preview", "ninth preview",
        "eighth token check", "validation return", "order submission", "raw response",
    ):
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
    if not isinstance(seal, dict) or seal.get("status") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
        return
    if seal.get("untouched_start") != "2016-01-04" or seal.get("untouched_end") != "2026-06-30":
        blockers.append("validation_window_mismatch")
    for field in (
        "prices_opened", "adjusted_prices_opened", "returns_opened", "signals_opened",
        "positions_opened", "regimes_opened", "benchmarks_opened", "pnl_opened",
    ):
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
    expected = {
        "artifact_path": "experiments/l_0_webull_th_fractional_preview_activation_v2.json",
        "validator_path": "scripts/validate_l_0_webull_th_fractional_preview_activation_v2.py",
        "artifact_sha256": file_sha256(path),
        "validator_sha256": file_sha256(Path(__file__)),
        "supersedes_gate_id": PREDECESSOR_GATE_ID,
    }
    for field, value in expected.items():
        if row.get(field) != value:
            blockers.append(f"active_gate_manifest_mismatch:{field}")


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "activation_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the locked B4.12 Webull UAT activation gate.")
    parser.add_argument("--activation", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    result = validate_activation(args.activation)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
