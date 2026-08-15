"""Closed-world validator for the B8.8R5AR-X control-plane incident.

This validator reads only the incident report, its schema, the committed v6
marker, the activation record, and the explicitly listed absent output paths.
It never opens, hashes, stats, or imports any container or return artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = "reports/incidents/l_4_breadth_b88r5arx_runtime_tracker_incident_v1.json"
SCHEMA = ROOT / "schemas/l_4_breadth_b88r5arx_incident_v1.schema.json"
MARKER = "reports/experiments/l_4_breadth_b88r5_one_shot_marker_v6.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b88r5_scientific_execution_activation_v6.json"
MARKER_SHA256 = "82ff7980d3e15b372747e1cdefdacfe68688c8c15899041b73c8e10ad9e0432c"
ACTIVATION_SHA256 = "6f092c187b8236ba52ecc9d3dfde78192a70f05ef635c4c9b5d67b97a9604913"
MARKER_FIELDS = {
    "activation_sha256": ACTIVATION_SHA256,
    "producing_commit": "8f080d39dca04714f7a245e13e8a4d782875c7d9",
    "schema_version": "lily_l4_b88r5_marker_v6",
}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.draft202012_subset import ValidationError, validate as draft_validate


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _relative(value: object) -> bool:
    path = Path(value) if isinstance(value, str) else None
    return path is not None and not path.is_absolute() and ".." not in path.parts and path.as_posix() == value


def _load_json(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("ascii"))
    if not isinstance(value, dict):
        raise ValueError("object_required")
    return raw, value


def validate(report_path: Path = ROOT / DEFAULT_REPORT, *, project_root: Path = ROOT) -> dict[str, object]:
    root = Path(project_root).resolve()
    report_path = Path(report_path)
    if not report_path.is_absolute():
        report_path = root / report_path
    blockers: list[str] = []
    try:
        report_raw, report = _load_json(report_path)
        schema = json.loads((root / "schemas/l_4_breadth_b88r5arx_incident_v1.schema.json").read_text(encoding="ascii"))
        draft_validate(schema, report)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, ValidationError) as exc:
        return {"status": "blocked", "blockers": [f"report_or_schema_invalid:{type(exc).__name__}"], "real_accessed": False}

    if report_path.as_posix().replace("\\", "/") != (root / DEFAULT_REPORT).as_posix().replace("\\", "/"):
        blockers.append("report_path_mismatch")
    try:
        marker_raw, marker = _load_json(root / MARKER)
        activation_raw, activation = _load_json(root / ACTIVATION)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {"status": "blocked", "blockers": [f"incident_binding_unreadable:{type(exc).__name__}"], "real_accessed": False}

    if _sha(marker_raw) != MARKER_SHA256 or report["marker"]["sha256"] != MARKER_SHA256:
        blockers.append("marker_sha256_mismatch")
    if marker != MARKER_FIELDS or report["marker"]["fields"] != MARKER_FIELDS:
        blockers.append("marker_fields_mismatch")
    if _sha(activation_raw) != ACTIVATION_SHA256 or report["activation"]["sha256"] != ACTIVATION_SHA256:
        blockers.append("activation_sha256_mismatch")
    activation_reference = report["activation"]
    for key in ("path", "gate_id", "accepted_gate_head_sha", "owner_literal", "validation_seal"):
        expected = activation_reference[key]
        actual_key = "path" if key == "path" else key
        if key == "path":
            if expected != ACTIVATION:
                blockers.append("activation_path_mismatch")
        elif activation.get(actual_key) != expected:
            blockers.append(f"activation_{key}_mismatch")

    absent = report["confirmed_absent_artifacts"]
    if len(absent) != len(set(absent)) or any(not _relative(path) for path in absent):
        blockers.append("absent_artifact_paths_invalid")
    for path in absent:
        if (root / path).exists():
            blockers.append(f"unexpected_artifact_present:{path}")
    structural = report["structural_reads"]
    expected_structural = {
        "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json",
        "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json",
    }
    if {item["path"] for item in structural} != expected_structural:
        blockers.append("structural_read_paths_mismatch")

    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "report_sha256": _sha(report_raw),
        "marker_sha256": _sha(marker_raw),
        "activation_sha256": _sha(activation_raw),
        "real_accessed": False,
        "container_return_access": report["access_bounds"]["container_return_access"],
        "validation_access_count": report["access_bounds"]["validation_access_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the B8.8R5AR-X incident report.")
    parser.add_argument("report", nargs="?", type=Path, default=ROOT / DEFAULT_REPORT)
    args = parser.parse_args()
    result = validate(args.report)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
