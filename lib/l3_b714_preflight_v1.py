"""B7.13 structural-only B7.14 preflight primitives; never open a container."""
from __future__ import annotations

from datetime import date
from typing import Any

ASSETS = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
START = date(2007, 2, 5)
END = date(2015, 12, 31)
MAX_WEEKLY_PAIRED_DATES = 465


def _date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def structural_preflight(metadata: Any) -> dict[str, Any]:
    """Validate only closed-world ``symbol``/``session_date`` fixture metadata."""
    if not isinstance(metadata, dict) or set(metadata) != {"schema_version", "symbols"}:
        return {"status": "blocked", "blockers": ["container_shape"]}
    if metadata["schema_version"] != "lily_l3_falsification_date_metadata_v1":
        return {"status": "blocked", "blockers": ["schema_version"]}
    symbols = metadata["symbols"]
    if not isinstance(symbols, dict) or set(symbols) != set(ASSETS):
        return {"status": "blocked", "blockers": ["symbol_set"]}
    common: set[date] | None = None
    for symbol in ASSETS:
        rows = symbols[symbol]
        if not isinstance(rows, list) or not rows:
            return {"status": "blocked", "blockers": ["missing_session_date"]}
        parsed = [_date(value) for value in rows]
        if any(value is None for value in parsed):
            return {"status": "blocked", "blockers": ["invalid_session_date"]}
        values = [value for value in parsed if value is not None]
        if any(value.weekday() >= 5 for value in values):
            return {"status": "blocked", "blockers": ["non_session_date"]}
        if any(value > END for value in values):
            return {"status": "blocked", "blockers": ["individual_post_end_session"]}
        if values != sorted(values) or len(values) != len(set(values)):
            return {"status": "blocked", "blockers": ["nonmonotonic_session_date"]}
        common = set(values) if common is None else common & set(values)
    sessions = sorted(value for value in common or set() if value >= START)
    if not sessions:
        return {"status": "blocked", "blockers": ["empty_common_weekly_schedule"]}
    # All supplied dates are weekday sessions; the last session in each week is the decision.
    weekly: dict[tuple[int, int], date] = {}
    for value in sessions:
        weekly[(value.isocalendar().year, value.isocalendar().week)] = value
    candidates = list(weekly.values())
    positions = {value: index for index, value in enumerate(sessions)}
    selected = [value for value in candidates if positions[value] + 20 < len(sessions)]
    if len(selected) > MAX_WEEKLY_PAIRED_DATES:
        return {"status": "blocked", "blockers": ["weekly_paired_ceiling"]}
    if not selected:
        return {"status": "blocked", "blockers": ["incomplete_t_plus_20"]}
    confirmations = [sessions[positions[value] + 20] for value in selected]
    return {"status": "pass", "blockers": [], "selected_weekly_paired_dates": [value.isoformat() for value in selected], "complete_t_plus_20_end_dates": [value.isoformat() for value in confirmations], "market_returns_read_count": 0, "validation_status": "sealed_not_accessed"}
