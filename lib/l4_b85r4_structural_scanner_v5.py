"""Capacity-aware, byte-only scanner for the B8.5R4 v5 contract."""
from __future__ import annotations

import hashlib
from datetime import date
from typing import Any

U8 = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
CUTOFF = "2015-12-31"
MAX_SESSION_DATES_PER_SYMBOL = 4096
MANIFEST_SCHEMA = "lily_l4_b85r4_structural_manifest_v5"
PAYLOAD_SCHEMA = "lily_l4_b85r4_u8_symbol_session_dates_v5"


def canonical_payload_capacity_bytes() -> int:
    date_array = MAX_SESSION_DATES_PER_SYMBOL * len('"0001-01-01"') + (MAX_SESSION_DATES_PER_SYMBOL - 1)
    members = sum(len('{"symbol":"' + symbol + '","session_dates":[') + date_array + len(']}') for symbol in U8) + (len(U8) - 1)
    return len('{"schema_version":"' + PAYLOAD_SCHEMA + '","symbol_sessions":[') + members + len(']}')


MAX_BYTES = canonical_payload_capacity_bytes()


class ScanError(ValueError):
    pass


class _Reader:
    def __init__(self, raw: bytes) -> None:
        if not isinstance(raw, bytes) or not raw:
            raise ScanError("bounded_raw_bytes_required")
        if len(raw) > MAX_BYTES:
            raise ScanError("input_over_limit")
        if raw.startswith(b"\xef\xbb\xbf") or any(value > 0x7F or value < 0x20 and value not in b"\t\n\r" for value in raw) or b"\\" in raw:
            raise ScanError("bom_escape_or_encoding_ambiguity")
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
        self._space(); self.byte(ord('"')); start = self.pos
        while self.pos < len(self.raw) and self.raw[self.pos] != ord('"'):
            value = self.raw[self.pos]
            if value < 0x20 or value > 0x7E or value == ord("\\"):
                raise ScanError("ambiguous_string")
            self.pos += 1
        if self.pos >= len(self.raw):
            raise ScanError("unterminated_string")
        self.pos += 1
        return self.raw[start : self.pos - 1]

    def field(self, expected: bytes) -> None:
        if self.string() != expected:
            raise ScanError("unknown_or_duplicate_field")
        self.byte(ord(':'))

    def finish(self) -> None:
        self._space()
        if self.pos != len(self.raw):
            raise ScanError("trailing_bytes")


def _session(value: bytes) -> str:
    text = value.decode("ascii")
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
    reader = _Reader(raw); reader.byte(ord('{')); reader.field(b"schema_version")
    if reader.string() != MANIFEST_SCHEMA.encode("ascii"):
        raise ScanError("manifest_schema_mismatch")
    reader.byte(ord(',')); reader.field(b"container_identity")
    if reader.string() != expected_identity.encode("ascii"):
        raise ScanError("container_identity_mismatch")
    reader.byte(ord(',')); reader.field(b"metadata_path")
    if reader.string() != expected_payload_path.encode("ascii"):
        raise ScanError("payload_path_mismatch")
    reader.byte(ord(',')); reader.field(b"metadata_sha256"); digest = reader.string()
    if len(digest) != 64 or set(digest) - set(b"0123456789abcdef"):
        raise ScanError("manifest_hash_shape")
    reader.byte(ord('}')); reader.finish()
    return {"complete_raw_sha256": hashlib.sha256(raw).hexdigest(), "observed_byte_count": len(raw), "metadata_sha256": digest.decode("ascii"), "minimal_ascii_decode_count": 1}


def scan_payload(raw: bytes) -> dict[str, Any]:
    reader = _Reader(raw); reader.byte(ord('{')); reader.field(b"schema_version")
    if reader.string() != PAYLOAD_SCHEMA.encode("ascii"):
        raise ScanError("payload_schema_mismatch")
    reader.byte(ord(',')); reader.field(b"symbol_sessions"); reader.byte(ord('['))
    members: list[str] = []; dates_by_symbol: dict[str, list[str]] = {}; pairs: set[tuple[str, str]] = set()
    while True:
        reader._space()
        if reader.pos < len(reader.raw) and reader.raw[reader.pos] == ord(']'):
            reader.pos += 1; break
        if members: reader.byte(ord(','))
        reader.byte(ord('{')); reader.field(b"symbol"); symbol = reader.string().decode("ascii")
        reader.byte(ord(',')); reader.field(b"session_dates"); reader.byte(ord('[')); sessions: list[str] = []
        while True:
            reader._space()
            if reader.pos < len(reader.raw) and reader.raw[reader.pos] == ord(']'):
                reader.pos += 1; break
            if sessions: reader.byte(ord(','))
            if len(sessions) >= MAX_SESSION_DATES_PER_SYMBOL:
                raise ScanError("record_bound_exceeded")
            current = _session(reader.string())
            if sessions and current <= sessions[-1]:
                raise ScanError("session_dates_not_strictly_ordered")
            if (symbol, current) in pairs:
                raise ScanError("duplicate_symbol_session")
            pairs.add((symbol, current)); sessions.append(current)
        reader.byte(ord('}'))
        if symbol not in U8 or not sessions:
            raise ScanError("missing_or_ambiguous_u8_member")
        members.append(symbol); dates_by_symbol[symbol] = sessions
    reader.byte(ord('}')); reader.finish()
    if tuple(members) != U8 or len(set(members)) != len(members):
        raise ScanError("missing_or_ambiguous_u8_member")
    all_dates = [item for symbol in U8 for item in dates_by_symbol[symbol]]
    return {"complete_raw_sha256": hashlib.sha256(raw).hexdigest(), "observed_byte_count": len(raw), "u8_members_in_order": members, "session_count": len(all_dates), "session_counts_by_symbol": {symbol: len(dates_by_symbol[symbol]) for symbol in U8}, "session_dates_by_symbol": {symbol: dates_by_symbol[symbol] for symbol in U8}, "max_session_date": max(all_dates), "minimal_ascii_decode_count": len(all_dates) + len(U8) + 1}
