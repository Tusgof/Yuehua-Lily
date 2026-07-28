"""Closed-world semantic validator for the committed B7.14R7/v9 E0 fixtures."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.l3_b714_date_only_scanner_v9 import ASSETS, scan_synthetic_date_only
from lib.provenance import file_sha256

FIXTURE_ROOT = ROOT / "tests/fixtures/l3_b714_v9"
METADATA = FIXTURE_ROOT / "metadata.json"
REPORT = FIXTURE_ROOT / "report.json"
ATTESTATION = FIXTURE_ROOT / "attestation.json"
ZERO = {"real_container_access_count": 0, "return_decode_count": 0, "research_decision_count": 0, "ledger_row_count": 0, "validation_access_count": 0, "new_schedule_attestation_count": 0}
SEAL = {"status": "sealed_not_accessed", "accessed": False}
SOURCES = {"v3_checkpoint": "99e33857064e6eec76baba21ea64d9aaecea578f", "v3_report_sha256": "71727c6ee76f2af5c862da1fdc59c9a717005065c3abc0d61830dc08dd1c41dc", "v3_addendum_sha256": "c3ae1a58a6f00da691ef4edccf54dffb98c1415dd4613b0ac9f709286923a6fa", "historical_container_sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd", "b73_original_ledger_row_sha256": "594b8cbbdf7c27769191ab9495275803478481121372cd3bfc6f7e6d3a8a556a", "missing_agent_trailer_commit": "512120f35461ecb99e607d20aa2937a056434339"}
ARTIFACTS = {"scanner": "lib/l3_b714_date_only_scanner_v9.py", "runner": "scripts/run_l_3_b714_date_only_preflight_v9.py", "report_schema": "schemas/l_3_b714_date_only_preflight_report_v9.schema.json", "attestation_schema": "schemas/l_3_b714_date_only_schedule_attestation_v9.schema.json", "report_validator": "scripts/validate_l_3_b714_date_only_preflight_report_v9.py"}


def _closed(value: Any, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _identity(path: str) -> dict[str, str]:
    return {"path": path, "sha256": file_sha256(ROOT / path)}


def _raw(metadata: dict[str, Any]) -> bytes:
    payload = {"schema_version": "lily_l1_daily_dataset_v1", "acquired_at": "synthetic-fixture-only", "cutoff_inclusive": "2015-12-31", "symbols": [{"symbol": symbol, "records": [{"session_date": day, "availability_timestamp": "synthetic-fixture-only", "total_return_close": 1} for day in metadata["common_sessions"]]} for symbol in ASSETS]}
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _commit_exists(value: object) -> bool:
    if not isinstance(value, str) or value == "":
        return False
    return subprocess.run(["git", "cat-file", "-e", f"{value}^{{commit}}"], cwd=ROOT, capture_output=True, check=False).returncode == 0


def validate(report_path: Path = REPORT, attestation_path: Path | None = ATTESTATION) -> dict[str, object]:
    blockers: list[str] = []
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        metadata = json.loads(METADATA.read_text(encoding="utf-8"))
        attestation = json.loads(attestation_path.read_text(encoding="utf-8")) if attestation_path else None
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    if not _closed(metadata, {"schema_version", "common_sessions"}) or metadata.get("schema_version") != "lily_l3_b714_synthetic_date_metadata_v9" or not isinstance(metadata.get("common_sessions"), list):
        return {"status": "blocked", "blockers": ["metadata_closed_world"]}
    scanned = scan_synthetic_date_only(_raw(metadata))
    schedule = scanned.get("schedule") if scanned.get("status") == "synthetic_preflight_pass" else None
    if not isinstance(schedule, dict):
        blockers.append("metadata_not_scannable")
        schedule = {}
    else:
        schedule = {key: value for key, value in schedule.items() if key != "per_symbol_sessions"}
    identities = {key: _identity(path) for key, path in ARTIFACTS.items()}
    metadata_identity = _identity("tests/fixtures/l3_b714_v9/metadata.json")
    common = {"schema_version", "order_id", "hypothesis_id", "outcome", "evidence_tier", "edge_claim", "mode", "provenance", "metadata", "artifacts", "validation_seal", "access_counters", "contract_commit"}
    if report.get("mode") == "synthetic_preflight_pass":
        common.add("attestation")
    elif report.get("mode") == "scope_restricted":
        common.add("blocker")
    else:
        blockers.append("mode")
    if not _closed(report, common): blockers.append("report_closed_world")
    if {key: report.get(key) for key in ("schema_version", "order_id", "hypothesis_id", "evidence_tier", "edge_claim")} != {"schema_version": "lily_l3_b714_date_only_preflight_report_v9", "order_id": "B7.14R7", "hypothesis_id": "L-3", "evidence_tier": "E0", "edge_claim": "none"}: blockers.append("report_identity")
    if report.get("provenance") != SOURCES or report.get("metadata") != metadata_identity or report.get("artifacts") != identities or report.get("validation_seal") != SEAL or report.get("access_counters") != ZERO: blockers.append("report_bindings")
    if not _commit_exists(report.get("contract_commit")): blockers.append("contract_commit_tree")
    if report.get("mode") == "synthetic_preflight_pass":
        expected = {"schema_version": "lily_l3_b714_date_only_schedule_attestation_v9", "order_id": "B7.14R7", "hypothesis_id": "L-3", "evidence_tier": "E0", "edge_claim": "none", "mode": "synthetic_preflight_pass", "metadata": metadata_identity, "schedule": schedule, "validation_seal": SEAL, "access_counters": ZERO}
        if attestation != expected: blockers.append("attestation_content")
        if attestation_path is None or report.get("attestation") != _identity("tests/fixtures/l3_b714_v9/attestation.json"): blockers.append("attestation_identity")
        if report.get("outcome") != "synthetic_preflight_pass": blockers.append("outcome_mode_mismatch")
    elif report.get("mode") == "scope_restricted":
        if attestation_path is not None or report.get("outcome") != "scope_restricted" or not isinstance(report.get("blocker"), str) or not report["blocker"]:
            blockers.append("scope_restricted_matrix")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
