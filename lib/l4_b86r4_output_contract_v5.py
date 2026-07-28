"""Closed structural-output contract for B8.6R4; no market values are accepted."""
from __future__ import annotations

from datetime import date

from lib.l4_b86r2_provisioning_scanner_v3 import CUTOFF, U8

MANIFEST_SCHEMA = "lily_l4_b86r4_falsification_manifest_v5"
PAYLOAD_SCHEMA = "lily_l4_b86r4_u8_session_dates_v5"
SEAL = {"status": "sealed_not_accessed", "accessed": False}


def _date(value):
    return isinstance(value, str) and _valid_date(value) and value <= CUTOFF


def _valid_date(value):
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def validate_outputs(manifest, payload):
    manifest_keys = {
        "schema_version", "dataset_reference", "dataset_sha256", "dataset_byte_count",
        "u8_members_in_order", "coverage_by_symbol", "session_count", "max_session_date",
        "validation_seal",
    }
    payload_keys = {"schema_version", "dataset_sha256", "u8_members_in_order", "session_dates_by_symbol"}
    if not isinstance(manifest, dict) or set(manifest) != manifest_keys:
        return False
    if not isinstance(payload, dict) or set(payload) != payload_keys:
        return False
    if (
        manifest.get("schema_version") != MANIFEST_SCHEMA
        or payload.get("schema_version") != PAYLOAD_SCHEMA
        or manifest.get("dataset_reference") != "data/normalized/l1_yahoo_daily_v1.json"
        or manifest.get("validation_seal") != SEAL
        or not isinstance(manifest.get("dataset_sha256"), str)
        or len(manifest["dataset_sha256"]) != 64
        or payload.get("dataset_sha256") != manifest["dataset_sha256"]
        or not isinstance(manifest.get("dataset_byte_count"), int)
        or manifest["dataset_byte_count"] < 1
        or manifest.get("u8_members_in_order") != list(U8)
        or payload.get("u8_members_in_order") != list(U8)
    ):
        return False
    coverage, sessions = manifest.get("coverage_by_symbol"), payload.get("session_dates_by_symbol")
    if not isinstance(coverage, dict) or not isinstance(sessions, dict) or set(coverage) != set(U8) or set(sessions) != set(U8):
        return False
    total, all_dates = 0, []
    for symbol in U8:
        row, dates = coverage[symbol], sessions[symbol]
        if not isinstance(row, dict) or set(row) != {"start", "end", "row_count"} or not isinstance(dates, list) or not dates:
            return False
        if not all(_date(item) for item in dates) or dates != sorted(set(dates)):
            return False
        if row.get("start") != dates[0] or row.get("end") != dates[-1] or row.get("row_count") != len(dates):
            return False
        total += len(dates)
        all_dates.extend(dates)
    return manifest.get("session_count") == total and manifest.get("max_session_date") == max(all_dates)
