"""E0-only, in-memory byte scanner for the prospective B7.14 remediation.

This module intentionally has no path or filesystem API.  It accepts synthetic
bytes only; callers cannot use it to open a real container.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from typing import Any, Callable

ASSETS = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
START = "2007-02-05"
END = "2015-12-31"
SCHEMA = "lily_l1_daily_dataset_v1"
NUMBER = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")


class ScanError(ValueError):
    """The synthetic bytes do not meet the closed-world structural contract."""


def valid_utf8_bytes(raw: bytes) -> bool:
    """Validate UTF-8 bytes without decoding, including RFC 3629 boundary rules."""
    index = 0
    size = len(raw)
    while index < size:
        first = raw[index]
        if first <= 0x7F:
            index += 1
            continue
        if 0xC2 <= first <= 0xDF:
            needed, low, high = 1, 0x80, 0xBF
        elif first == 0xE0:
            needed, low, high = 2, 0xA0, 0xBF
        elif 0xE1 <= first <= 0xEC or 0xEE <= first <= 0xEF:
            needed, low, high = 2, 0x80, 0xBF
        elif first == 0xED:
            needed, low, high = 2, 0x80, 0x9F
        elif first == 0xF0:
            needed, low, high = 3, 0x90, 0xBF
        elif 0xF1 <= first <= 0xF3:
            needed, low, high = 3, 0x80, 0xBF
        elif first == 0xF4:
            needed, low, high = 3, 0x80, 0x8F
        else:
            return False
        if index + needed >= size or not low <= raw[index + 1] <= high:
            return False
        if any(not 0x80 <= raw[index + offset] <= 0xBF for offset in range(2, needed + 1)):
            return False
        index += needed + 1
    return True


def _valid_json_string_lexeme(raw: bytes) -> bool:
    if len(raw) < 2 or raw[:1] != b'"' or raw[-1:] != b'"':
        return False
    index = 1
    segment = index
    end = len(raw) - 1
    while index < end:
        value = raw[index]
        if value < 0x20:
            return False
        if value != 0x5C:
            index += 1
            continue
        if not valid_utf8_bytes(raw[segment:index]) or index + 1 >= end:
            return False
        escaped = raw[index + 1]
        if escaped in b'"\\/bfnrt':
            index += 2
        elif escaped == 0x75 and index + 5 < end and all(
            character in b"0123456789abcdefABCDEF" for character in raw[index + 2 : index + 6]
        ):
            index += 6
        else:
            return False
        segment = index
    return valid_utf8_bytes(raw[segment:end])


def skip_timestamp_lexeme(raw: bytes) -> bool:
    """Validate and skip a timestamp string without creating text or a date."""
    return _valid_json_string_lexeme(raw)


def skip_return_number_lexeme(raw: bytes) -> bool:
    """Validate and skip a JSON number without numeric conversion."""
    return bool(NUMBER.fullmatch(raw))


class _Parser:
    def __init__(self, raw: bytes, counters: dict[str, int]) -> None:
        self.raw = raw
        self.position = 0
        self.counters = counters

    def _ws(self) -> None:
        while self.position < len(self.raw) and self.raw[self.position] in b" \t\r\n":
            self.position += 1

    def _expect(self, value: bytes) -> None:
        self._ws()
        if not self.raw.startswith(value, self.position):
            raise ScanError("malformed_json")
        self.position += len(value)

    def _string_lexeme(self) -> bytes:
        self._ws()
        begin = self.position
        if begin >= len(self.raw) or self.raw[begin] != 0x22:
            raise ScanError("expected_json_string")
        self.position += 1
        escaped = False
        while self.position < len(self.raw):
            value = self.raw[self.position]
            if value == 0x22 and not escaped:
                self.position += 1
                lexeme = self.raw[begin:self.position]
                if not _valid_json_string_lexeme(lexeme):
                    raise ScanError("invalid_json_string")
                return lexeme
            escaped = value == 0x5C and not escaped
            if value != 0x5C:
                escaped = False
            self.position += 1
        raise ScanError("malformed_json")

    def text(self) -> str:
        lexeme = self._string_lexeme()
        body = lexeme[1:-1]
        if b"\\" in body or not valid_utf8_bytes(body):
            raise ScanError("escaped_or_invalid_allowed_string")
        self.counters["allowed_string_decode_count"] += 1
        return body.decode("utf-8")

    def timestamp(self) -> None:
        if not skip_timestamp_lexeme(self._string_lexeme()):
            raise ScanError("invalid_timestamp_lexeme")
        self.counters["skipped_timestamp_string_lexeme_count"] += 1

    def return_number(self) -> None:
        self._ws()
        begin = self.position
        while self.position < len(self.raw) and self.raw[self.position] not in b" \t\r\n,]}":
            self.position += 1
        if not skip_return_number_lexeme(self.raw[begin:self.position]):
            raise ScanError("invalid_total_return_close_lexeme")
        self.counters["skipped_return_number_lexeme_count"] += 1

    def object(self, handlers: dict[str, Callable[[], Any]]) -> dict[str, Any]:
        self._expect(b"{")
        result: dict[str, Any] = {}
        self._ws()
        if self.position < len(self.raw) and self.raw[self.position] == 0x7D:
            self.position += 1
            return result
        while True:
            key = self.text()
            if key in result or key not in handlers:
                raise ScanError("unknown_or_duplicate_structural_key")
            self._expect(b":")
            result[key] = handlers[key]()
            self._ws()
            if self.position < len(self.raw) and self.raw[self.position] == 0x7D:
                self.position += 1
                return result
            self._expect(b",")

    def array(self, item: Callable[[], Any]) -> list[Any]:
        self._expect(b"[")
        result: list[Any] = []
        self._ws()
        if self.position < len(self.raw) and self.raw[self.position] == 0x5D:
            self.position += 1
            return result
        while True:
            result.append(item())
            self._ws()
            if self.position < len(self.raw) and self.raw[self.position] == 0x5D:
                self.position += 1
                return result
            self._expect(b",")


def _closed_shape(value: dict[str, Any], expected: set[str], blocker: str) -> None:
    if set(value) != expected:
        raise ScanError(blocker)


def _date_string(value: str, blocker: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ScanError(blocker) from exc
    if parsed.isoformat() != value:
        raise ScanError(blocker)
    return parsed


def build_schedule(per_symbol_sessions: dict[str, list[str]]) -> dict[str, Any]:
    common = sorted(set.intersection(*(set(per_symbol_sessions[symbol]) for symbol in ASSETS)))
    if not common:
        raise ScanError("empty_common_intersection")
    weekly: list[str] = []
    for session in common:
        if START <= session <= END:
            if weekly and _date_string(weekly[-1], "invalid_session_date").isocalendar()[:2] == _date_string(session, "invalid_session_date").isocalendar()[:2]:
                weekly[-1] = session
            else:
                weekly.append(session)
    index = {session: position for position, session in enumerate(common)}
    selected = [session for session in weekly if index[session] + 20 < len(common) and common[index[session] + 20] <= END]
    if not selected:
        raise ScanError("empty_schedule")
    if len(selected) > 465:
        raise ScanError("weekly_pair_ceiling_exceeded")
    execution = [common[index[session] + 1] for session in selected]
    t_plus_20 = [common[index[session] + 20] for session in selected]
    evidence = {
        "per_symbol_sessions": per_symbol_sessions,
        "common_sessions": common,
        "selected_decision_dates": selected,
        "execution_dates": execution,
        "t_plus_20_dates": t_plus_20,
    }
    canonical = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**evidence, "date_evidence_sha256": hashlib.sha256(canonical).hexdigest()}


def scan_synthetic_date_only(raw: bytes) -> dict[str, Any]:
    """Inspect the closed synthetic fixture and return date-only schedule evidence."""
    counters = {
        "allowed_string_decode_count": 0,
        "session_date_values_decoded_count": 0,
        "date_metadata_inspection_count": 0,
        "skipped_timestamp_string_lexeme_count": 0,
        "skipped_return_number_lexeme_count": 0,
        "real_container_access_count": 0,
        "return_decode_count": 0,
        "research_decision_count": 0,
        "ledger_row_count": 0,
        "validation_access_count": 0,
    }
    parser = _Parser(raw, counters)
    try:
        def record() -> str:
            def session_date() -> str:
                value = parser.text()
                counters["session_date_values_decoded_count"] += 1
                counters["date_metadata_inspection_count"] += 1
                return value

            value = parser.object(
                {
                    "session_date": session_date,
                    "availability_timestamp": parser.timestamp,
                    "total_return_close": parser.return_number,
                }
            )
            _closed_shape(value, {"session_date", "availability_timestamp", "total_return_close"}, "record_shape")
            return value["session_date"]

        def symbol() -> tuple[str, list[str]]:
            value = parser.object({"symbol": parser.text, "records": lambda: parser.array(record)})
            _closed_shape(value, {"symbol", "records"}, "symbol_shape")
            return value["symbol"], value["records"]

        root = parser.object(
            {
                "schema_version": parser.text,
                "acquired_at": parser.timestamp,
                "cutoff_inclusive": parser.text,
                "symbols": lambda: parser.array(symbol),
            }
        )
        _closed_shape(root, {"schema_version", "acquired_at", "cutoff_inclusive", "symbols"}, "root_shape")
        parser._ws()
        if parser.position != len(raw):
            raise ScanError("malformed_json")
        if root["schema_version"] != SCHEMA or root["cutoff_inclusive"] != END:
            raise ScanError("schema_or_cutoff_mismatch")
        if [item[0] for item in root["symbols"]] != list(ASSETS):
            raise ScanError("symbol_identity_or_order_mismatch")
        sessions = dict(root["symbols"])
        for values in sessions.values():
            if not values or values != sorted(values) or len(values) != len(set(values)):
                raise ScanError("nonmonotonic_or_duplicate_session_date")
            for value in values:
                parsed = _date_string(value, "invalid_session_date")
                if parsed.weekday() > 4:
                    raise ScanError("invalid_or_weekend_session_date")
                if value > END:
                    raise ScanError("post_end_session_before_intersection")
        return {"status": "synthetic_preflight_pass", "schedule": build_schedule(sessions), "counters": counters}
    except ScanError as exc:
        return {"status": "scope_restricted", "blocker": str(exc), "counters": counters}
