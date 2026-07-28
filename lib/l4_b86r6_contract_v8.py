"""Single identity contract for the B8.6R6/v8 structural provisioning path."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from lib.l4_b86r2_provisioning_scanner_v3 import MAX_BYTES, ScanError, U8, scan_dataset

GATE_ID = "l_4_breadth_b86r6_provisioning_gate_v8"
GATE_PATH = "experiments/l_4_breadth_b86r6_provisioning_gate_v8.json"
DATASET = "data/normalized/l1_yahoo_daily_v1.json"
EXPECTED_DATASET_SHA256 = "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd"
ACTIVATION = "experiments/activation_records/l_4_breadth_b86r6_provisioning_activation_v8.json"
MARKER = "reports/experiments/l_4_breadth_b86r6_provisioning_attempt_v8.json"
REPORT = "reports/experiments/l_4_breadth_b86r6_provisioning_report_v8.json"
MANIFEST = "experiments/provisioned/l_4_breadth_b86r6_falsification_manifest_v8.json"
PAYLOAD = "experiments/provisioned/l_4_breadth_b86r6_u8_session_dates_v8.json"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
MANIFEST_SCHEMA = "lily_l4_b86r6_falsification_manifest_v8"
PAYLOAD_SCHEMA = "lily_l4_b86r6_u8_session_dates_v8"
REPORT_SCHEMA = "lily_l4_b86r6_provisioning_report_v8"
ACTIVATION_SCHEMA = "lily_l4_b86r6_provisioning_activation_v8"
MARKER_BYTES = b'{"schema_version":"lily_l4_b86r6_attempt_v8","state":"consumed"}'
BLOCKERS = frozenset(("dataset_missing", "dataset_read_error", "dataset_input_over_limit", "dataset_hash_mismatch", "structural_syntax", "unterminated_string", "invalid_numeric_lexeme", "unknown_or_duplicate_field", "trailing_bytes", "dataset_schema_mismatch", "symbol_order_mismatch", "symbol_schema_mismatch", "limitations_schema_mismatch", "invalid_calendar_session", "post_cutoff_session", "missing_or_ambiguous_u8_member", "record_schema_mismatch", "unsafe_value_not_opaque_scalar", "duplicate_symbol_session", "schema_mismatch", "bounded_raw_bytes_required"))

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def artifact():
    return {"attempted_read_count": 0, "read_count": 0, "observed_byte_count": None, "complete_read": False, "complete_raw_sha256": None, "bounded_prefix_sha256": None, "hash_count": 0, "scan_count": 0, "return_value_decode_count": 0}

def read_once(path, row):
    row["attempted_read_count"] = 1
    try:
        with Path(path).open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return None, "dataset_missing"
    except OSError:
        return None, "dataset_read_error"
    row.update({"read_count": 1, "observed_byte_count": len(raw), "hash_count": 1, "bounded_prefix_sha256": hashlib.sha256(raw).hexdigest()})
    if len(raw) > MAX_BYTES:
        return None, "dataset_input_over_limit"
    row.update({"complete_read": True, "complete_raw_sha256": row["bounded_prefix_sha256"]})
    return raw, None

def write_atomic(path, raw):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(descriptor, raw); os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)

def claim_once(path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    try:
        os.write(descriptor, MARKER_BYTES); os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True

def output_pair(scanned):
    manifest = {"schema_version": MANIFEST_SCHEMA, "dataset_reference": DATASET, "dataset_sha256": scanned["dataset_sha256"], "dataset_byte_count": scanned["dataset_byte_count"], "u8_members_in_order": list(U8), "coverage_by_symbol": scanned["coverage_by_symbol"], "session_count": scanned["session_count"], "max_session_date": scanned["max_session_date"], "validation_seal": SEAL}
    payload = {"schema_version": PAYLOAD_SCHEMA, "dataset_sha256": scanned["dataset_sha256"], "u8_members_in_order": list(U8), "session_dates_by_symbol": scanned["session_dates_by_symbol"]}
    return manifest, payload

def validate_outputs(manifest, payload):
    keys = {"schema_version", "dataset_reference", "dataset_sha256", "dataset_byte_count", "u8_members_in_order", "coverage_by_symbol", "session_count", "max_session_date", "validation_seal"}
    if not isinstance(manifest, dict) or set(manifest) != keys or manifest.get("schema_version") != MANIFEST_SCHEMA or manifest.get("dataset_reference") != DATASET or manifest.get("validation_seal") != SEAL:
        return False
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "dataset_sha256", "u8_members_in_order", "session_dates_by_symbol"} or payload.get("schema_version") != PAYLOAD_SCHEMA or payload.get("dataset_sha256") != manifest.get("dataset_sha256") or manifest.get("u8_members_in_order") != list(U8) or payload.get("u8_members_in_order") != list(U8):
        return False
    coverage, sessions = manifest.get("coverage_by_symbol"), payload.get("session_dates_by_symbol")
    if set(coverage or ()) != set(U8) or set(sessions or ()) != set(U8): return False
    total, dates = 0, []
    for symbol in U8:
        row, values = coverage[symbol], sessions[symbol]
        if set(row or ()) != {"start", "end", "row_count"} or not isinstance(values, list) or not values or values != sorted(set(values)) or row != {"start": values[0], "end": values[-1], "row_count": len(values)}: return False
        total += len(values); dates.extend(values)
    return manifest.get("session_count") == total and manifest.get("max_session_date") == max(dates)

def structural(raw, row):
    row["scan_count"] = 1
    try:
        scanned = scan_dataset(raw, expected_sha256=EXPECTED_DATASET_SHA256)
    except ScanError as error:
        return {"outcome": "provisioning_blocked", "blocker": str(error)}
    manifest, payload = output_pair(scanned)
    return {"outcome": "structural_provisioned", "manifest": manifest, "payload": payload}
