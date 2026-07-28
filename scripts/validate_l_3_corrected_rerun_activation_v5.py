"""Fail closed on the B7.9 synthetic-only activation supersession."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.provenance import file_sha256

GATE = ROOT / "experiments/l_3_corrected_rerun_activation_v5.json"
IDENTITY = {"schema_version": "lily_l3_corrected_rerun_activation_v5", "order_id": "B7.9", "gate_id": "l_3_corrected_rerun_activation_v5", "supersedes_gate_id": "l_3_corrected_rerun_activation_v4", "hypothesis_id": "L-3", "status": "locked_synthetic_only_adversarial_remediation", "evidence_ceiling": "E0", "edge_claim": "none"}
TOP = set(IDENTITY) | {"source_binding", "implementation", "authorizations", "attestation", "hard_stops"}
IMPLEMENTATION = {"runner": "scripts/run_l_3_corrected_rerun_v5.py", "activation_validator": "scripts/validate_l_3_corrected_rerun_activation_v5.py", "report_validator": "scripts/validate_l_3_corrected_rerun_report_v5.py", "report_schema": "schemas/l_3_corrected_rerun_report_v5.schema.json", "side_effect_library": "lib/l3_corrected_rerun_v5.py"}
AUTHORIZATIONS = {"real_container_access", "container_hashing", "date_column_inspection", "return_parsing", "execution", "report_decision", "validation_access", "provider_network", "credentials_environment", "acquisition", "paid_action", "broker", "paper_trade", "real_money"}
ATTESTATION = {"real_container_read_hash_count": 0, "market_returns_read_count": 0, "new_schedule_attestation_count": 0, "fresh_ledger_row_count": 0, "validation_status": "sealed_not_accessed"}
SOURCE_KEYS = {"b7_8_v4", "b7_7_v2", "locked_science", "whole_manifest_hash_binding", "self_or_circular_hash_binding"}
SCIENCE_KEYS = {"path", "sha256", "validator_path", "validator_sha256", "required_source_keys"}
SCIENCE_SOURCE_KEYS = ["active_l3_v2", "immutable_l3_v1", "b7_1_preflight", "b7_3_one_run_authorization", "b7_3_final_invalidated_report", "b7_4_remediation", "b7_4_original_run_row", "b7_4_invalidation_event", "whole_manifest_hash_binding", "self_or_circular_hash_binding"]
HARD_STOPS = ["Synthetic fixtures only; no real container API, path, or hash is available in B7.9.", "No return parsing, schedule attestation, execution, report decision, or ledger row is authorized.", "Validation, provider, credential, broker, paid, paper-trade, and real-money access remain forbidden.", "The locked L-3 universe, scientific semantics, MinTRL 49, 465 ceiling, and validation seal are unchanged.", "No future run is authorized until Inspector acceptance and a new owner order."]


def _manifest_identity(gate_id: str) -> dict[str, Any] | None:
    manifest = ROOT / "experiments/locked_gates.jsonl"
    if not manifest.is_file():
        return None
    for line in manifest.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("gate_id") == gate_id:
            return {key: row.get(key) for key in ("gate_id", "artifact_path", "artifact_sha256", "validator_path", "validator_sha256")}
    return None


def _source_row(value: Any, *, gate_id: str, path: str) -> bool:
    return isinstance(value, dict) and set(value) == {"path", "sha256", "manifest_identity"} and value.get("path") == path and (ROOT / path).is_file() and file_sha256(ROOT / path) == value.get("sha256") and value.get("manifest_identity") == _manifest_identity(gate_id)


def validate(path: Path = GATE) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "blocked", "blockers": [f"unreadable:{type(exc).__name__}"]}
    blockers = [f"unknown:{key}" for key in set(payload) - TOP] + [f"missing:{key}" for key in TOP - set(payload)]
    blockers.extend(f"identity:{key}" for key, value in IDENTITY.items() if payload.get(key) != value)
    source = payload.get("source_binding")
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        blockers.append("source_binding_shape")
    else:
        if not _source_row(source.get("b7_8_v4"), gate_id="l_3_corrected_rerun_activation_v4", path="experiments/l_3_corrected_rerun_activation_v4.json"):
            blockers.append("b78_source_binding_mismatch")
        if not _source_row(source.get("b7_7_v2"), gate_id="l_3_corrected_rerun_activation_v2", path="experiments/l_3_corrected_rerun_activation_v2.json"):
            blockers.append("b77_source_binding_mismatch")
        science = source.get("locked_science")
        if not isinstance(science, dict) or set(science) != SCIENCE_KEYS or science.get("path") != "experiments/l_3_corrected_rerun_pre_return_schedule_v1.json" or science.get("validator_path") != "scripts/validate_l_3_corrected_rerun_pre_return_schedule_v1.py" or science.get("required_source_keys") != SCIENCE_SOURCE_KEYS:
            blockers.append("locked_science_shape")
        else:
            artifact, validator = ROOT / science["path"], ROOT / science["validator_path"]
            if not artifact.is_file() or not validator.is_file() or file_sha256(artifact) != science.get("sha256") or file_sha256(validator) != science.get("validator_sha256"):
                blockers.append("locked_science_hash_mismatch")
            else:
                binding = json.loads(artifact.read_text(encoding="utf-8")).get("source_binding")
                if not isinstance(binding, dict) or set(binding) != set(SCIENCE_SOURCE_KEYS) or binding.get("whole_manifest_hash_binding") is not False or binding.get("self_or_circular_hash_binding") is not False:
                    blockers.append("locked_science_content_mismatch")
        if source.get("whole_manifest_hash_binding") is not False or source.get("self_or_circular_hash_binding") is not False:
            blockers.append("circular_binding")
    implementation = payload.get("implementation")
    if not isinstance(implementation, dict) or set(implementation) != set(IMPLEMENTATION):
        blockers.append("implementation_shape")
    else:
        for name, expected_path in IMPLEMENTATION.items():
            row = implementation.get(name)
            if not isinstance(row, dict) or set(row) != {"path", "sha256"} or row.get("path") != expected_path or not (ROOT / expected_path).is_file() or file_sha256(ROOT / expected_path) != row.get("sha256"):
                blockers.append(f"implementation_mismatch:{name}")
    authorizations = payload.get("authorizations")
    if not isinstance(authorizations, dict) or set(authorizations) != AUTHORIZATIONS or any(type(value) is not bool or value is not False for value in authorizations.values()):
        blockers.append("authorization_drift")
    if payload.get("attestation") != ATTESTATION:
        blockers.append("zero_access_attestation_mismatch")
    if payload.get("hard_stops") != HARD_STOPS:
        blockers.append("hard_stops_mismatch")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass" else 1)
