"""Byte-level B7.14 metadata scanner; it never decodes a return or price value."""
from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from typing import Any


ASSETS = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
START = "2007-02-05"
END = "2015-12-31"
SCHEMA = "lily_l1_daily_dataset_v1"


class ScanError(ValueError):
    pass


class _BytesJson:
    def __init__(self, raw: bytes) -> None:
        self.raw, self.pos = raw, 0

    def whitespace(self) -> None:
        while self.pos < len(self.raw) and self.raw[self.pos] in b" \t\r\n":
            self.pos += 1

    def expect(self, token: bytes) -> None:
        self.whitespace()
        if not self.raw.startswith(token, self.pos):
            raise ScanError("malformed_json")
        self.pos += len(token)

    def string(self) -> str:
        self.whitespace()
        if self.pos >= len(self.raw) or self.raw[self.pos] != ord('"'):
            raise ScanError("expected_string")
        start = self.pos
        self.pos += 1
        escaped = False
        while self.pos < len(self.raw):
            value = self.raw[self.pos]
            self.pos += 1
            if escaped:
                escaped = False
            elif value == ord('\\'):
                escaped = True
            elif value == ord('"'):
                try:
                    fragment = self.raw[start + 1:self.pos - 1]
                    if b"\\" in fragment:
                        raise ValueError("escaped metadata strings are not accepted")
                    return fragment.decode("utf-8")
                except (UnicodeDecodeError, ValueError) as exc:
                    raise ScanError("invalid_json_string") from exc
            elif value < 0x20:
                raise ScanError("invalid_json_string")
        raise ScanError("malformed_json")

    def skip(self) -> None:
        self.whitespace()
        if self.pos >= len(self.raw):
            raise ScanError("malformed_json")
        token = self.raw[self.pos]
        if token == ord('"'):
            self._skip_string(); return
        if token == ord('{'):
            self.pos += 1; seen: set[str] = set(); self.whitespace()
            if self.pos < len(self.raw) and self.raw[self.pos] == ord('}'):
                self.pos += 1; return
            while True:
                key = self.string()
                if key in seen: raise ScanError("duplicate_json_key")
                seen.add(key); self.expect(b":"); self.skip(); self.whitespace()
                if self.pos < len(self.raw) and self.raw[self.pos] == ord('}'):
                    self.pos += 1; return
                self.expect(b",")
        elif token == ord('['):
            self.pos += 1; self.whitespace()
            if self.pos < len(self.raw) and self.raw[self.pos] == ord(']'):
                self.pos += 1; return
            while True:
                self.skip(); self.whitespace()
                if self.pos < len(self.raw) and self.raw[self.pos] == ord(']'):
                    self.pos += 1; return
                self.expect(b",")
        else:
            start = self.pos
            while self.pos < len(self.raw) and self.raw[self.pos] not in b" \t\r\n,]}":
                self.pos += 1
            if start == self.pos or self.raw[start:self.pos] not in (b"true", b"false", b"null") and not _number(self.raw[start:self.pos]):
                raise ScanError("malformed_json")

    def _skip_string(self) -> None:
        self.pos += 1; escaped = False
        while self.pos < len(self.raw):
            value = self.raw[self.pos]; self.pos += 1
            if escaped: escaped = False
            elif value == ord('\\'): escaped = True
            elif value == ord('"'): return
            elif value < 0x20: raise ScanError("invalid_json_string")
        raise ScanError("malformed_json")


def _number(value: bytes) -> bool:
    try:
        text = value.decode("ascii")
        float(text)
    except (UnicodeDecodeError, ValueError):
        return False
    return text not in {"NaN", "Infinity", "-Infinity"}


def scan_date_metadata(path: Path) -> dict[str, Any]:
    """Hash raw bytes then decode only approved structural strings and session dates."""
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    parser = _BytesJson(raw)
    try:
        parser.expect(b"{")
        root: dict[str, Any] = {}
        while True:
            parser.whitespace()
            if parser.pos < len(raw) and raw[parser.pos] == ord('}'):
                parser.pos += 1; break
            key = parser.string()
            if key in root: raise ScanError("duplicate_json_key")
            parser.expect(b":")
            if key in {"schema_version", "cutoff_inclusive"}:
                root[key] = parser.string()
            elif key == "acquired_at":
                parser.skip()
            elif key == "symbols":
                root[key] = _symbols(parser)
            else:
                raise ScanError("unknown_root_key")
            parser.whitespace()
            if parser.pos < len(raw) and raw[parser.pos] == ord('}'):
                parser.pos += 1; break
            parser.expect(b",")
        parser.whitespace()
        if parser.pos != len(raw): raise ScanError("malformed_json")
        if set(root) != {"schema_version", "cutoff_inclusive", "symbols"}: raise ScanError("root_shape")
        if root["schema_version"] != SCHEMA: raise ScanError("schema_version_mismatch")
        if root["cutoff_inclusive"] != END: raise ScanError("cutoff_inclusive_mismatch")
        names = [item[0] for item in root["symbols"]]
        if names != list(ASSETS): raise ScanError("symbol_identity_or_order_mismatch")
        sessions = {symbol: values for symbol, values in root["symbols"]}
        for values in sessions.values():
            _validate_dates(values)
            if any(value > END for value in values): raise ScanError("post_end_session_before_intersection")
        common = sorted(set.intersection(*(set(sessions[asset]) for asset in ASSETS)))
        schedule = build_schedule(common)
        return {"status": "preflight_pass", "container_sha256": digest, "schema_version": SCHEMA,
                "cutoff_inclusive": END, "per_symbol": {asset: _summary(sessions[asset]) for asset in ASSETS},
                "common_session_count": len(common), **schedule, "return_values_decoded_count": 0}
    except ScanError as exc:
        return {"status": "scope_restricted", "container_sha256": digest, "blocker": str(exc),
                "return_values_decoded_count": 0}


