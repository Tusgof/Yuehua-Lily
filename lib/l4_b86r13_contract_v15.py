"""Closed-world B8.6R13/v15 contract.  It performs no dataset access."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path

from lib.l4_b86r2_provisioning_scanner_v3 import CUTOFF, MAX_BYTES, U8

GATE = "experiments/l_4_breadth_b86r13_provisioning_gate_v15.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b86r13_provisioning_activation_v15.json"
DATASET = "data/normalized/l1_yahoo_daily_v1.json"
EXPECTED_DATASET_SHA256 = "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd"
MARKER = "reports/experiments/l_4_breadth_b86r13_provisioning_attempt_v15.json"
REPORT = "reports/experiments/l_4_breadth_b86r13_provisioning_report_v15.json"
MANIFEST = "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json"
PAYLOAD = "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json"
REPORT_SCHEMA = "lily_l4_b86r13_provisioning_report_v15"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MARKER_BYTES = b'{"schema_version":"lily_l4_b86r13_attempt_v15","state":"consumed"}'
BLOCKERS = frozenset(("dataset_missing", "dataset_read_error", "dataset_input_over_limit", "dataset_hash_mismatch", "structural_syntax", "unterminated_string", "invalid_numeric_lexeme", "unknown_or_duplicate_field", "trailing_bytes", "dataset_schema_mismatch", "symbol_order_mismatch", "symbol_schema_mismatch", "limitations_schema_mismatch", "invalid_calendar_session", "post_cutoff_session", "missing_or_ambiguous_u8_member", "record_schema_mismatch", "unsafe_value_not_opaque_scalar", "duplicate_symbol_session", "schema_mismatch", "bounded_raw_bytes_required"))
ARTIFACT_KEYS = {"attempted_read_count", "read_count", "observed_byte_count", "complete_read", "complete_raw_sha256", "bounded_prefix_sha256", "hash_count", "scan_count", "return_value_decode_count"}
COMMON_REPORT_KEYS = {"schema_version", "order_id", "hypothesis_id", "mode", "outcome", "evidence_tier", "edge_claim", "real_provisioning_consumed", "dataset_reference", "expected_dataset_sha256", "dataset_artifact", "contract_artifacts", "activation_provenance", "access_counters", "validation_seal", "producing_git_commit"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def h40(value):
    return isinstance(value, str) and bool(HEX40.fullmatch(value))


def h64(value):
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


def d8(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value and value <= CUTOFF
    except ValueError:
        return False


def activation_content(gate, gate_raw, *, accepted_gate_head_sha, hermetic_ci_run_id):
    """All controlled literals come from the locked gate, never a caller."""
    return {"schema_version": gate["activation_schema_version"], "gate_id": gate["gate_id"], "gate_sha256": sha256(gate_raw), "accepted_gate_head_sha": accepted_gate_head_sha, "hermetic_ci_head_sha": accepted_gate_head_sha, "hermetic_ci_run_id": hermetic_ci_run_id, "inspector_decision": "ACCEPTED", "owner_authorization_reference": gate["required_owner_authorization_reference"], "scope": "one_repo_relative_falsification_container_provisioning_only", "validation_seal": SEAL}


def artifact():
    return {"attempted_read_count": 0, "read_count": 0, "observed_byte_count": None, "complete_read": False, "complete_raw_sha256": None, "bounded_prefix_sha256": None, "hash_count": 0, "scan_count": 0, "return_value_decode_count": 0}


def row_ok(row, blocker=None):
    if not isinstance(row, dict) or set(row) != ARTIFACT_KEYS or row["return_value_decode_count"] != 0:
        return False
    if blocker in {"dataset_missing", "dataset_read_error"}:
        return row == artifact() | {"attempted_read_count": 1}
    if blocker == "dataset_input_over_limit":
        return row["attempted_read_count"] == row["read_count"] == row["hash_count"] == 1 and row["observed_byte_count"] == MAX_BYTES + 1 and not row["complete_read"] and h64(row["bounded_prefix_sha256"]) and row["complete_raw_sha256"] is None and row["scan_count"] == 0
    return row["attempted_read_count"] == row["read_count"] == row["hash_count"] == row["scan_count"] == 1 and isinstance(row["observed_byte_count"], int) and not isinstance(row["observed_byte_count"], bool) and 0 < row["observed_byte_count"] <= MAX_BYTES and row["complete_read"] and h64(row["complete_raw_sha256"]) and row["complete_raw_sha256"] == row["bounded_prefix_sha256"]


def outputs_ok(manifest, payload):
    manifest_keys = {"schema_version", "dataset_reference", "dataset_sha256", "dataset_byte_count", "u8_members_in_order", "coverage_by_symbol", "session_count", "max_session_date", "validation_seal"}
    payload_keys = {"schema_version", "dataset_sha256", "u8_members_in_order", "session_dates_by_symbol"}
    if not isinstance(manifest, dict) or set(manifest) != manifest_keys or not isinstance(payload, dict) or set(payload) != payload_keys:
        return False
    if manifest.get("schema_version") != "lily_l4_b86r13_falsification_manifest_v15" or payload.get("schema_version") != "lily_l4_b86r13_u8_session_dates_v15" or manifest.get("dataset_reference") != DATASET or manifest.get("dataset_sha256") != EXPECTED_DATASET_SHA256 or payload.get("dataset_sha256") != EXPECTED_DATASET_SHA256 or not isinstance(manifest.get("dataset_byte_count"), int) or isinstance(manifest["dataset_byte_count"], bool) or not 0 < manifest["dataset_byte_count"] <= MAX_BYTES or manifest.get("u8_members_in_order") != list(U8) or payload.get("u8_members_in_order") != list(U8) or manifest.get("validation_seal") != SEAL:
        return False
    coverage, sessions = manifest.get("coverage_by_symbol"), payload.get("session_dates_by_symbol")
    if not isinstance(coverage, dict) or not isinstance(sessions, dict) or set(coverage) != set(U8) or set(sessions) != set(U8):
        return False
    all_dates = []
    for symbol in U8:
        row, dates = coverage[symbol], sessions[symbol]
        if not isinstance(row, dict) or set(row) != {"start", "end", "row_count"} or not isinstance(dates, list) or not dates or any(not d8(item) for item in dates) or dates != sorted(set(dates)) or not isinstance(row["row_count"], int) or isinstance(row["row_count"], bool) or row["row_count"] <= 0 or row != {"start": dates[0], "end": dates[-1], "row_count": len(dates)}:
            return False
        all_dates += dates
    return isinstance(manifest.get("session_count"), int) and not isinstance(manifest["session_count"], bool) and manifest["session_count"] == len(all_dates) and manifest.get("max_session_date") == max(all_dates) and d8(manifest["max_session_date"])


def atomic_write(path, raw):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_name(path.name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        offset = 0
        while offset < len(raw): offset += os.write(fd, raw[offset:])
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)


def atomic_write_all(items):
    for path, raw in items: atomic_write(path, raw)


def claim_once(path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    try: fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError: return False
    try:
        os.write(fd, MARKER_BYTES); os.fsync(fd)
    finally:
        os.close(fd)
    return True
