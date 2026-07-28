"""Fail closed validation for the E0-only B7.14R v4 remediation gate."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.provenance import file_sha256
from scripts.validate_l_3_b714_v3_timestamp_decode_violation_addendum_v1 import validate as validate_addendum

GATE = ROOT / "experiments/l_3_b714_date_only_preflight_remediation_v4.json"
MANIFEST = ROOT / "experiments/locked_gates.jsonl"
SOURCE_SHA256S = {
    "b713_v3": ("experiments/l_3_b714_activation_contract_v3.json", "29808a30a0451a4f2d39eeca73dd053a87edf7caab4b05231e3cad5471e38032"),
    "b75": ("experiments/l_3_corrected_rerun_pre_return_schedule_v1.json", "1202f477bf6d890dfb0b926b3bff9c775215762209627cb53e9c55b5c18957eb"),
    "v3_report": ("reports/experiments/l_3_b714_date_only_preflight_report_v3.json", "71727c6ee76f2af5c862da1fdc59c9a717005065c3abc0d61830dc08dd1c41dc"),
    "v3_addendum": ("experiments/l_3_b714_v3_timestamp_decode_violation_addendum_v1.json", "c3ae1a58a6f00da691ef4edccf54dffb98c1415dd4613b0ac9f709286923a6fa"),
}
ARTIFACT_PATHS = {
    "scanner": "lib/l3_b714_date_only_scanner_v4.py",
    "runner": "scripts/run_l_3_b714_date_only_preflight_v4.py",
    "report_schema": "schemas/l_3_b714_date_only_preflight_report_v4.schema.json",
    "attestation_schema": "schemas/l_3_b714_date_only_schedule_attestation_v4.schema.json",
    "report_validator": "scripts/validate_l_3_b714_date_only_preflight_report_v4.py",
    "remediation_validator": "scripts/validate_l_3_b714_date_only_preflight_remediation_v4.py",
    "synthetic_metadata": "tests/fixtures/l3_b714_v4/metadata.json",
    "synthetic_report": "tests/fixtures/l3_b714_v4/report.json",
    "synthetic_attestation": "tests/fixtures/l3_b714_v4/attestation.json",
}
AUTHORIZATIONS = {
    "real_container_access": False, "container_hashing": False, "date_inspection": False,
    "return_parsing": False, "execution": False, "research_decision": False,
    "ledger_write": False, "validation": False, "provider": False, "credentials": False,
    "broker": False, "paid": False, "paper_trade": False, "real_money": False,
}


def validate() -> dict[str, object]:
    try:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line]
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    blockers: list[str] = []
    identity = {
        "schema_version": "lily_l3_b714_date_only_preflight_remediation_v4",
        "order_id": "B7.14R", "gate_id": "l_3_b714_date_only_preflight_remediation_v4",
        "supersedes_gate_id": "l_3_b714_date_only_preflight_activation_v3", "hypothesis_id": "L-3",
        "status": "locked_E0_rejected_v3_remediation", "evidence_ceiling": "E0", "edge_claim": "none",
        "validation_seal": {"status": "sealed_not_accessed", "accessed": False},
    }
    required = set(identity) | {"source_binding", "authorizations", "artifact_paths"}
    if set(gate) != required or any(gate.get(key) != value for key, value in identity.items()):
        blockers.append("identity_or_unknown_field")
    if gate.get("authorizations") != AUTHORIZATIONS:
        blockers.append("authorizations")
    if gate.get("artifact_paths") != ARTIFACT_PATHS or any(not (ROOT / path).is_file() for path in ARTIFACT_PATHS.values()):
        blockers.append("artifact_paths")
    source = gate.get("source_binding")
    if not isinstance(source, dict) or set(source) != {"b713_v3", "b75", "v3_checkpoint", "v3_report", "v3_addendum", "historical_container_sha256", "b73_original_ledger_row_sha256"}:
        blockers.append("source_binding_shape")
    else:
        for name, (path, digest) in SOURCE_SHA256S.items():
            entry = source.get(name)
            if not isinstance(entry, dict) or entry.get("path") != path or entry.get("sha256") != digest or file_sha256(ROOT / path) != digest:
                blockers.append(f"source_binding:{name}")
        expected_manifest = {
            "gate_id": "l_3_b714_activation_contract_v3", "artifact_sha256": SOURCE_SHA256S["b713_v3"][1],
            "validator_path": "scripts/validate_l_3_b714_activation_contract_v3.py",
            "validator_sha256": "b00de2dca5ceadbb8d16c49449fa81098b39770e32bc082118bb3d76e3c25cf6",
        }
        b713 = source.get("b713_v3", {})
        manifest_row = next((row for row in rows if row.get("gate_id") == "l_3_b714_activation_contract_v3"), None)
        if not isinstance(b713, dict) or b713.get("manifest_identity") != expected_manifest or not isinstance(manifest_row, dict) or {key: manifest_row.get(key) for key in expected_manifest} != expected_manifest:
            blockers.append("b713_manifest_identity")
        if source.get("v3_checkpoint") != "99e33857064e6eec76baba21ea64d9aaecea578f" or source.get("historical_container_sha256") != "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd" or source.get("b73_original_ledger_row_sha256") != "594b8cbbdf7c27769191ab9495275803478481121372cd3bfc6f7e6d3a8a556a":
            blockers.append("historical_bindings")
    if validate_addendum().get("status") != "pass":
        blockers.append("v3_rejection_addendum")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
