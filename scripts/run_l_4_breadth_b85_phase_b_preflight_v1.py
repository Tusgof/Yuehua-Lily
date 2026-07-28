"""One-shot B8.5 Phase-B structural preflight; synthetic tests never resolve LILY_DATA_ROOT."""
from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.environment import require_configured_path
from lib.l4_b85_structural_scanner_v1 import ScanError, scan_manifest, scan_payload
from lib.provenance import file_sha256, git_commit

MANIFEST_RELATIVE = Path("sealed/l4_b85/l4_b85_structural_manifest_v1.json")
PAYLOAD_RELATIVE = Path("sealed/l4_b85/l4_b85_u8_symbol_session_dates_v1.json")
MANIFEST_REFERENCE = "${LILY_DATA_ROOT}/sealed/l4_b85/l4_b85_structural_manifest_v1.json"
PAYLOAD_REFERENCE = "${LILY_DATA_ROOT}/sealed/l4_b85/l4_b85_u8_symbol_session_dates_v1.json"
CONTAINER_IDENTITY = "lily-l4-falsification-pre2016-v1"
CONTRACT_ARTIFACTS = {
    "phase_a_gate": "experiments/l_4_breadth_b85_phase_a_activation_order_v2.json",
    "phase_a_validator": "scripts/validate_l_4_breadth_b85_phase_a_activation_order_v2.py",
    "scanner": "lib/l4_b85_structural_scanner_v1.py",
    "runner": "scripts/run_l_4_breadth_b85_phase_b_preflight_v1.py",
    "report_schema": "schemas/l_4_breadth_b85_structural_preflight_report_v1.schema.json",
    "report_validator": "scripts/validate_l_4_breadth_b85_structural_preflight_report_v1.py",
}


def contract_identities() -> dict[str, dict[str, str]]:
    return {name: {"path": path, "sha256": file_sha256(ROOT / path)} for name, path in CONTRACT_ARTIFACTS.items()}


def preflight_from_raw(manifest_raw: bytes, payload_raw: bytes, *, mode: str) -> dict[str, object]:
    counters = {"real_preflight_consumed": False, "return_value_decode_count": 0, "validation_access_count": 0}
    observed = {"manifest_raw_sha256": hashlib.sha256(manifest_raw).hexdigest(), "manifest_byte_count": len(manifest_raw), "payload_raw_sha256": hashlib.sha256(payload_raw).hexdigest(), "payload_byte_count": len(payload_raw)}
    try:
        manifest = scan_manifest(manifest_raw, expected_identity=CONTAINER_IDENTITY, expected_payload_path=PAYLOAD_RELATIVE.as_posix())
        payload = scan_payload(payload_raw)
        if manifest["metadata_sha256"] != payload["raw_sha256"]: raise ScanError("manifest_payload_hash_mismatch")
        return {"schema_version": "lily_l4_b85_structural_preflight_report_v1", "order_id": "B8.5R", "hypothesis_id": "L-4", "mode": mode, "outcome": "structural_pass", "evidence_tier": "E0", "edge_claim": "none", "storage_references": {"manifest": MANIFEST_REFERENCE, "payload": PAYLOAD_REFERENCE}, "container_identity": CONTAINER_IDENTITY, "observed_raw": observed, "manifest": manifest, "payload": payload, "contract_artifacts": contract_identities(), "access_counters": counters, "validation_seal": {"status": "sealed_not_accessed", "accessed": False}, "producing_git_commit": git_commit(ROOT)}
    except (ScanError, TypeError) as exc:
        return {"schema_version": "lily_l4_b85_structural_preflight_report_v1", "order_id": "B8.5R", "hypothesis_id": "L-4", "mode": mode, "outcome": "preflight_blocked", "evidence_tier": "E0", "edge_claim": "none", "blocker": str(exc), "observed_raw": observed, "contract_artifacts": contract_identities(), "access_counters": counters, "validation_seal": {"status": "sealed_not_accessed", "accessed": False}, "producing_git_commit": git_commit(ROOT)}


def run_phase_b() -> dict[str, object]:
    root = require_configured_path("LILY_DATA_ROOT")
    manifest_path, payload_path = root / MANIFEST_RELATIVE, root / PAYLOAD_RELATIVE
    try:
        report = preflight_from_raw(manifest_path.read_bytes(), payload_path.read_bytes(), mode="real_one_shot")
    except OSError as exc:
        report = preflight_from_raw(b"", b"", mode="real_one_shot"); report["blocker"] = type(exc).__name__
    report["access_counters"]["real_preflight_consumed"] = True
    return report


if __name__ == "__main__":
    raise SystemExit("B8.5R Phase A does not invoke the real preflight")
