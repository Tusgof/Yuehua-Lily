"""Closed E0 contract for B8.6R8/v10; it never decodes market values."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path

from lib.l4_b86r2_provisioning_scanner_v3 import CUTOFF, MAX_BYTES, U8

GATE_ID = "l_4_breadth_b86r8_provisioning_gate_v10"
GATE = "experiments/l_4_breadth_b86r8_provisioning_gate_v10.json"
DATASET = "data/normalized/l1_yahoo_daily_v1.json"
EXPECTED_DATASET_SHA256 = "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd"
ACTIVATION = "experiments/activation_records/l_4_breadth_b86r8_provisioning_activation_v10.json"
MARKER = "reports/experiments/l_4_breadth_b86r8_provisioning_attempt_v10.json"
REPORT = "reports/experiments/l_4_breadth_b86r8_provisioning_report_v10.json"
MANIFEST = "experiments/provisioned/l_4_breadth_b86r8_falsification_manifest_v10.json"
PAYLOAD = "experiments/provisioned/l_4_breadth_b86r8_u8_session_dates_v10.json"
REPORT_SCHEMA = "lily_l4_b86r8_provisioning_report_v10"
ACTIVATION_SCHEMA = "lily_l4_b86r8_provisioning_activation_v10"
MANIFEST_SCHEMA = "lily_l4_b86r8_falsification_manifest_v10"
PAYLOAD_SCHEMA = "lily_l4_b86r8_u8_session_dates_v10"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
MARKER_BYTES = b'{"schema_version":"lily_l4_b86r8_attempt_v10","state":"consumed"}'
BLOCKERS = frozenset(("dataset_missing", "dataset_read_error", "dataset_input_over_limit", "dataset_hash_mismatch", "structural_syntax", "unterminated_string", "invalid_numeric_lexeme", "unknown_or_duplicate_field", "trailing_bytes", "dataset_schema_mismatch", "symbol_order_mismatch", "symbol_schema_mismatch", "limitations_schema_mismatch", "invalid_calendar_session", "post_cutoff_session", "missing_or_ambiguous_u8_member", "record_schema_mismatch", "unsafe_value_not_opaque_scalar", "duplicate_symbol_session", "schema_mismatch", "bounded_raw_bytes_required"))
DEPENDENCY_PATHS = {
    "gate": GATE,
    "runner": "scripts/run_l_4_breadth_b86r8_provisioning_v10.py",
    "contract": "lib/l4_b86r8_contract_v10.py",
    "scanner": "lib/l4_b86r2_provisioning_scanner_v3.py",
    "gate_validator": "scripts/validate_l_4_breadth_b86r8_provisioning_gate_v10.py",
    "report_validator": "scripts/validate_l_4_breadth_b86r8_provisioning_report_v10.py",
    "draft_subset": "lib/draft202012_subset.py",
    "report_schema": "schemas/l_4_breadth_b86r8_provisioning_report_v10.schema.json",
    "activation_schema": "schemas/l_4_breadth_b86r8_provisioning_activation_v10.schema.json",
    "manifest_schema": "schemas/l_4_breadth_b86r8_falsification_manifest_v10.schema.json",
    "payload_schema": "schemas/l_4_breadth_b86r8_u8_session_dates_v10.schema.json",
}


def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
def sha256(raw): return hashlib.sha256(raw).hexdigest()
def h64(value): return isinstance(value, str) and bool(HEX64.fullmatch(value))
def d8(value):
    try: return isinstance(value, str) and date.fromisoformat(value).isoformat() == value and value <= CUTOFF
    except ValueError: return False


def dependency_identities(root):
    return {name: {"path": path, "sha256": sha256((Path(root) / path).read_bytes())} for name, path in DEPENDENCY_PATHS.items()}


def gate_source_binding_ok(root, identities):
    try: sources = json.loads((Path(root) / GATE).read_text("ascii"))["source_binding"]
    except (OSError, ValueError, KeyError, TypeError): return False
    return isinstance(sources, dict) and all(sources.get(name) == identities[name] for name in DEPENDENCY_PATHS if name != "gate")


def execution_provenance_ok(head, root, blob_loader):
    if not isinstance(head, str) or not HEX40.fullmatch(head): return None
    try: identities = dependency_identities(root)
    except OSError: return None
    for name, item in identities.items():
        raw = blob_loader(head, item["path"])
        if raw is None or sha256(raw) != item["sha256"]: return None
    if not gate_source_binding_ok(root, identities): return None
    return identities


def activation_ok(value, gate_sha256):
    keys = {"schema_version", "gate_id", "gate_sha256", "accepted_gate_head_sha", "hermetic_ci_head_sha", "hermetic_ci_run_id", "inspector_decision", "owner_authorization_reference", "scope", "validation_seal"}
    return isinstance(value, dict) and set(value) == keys and value.get("schema_version") == ACTIVATION_SCHEMA and value.get("gate_id") == GATE_ID and value.get("gate_sha256") == gate_sha256 and h64(gate_sha256) and isinstance(value.get("accepted_gate_head_sha"), str) and bool(HEX40.fullmatch(value["accepted_gate_head_sha"])) and value["accepted_gate_head_sha"] == value.get("hermetic_ci_head_sha") and isinstance(value.get("hermetic_ci_run_id"), int) and value["hermetic_ci_run_id"] > 0 and value.get("inspector_decision") == "ACCEPTED" and value.get("owner_authorization_reference") == "B8.6R8 one-shot owner authorization" and value.get("scope") == "one_repo_relative_falsification_container_provisioning_only" and value.get("validation_seal") == SEAL


def artifact(): return {"attempted_read_count": 0, "read_count": 0, "observed_byte_count": None, "complete_read": False, "complete_raw_sha256": None, "bounded_prefix_sha256": None, "hash_count": 0, "scan_count": 0, "return_value_decode_count": 0}
def row_ok(row, blocker=None):
    if not isinstance(row, dict) or set(row) != set(artifact()) or row["return_value_decode_count"] != 0: return False
    if blocker in {"dataset_missing", "dataset_read_error"}: return row == artifact() | {"attempted_read_count": 1}
    if blocker == "dataset_input_over_limit": return row["attempted_read_count"] == row["read_count"] == row["hash_count"] == 1 and row["observed_byte_count"] == MAX_BYTES + 1 and not row["complete_read"] and h64(row["bounded_prefix_sha256"]) and row["complete_raw_sha256"] is None and row["scan_count"] == 0
    return row["attempted_read_count"] == row["read_count"] == row["hash_count"] == row["scan_count"] == 1 and isinstance(row["observed_byte_count"], int) and 0 < row["observed_byte_count"] <= MAX_BYTES and row["complete_read"] and h64(row["complete_raw_sha256"]) and row["complete_raw_sha256"] == row["bounded_prefix_sha256"]


def outputs_ok(manifest, payload):
    mk = {"schema_version", "dataset_reference", "dataset_sha256", "dataset_byte_count", "u8_members_in_order", "coverage_by_symbol", "session_count", "max_session_date", "validation_seal"}; pk = {"schema_version", "dataset_sha256", "u8_members_in_order", "session_dates_by_symbol"}
    if not isinstance(manifest, dict) or set(manifest) != mk or not isinstance(payload, dict) or set(payload) != pk or manifest.get("schema_version") != MANIFEST_SCHEMA or payload.get("schema_version") != PAYLOAD_SCHEMA or manifest.get("dataset_reference") != DATASET or manifest.get("dataset_sha256") != EXPECTED_DATASET_SHA256 or payload.get("dataset_sha256") != EXPECTED_DATASET_SHA256 or not isinstance(manifest.get("dataset_byte_count"), int) or not 0 < manifest["dataset_byte_count"] <= MAX_BYTES or manifest.get("u8_members_in_order") != list(U8) or payload.get("u8_members_in_order") != list(U8) or manifest.get("validation_seal") != SEAL: return False
    coverage, sessions = manifest.get("coverage_by_symbol"), payload.get("session_dates_by_symbol")
    if not isinstance(coverage, dict) or not isinstance(sessions, dict) or set(coverage) != set(U8) or set(sessions) != set(U8): return False
    all_dates = []
    for symbol in U8:
        row, dates = coverage[symbol], sessions[symbol]
        if not isinstance(row, dict) or set(row) != {"start", "end", "row_count"} or not isinstance(dates, list) or not dates or any(not d8(x) for x in dates) or dates != sorted(set(dates)) or not isinstance(row["row_count"], int) or row["row_count"] <= 0 or row != {"start": dates[0], "end": dates[-1], "row_count": len(dates)}: return False
        all_dates += dates
    return isinstance(manifest.get("session_count"), int) and manifest["session_count"] == len(all_dates) and manifest.get("max_session_date") == max(all_dates) and d8(manifest["max_session_date"])


def atomic_write(path, raw):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_name(path.name + ".tmp"); descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        offset = 0
        while offset < len(raw): offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
    finally: os.close(descriptor)
    os.replace(temporary, path)
def atomic_write_all(items):
    for path, raw in items: atomic_write(path, raw)
def claim_once(path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    try: descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError: return False
    try:
        offset = 0
        while offset < len(MARKER_BYTES): offset += os.write(descriptor, MARKER_BYTES[offset:])
        os.fsync(descriptor)
    finally: os.close(descriptor)
    return True
