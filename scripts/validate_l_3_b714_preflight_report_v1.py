"""Validate B7.13 synthetic-only B7.14 date-metadata preflight reports."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.l3_b714_preflight_v1 import structural_preflight
from lib.provenance import file_sha256

TOP = {"schema_version", "order_id", "hypothesis_id", "report_mode", "decision", "evidence_tier", "edge_claim", "provenance", "synthetic_date_metadata", "validation_seal"}
IDENTITY = {"schema_version": "lily_l3_b714_preflight_report_v1", "order_id": "B7.14", "hypothesis_id": "L-3", "report_mode": "synthetic_preflight", "decision": "not_run", "evidence_tier": "E0", "edge_claim": "none"}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"status": "blocked", "blockers": ["report_not_object"]}
    blockers: list[str] = []
    if set(payload) != TOP:
        blockers.append("top_shape")
    if any(payload.get(key) != value for key, value in IDENTITY.items()):
        blockers.append("e0_only_matrix")
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict) or set(provenance) != {"active_gate_id", "active_gate_sha256", "fixture_metadata_sha256"} or provenance.get("active_gate_id") != "l_3_b714_activation_contract_v1":
        blockers.append("provenance_binding")
    if payload.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}:
        blockers.append("validation_seal")
    result = structural_preflight(payload.get("synthetic_date_metadata"))
    blockers.extend(result["blockers"])
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers)), "preflight": result if not blockers else None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    result = validate(json.loads(args.report.read_text(encoding="utf-8")))
    print(json.dumps(result, sort_keys=True))
    return result["status"] != "pass"


if __name__ == "__main__":
    raise SystemExit(main())
