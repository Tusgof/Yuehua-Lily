from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def parse_aware_timestamp(value: str | datetime) -> datetime:
    timestamp = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must include a timezone offset")
    return timestamp


def timestamp_utc(value: str | datetime) -> datetime:
    return parse_aware_timestamp(value).astimezone(UTC)


def timestamp_utc_iso(value: str | datetime) -> str:
    return timestamp_utc(value).isoformat().replace("+00:00", "Z")


def session_date(value: str | datetime, timezone_name: str) -> date:
    return parse_aware_timestamp(value).astimezone(ZoneInfo(timezone_name)).date()


def is_available_by(value: str | datetime, decision_time: str | datetime) -> bool:
    return timestamp_utc(value) <= timestamp_utc(decision_time)


def require_available_by(
    value: str | datetime,
    decision_time: str | datetime,
    *,
    label: str = "input",
) -> None:
    if not is_available_by(value, decision_time):
        raise ValueError(f"{label} is not available by the decision timestamp")
