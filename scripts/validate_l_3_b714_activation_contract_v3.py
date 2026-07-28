"""Fail-closed validator for the B7.13 v3 manifest-integrity corrective gate."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.provenance import file_sha256


GATE = ROOT / "experiments/l_3_b714_activation_contract_v3.json"
SOURCES = {
    "b7_13_v2": (
        "experiments/l_3_b714_activation_contract_v2.json",
        "7a46162ae39caa9a4dd96707dc32d910cfd570370cbf851a1faf1f9e95d6f51a",
        "l_3_b714_activation_contract_v2",
        "scripts/validate_l_3_b714_activation_contract_v2.py",
        "779cd7e2385024bfc85e3767473c22183775cb3cca0835195ae4783215fd2164",
    ),
    "b7_13_v1": (
        "experiments/l_3_b714_activation_contract_v1.json",
        "3c7b620aa36423f1cb94804cdffcd4454256eedb205741ad3ca44a4d2f2cbc01",
        "l_3_b714_activation_contract_v1",
        "scripts/validate_l_3_b714_activation_contract_v1.py",
        "f241b35f8caf47981d98ef4859e03f4f3ae442842eaeca9f9da8804c7d989031",
    ),
    "b7_6_addendum": (
        "experiments/l_3_b76_preflight_provenance_addendum_v1.json",
        "69eea0f80cb303872c83e32ba940f96b11d05fe9a67df3891cfd8ada59036400",
        None,
        "scripts/validate_l_3_b76_preflight_provenance_addendum_v1.py",
        "1ed047c771b39493454a629f74373e3313116123ef69b7f3901be577e396132e",
    ),
}
FIXTURE = {
    "path": "tests/fixtures/l3_b714_preflight_v1/approved_metadata_v2.json",
    "sha256": "43602677bae676c34a92183ff23a174e194270ab2d61ee00baa796c702ebdbf0",
    "canonical_metadata_sha256": "6fbd71019f05c59d198a83b8e7924b35aa9c18ef599561d2c1ae9832fe272ff3",
}


def validate() -> dict[str, object]:
    try:
        payload = json.loads(GATE.read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in (ROOT / "experiments/locked_gates.jsonl").read_text(encoding="utf-8").splitlines() if line]
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    blockers: list[str] = []
    expected_identity = {
        "schema_version": "lily_l3_b714_activation_contract_v3",
        "order_id": "B7.13",
        "gate_id": "l_3_b714_activation_contract_v3",
        "supersedes_gate_id": "l_3_b714_activation_contract_v2",
        "hypothesis_id": "L-3",
        "status": "locked_E0_future_B7_14_date_only_preflight_contract_v3",
        "evidence_ceiling": "E0",
        "edge_claim": "none",
    }
    if {key: payload.get(key) for key in expected_identity} != expected_identity:
        blockers.append("identity")
    source = payload.get("source_binding", {})
    for key, (path, digest, gate_id, validator_path, validator_digest) in SOURCES.items():
        row = source.get(key, {})
        if row.get("path") != path or row.get("sha256") != digest or file_sha256(ROOT / path) != digest:
            blockers.append(f"source_binding:{key}")
            continue
        if row.get("validator_path") not in (None, validator_path) or row.get("validator_sha256") not in (None, validator_digest):
            blockers.append(f"source_binding:{key}")
        if validator_path and file_sha256(ROOT / validator_path) != validator_digest:
            blockers.append(f"source_validator:{key}")
        if gate_id:
            manifest_identity = row.get("manifest_identity", {})
            manifest_row = next((item for item in rows if item.get("gate_id") == gate_id), {})
            if (
                manifest_identity.get("gate_id") != gate_id
                or manifest_identity.get("validator_path") != validator_path
                or manifest_identity.get("validator_sha256") != validator_digest
                or manifest_row.get("artifact_sha256") != digest
                or manifest_row.get("validator_path") != validator_path
                or manifest_row.get("validator_sha256") != validator_digest
            ):
                blockers.append(f"manifest_identity:{key}")
    fixture = payload.get("approved_synthetic_metadata", {})
    if fixture != FIXTURE or file_sha256(ROOT / FIXTURE["path"]) != FIXTURE["sha256"]:
        blockers.append("fixture")
    authorizations = payload.get("authorizations")
    if not isinstance(authorizations, dict) or any(authorizations.values()):
        blockers.append("authorizations")
    if payload.get("attestation") != {
        "real_container_read_hash_count": 0,
        "market_returns_read_count": 0,
        "new_schedule_attestation_count": 0,
        "fresh_ledger_row_count": 0,
        "validation_status": "sealed_not_accessed",
    }:
        blockers.append("attestation")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result))
    raise SystemExit(result["status"] != "pass")
