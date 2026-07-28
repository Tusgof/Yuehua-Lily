"""Byte-level structural scanner for the future B8.6 provisioning input."""
from __future__ import annotations

import hashlib
from datetime import date

DATASET_SCHEMA = "lily_l1_daily_dataset_v1"
NORMALIZED_SCHEMA = "lily_yahoo_daily_normalized_v1"
U8 = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
CUTOFF = "2015-12-31"
MAX_BYTES = 32 * 1024 * 1024
RECORD_KEYS = {"session_date", "availability_timestamp", "raw_close", "cash_distribution", "split", "total_return_close", "trading_currency", "provider_revision", "is_backfilled"}


class ScanError(ValueError):
    pass


class _Parser:
    """A bounded JSON parser: numbers are retained as opaque raw lexemes."""
    def __init__(self, raw: bytes): self.raw, self.i = raw, 0
    def ws(self):
        while self.i < len(self.raw) and self.raw[self.i] in b" \t\r\n": self.i += 1
    def value(self):
        self.ws()
        if self.i >= len(self.raw): raise ScanError("structural_syntax")
        c = self.raw[self.i]
        if c == 123: return self.obj()
        if c == 91: return self.arr()
        if c == 34: return self.string()
        for literal, value in ((b"true", True), (b"false", False), (b"null", None)):
            if self.raw.startswith(literal, self.i): self.i += len(literal); return value
        if c in b"-0123456789": return self.number()
        raise ScanError("structural_syntax")
    def string(self):
        start = self.i; self.i += 1
        while self.i < len(self.raw):
            c = self.raw[self.i]
            if c == 34:
                self.i += 1
                try: return self.raw[start + 1:self.i - 1].decode("ascii")
                except UnicodeDecodeError as exc: raise ScanError("non_ascii_string") from exc
            if c < 32 or c == 92: raise ScanError("ambiguous_string")
            self.i += 1
        raise ScanError("unterminated_string")
    def number(self):
        start = self.i
        while self.i < len(self.raw) and self.raw[self.i] in b"-+0123456789.eE": self.i += 1
        if start == self.i: raise ScanError("structural_syntax")
        return ("numeric_lexeme", self.raw[start:self.i])
    def obj(self):
        result = {}; self.i += 1; self.ws()
        if self.i < len(self.raw) and self.raw[self.i] == 125: self.i += 1; return result
        while True:
            self.ws()
            if self.i >= len(self.raw) or self.raw[self.i] != 34: raise ScanError("structural_syntax")
            key = self.string(); self.ws()
            if self.i >= len(self.raw) or self.raw[self.i] != 58 or key in result: raise ScanError("unknown_or_duplicate_field")
            self.i += 1; result[key] = self.value(); self.ws()
            if self.i < len(self.raw) and self.raw[self.i] == 125: self.i += 1; return result
            if self.i >= len(self.raw) or self.raw[self.i] != 44: raise ScanError("structural_syntax")
            self.i += 1
    def arr(self):
        result = []; self.i += 1; self.ws()
        if self.i < len(self.raw) and self.raw[self.i] == 93: self.i += 1; return result
        while True:
            result.append(self.value()); self.ws()
            if self.i < len(self.raw) and self.raw[self.i] == 93: self.i += 1; return result
            if self.i >= len(self.raw) or self.raw[self.i] != 44: raise ScanError("structural_syntax")
            self.i += 1


def _exact(value, keys, error="unknown_or_duplicate_field"):
    if not isinstance(value, dict) or set(value) != set(keys): raise ScanError(error)


def _date(value, *, post_cutoff=True):
    if not isinstance(value, str): raise ScanError("invalid_calendar_session")
    try:
        if date.fromisoformat(value).isoformat() != value: raise ValueError
    except ValueError as exc: raise ScanError("invalid_calendar_session") from exc
    if post_cutoff and value > CUTOFF: raise ScanError("post_cutoff_session")
    return value


def scan_dataset(raw: bytes, *, expected_sha256: str) -> dict:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES: raise ScanError("bounded_raw_bytes_required")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256: raise ScanError("dataset_hash_mismatch")
    parser = _Parser(raw); payload = parser.value(); parser.ws()
    if parser.i != len(raw): raise ScanError("trailing_bytes")
    _exact(payload, ("schema_version", "acquired_at", "cutoff_inclusive", "symbols"))
    if payload["schema_version"] != DATASET_SCHEMA or payload["cutoff_inclusive"] != CUTOFF or not isinstance(payload["acquired_at"], str): raise ScanError("dataset_schema_mismatch")
    symbols = payload["symbols"]
    if not isinstance(symbols, list) or len(symbols) != len(U8): raise ScanError("symbol_order_mismatch")
    sessions = {}; coverage = {}; total = 0
    for expected, item in zip(U8, symbols, strict=True):
        _exact(item, ("schema_version", "provider", "symbol", "legal_inception", "coverage", "records", "limitations"))
        if item["schema_version"] != NORMALIZED_SCHEMA or item["symbol"] != expected or not isinstance(item["provider"], str) or not isinstance(item["legal_inception"], str) or not isinstance(item["limitations"], list): raise ScanError("symbol_schema_mismatch")
        _exact(item["coverage"], ("start", "end")); start = _date(item["coverage"]["start"]); end = _date(item["coverage"]["end"])
        rows = item["records"]
        if not isinstance(rows, list) or not rows: raise ScanError("missing_or_ambiguous_u8_member")
        dates = []
        for row in rows:
            _exact(row, RECORD_KEYS)
            if not isinstance(row["availability_timestamp"], str) or not isinstance(row["trading_currency"], str) or not isinstance(row["provider_revision"], str) or not isinstance(row["is_backfilled"], bool): raise ScanError("record_schema_mismatch")
            dates.append(_date(row["session_date"]))
        if dates != sorted(set(dates)) or dates[0] != start or dates[-1] != end: raise ScanError("duplicate_symbol_session")
        sessions[expected] = dates; coverage[expected] = {"start": start, "end": end, "row_count": len(dates)}; total += len(dates)
    return {"dataset_sha256": digest, "dataset_byte_count": len(raw), "u8_members_in_order": list(U8), "session_dates_by_symbol": sessions, "coverage_by_symbol": coverage, "session_count": total, "max_session_date": max(x[-1] for x in sessions.values()), "numeric_lexeme_decode_count": 0, "validation_access_count": 0}