def _symbols(parser: _BytesJson) -> list[tuple[str, list[str]]]:
    parser.expect(b"["); result: list[tuple[str, list[str]]] = []; parser.whitespace()
    if parser.pos < len(parser.raw) and parser.raw[parser.pos] == ord(']'): raise ScanError("symbol_count_mismatch")
    while True:
        result.append(_symbol(parser)); parser.whitespace()
        if parser.pos < len(parser.raw) and parser.raw[parser.pos] == ord(']'):
            parser.pos += 1; return result
        parser.expect(b",")


def _symbol(parser: _BytesJson) -> tuple[str, list[str]]:
    parser.expect(b"{"); item: dict[str, Any] = {}
    while True:
        key = parser.string()
        if key in item: raise ScanError("duplicate_json_key")
        parser.expect(b":")
        if key == "symbol": item[key] = parser.string()
        elif key == "records": item[key] = _records(parser)
        else: raise ScanError("unknown_symbol_key")
        parser.whitespace()
        if parser.pos < len(parser.raw) and parser.raw[parser.pos] == ord('}'):
            parser.pos += 1; break
        parser.expect(b",")
    if set(item) != {"symbol", "records"} or not isinstance(item["symbol"], str): raise ScanError("symbol_shape")
    return item["symbol"], item["records"]


def _records(parser: _BytesJson) -> list[str]:
    parser.expect(b"["); dates: list[str] = []; parser.whitespace()
    if parser.pos < len(parser.raw) and parser.raw[parser.pos] == ord(']'):
        parser.pos += 1; return dates
    while True:
        parser.expect(b"{"); row: dict[str, str] = {}
        while True:
            key = parser.string()
            if key in row: raise ScanError("duplicate_json_key")
            parser.expect(b":")
            if key == "session_date": row[key] = parser.string()
            elif key in {"availability_timestamp", "total_return_close"}: parser.skip(); row[key] = "skipped"
            else: raise ScanError("unknown_record_key")
            parser.whitespace()
            if parser.pos < len(parser.raw) and parser.raw[parser.pos] == ord('}'):
                parser.pos += 1; break
            parser.expect(b",")
        if set(row) != {"session_date", "availability_timestamp", "total_return_close"}: raise ScanError("record_shape")
        dates.append(row["session_date"]); parser.whitespace()
        if parser.pos < len(parser.raw) and parser.raw[parser.pos] == ord(']'):
            parser.pos += 1; return dates
        parser.expect(b",")


def _validate_dates(values: list[str]) -> None:
    parsed = []
    for value in values:
        try: item = date.fromisoformat(value)
        except ValueError as exc: raise ScanError("invalid_session_date") from exc
        if item.weekday() >= 5: raise ScanError("weekend_session_date")
        parsed.append(value)
    if values != sorted(values) or len(values) != len(set(values)): raise ScanError("nonmonotonic_or_duplicate_session_date")


def _summary(values: list[str]) -> dict[str, Any]:
    return {"date_count": len(values), "min_session_date": values[0] if values else None, "max_session_date": values[-1] if values else None}


def build_schedule(common: list[str]) -> dict[str, Any]:
    candidates: list[str] = []
    for item in common:
        if START <= item <= END:
            if not candidates or date.fromisoformat(candidates[-1]).isocalendar()[:2] != date.fromisoformat(item).isocalendar()[:2]: candidates.append(item)
            else: candidates[-1] = item
    selected: list[str] = []; executions: list[str] = []; confirmations: list[str] = []
    for item in candidates:
        index = common.index(item)
        if index + 20 < len(common) and common[index + 20] <= END:
            selected.append(item); executions.append(common[index + 1]); confirmations.append(common[index + 20])
    if len(selected) > 465: raise ScanError("weekly_observation_ceiling_exceeded")
    canonical = {"selected_decision_dates": selected, "execution_dates": executions, "t_plus_20_dates": confirmations}
    import json
    return {**canonical, "canonical_schedule_sha256": hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
