"""B7.9 hermetic structural contracts; no real-container interface exists."""
from __future__ import annotations

from datetime import date
from typing import Any

from lib.l3_corrected_rerun_v3 import ASSETS, END, START, VALIDATION, build_canonical_schedule, canonical_schedule_sha256, derive_side_effects

_ENVELOPE_KEYS = {"schema_version", "acquired_at", "cutoff_inclusive", "symbols"}
_RECORD_KEYS = {"session_date", "availability_timestamp", "total_return_close"}


def scan_synthetic_envelope(envelope: Any) -> dict[str, Any]:
    """Check every synthetic symbol's dates before computing their intersection.

    This intentionally never reads the return field, metadata timestamps, a path,
    or a hash.  The inclusive falsification end is valid; every later date is a
    hard stop even if it exists on only one symbol and would disappear on
    intersection.
    """
    blockers: list[str] = []
    sessions: dict[str, list[str]] = {}
    if not isinstance(envelope, dict) or set(envelope) != _ENVELOPE_KEYS:
        return {"status": "blocked", "blockers": ["envelope_shape"], "return_values_exposed": False}
    if envelope["schema_version"] != "lily_l1_daily_dataset_v1":
        blockers.append("schema_version_mismatch")
    if envelope["cutoff_inclusive"] != END:
        blockers.append("cutoff_inclusive_mismatch")
    symbols = envelope["symbols"]
    if not isinstance(symbols, list) or len(symbols) != len(ASSETS):
        blockers.append("symbol_count_mismatch")
        symbols = []
    names = [row.get("symbol") for row in symbols if isinstance(row, dict)]
    if names != list(ASSETS):
        blockers.append("symbol_identity_or_order_mismatch")
    for item in symbols:
        if not isinstance(item, dict) or set(item) != {"symbol", "records"}:
            blockers.append("symbol_shape_mismatch")
            continue
        symbol, records = item["symbol"], item["records"]
        if not isinstance(symbol, str) or not isinstance(records, list):
            blockers.append("records_shape_mismatch")
            continue
        dates: list[str] = []
        for record in records:
            if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
                blockers.append("record_shape_mismatch")
                continue
            session = record["session_date"]
            if not isinstance(session, str):
                blockers.append("session_date_invalid")
                continue
            try:
                parsed = date.fromisoformat(session)
            except ValueError:
                blockers.append("session_date_invalid")
                continue
            if parsed > date.fromisoformat(END):
                blockers.append("post_end_session_before_intersection")
            dates.append(session)
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            blockers.append("per_symbol_sessions_not_strictly_monotonic")
        sessions[symbol] = dates
    common = sorted(set.intersection(*(set(sessions.get(asset, [])) for asset in ASSETS))) if set(sessions) == set(ASSETS) else []
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "assets": list(ASSETS),
        "common_session_count": len(common),
        "common_sessions": common,
        "return_values_exposed": False,
    }
