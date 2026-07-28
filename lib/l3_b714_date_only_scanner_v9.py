"""E0-only v9 synthetic byte scanner with no filesystem or data path API."""
from __future__ import annotations

from typing import Any

from lib.l3_b714_date_only_scanner_v5 import (
    ASSETS,
    END,
    START,
    ScanError,
    enforce_weekly_pair_ceiling,
    scan_synthetic_date_only as _scan_synthetic_date_only,
    valid_utf8_bytes,
)


def scan_synthetic_date_only(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes):
        raise TypeError("synthetic bytes are required")
    return _scan_synthetic_date_only(raw)
