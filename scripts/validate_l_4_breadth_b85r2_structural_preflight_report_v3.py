"""Strict validator for B8.5R2 structural-only preflight reports."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.l4_b85r2_structural_scanner_v3 import CUTOFF, MAX_BYTES, ScanError, U8, read_bounded
from lib.provenance import git_commit
from scripts.run_l_4_breadth_b85r2_phase_b_preflight_v3 import (
    ATTEMPT_MARKER_BYTES,
    ATTEMPT_MARKER_RELATIVE,
    CONTAINER_IDENTITY,
    MANIFEST_REFERENCE,
    PAYLOAD_REFERENCE,
    REPORT_RELATIVE,
    contract_identities,
)

SCHEMA = ROOT / "schemas/l_4_breadth_b85r2_structural_preflight_report_v3.schema.json"
FIXTURE_ROOT = ROOT / "tests/fixtures/l4_b85r2"
MANIFEST = FIXTURE_ROOT / "structural_manifest_v3.json"
PAYLOAD = FIXTURE_ROOT / "u8_symbol_session_dates_v3.json"
REPORT = ROOT / REPORT_RELATIVE
MARKER = ROOT / ATTEMPT_MARKER_RELATIVE
ARTIFACT_KEYS = {"attempted_read_count", "read_count", "byte_count", "hash_count", "scan_count", "raw_sha256"}
BASE_KEYS = {
    "schema_version", "order_id", "hypothesis_id", "mode", "outcome", "evidence_tier", "edge_claim",
    "real_preflight_consumed", "storage_references", "container_identity", "artifacts", "contract_artifacts",
    "access_counters", "validation_seal", "attempt", "producing_git_commit",
}
GATE_ID = "l_4_breadth_b85r2_phase_a_activation_order_v3"


def _load_json(path: Path) -> object:
    return json.loads(read_bounded(path).decode("ascii"))


def _artifact_is_valid(value: object, *, real: bool, passed: bool) -> bool:
    if not isinstance(value, dict) or set(value) != ARTIFACT_KEYS:
        return False
    attempted, read = value.get("attempted_read_count"), value.get("read_count")
    byte_count, hashes, scans, digest = value.get("byte_count"), value.get("hash_count"), value.get("scan_count"), value.get("raw_sha256")
    if not all(isinstance(item, int) and item >= 0 for item in (attempted, read, hashes, scans)):
        return False
    if byte_count is not None and (not isinstance(byte_count, int) or not 0 <= byte_count <= MAX_BYTES):
        return False
    if digest is not None and (not isinstance(digest, str) or len(digest) != 64 or set(digest) - set("0123456789abcdef")):
        return False
    if passed:
        if real and (attempted != 1 or read != 1):
            return False
        if not real and (attempted != 0 or read != 0):
            return False
        return hashes == 1 and byte_count is not None and digest is not None and scans == 1
    if attempted not in (0, 1) or read not in (0, 1) or read > attempted or scans not in (0, 1):
        return False
    return (read == 0 and byte_count is None and hashes == 0 and digest is None) or (read == 1 and byte_count is not None and hashes == 1 and digest is not None)


def _payload_is_valid(payload: object) -> bool:
    if not isinstance(payload, dict) or set(payload) != {"raw_sha256", "byte_count", "u8_members_in_order", "session_count", "session_counts_by_symbol", "session_dates_by_symbol", "max_session_date", "minimal_ascii_decode_count"}:
        return False
    if payload.get("u8_members_in_order") != list(U8) or not isinstance(payload.get("session_counts_by_symbol"), dict):
        return False
    if not isinstance(payload.get("raw_sha256"), str) or len(payload["raw_sha256"]) != 64 or set(payload["raw_sha256"]) - set("0123456789abcdef") or not isinstance(payload.get("byte_count"), int) or not 0 <= payload["byte_count"] <= MAX_BYTES:
        return False
    counts = payload["session_counts_by_symbol"]
    sessions = payload.get("session_dates_by_symbol")
    if set(counts) != set(U8) or not isinstance(sessions, dict) or set(sessions) != set(U8) or any(not isinstance(counts.get(symbol), int) or counts[symbol] < 1 or not isinstance(sessions.get(symbol), list) or len(sessions[symbol]) != counts[symbol] for symbol in U8):
        return False
    try:
        if any(item > CUTOFF or date.fromisoformat(item).isoformat() != item for symbol in U8 for item in sessions[symbol]) or any(sessions[symbol] != sorted(set(sessions[symbol])) for symbol in U8):
            return False
    except (TypeError, ValueError):
        return False
    if payload.get("session_count") != sum(counts.values()) or payload.get("max_session_date") is None or payload["max_session_date"] > CUTOFF:
        return False
    return isinstance(payload.get("minimal_ascii_decode_count"), int) and payload["minimal_ascii_decode_count"] == payload["session_count"] + len(U8) + 1


def _gate_manifest_is_current() -> bool:
    try:
        rows = [json.loads(line) for line in read_bounded(ROOT / "experiments/locked_gates.jsonl").decode("utf-8").splitlines() if line]
        row = next(item for item in rows if item.get("gate_id") == GATE_ID)
        identities = contract_identities()
    except (OSError, ValueError, StopIteration, json.JSONDecodeError):
        return False
    return row.get("artifact_path") == identities["phase_a_gate"]["path"] and row.get("artifact_sha256") == identities["phase_a_gate"]["sha256"] and row.get("validator_path") == identities["phase_a_validator"]["path"] and row.get("validator_sha256") == identities["phase_a_validator"]["sha256"]


def validate(report: object | None = None, *, attempt_marker_path: Path | None = None) -> dict[str, object]:
    blockers: list[str] = []
    try:
        schema = _load_json(SCHEMA)
    except (OSError, ScanError, UnicodeDecodeError, json.JSONDecodeError, NameError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    if not isinstance(schema, dict) or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        return {"status": "blocked", "blockers": ["schema"]}
    if report is None:
        try:
            report = _load_json(REPORT)
        except Exception as exc:
            return {"status": "blocked", "blockers": [type(exc).__name__]}
    if not isinstance(report, dict):
        return {"status": "blocked", "blockers": ["report_type"]}
    expected_identity = {"schema_version": "lily_l4_b85r2_structural_preflight_report_v3", "order_id": "B8.5R2", "hypothesis_id": "L-4", "evidence_tier": "E0", "edge_claim": "none", "container_identity": CONTAINER_IDENTITY}
    if any(report.get(key) != value for key, value in expected_identity.items()):
        blockers.append("identity")
    mode, outcome, real = report.get("mode"), report.get("outcome"), report.get("mode") == "real_one_shot"
    allowed = BASE_KEYS | ({"manifest", "payload"} if outcome == "structural_pass" else {"blocker"} if outcome == "preflight_blocked" else set())
    if mode not in ("synthetic_fixture", "real_one_shot") or outcome not in ("structural_pass", "preflight_blocked") or set(report) != allowed:
        blockers.append("closed_world_shape")
    if report.get("storage_references") != {"manifest": MANIFEST_REFERENCE, "payload": PAYLOAD_REFERENCE}:
        blockers.append("storage_references")
    if report.get("contract_artifacts") != contract_identities():
        blockers.append("contract_artifacts")
    if not _gate_manifest_is_current():
        blockers.append("gate_manifest")
    if report.get("access_counters") != {"return_value_decode_count": 0, "validation_access_count": 0} or report.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}:
        blockers.append("sealed_access")
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {"manifest", "payload"}:
        blockers.append("artifact_shape")
    else:
        passed = outcome == "structural_pass"
        if not _artifact_is_valid(artifacts["manifest"], real=real and bool(report.get("real_preflight_consumed")), passed=passed):
            blockers.append("manifest_counters")
        if not _artifact_is_valid(artifacts["payload"], real=real and bool(report.get("real_preflight_consumed")), passed=passed):
            blockers.append("payload_counters")
    attempt = report.get("attempt")
    expected_attempt_path = ATTEMPT_MARKER_RELATIVE.as_posix()
    if not isinstance(attempt, dict) or set(attempt) != {"state", "repo_relative_marker_path", "marker_raw_sha256"} or attempt.get("repo_relative_marker_path") != expected_attempt_path:
        blockers.append("attempt_shape")
    if mode == "synthetic_fixture":
        if report.get("real_preflight_consumed") is not False or attempt != {"state": "not_consumed", "repo_relative_marker_path": expected_attempt_path, "marker_raw_sha256": None}:
            blockers.append("synthetic_state")
    elif report.get("real_preflight_consumed") is not True or not isinstance(attempt, dict) or attempt.get("state") != "consumed" or attempt.get("marker_raw_sha256") != hashlib.sha256(ATTEMPT_MARKER_BYTES).hexdigest():
        blockers.append("real_consumption_state")
    if real and report.get("producing_git_commit") != git_commit(ROOT):
        blockers.append("current_checkout")
    if outcome == "structural_pass":
        manifest, payload = report.get("manifest"), report.get("payload")
        if not isinstance(manifest, dict) or set(manifest) != {"raw_sha256", "byte_count", "metadata_sha256"} or not all(isinstance(manifest.get(key), str) and len(manifest[key]) == 64 for key in ("raw_sha256", "metadata_sha256")) or not isinstance(manifest.get("byte_count"), int) or not _payload_is_valid(payload):
            blockers.append("pass_structure")
        elif manifest.get("metadata_sha256") != payload.get("raw_sha256") or artifacts["manifest"].get("raw_sha256") != manifest.get("raw_sha256") or artifacts["payload"].get("raw_sha256") != payload.get("raw_sha256"):
            blockers.append("raw_hash_binding")
    elif not isinstance(report.get("blocker"), str) or not report["blocker"]:
        blockers.append("blocked_structure")
    if real:
        marker = attempt_marker_path or MARKER
        try:
            if read_bounded(marker) != ATTEMPT_MARKER_BYTES:
                blockers.append("attempt_marker")
        except (OSError, ScanError):
            blockers.append("attempt_marker")
    if outcome == "preflight_blocked" and report.get("blocker") == "attempt_already_consumed":
        blockers.append("second_attempt")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    from scripts.run_l_4_breadth_b85r2_phase_b_preflight_v3 import preflight_from_raw

    result = validate(preflight_from_raw(read_bounded(MANIFEST), read_bounded(PAYLOAD)))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
