"""Opaque, bounded structural scan for the future B8.6R one-shot input."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date

DATASET_SCHEMA = "lily_l1_daily_dataset_v1"
NORMALIZED_SCHEMA = "lily_yahoo_daily_normalized_v1"
U8 = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
CUTOFF = "2015-12-31"
MAX_BYTES = 32 * 1024 * 1024
TOP_KEYS = ("schema_version", "acquired_at", "cutoff_inclusive", "symbols")
SYMBOL_KEYS = ("schema_version", "provider", "symbol", "legal_inception", "coverage", "records", "limitations")
RECORD_KEYS = ("session_date", "availability_timestamp", "raw_close", "cash_distribution", "split", "total_return_close", "trading_currency", "provider_revision", "is_backfilled")
UNSAFE_KEYS = ("raw_close", "cash_distribution", "split", "total_return_close")


class ScanError(ValueError):
    pass


@dataclass(frozen=True)
class Opaque:
    raw: bytes
    kind: str


class Parser:
    """A JSON parser which retains every scalar as its original lexeme."""
    def __init__(self, raw: bytes): self.raw, self.i = raw, 0
    def ws(self):
        while self.i < len(self.raw) and self.raw[self.i] in b" \t\r\n": self.i += 1
    def value(self):
        self.ws()
        if self.i >= len(self.raw): raise ScanError("structural_syntax")
        c = self.raw[self.i]
        if c == 123: return self.obj()
        if c == 91: return self.arr()
        if c == 34: return self.scalar("string")
        for literal, kind in ((b"true", "bool"), (b"false", "bool"), (b"null", "null")):
            if self.raw.startswith(literal, self.i):
                self.i += len(literal); return Opaque(literal, kind)
        if c in b"-0123456789": return self.number()
        raise ScanError("structural_syntax")
    def scalar(self, kind):
        start = self.i; self.i += 1; escaped = False
        while self.i < len(self.raw):
            c = self.raw[self.i]
            if escaped: escaped = False
            elif c == 92: escaped = True
            elif c == 34:
                self.i += 1; return Opaque(self.raw[start:self.i], kind)
            elif c < 32: raise ScanError("structural_syntax")
            self.i += 1
        raise ScanError("unterminated_string")
    def number(self):
        start = self.i
        while self.i < len(self.raw) and self.raw[self.i] in b"-+0123456789.eE": self.i += 1
        raw = self.raw[start:self.i]
        try: json.loads(raw.decode("ascii"))
        except (UnicodeDecodeError, ValueError) as exc: raise ScanError("structural_syntax") from exc
        return Opaque(raw, "number")
    def obj(self):
        out = {}; self.i += 1; self.ws()
        if self.i < len(self.raw) and self.raw[self.i] == 125: self.i += 1; return out
        while True:
            self.ws()
            if self.i >= len(self.raw) or self.raw[self.i] != 34: raise ScanError("structural_syntax")
            key = self.text(self.scalar("string")); self.ws()
            if self.i >= len(self.raw) or self.raw[self.i] != 58 or key in out: raise ScanError("unknown_or_duplicate_field")
            self.i += 1; out[key] = self.value(); self.ws()
            if self.i < len(self.raw) and self.raw[self.i] == 125: self.i += 1; return out
            if self.i >= len(self.raw) or self.raw[self.i] != 44: raise ScanError("structural_syntax")
            self.i += 1
    def arr(self):
        out = []; self.i += 1; self.ws()
        if self.i < len(self.raw) and self.raw[self.i] == 93: self.i += 1; return out
        while True:
            out.append(self.value()); self.ws()
            if self.i < len(self.raw) and self.raw[self.i] == 93: self.i += 1; return out
            if self.i >= len(self.raw) or self.raw[self.i] != 44: raise ScanError("structural_syntax")
            self.i += 1
    @staticmethod
    def text(value):
        if not isinstance(value, Opaque) or value.kind != "string": raise ScanError("schema_mismatch")
        try:
            text = json.loads(value.raw.decode("ascii"))
        except (UnicodeDecodeError, ValueError) as exc: raise ScanError("schema_mismatch") from exc
        if not isinstance(text, str): raise ScanError("schema_mismatch")
        return text


def _exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys): raise ScanError("unknown_or_duplicate_field")
def _text(value): return Parser.text(value)
def _bool(value):
    if not isinstance(value, Opaque) or value.kind != "bool": raise ScanError("record_schema_mismatch")
    return value.raw == b"true"
def _date(value):
    text = _text(value)
    try:
        if date.fromisoformat(text).isoformat() != text: raise ValueError
    except ValueError as exc: raise ScanError("invalid_calendar_session") from exc
    if text > CUTOFF: raise ScanError("post_cutoff_session")
    return text
def _unsafe(value):
    if not isinstance(value, Opaque) or value.kind not in ("string", "number", "null"): raise ScanError("unsafe_value_not_opaque_scalar")


def scan_dataset(raw: bytes, *, expected_sha256: str) -> dict:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES: raise ScanError("bounded_raw_bytes_required")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256: raise ScanError("dataset_hash_mismatch")
    parser = Parser(raw); payload = parser.value(); parser.ws()
    if parser.i != len(raw): raise ScanError("trailing_bytes")
    _exact(payload, TOP_KEYS)
    if _text(payload["schema_version"]) != DATASET_SCHEMA or _text(payload["cutoff_inclusive"]) != CUTOFF: raise ScanError("dataset_schema_mismatch")
    _text(payload["acquired_at"])
    symbols = payload["symbols"]
    if not isinstance(symbols, list) or len(symbols) != len(U8): raise ScanError("symbol_order_mismatch")
    sessions, coverage, total = {}, {}, 0
    for expected, item in zip(U8, symbols, strict=True):
        _exact(item, SYMBOL_KEYS)
        if _text(item["schema_version"]) != NORMALIZED_SCHEMA or _text(item["symbol"]) != expected: raise ScanError("symbol_schema_mismatch")
        for name in ("provider", "legal_inception"): _text(item[name])
        if not isinstance(item["limitations"], list): raise ScanError("symbol_schema_mismatch")
        _exact(item["coverage"], ("start", "end")); start, end = _date(item["coverage"]["start"]), _date(item["coverage"]["end"])
        rows = item["records"]
        if not isinstance(rows, list) or not rows: raise ScanError("missing_or_ambiguous_u8_member")
        dates = []
        for row in rows:
            _exact(row, RECORD_KEYS)
            dates.append(_date(row["session_date"]))
            for name in ("availability_timestamp", "trading_currency", "provider_revision"): _text(row[name])
            _bool(row["is_backfilled"])
            for name in UNSAFE_KEYS: _unsafe(row[name])
        if dates != sorted(set(dates)) or dates[0] != start or dates[-1] != end: raise ScanError("duplicate_symbol_session")
        sessions[expected] = dates; coverage[expected] = {"start": start, "end": end, "row_count": len(dates)}; total += len(dates)
    return {"dataset_sha256": digest, "dataset_byte_count": len(raw), "u8_members_in_order": list(U8), "session_dates_by_symbol": sessions, "coverage_by_symbol": coverage, "session_count": total, "max_session_date": max(x[-1] for x in sessions.values()), "opaque_unsafe_lexeme_decode_count": 0, "return_value_decode_count": 0, "validation_access_count": 0}
