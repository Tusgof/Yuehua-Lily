"""Closed-world E0 v5 report validator for committed synthetic fixtures only."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.l3_b714_date_only_scanner_v5 import ASSETS, scan_synthetic_date_only
from lib.provenance import file_sha256

FIXTURE_ROOT = ROOT / "tests/fixtures/l3_b714_v5"
METADATA = FIXTURE_ROOT / "metadata.json"
REPORT = FIXTURE_ROOT / "report.json"
ATTESTATION = FIXTURE_ROOT / "attestation.json"
ZERO = {"real_container_access_count": 0, "return_decode_count": 0, "research_decision_count": 0, "ledger_row_count": 0, "validation_access_count": 0, "new_schedule_attestation_count": 0}
SOURCES = {"v3_checkpoint": "99e33857064e6eec76baba21ea64d9aaecea578f", "v3_report_sha256": "71727c6ee76f2af5c862da1fdc59c9a717005065c3abc0d61830dc08dd1c41dc", "v3_addendum_sha256": "c3ae1a58a6f00da691ef4edccf54dffb98c1415dd4613b0ac9f709286923a6fa", "historical_container_sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd", "b73_original_ledger_row_sha256": "594b8cbbdf7c27769191ab9495275803478481121372cd3bfc6f7e6d3a8a556a", "missing_agent_trailer_commit": "512120f35461ecb99e607d20aa2937a056434339"}
ARTIFACTS = {"scanner": "lib/l3_b714_date_only_scanner_v5.py", "runner": "scripts/run_l_3_b714_date_only_preflight_v5.py", "report_schema": "schemas/l_3_b714_date_only_preflight_report_v5.schema.json", "attestation_schema": "schemas/l_3_b714_date_only_schedule_attestation_v5.schema.json", "report_validator": "scripts/validate_l_3_b714_date_only_preflight_report_v5.py"}
SEAL = {"status": "sealed_not_accessed", "accessed": False}


def _closed(value: Any, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _identity(path: str) -> dict[str, str]:
    return {"path": path, "sha256": file_sha256(ROOT / path)}


def _raw(metadata: dict[str, Any]) -> bytes:
    payload = {"schema_version": "lily_l1_daily_dataset_v1", "acquired_at": "synthetic-fixture-only", "cutoff_inclusive": "2015-12-31", "symbols": [{"symbol": symbol, "records": [{"session_date": day, "availability_timestamp": "synthetic-fixture-only", "total_return_close": 1} for day in metadata["common_sessions"]]} for symbol in ASSETS]}
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _git_tree_contains(commit: str) -> bool:
    if commit != "HEAD":
        return False
    probe = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT, capture_output=True, check=False)
    if probe.returncode:
        return False
    for path in ("experiments/l_3_b714_date_only_preflight_remediation_v5.json", *ARTIFACTS.values(), "experiments/locked_gates.jsonl"):
        shown = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
        if shown.returncode or shown.stdout != (ROOT / path).read_bytes():
            return False
    return b'l_3_b714_date_only_preflight_remediation_v5' in subprocess.run(["git", "show", f"{commit}:experiments/locked_gates.jsonl"], cwd=ROOT, capture_output=True, check=False).stdout


def validate(report_path: Path = REPORT, attestation_path: Path | None = ATTESTATION) -> dict[str, object]:
    blockers: list[str] = []
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        metadata = json.loads(METADATA.read_text(encoding="utf-8"))
        attestation = json.loads(attestation_path.read_text(encoding="utf-8")) if attestation_path else None
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    if not _closed(metadata, {"schema_version", "common_sessions"}) or metadata.get("schema_version") != "lily_l3_b714_synthetic_date_metadata_v5" or not isinstance(metadata.get("common_sessions"), list):
        return {"status": "blocked", "blockers": ["metadata_closed_world"]}
    scanned = scan_synthetic_date_only(_raw(metadata))
    schedule = scanned.get("schedule") if scanned.get("status") == "synthetic_preflight_pass" else None
    if not isinstance(schedule, dict):
        blockers.append("metadata_not_scannable")
        schedule = {}
    else:
        schedule = {key: value for key, value in schedule.items() if key != "per_symbol_sessions"}
    artifact_identities = {key: _identity(path) for key, path in ARTIFACTS.items()}
    metadata_identity = {"path": "tests/fixtures/l3_b714_v5/metadata.json", "sha256": file_sha256(METADATA)}
    common = {"schema_version", "order_id", "hypothesis_id", "outcome", "evidence_tier", "edge_claim", "mode", "provenance", "metadata", "artifacts", "validation_seal", "access_counters", "contract_commit"}
    if report.get("mode") == "synthetic_preflight_pass":
        common.add("attestation")
    elif report.get("mode") == "scope_restricted":
        common.add("blocker")
    else:
        blockers.append("mode")
    if not _closed(report, common): blockers.append("report_closed_world")
    if {key: report.get(key) for key in ("schema_version", "order_id", "hypothesis_id", "evidence_tier", "edge_claim")} != {"schema_version": "lily_l3_b714_date_only_preflight_report_v5", "order_id": "B7.14R3", "hypothesis_id": "L-3", "evidence_tier": "E0", "edge_claim": "none"}: blockers.append("report_identity")
    if report.get("provenance") != SOURCES or report.get("metadata") != metadata_identity or report.get("artifacts") != artifact_identities or report.get("validation_seal") != SEAL or report.get("access_counters") != ZERO: blockers.append("report_bindings")
    if not _git_tree_contains(report.get("contract_commit", "")): blockers.append("contract_commit_tree")
    if report.get("mode") == "synthetic_preflight_pass":
        expected_attestation = {"schema_version": "lily_l3_b714_date_only_schedule_attestation_v5", "order_id": "B7.14R3", "hypothesis_id": "L-3", "evidence_tier": "E0", "edge_claim": "none", "mode": "synthetic_preflight_pass", "metadata": metadata_identity, "schedule": schedule, "validation_seal": SEAL, "access_counters": ZERO}
        if attestation != expected_attestation: blockers.append("attestation_content")
        if attestation_path is None or report.get("attestation") != {"path": "tests/fixtures/l3_b714_v5/attestation.json", "sha256": file_sha256(attestation_path)}: blockers.append("attestation_identity")
        if report.get("outcome") != "synthetic_preflight_pass": blockers.append("outcome_mode_mismatch")
    elif report.get("mode") == "scope_restricted":
        if attestation_path is not None or report.get("outcome") != "scope_restricted" or not isinstance(report.get("blocker"), str): blockers.append("scope_restricted_matrix")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate(); print(json.dumps(result, sort_keys=True)); raise SystemExit(result["status"] != "pass")
