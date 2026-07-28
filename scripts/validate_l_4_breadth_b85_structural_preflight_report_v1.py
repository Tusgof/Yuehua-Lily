"""Closed-world validator for B8.5R structural-only preflight reports."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.l4_b85_structural_scanner_v1 import U8
from lib.provenance import file_sha256
from scripts.run_l_4_breadth_b85_phase_b_preflight_v1 import (
    CONTAINER_IDENTITY, MANIFEST_REFERENCE, PAYLOAD_REFERENCE, preflight_from_raw,
)

FIXTURE_ROOT = ROOT / "tests/fixtures/l4_b85"
MANIFEST = FIXTURE_ROOT / "structural_manifest_v1.json"
PAYLOAD = FIXTURE_ROOT / "u8_symbol_session_dates_v1.json"
SCHEMA = ROOT / "schemas/l_4_breadth_b85_structural_preflight_report_v1.schema.json"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
COUNTERS = {"real_preflight_consumed": False, "return_value_decode_count": 0, "validation_access_count": 0}


def validate(report: object | None = None, *, committed_synthetic: bool = False) -> dict[str, object]:
    try:
        json.loads(SCHEMA.read_text(encoding="utf-8"))
        expected = preflight_from_raw(MANIFEST.read_bytes(), PAYLOAD.read_bytes(), mode="synthetic_fixture")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    candidate = expected if report is None else report
    blockers: list[str] = []
    pass_keys = {"schema_version", "order_id", "hypothesis_id", "mode", "outcome", "evidence_tier", "edge_claim", "storage_references", "container_identity", "observed_raw", "manifest", "payload", "contract_artifacts", "access_counters", "validation_seal", "producing_git_commit"}
    blocked_keys = {"schema_version", "order_id", "hypothesis_id", "mode", "outcome", "evidence_tier", "edge_claim", "blocker", "observed_raw", "contract_artifacts", "access_counters", "validation_seal", "producing_git_commit"}
    if not isinstance(candidate, dict) or set(candidate) not in (pass_keys, blocked_keys): blockers.append("closed_world_shape")
    identity = {"schema_version": "lily_l4_b85_structural_preflight_report_v1", "order_id": "B8.5R", "hypothesis_id": "L-4", "evidence_tier": "E0", "edge_claim": "none"}
    if not isinstance(candidate, dict) or any(candidate.get(key) != value for key, value in identity.items()): blockers.append("identity")
    if not isinstance(candidate, dict) or candidate.get("mode") not in ("synthetic_fixture", "real_one_shot") or candidate.get("outcome") not in ("structural_pass", "preflight_blocked"): blockers.append("mode")
    if not isinstance(candidate, dict) or candidate.get("access_counters") != COUNTERS or candidate.get("validation_seal") != SEAL: blockers.append("seals")
    if isinstance(candidate, dict) and candidate.get("outcome") == "structural_pass":
        expected_pass = dict(expected)
        if candidate != expected_pass or not committed_synthetic: blockers.append("synthetic_provenance_or_content")
        payload = candidate.get("payload", {})
        if not isinstance(payload, dict) or payload.get("u8_members_in_order") != list(U8) or payload.get("max_session_date") != "2015-12-31": blockers.append("u8_or_cutoff")
    elif isinstance(candidate, dict) and candidate.get("outcome") == "preflight_blocked":
        if not isinstance(candidate.get("blocker"), str) or not candidate["blocker"]: blockers.append("blocked_outcome")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate(committed_synthetic=True)
    print(json.dumps(result))
    raise SystemExit(result["status"] != "pass")
