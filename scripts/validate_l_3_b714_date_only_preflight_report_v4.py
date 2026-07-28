"""Validate prospective v4 synthetic report/attestation pairs without real I/O."""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.l3_b714_date_only_scanner_v4 import ASSETS, build_schedule, scan_synthetic_date_only
from lib.provenance import file_sha256

FIXTURE_ROOT = ROOT / "tests/fixtures/l3_b714_v4"
METADATA = FIXTURE_ROOT / "metadata.json"
REPORT = FIXTURE_ROOT / "report.json"
ATTESTATION = FIXTURE_ROOT / "attestation.json"
HISTORICAL_SHA256 = "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd"
B73_LEDGER_SHA256 = "594b8cbbdf7c27769191ab9495275803478481121372cd3bfc6f7e6d3a8a556a"


def _fixture_raw(metadata: dict[str, Any]) -> bytes:
    sessions = metadata["common_sessions"]
    payload = {
        "schema_version": "lily_l1_daily_dataset_v1",
        "acquired_at": "synthetic-fixture-only",
        "cutoff_inclusive": "2015-12-31",
        "symbols": [
            {
                "symbol": symbol,
                "records": [
                    {
                        "session_date": session,
                        "availability_timestamp": "synthetic-fixture-only",
                        "total_return_close": 1,
                    }
                    for session in sessions
                ],
            }
            for symbol in ASSETS
        ],
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _expected_provenance() -> dict[str, Any]:
    paths = {
        "remediation_gate": "experiments/l_3_b714_date_only_preflight_remediation_v4.json",
        "b713_v3": "experiments/l_3_b714_activation_contract_v3.json",
        "b75": "experiments/l_3_corrected_rerun_pre_return_schedule_v1.json",
        "v3_addendum": "experiments/l_3_b714_v3_timestamp_decode_violation_addendum_v1.json",
    }
    return {
        "v3_checkpoint": "99e33857064e6eec76baba21ea64d9aaecea578f",
        "v3_report_sha256": "71727c6ee76f2af5c862da1fdc59c9a717005065c3abc0d61830dc08dd1c41dc",
        "historical_container_sha256": HISTORICAL_SHA256,
        "b73_original_ledger_row_sha256": B73_LEDGER_SHA256,
        **{f"{name}_sha256": file_sha256(ROOT / path) for name, path in paths.items()},
    }


def _closed_dict(value: Any, keys: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == keys


def _static_skip_call_graph_blockers() -> list[str]:
    source = ROOT / "lib/l3_b714_date_only_scanner_v4.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    methods = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in {"timestamp", "return_number", "_string_lexeme"}
    }
    nodes = {**functions, **methods}
    forbidden = {"decode", "str", "float", "Decimal", "loads", "codecs", "date", "datetime", "fromisoformat"}
    blockers: list[str] = []
    for root in ("skip_timestamp_lexeme", "skip_return_number_lexeme", "timestamp", "return_number"):
        pending = [root]
        visited: set[str] = set()
        while pending:
            name = pending.pop()
            if name in visited or name not in nodes:
                continue
            visited.add(name)
            for call in (item for item in ast.walk(nodes[name]) if isinstance(item, ast.Call)):
                if isinstance(call.func, ast.Name):
                    called = call.func.id
                elif isinstance(call.func, ast.Attribute):
                    called = call.func.attr
                else:
                    continue
                if called in forbidden:
                    blockers.append(f"{root}:{called}")
                if called in nodes:
                    pending.append(called)
    return sorted(set(blockers))


def validate_static() -> dict[str, object]:
    blockers = _static_skip_call_graph_blockers()
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers}


def validate(report_path: Path = REPORT, attestation_path: Path = ATTESTATION) -> dict[str, object]:
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
        metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    blockers = _static_skip_call_graph_blockers()
    metadata_keys = {"schema_version", "common_sessions"}
    if not _closed_dict(metadata, metadata_keys) or metadata.get("schema_version") != "lily_l3_b714_synthetic_date_metadata_v4" or not isinstance(metadata.get("common_sessions"), list):
        blockers.append("metadata_closed_world")
        expected_schedule: dict[str, Any] = {}
        expected_counters: dict[str, int] = {}
    else:
        synthetic = scan_synthetic_date_only(_fixture_raw(metadata))
        if synthetic.get("status") != "synthetic_preflight_pass":
            blockers.append("synthetic_fixture_not_scannable")
            expected_schedule, expected_counters = {}, {}
        else:
            expected_schedule = dict(synthetic["schedule"])
            expected_schedule.pop("per_symbol_sessions")
            expected_counters = synthetic["counters"]
    metadata_sha256 = file_sha256(METADATA)
    attestation_keys = {
        "schema_version", "order_id", "hypothesis_id", "evidence_tier", "edge_claim",
        "synthetic_metadata_sha256", "schedule", "validation_seal", "access_counters",
    }
    expected_attestation_identity = {
        "schema_version": "lily_l3_b714_date_only_schedule_attestation_v4",
        "order_id": "B7.14R",
        "hypothesis_id": "L-3",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "synthetic_metadata_sha256": metadata_sha256,
        "validation_seal": {"status": "sealed_not_accessed", "accessed": False},
    }
    if not _closed_dict(attestation, attestation_keys) or any(attestation.get(key) != value for key, value in expected_attestation_identity.items()):
        blockers.append("attestation_identity_or_unknown_field")
    if attestation.get("schedule") != expected_schedule or attestation.get("access_counters") != expected_counters:
        blockers.append("attestation_schedule_or_counter_drift")
    report_keys = {
        "schema_version", "order_id", "hypothesis_id", "outcome", "evidence_tier", "edge_claim",
        "provenance", "synthetic_metadata_sha256", "attestation_sha256", "validation_seal", "access_counters",
    }
    expected_report_identity = {
        "schema_version": "lily_l3_b714_date_only_preflight_report_v4",
        "order_id": "B7.14R",
        "hypothesis_id": "L-3",
        "outcome": "synthetic_preflight_pass",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "synthetic_metadata_sha256": metadata_sha256,
        "attestation_sha256": file_sha256(attestation_path),
        "validation_seal": {"status": "sealed_not_accessed", "accessed": False},
    }
    if not _closed_dict(report, report_keys) or any(report.get(key) != value for key, value in expected_report_identity.items()):
        blockers.append("report_identity_or_unknown_field")
    if report.get("provenance") != _expected_provenance():
        blockers.append("report_provenance")
    if report.get("access_counters") != expected_counters:
        blockers.append("report_counter_drift")
    prohibited = {"real_container_access_count", "return_decode_count", "research_decision_count", "ledger_row_count", "validation_access_count"}
    if not isinstance(report.get("access_counters"), dict) or any(report["access_counters"].get(key) != 0 for key in prohibited):
        blockers.append("sealed_access_drift")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
