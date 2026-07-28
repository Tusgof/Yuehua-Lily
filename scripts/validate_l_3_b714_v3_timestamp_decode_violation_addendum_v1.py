"""Fail-closed validator for the rejected B7.14 v3 historical record."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.provenance import file_sha256

ADDENDUM = ROOT / "experiments/l_3_b714_v3_timestamp_decode_violation_addendum_v1.json"
REPORT = ROOT / "reports/experiments/l_3_b714_date_only_preflight_report_v3.json"
REPORT_SHA256 = "71727c6ee76f2af5c862da1fdc59c9a717005065c3abc0d61830dc08dd1c41dc"
V3_CHECKPOINT = "99e33857064e6eec76baba21ea64d9aaecea578f"
CONTAINER_SHA256 = "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd"


def validate() -> dict[str, object]:
    try:
        addendum = json.loads(ADDENDUM.read_text(encoding="utf-8"))
        report = json.loads(REPORT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}

    blockers: list[str] = []
    expected = {
        "schema_version": "lily_l3_b714_v3_timestamp_decode_violation_addendum_v1",
        "order_id": "B7.14",
        "checkpoint_git_commit": V3_CHECKPOINT,
        "v3_report": {
            "path": "reports/experiments/l_3_b714_date_only_preflight_report_v3.json",
            "sha256": REPORT_SHA256,
        },
        "v3_artifacts": {
            "gate": "350882a15e95fde168c01612ccce17e1811071f277cde4aa06305d01af257810",
            "scanner": "6d341c8f17d2f1cb681f6fc040a95729c037e507b406eb9555fc97f4a153a392",
            "runner": "e8f7ce14bb5c494cb4ac4144ada408caf1af945e1cfc0c2327f7deed48d4ffa4",
            "schema": "683e4d9339b43d5f5e3ef32a2bcae72c1a9642469c7963deb309efd4eb34a976",
            "report_validator": "d3903add31037bbb77a460d09bdc31e315d93b766668e3994da39c80e62226da",
        },
        "container_sha256": CONTAINER_SHA256,
        "outcome": "scope_restricted",
        "blocker": "unknown_structural_key",
        "attestation_created": False,
        "violation": {
            "forbidden_timestamp_utf8_text_decode_count": 1,
            "call_path": "P.timestamp -> P.bounds -> _utf8 -> raw.decode('utf-8')",
            "semantic_timestamp_parsing_count": 0,
            "description": "A skipped timestamp lexeme was decoded as UTF-8 text only; no date/time interpretation occurred.",
        },
        "zero_access_counts": {
            "session_date": 0,
            "return": 0,
            "research_decision": 0,
            "ledger": 0,
            "validation": 0,
            "provider": 0,
            "broker": 0,
        },
    }
    if set(addendum) != set(expected) or addendum != expected:
        blockers.append("addendum_closed_world_or_identity")
    if file_sha256(REPORT) != REPORT_SHA256:
        blockers.append("report_sha256")
    report_expected = {
        "schema_version": "lily_l3_b714_date_only_preflight_report_v3",
        "order_id": "B7.14",
        "hypothesis_id": "L-3",
        "outcome": "scope_restricted",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "validation_seal": {"status": "sealed_not_accessed", "accessed": False},
        "preflight": {"blocker": "unknown_structural_key"},
    }
    if any(report.get(key) != value for key, value in report_expected.items()):
        blockers.append("report_identity")
    provenance = report.get("provenance")
    counters = report.get("access_counters")
    if not isinstance(provenance, dict) or provenance.get("checkpoint_git_commit") != V3_CHECKPOINT or provenance.get("actual_container_sha256") != CONTAINER_SHA256 or provenance.get("attestation_path") is not None or provenance.get("attestation_sha256") is not None:
        blockers.append("report_provenance")
    if not isinstance(counters, dict) or any(counters.get(key) != 0 for key in ("session_date_values_decoded_count", "date_metadata_inspection_count", "skipped_return_number_lexeme_count", "research_decision_count", "ledger_row_count")):
        blockers.append("report_zero_access_accounting")
    incident = report.get("pre_checkpoint_incident_counts")
    if not isinstance(incident, dict) or incident.get("validation_access_count") != 0:
        blockers.append("report_validation_seal")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
