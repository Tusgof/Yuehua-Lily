"""E0-only v5 byte scanner façade; it accepts bytes and no path-like input."""
from __future__ import annotations

from typing import Any

from lib.l3_b714_date_only_scanner_v4 import ASSETS, END, START, ScanError, valid_utf8_bytes
from lib.l3_b714_date_only_scanner_v4 import scan_synthetic_date_only as _scan_v4


def scan_synthetic_date_only(raw: bytes) -> dict[str, Any]:
    """Scan only committed synthetic bytes; callers cannot provide a filesystem path."""
    if not isinstance(raw, bytes):
        raise TypeError("synthetic bytes are required")
    return _scan_v4(raw)


def enforce_weekly_pair_ceiling(count: int) -> None:
    """Pure inclusive B7.5 ceiling guard."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 0 or count > 465:
        raise ScanError("weekly_pair_ceiling_exceeded")
