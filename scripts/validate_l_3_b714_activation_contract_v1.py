"""Fail-closed validator for the B7.13 E0 future-preflight contract."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.provenance import file_sha256

GATE = ROOT / "experiments/l_3_b714_activation_contract_v1.json"
SOURCES = {"active_l3_v2": ("experiments/l_3_inverse_volatility_sizing_preregistration_v2.json", "83a68792614ee0def3ddb96349d6d95c7f0aeb0ac8b1c984c1e3d29ed74e709e", "l_3_inverse_volatility_sizing_v2"), "b7_5_schedule": ("experiments/l_3_corrected_rerun_pre_return_schedule_v1.json", "1202f477bf6d890dfb0b926b3bff9c775215762209627cb53e9c55b5c18957eb", "l_3_corrected_rerun_pre_return_schedule_v1"), "accepted_b7_12_v8": ("experiments/l_3_corrected_rerun_activation_v8.json", "419ff507490889ae761c1638ce24da2eaa25c38fd4e5223714fc885e2fce67f6", "l_3_corrected_rerun_activation_v8")}


def validate() -> dict:
    try:
        payload = json.loads(GATE.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    blockers: list[str] = []
    if {key: payload.get(key) for key in ("schema_version", "order_id", "gate_id", "hypothesis_id", "status", "evidence_ceiling", "edge_claim")} != {"schema_version": "lily_l3_b714_activation_contract_v1", "order_id": "B7.13", "gate_id": "l_3_b714_activation_contract_v1", "hypothesis_id": "L-3", "status": "locked_E0_future_B7_14_date_only_preflight_contract", "evidence_ceiling": "E0", "edge_claim": "none"}:
        blockers.append("identity")
    source = payload.get("source_binding", {})
    manifest = [json.loads(line) for line in (ROOT / "experiments/locked_gates.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    for key, (relative, digest, gate_id) in SOURCES.items():
        row = source.get(key, {})
        manifest_row = next((item for item in manifest if item.get("gate_id") == gate_id), None)
        if row.get("path") != relative or row.get("sha256") != digest or row.get("manifest_gate_id") != gate_id or not (ROOT / relative).is_file() or file_sha256(ROOT / relative) != digest or not isinstance(manifest_row, dict) or manifest_row.get("artifact_path") != relative or manifest_row.get("artifact_sha256") != digest:
            blockers.append("source_binding:" + key)
    b76 = source.get("b7_6_hard_stop_addendum", {})
    if b76.get("path") != "experiments/l_3_b76_preflight_provenance_addendum_v1.json" or b76.get("sha256") != "69eea0f80cb303872c83e32ba940f96b11d05fe9a67df3891cfd8ada59036400" or not (ROOT / b76.get("path", "")).is_file() or file_sha256(ROOT / b76["path"]) != b76["sha256"] or b76.get("required_outcome") != "scope_restricted" or source.get("whole_manifest_hash_binding") is not False or source.get("self_or_circular_hash_binding") is not False:
        blockers.append("source_binding")
    if not isinstance(payload.get("authorizations"), dict) or any(payload["authorizations"].values()) or payload.get("attestation", {}).get("validation_status") != "sealed_not_accessed":
        blockers.append("authorization_or_attestation")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate(); print(json.dumps(result)); raise SystemExit(result["status"] != "pass")
