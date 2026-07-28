"""Byte-only structural scanner for the future B8.5 one-shot preflight."""
from __future__ import annotations

import hashlib
from typing import Any

U8 = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
CUTOFF = "2015-12-31"
MANIFEST_SCHEMA = "lily_l4_b85_structural_manifest_v1"
PAYLOAD_SCHEMA = "lily_l4_b85_u8_symbol_session_dates_v1"
MAX_BYTES = 65536


class ScanError(ValueError):
    pass


class _Reader:
    def __init__(self, raw: bytes) -> None:
        if not isinstance(raw, bytes) or not raw or len(raw) > MAX_BYTES:
            raise ScanError("bounded_raw_bytes_required")
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
        self._space(); self.byte(ord('"'))
        start = self.pos
        while self.pos < len(self.raw) and self.raw[self.pos] != ord('"'):
            byte = self.raw[self.pos]
            if byte < 0x20 or byte > 0x7E or byte in (ord('\\'),):
                raise ScanError("ambiguous_string")
            self.pos += 1
        if self.pos >= len(self.raw):
            raise ScanError("unterminated_string")
        self.pos += 1
        return self.raw[start:self.pos - 1]

    def field(self, key: bytes) -> None:
        if self.string() != key:
            raise ScanError("unknown_or_duplicate_field")
        self.byte(ord(':'))

    def finish(self) -> None:
        self._space()
        if self.pos != len(self.raw):
            raise ScanError("trailing_bytes")


def _ascii(token: bytes) -> str:
    return token.decode("ascii")


def scan_manifest(raw: bytes, *, expected_identity: str, expected_payload_path: str) -> dict[str, Any]:
    reader = _Reader(raw)
    reader.byte(ord('{')); reader.field(b"schema_version")
    if reader.string() != MANIFEST_SCHEMA.encode(): raise ScanError("manifest_schema_mismatch")
    reader.byte(ord(',')); reader.field(b"container_identity")
    if reader.string() != expected_identity.encode(): raise ScanError("container_identity_mismatch")
    reader.byte(ord(',')); reader.field(b"metadata_path")
    if reader.string() != expected_payload_path.encode(): raise ScanError("payload_path_mismatch")
    reader.byte(ord(',')); reader.field(b"metadata_sha256")
    digest = reader.string()
    if len(digest) != 64 or any(byte not in b"0123456789abcdef" for byte in digest): raise ScanError("manifest_hash_shape")
    reader.byte(ord('}')); reader.finish()
    return {"raw_sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw), "metadata_sha256": _ascii(digest)}


def scan_payload(raw: bytes) -> dict[str, Any]:
    reader = _Reader(raw)
    reader.byte(ord('{')); reader.field(b"schema_version")
    if reader.string() != PAYLOAD_SCHEMA.encode(): raise ScanError("payload_schema_mismatch")
    reader.byte(ord(',')); reader.field(b"symbol_sessions"); reader.byte(ord('['))
    rows: list[tuple[str, str]] = []
    while True:
        reader._space()
        if reader.pos < len(reader.raw) and reader.raw[reader.pos] == ord(']'):
            reader.pos += 1; break
        if rows: reader.byte(ord(','))
        reader.byte(ord('{')); reader.field(b"symbol")
        symbol = reader.string()
        reader.byte(ord(',')); reader.field(b"session_date")
        session = reader.string()
        reader.byte(ord('}'))
        if symbol.decode("ascii") not in U8 or len(session) != 10 or session[4:5] != b"-" or session[7:8] != b"-" or not (session[:4] + session[5:7] + session[8:]).isdigit():
            raise ScanError("non_structural_symbol_or_session")
        rows.append((_ascii(symbol), _ascii(session)))
        if len(rows) > 4096: raise ScanError("record_bound_exceeded")
    reader.byte(ord('}')); reader.finish()
    members = [symbol for symbol, _ in rows]
    if len(set(members)) != len(members) or sorted(members) != sorted(U8): raise ScanError("missing_or_ambiguous_u8_member")
    if any(session > CUTOFF for _, session in rows): raise ScanError("post_cutoff_session")
    return {"raw_sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw), "u8_members_in_order": members, "session_count": len(rows), "max_session_date": max(session for _, session in rows), "minimal_ascii_token_decode_count": len(rows) * 2 + 1}
