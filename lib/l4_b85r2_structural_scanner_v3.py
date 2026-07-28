"""Bounded byte-only scanner for the B8.5R2 structural preflight."""
from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from typing import Any

U8 = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
CUTOFF = "2015-12-31"
MANIFEST_SCHEMA = "lily_l4_b85r2_structural_manifest_v3"
PAYLOAD_SCHEMA = "lily_l4_b85r2_u8_symbol_session_dates_v3"
MAX_BYTES = 65536
MAX_SESSION_DATES_PER_SYMBOL = 4096


class ScanError(ValueError):
    pass


def read_bounded(path: Path) -> bytes:
    """Read at most MAX_BYTES + 1 bytes so an oversized input never loads fully."""
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ScanError("input_over_limit")
    return raw


class _Reader:
    def __init__(self, raw: bytes) -> None:
        if not isinstance(raw, bytes) or not raw:
            raise ScanError("bounded_raw_bytes_required")
        if len(raw) > MAX_BYTES:
            raise ScanError("input_over_limit")
        if raw.startswith(b"\xef\xbb\xbf") or any(byte > 0x7F or byte < 0x20 and byte not in b"\t\n\r" for byte in raw):
            raise ScanError("bom_or_encoding_ambiguity")
        if b"\\" in raw:
            raise ScanError("escaped_or_ambiguous_token")
        self.raw, self.pos = raw, 0

    def _space(self) -> None:
        while self.pos < len(self.raw) and self.raw[self.pos] in b" \t\r\n":
            self.pos += 1

    def byte(self, value: int) -> None:
        self._space()
        if self.pos >= len(self.raw) or self.raw[self.pos] != value:
            raise ScanError("structural_syntax")
        self.pos += 1

    def string(self) -> bytes:
        self._space()
        self.byte(ord('"'))
        start = self.pos
        while self.pos < len(self.raw) and self.raw[self.pos] != ord('"'):
            current = self.raw[self.pos]
            if current < 0x20 or current > 0x7E or current == ord("\\"):
                raise ScanError("ambiguous_string")
            self.pos += 1
        if self.pos >= len(self.raw):
            raise ScanError("unterminated_string")
        self.pos += 1
        return self.raw[start : self.pos - 1]

    def field(self, key: bytes) -> None:
        if self.string() != key:
            raise ScanError("unknown_or_duplicate_field")
        self.byte(ord(":"))

    def finish(self) -> None:
        self._space()
        if self.pos != len(self.raw):
            raise ScanError("trailing_bytes")


def _ascii(value: bytes) -> str:
    return value.decode("ascii")


def _session_date(value: bytes) -> str:
    text = _ascii(value)
    if len(text) != 10 or text[4:5] != "-" or text[7:8] != "-" or not (text[:4] + text[5:7] + text[8:]).isdigit():
        raise ScanError("invalid_calendar_session")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ScanError("invalid_calendar_session") from exc
    if text > CUTOFF:
        raise ScanError("post_cutoff_session")
    return text


def scan_manifest(raw: bytes, *, expected_identity: str, expected_payload_path: str) -> dict[str, Any]:
    reader = _Reader(raw)
    reader.byte(ord("{")); reader.field(b"schema_version")
    if reader.string() != MANIFEST_SCHEMA.encode("ascii"):
        raise ScanError("manifest_schema_mismatch")
    reader.byte(ord(",")); reader.field(b"container_identity")
    if reader.string() != expected_identity.encode("ascii"):
        raise ScanError("container_identity_mismatch")
    reader.byte(ord(",")); reader.field(b"metadata_path")
    if reader.string() != expected_payload_path.encode("ascii"):
        raise ScanError("payload_path_mismatch")
    reader.byte(ord(",")); reader.field(b"metadata_sha256")
    digest = reader.string()
    if len(digest) != 64 or any(current not in b"0123456789abcdef" for current in digest):
        raise ScanError("manifest_hash_shape")
    reader.byte(ord("}")); reader.finish()
    return {
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "metadata_sha256": _ascii(digest),
    }


def scan_payload(raw: bytes) -> dict[str, Any]:
    reader = _Reader(raw)
    reader.byte(ord("{")); reader.field(b"schema_version")
    if reader.string() != PAYLOAD_SCHEMA.encode("ascii"):
        raise ScanError("payload_schema_mismatch")
    reader.byte(ord(",")); reader.field(b"symbol_sessions"); reader.byte(ord("["))
    members: list[str] = []
    session_dates_by_symbol: dict[str, list[str]] = {}
    pairs: set[tuple[str, str]] = set()
    while True:
        reader._space()
        if reader.pos < len(reader.raw) and reader.raw[reader.pos] == ord("]"):
            reader.pos += 1
            break
        if members:
            reader.byte(ord(","))
        reader.byte(ord("{")); reader.field(b"symbol")
        symbol = _ascii(reader.string())
        reader.byte(ord(",")); reader.field(b"session_dates"); reader.byte(ord("["))
        dates: list[str] = []
        while True:
            reader._space()
            if reader.pos < len(reader.raw) and reader.raw[reader.pos] == ord("]"):
                reader.pos += 1
                break
            if dates:
                reader.byte(ord(","))
            if len(dates) >= MAX_SESSION_DATES_PER_SYMBOL:
                raise ScanError("record_bound_exceeded")
            session = _session_date(reader.string())
            if dates and session <= dates[-1]:
                raise ScanError("session_dates_not_strictly_ordered")
            if (symbol, session) in pairs:
                raise ScanError("duplicate_symbol_session")
            pairs.add((symbol, session))
            dates.append(session)
        reader.byte(ord("}"))
        if symbol not in U8 or not dates:
            raise ScanError("missing_or_ambiguous_u8_member")
        members.append(symbol)
        session_dates_by_symbol[symbol] = dates
    reader.byte(ord("}")); reader.finish()
    if len(set(members)) != len(members) or tuple(members) != U8:
        raise ScanError("missing_or_ambiguous_u8_member")
    all_dates = [item for dates in session_dates_by_symbol.values() for item in dates]
    return {
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
        "u8_members_in_order": members,
        "session_count": len(all_dates),
        "session_counts_by_symbol": {symbol: len(session_dates_by_symbol[symbol]) for symbol in U8},
        "session_dates_by_symbol": {symbol: session_dates_by_symbol[symbol] for symbol in U8},
        "max_session_date": max(all_dates),
        "minimal_ascii_decode_count": len(all_dates) + len(members) + 1,
    }
