"""B7.14 v2 byte parser.  Skipped values are lexed, never decoded."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Callable

ASSETS = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
START, END, SCHEMA = "2007-02-05", "2015-12-31", "lily_l1_daily_dataset_v1"
NUMBER = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")


class ScanError(ValueError):
    pass


def _utf8_lexeme(value: bytes) -> bool:
    """Validate UTF-8 bytes without creating a text value."""
    pos = 0
    while pos < len(value):
        first = value[pos]
        if first < 0x80:
            pos += 1; continue
        width = 2 if 0xC2 <= first <= 0xDF else 3 if 0xE0 <= first <= 0xEF else 4 if 0xF0 <= first <= 0xF4 else 0
        if not width or pos + width > len(value) or any(value[pos + n] & 0xC0 != 0x80 for n in range(1, width)):
            return False
        second = value[pos + 1]
        if (first == 0xE0 and second < 0xA0) or (first == 0xED and second > 0x9F) or (first == 0xF0 and second < 0x90) or (first == 0xF4 and second > 0x8F):
            return False
        pos += width
    return True


class _Parser:
    def __init__(self, raw: bytes, counters: dict[str, int]) -> None:
        self.raw, self.pos, self.counters = raw, 0, counters

    def ws(self) -> None:
        while self.pos < len(self.raw) and self.raw[self.pos] in b" \t\r\n": self.pos += 1

    def expect(self, value: bytes) -> None:
        self.ws()
        if not self.raw.startswith(value, self.pos): raise ScanError("malformed_json")
        self.pos += len(value)

    def _string_bounds(self) -> tuple[int, int]:
        self.ws()
        if self.pos >= len(self.raw) or self.raw[self.pos] != 34: raise ScanError("expected_string")
        self.pos += 1; begin = self.pos; segment = begin
        while self.pos < len(self.raw):
            byte = self.raw[self.pos]
            if byte == 34:
                if not _utf8_lexeme(self.raw[segment:self.pos]): raise ScanError("invalid_utf8_string")
                end = self.pos; self.pos += 1; return begin, end
            if byte < 0x20: raise ScanError("invalid_json_string")
            if byte == 92:
                if not _utf8_lexeme(self.raw[segment:self.pos]): raise ScanError("invalid_utf8_string")
                self.pos += 1
                if self.pos >= len(self.raw): raise ScanError("malformed_json")
                escaped = self.raw[self.pos]
                if escaped not in b'"\\/bfnrtu': raise ScanError("invalid_json_escape")
                if escaped == ord("u"):
                    if self.pos + 4 >= len(self.raw) or any(chr(x) not in "0123456789abcdefABCDEF" for x in self.raw[self.pos + 1:self.pos + 5]): raise ScanError("invalid_json_escape")
                    self.pos += 5
                else: self.pos += 1
                segment = self.pos
            else: self.pos += 1
        raise ScanError("malformed_json")

    def structural_key(self) -> str:
        begin, end = self._string_bounds(); value = self.raw[begin:end]
        if b"\\" in value: raise ScanError("escaped_structural_string")
        try: return value.decode("utf-8")
        except UnicodeDecodeError as exc: raise ScanError("invalid_utf8_metadata") from exc

    def metadata_string(self) -> str:
        begin, end = self._string_bounds(); value = self.raw[begin:end]
        if b"\\" in value: raise ScanError("escaped_metadata_string")
        try: result = value.decode("utf-8")
        except UnicodeDecodeError as exc: raise ScanError("invalid_utf8_metadata") from exc
        self.counters["metadata_strings_decoded_count"] += 1
        return result

    def skip_value(self) -> None:
        self.ws()
        if self.pos >= len(self.raw): raise ScanError("malformed_json")
        if self.raw[self.pos] == 34:
            self._string_bounds(); self.counters["skipped_string_values_count"] += 1; return
        if self.raw[self.pos] == 123:
            self._object(None); return
        if self.raw[self.pos] == 91:
            self.pos += 1; self.ws()
            if self.pos < len(self.raw) and self.raw[self.pos] == 93: self.pos += 1; return
            while True:
                self.skip_value(); self.ws()
                if self.pos < len(self.raw) and self.raw[self.pos] == 93: self.pos += 1; return
                self.expect(b",")
        start = self.pos
        while self.pos < len(self.raw) and self.raw[self.pos] not in b" \t\r\n,]}": self.pos += 1
        value = self.raw[start:self.pos]
        if value in (b"true", b"false", b"null"): return
        if NUMBER.fullmatch(value): self.counters["skipped_return_values_count"] += 1; return
        raise ScanError("malformed_json")

    def skip_return_value(self) -> None:
        """Accept only a JSON number lexeme; never decode the return value."""
        self.ws()
        start = self.pos
        while self.pos < len(self.raw) and self.raw[self.pos] not in b" \t\r\n,]}":
            self.pos += 1
        if not NUMBER.fullmatch(self.raw[start:self.pos]):
            raise ScanError("invalid_total_return_close_lexeme")
        self.counters["skipped_return_values_count"] += 1

    def _object(self, handlers: dict[str, Callable[[], Any]] | None) -> dict[str, Any]:
        self.expect(b"{"); result: dict[str, Any] = {}; self.ws()
        if self.pos < len(self.raw) and self.raw[self.pos] == 125: self.pos += 1; return result
        while True:
            key = self.structural_key()
            if key in result: raise ScanError("duplicate_json_key")
            self.expect(b":")
            if handlers is None: self.skip_value()
            elif key not in handlers: raise ScanError("unknown_structural_key")
            else: result[key] = handlers[key]()
            self.ws()
            if self.pos < len(self.raw) and self.raw[self.pos] == 125: self.pos += 1; return result
            self.expect(b",")


def _require_shape(item: dict[str, Any], keys: set[str], label: str) -> None:
    if set(item) != keys: raise ScanError(label)


def _schedule(sessions: dict[str, list[str]]) -> dict[str, Any]:
    common = sorted(set.intersection(*(set(sessions[item]) for item in ASSETS)))
    if not common: raise ScanError("empty_common_intersection")
    candidates: list[str] = []
    for item in common:
        if START <= item <= END:
            if candidates and date.fromisoformat(candidates[-1]).isocalendar()[:2] == date.fromisoformat(item).isocalendar()[:2]: candidates[-1] = item
            else: candidates.append(item)
    selected = [item for item in candidates if common.index(item) + 20 < len(common) and common[common.index(item) + 20] <= END]
    execution = [common[common.index(item) + 1] for item in selected]
    confirmation = [common[common.index(item) + 20] for item in selected]
    if not selected: raise ScanError("empty_schedule")
    if len(selected) > 465: raise ScanError("weekly_pair_ceiling_exceeded")
    payload = {"per_symbol_sessions": sessions, "common_sessions": common, "selected_decision_dates": selected, "execution_dates": execution, "t_plus_20_dates": confirmation}
    payload["canonical_schedule_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


def scan_date_only(path: Path) -> dict[str, Any]:
    counters = {"raw_byte_read_count": 0, "raw_byte_hash_count": 0, "metadata_strings_decoded_count": 0, "skipped_string_values_count": 0, "skipped_return_values_count": 0, "forbidden_semantic_decode_count": 0, "date_metadata_inspection_count": 0, "research_decision_count": 0, "ledger_row_count": 0}
    try:
        raw = path.read_bytes(); counters["raw_byte_read_count"] += 1; counters["raw_byte_hash_count"] += 1
    except OSError as exc:
        return {"outcome": "scope_restricted", "blocker": type(exc).__name__, "counters": counters}
    digest = hashlib.sha256(raw).hexdigest(); parser = _Parser(raw, counters)
    try:
        def record() -> str:
            row = parser._object({"session_date": parser.metadata_string, "availability_timestamp": parser.metadata_string, "total_return_close": parser.skip_return_value})
            _require_shape(row, {"session_date", "availability_timestamp", "total_return_close"}, "record_shape")
            return row["session_date"]
        def symbol() -> tuple[str, list[str]]:
            def records() -> list[str]:
                parser.expect(b"["); values: list[str] = []; parser.ws()
                if parser.pos < len(raw) and raw[parser.pos] == 93: parser.pos += 1; return values
                while True:
                    values.append(record()); parser.ws()
                    if parser.pos < len(raw) and raw[parser.pos] == 93: parser.pos += 1; return values
                    parser.expect(b",")
            row = parser._object({"symbol": parser.metadata_string, "records": records})
            _require_shape(row, {"symbol", "records"}, "symbol_shape"); return row["symbol"], row["records"]
        def symbols() -> list[tuple[str, list[str]]]:
            parser.expect(b"["); values: list[tuple[str, list[str]]] = []; parser.ws()
            if parser.pos < len(raw) and raw[parser.pos] == 93: parser.pos += 1; return values
            while True:
                values.append(symbol()); parser.ws()
                if parser.pos < len(raw) and raw[parser.pos] == 93: parser.pos += 1; return values
                parser.expect(b",")
        root = parser._object({"schema_version": parser.metadata_string, "acquired_at": parser.metadata_string, "cutoff_inclusive": parser.metadata_string, "symbols": symbols})
        _require_shape(root, {"schema_version", "acquired_at", "cutoff_inclusive", "symbols"}, "root_shape"); parser.ws()
        if parser.pos != len(raw): raise ScanError("malformed_json")
        if root["schema_version"] != SCHEMA or root["cutoff_inclusive"] != END: raise ScanError("schema_or_cutoff_mismatch")
        if [item[0] for item in root["symbols"]] != list(ASSETS): raise ScanError("symbol_identity_or_order_mismatch")
        sessions = dict(root["symbols"])
        for values in sessions.values():
            if not values or values != sorted(values) or len(values) != len(set(values)): raise ScanError("nonmonotonic_or_duplicate_session_date")
            for item in values:
                try: parsed = date.fromisoformat(item)
                except ValueError as exc: raise ScanError("invalid_session_date") from exc
                if parsed.isoformat() != item or parsed.weekday() > 4: raise ScanError("invalid_or_weekend_session_date")
                if item > END: raise ScanError("post_end_session_before_intersection")
        counters["date_metadata_inspection_count"] = 1
        return {"outcome": "preflight_pass", "container_sha256": digest, "attestation": _schedule(sessions), "counters": counters}
    except (ScanError, ValueError) as exc:
        return {"outcome": "scope_restricted", "container_sha256": digest, "blocker": str(exc), "counters": counters}
