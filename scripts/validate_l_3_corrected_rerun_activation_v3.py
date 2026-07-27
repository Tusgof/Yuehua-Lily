"""Fail closed on the B7.8 E0 activation supersession."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.provenance import file_sha256
GATE = ROOT / "experiments/l_3_corrected_rerun_activation_v3.json"
_IDENTITY = {"schema_version": "lily_l3_corrected_rerun_activation_v3", "order_id": "B7.8", "gate_id": "l_3_corrected_rerun_activation_v3", "supersedes_gate_id": "l_3_corrected_rerun_activation_v2", "hypothesis_id": "L-3", "status": "locked_synthetic_only_execution_contract_supersession", "evidence_ceiling": "E0", "edge_claim": "none"}
_TOP = set(_IDENTITY) | {"source_binding", "implementation", "authorizations", "attestation", "hard_stops"}
_IMPLEMENTATION = {"runner", "activation_validator", "report_validator", "report_schema", "side_effect_library"}
_AUTHORIZATIONS = {"real_container_access", "container_hashing", "date_column_inspection", "return_parsing", "execution", "report_decision", "validation_access", "provider_network", "credentials_environment", "acquisition", "paid_action", "broker", "paper_trade", "real_money"}
_ATTESTATION = {"real_container_read_hash_count": 0, "market_returns_read_count": 0, "new_schedule_attestation_count": 0, "fresh_ledger_row_count": 0, "validation_status": "sealed_not_accessed"}
_SOURCE = {"b7_7_v2", "locked_science", "whole_manifest_hash_binding", "self_or_circular_hash_binding"}


def _sha(path: Path) -> str:
    return file_sha256(path)


def _manifest_identity() -> dict[str, Any] | None:
    manifest = ROOT / "experiments/locked_gates.jsonl"
    if not manifest.is_file():
        return None
    for line in manifest.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("gate_id") == "l_3_corrected_rerun_activation_v2":
            return {key: row.get(key) for key in ("gate_id", "artifact_path", "artifact_sha256", "validator_path", "validator_sha256")}
    return None


def validate(path: Path = GATE) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "blocked", "blockers": [f"unreadable:{type(exc).__name__}"]}
    blockers = [f"unknown:{key}" for key in set(payload) - _TOP] + [f"missing:{key}" for key in _TOP - set(payload)]
    blockers.extend(f"identity:{key}" for key, value in _IDENTITY.items() if payload.get(key) != value)
    source = payload.get("source_binding")
    if not isinstance(source, dict) or set(source) != _SOURCE:
        blockers.append("source_binding_shape")
    else:
        v2 = source["b7_7_v2"]
        science = source["locked_science"]
        if not isinstance(v2, dict) or set(v2) != {"path", "sha256", "manifest_identity"}:
            blockers.append("b77_source_shape")
        elif v2["path"] != "experiments/l_3_corrected_rerun_activation_v2.json" or not (ROOT / v2["path"]).is_file() or _sha(ROOT / v2["path"]) != v2["sha256"] or v2["manifest_identity"] != _manifest_identity():
            blockers.append("b77_source_binding_mismatch")
        required_science = {"path", "sha256", "validator_path", "validator_sha256", "required_source_keys"}
        if not isinstance(science, dict) or set(science) != required_science:
            blockers.append("locked_science_shape")
        else:
            source_gate = ROOT / science["path"]
            source_validator = ROOT / science["validator_path"]
            expected_keys = ["active_l3_v2", "immutable_l3_v1", "b7_1_preflight", "b7_3_one_run_authorization", "b7_3_final_invalidated_report", "b7_4_remediation", "b7_4_original_run_row", "b7_4_invalidation_event", "whole_manifest_hash_binding", "self_or_circular_hash_binding"]
            if not source_gate.is_file() or not source_validator.is_file() or _sha(source_gate) != science["sha256"] or _sha(source_validator) != science["validator_sha256"] or science["required_source_keys"] != expected_keys:
                blockers.append("locked_science_binding_mismatch")
            else:
                locked = json.loads(source_gate.read_text(encoding="utf-8")).get("source_binding")
                if not isinstance(locked, dict) or set(locked) != set(expected_keys) or locked.get("whole_manifest_hash_binding") is not False or locked.get("self_or_circular_hash_binding") is not False:
                    blockers.append("locked_science_content_mismatch")
        if source.get("whole_manifest_hash_binding") is not False or source.get("self_or_circular_hash_binding") is not False:
            blockers.append("circular_binding")
    implementation = payload.get("implementation")
    if not isinstance(implementation, dict) or set(implementation) != _IMPLEMENTATION:
        blockers.append("implementation_shape")
    else:
        expected_paths = {"runner": "scripts/run_l_3_corrected_rerun_v3.py", "activation_validator": "scripts/validate_l_3_corrected_rerun_activation_v3.py", "report_validator": "scripts/validate_l_3_corrected_rerun_report_v3.py", "report_schema": "schemas/l_3_corrected_rerun_report_v3.schema.json", "side_effect_library": "lib/l3_corrected_rerun_v3.py"}
        for name, expected_path in expected_paths.items():
            row = implementation.get(name)
            if not isinstance(row, dict) or set(row) != {"path", "sha256"} or row.get("path") != expected_path or not (ROOT / expected_path).is_file() or _sha(ROOT / expected_path) != row.get("sha256"):
                blockers.append(f"implementation_mismatch:{name}")
    if not isinstance(payload.get("authorizations"), dict) or set(payload["authorizations"]) != _AUTHORIZATIONS or any(value is not False for value in payload["authorizations"].values()):
        blockers.append("authorization_drift")
    if payload.get("attestation") != _ATTESTATION:
        blockers.append("zero_access_attestation_mismatch")
    if not isinstance(payload.get("hard_stops"), list) or len(payload["hard_stops"]) != 5 or not all(isinstance(item, str) and item for item in payload["hard_stops"]):
        blockers.append("hard_stops_shape")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass" else 1)
