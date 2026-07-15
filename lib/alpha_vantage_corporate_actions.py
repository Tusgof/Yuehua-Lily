"""Locked Alpha Vantage corporate-action acquisition for Lily B4.4."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from lib.io import load_json, write_json
from lib.provenance import file_sha256, payload_sha256


COMPARISON_START = date(2006, 2, 3)
COMPARISON_END = date(2015, 12, 31)
USER_AGENT = "Yuehua-Lily-research/1.0"
FetchResult = tuple[int, bytes]
Fetcher = Callable[[str, str], FetchResult]


class AcquisitionBlocked(RuntimeError):
    """Raised when a locked acquisition guardrail blocks progress."""


def acquire_corporate_actions(
    contract: dict[str, Any],
    *,
    data_root: Path,
    credential: str,
    fetcher: Fetcher | None = None,
    sleeper: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    if not credential:
        raise AcquisitionBlocked("credential_missing")
    clock = now or (lambda: datetime.now(UTC))
    request_guardrails = contract["request_guardrails"]
    universe = contract["request_universe"]
    raw_dir = data_root / "raw" / "alpha_vantage_corporate_actions_v1"
    normalized_path = data_root / "normalized" / "alpha_vantage_corporate_actions_v1.json"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_dir / "request_manifest.json"
    attempt_path = raw_dir / "attempt_ledger.json"
    private_reconciliation_path = raw_dir / "reconciliation_private.json"

    manifest = _load_or_initialize_manifest(manifest_path, clock())
    attempt_ledger = _load_or_initialize_attempt_ledger(attempt_path)
    completed = {(row["symbol"], row["function"]): row for row in manifest["containers"]}
    fetch = fetcher or _fetch
    last_attempt_started: float | None = None
    resumed_count = 0

    for symbol in universe["symbols"]:
        for function, endpoint_contract in universe["endpoints"].items():
            pair = (symbol, function)
            raw_path = raw_dir / f"{symbol}_{function}.json"
            if pair in completed:
                _verify_resumable_container(raw_path, completed[pair])
                resumed_count += 1
                continue
            if raw_path.exists():
                raise AcquisitionBlocked("orphan_raw_container")

            while True:
                current_day = clock().date().isoformat()
                daily_attempts = [row for row in attempt_ledger["attempts"] if row["utc_date"] == current_day]
                pair_attempts = [
                    row
                    for row in daily_attempts
                    if row["symbol"] == symbol and row["function"] == function
                ]
                if len(daily_attempts) >= request_guardrails["daily_total_attempt_cap"]:
                    raise AcquisitionBlocked("daily_attempt_cap_reached")
                if len(pair_attempts) >= request_guardrails["maximum_attempts_per_symbol_endpoint_per_day"]:
                    raise AcquisitionBlocked("pair_attempt_cap_reached")

                if last_attempt_started is not None:
                    remaining = (
                        request_guardrails["minimum_seconds_between_attempts"]
                        - (monotonic() - last_attempt_started)
                    )
                    if remaining > 0:
                        sleeper(remaining)
                last_attempt_started = monotonic()
                attempted_at = _timestamp(clock())
                status, raw, category = _attempt_fetch(
                    fetch,
                    contract["source"]["base_url"],
                    symbol,
                    function,
                    credential,
                )
                attempt_row = {
                    "symbol": symbol,
                    "function": function,
                    "attempted_at_utc": attempted_at,
                    "utc_date": attempted_at[:10],
                    "http_status": status,
                    "category": category,
                }
                attempt_ledger["attempts"].append(attempt_row)
                write_json(attempt_path, attempt_ledger)

                if category == "success":
                    summary, records = validate_and_normalize_payload(
                        raw,
                        symbol=symbol,
                        function=function,
                        endpoint_contract=endpoint_contract,
                        retrieved_at_utc=attempted_at,
                    )
                    if credential.encode("utf-8") in raw:
                        raise AcquisitionBlocked("credential_echoed_in_payload")
                    _write_immutable(raw_path, raw)
                    container_hash = hashlib.sha256(raw).hexdigest()
                    row = {
                        "provider": "Alpha Vantage",
                        "symbol": symbol,
                        "function": function,
                        "retrieved_at_utc": attempted_at,
                        "http_status": status,
                        "attempt_number": len(attempt_ledger["attempts"]),
                        "key_provenance_label": contract["source"]["key_provenance_label"],
                        "source_container_sha256": container_hash,
                        **summary,
                    }
                    manifest["containers"].append(row)
                    manifest["updated_at_utc"] = attempted_at
                    manifest["containers"].sort(key=lambda item: (item["symbol"], item["function"]))
                    write_json(manifest_path, manifest)
                    completed[pair] = row
                    break
                if category not in request_guardrails["retryable_categories"]:
                    raise AcquisitionBlocked(f"non_retryable_response:{category}")

    expected_pairs = {
        (symbol, function)
        for symbol in universe["symbols"]
        for function in universe["endpoints"]
    }
    if set(completed) != expected_pairs:
        raise AcquisitionBlocked("successful_pair_inventory_mismatch")

    normalized_records: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    for row in sorted(completed.values(), key=lambda item: (item["symbol"], item["function"])):
        raw_path = raw_dir / f"{row['symbol']}_{row['function']}.json"
        raw = raw_path.read_bytes()
        summary, records = validate_and_normalize_payload(
            raw,
            symbol=row["symbol"],
            function=row["function"],
            endpoint_contract=universe["endpoints"][row["function"]],
            retrieved_at_utc=row["retrieved_at_utc"],
        )
        if hashlib.sha256(raw).hexdigest() != row["source_container_sha256"]:
            raise AcquisitionBlocked("resumed_container_hash_mismatch")
        normalized_records.extend(records)
        coverage_rows.append(
            {
                "symbol": row["symbol"],
                "function": row["function"],
                "row_count": summary["row_count"],
                "field_inventory": summary["field_inventory"],
                "earliest_event_date": summary["earliest_event_date"],
                "latest_event_date": summary["latest_event_date"],
                "source_container_sha256": row["source_container_sha256"],
            }
        )

    normalized_records.sort(
        key=lambda row: (row["symbol"], row["event_type"], row["event_date"], row["source_container_sha256"])
    )
    acquired_at = min(row["retrieved_at_utc"] for row in completed.values())
    normalized = {
        "schema_version": "lily_alpha_vantage_corporate_actions_normalized_v1",
        "provider": "Alpha Vantage",
        "acquired_at": acquired_at,
        "records": normalized_records,
        "limitations": [
            "The provider response is a current snapshot rather than a point-in-time revision archive.",
            "Clean empty arrays are provider-reported no events and do not independently prove completeness.",
        ],
    }
    write_json(normalized_path, normalized)

    reconciliation = reconcile_with_yahoo(
        normalized_records,
        data_root=data_root,
        symbols=universe["symbols"],
    )
    write_json(private_reconciliation_path, reconciliation["private"])
    specification = {
        "base_url": contract["source"]["base_url"],
        "symbols": universe["symbols"],
        "endpoints": universe["endpoints"],
        "allowed_query_parameter_names": universe["allowed_query_parameter_names"],
        "request_guardrails": request_guardrails,
    }
    aggregate_hash = payload_sha256(
        [
            {
                "symbol": row["symbol"],
                "function": row["function"],
                "source_container_sha256": row["source_container_sha256"],
            }
            for row in coverage_rows
        ]
    )
    return {
        "acquired_at": acquired_at,
        "successful_payload_count": len(completed),
        "attempt_count": len(attempt_ledger["attempts"]),
        "resumed_payload_count": resumed_count,
        "coverage_rows": coverage_rows,
        "reconciliation_rows": reconciliation["public"],
        "all_pre_2016_events_exactly_reconciled": all(
            row["exact_match"] for row in reconciliation["public"]
        ),
        "duplicate_canonical_record_count": _duplicate_count(normalized_records),
        "hashes": {
            "aggregate_container_sha256": aggregate_hash,
            "request_manifest_sha256": file_sha256(manifest_path),
            "normalized_output_sha256": file_sha256(normalized_path),
            "request_and_normalization_specification_sha256": payload_sha256(specification),
            "private_reconciliation_sha256": file_sha256(private_reconciliation_path),
        },
        "storage_references": {
            "raw": "${LILY_DATA_ROOT}/raw/alpha_vantage_corporate_actions_v1",
            "normalized": "${LILY_DATA_ROOT}/normalized/alpha_vantage_corporate_actions_v1.json",
        },
        "validation_return_status": "sealed_not_accessed",
        "maximum_existing_market_or_return_date_accessed": "2015-12-31",
        "actual_paid_amount_usd": 0,
        "key_environment_name": contract["source"]["key_environment_name"],
        "key_provenance_label": contract["source"]["key_provenance_label"],
    }


def validate_and_normalize_payload(
    raw: bytes,
    *,
    symbol: str,
    function: str,
    endpoint_contract: dict[str, Any],
    retrieved_at_utc: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AcquisitionBlocked("provider_payload_invalid_json") from exc
    if not isinstance(payload, dict):
        raise AcquisitionBlocked("provider_payload_must_be_object")
    if any(field in payload for field in ("Information", "Note", "Error Message")):
        raise AcquisitionBlocked("service_message_not_success")
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise AcquisitionBlocked("provider_data_must_be_array")
    required = endpoint_contract["required_nonempty_row_fields"]
    records: list[dict[str, Any]] = []
    fields: set[str] = set()
    event_dates: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise AcquisitionBlocked(f"provider_row_must_be_object:{index}")
        fields.update(str(key) for key in row)
        missing = [field for field in required if field not in row]
        if missing:
            raise AcquisitionBlocked(f"provider_row_missing_required_field:{index}")
        event_date = _iso_date(row[endpoint_contract["canonical_event_date"]])
        event_dates.append(event_date)
        amount = None
        split_factor = None
        if function == "DIVIDENDS":
            amount = _decimal_text(row["amount"])
        elif function == "SPLITS":
            split_factor = _decimal_text(row["split_factor"])
        else:
            raise AcquisitionBlocked("unsupported_function")
        records.append(
            {
                "provider": "Alpha Vantage",
                "symbol": symbol,
                "event_type": function,
                "event_date": event_date,
                "amount": amount,
                "split_factor": split_factor,
                "declared_date": _optional_iso_date(row.get("declaration_date")),
                "record_date": _optional_iso_date(row.get("record_date")),
                "payment_date": _optional_iso_date(row.get("payment_date")),
                "retrieved_at_utc": retrieved_at_utc,
                "source_container_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return (
        {
            "row_count": len(rows),
            "field_inventory": sorted(fields),
            "earliest_event_date": min(event_dates) if event_dates else None,
            "latest_event_date": max(event_dates) if event_dates else None,
            "empty_array": not rows,
        },
        records,
    )


def reconcile_with_yahoo(
    alpha_records: list[dict[str, Any]], *, data_root: Path, symbols: list[str]
) -> dict[str, list[dict[str, Any]]]:
    public: list[dict[str, Any]] = []
    private: list[dict[str, Any]] = []
    for symbol in symbols:
        yahoo = _yahoo_events(data_root / "raw" / "yahoo_l1_v1" / f"{symbol}.json")
        for function in ("DIVIDENDS", "SPLITS"):
            alpha_keys = Counter(
                _comparison_key(row)
                for row in alpha_records
                if row["symbol"] == symbol
                and row["event_type"] == function
                and COMPARISON_START.isoformat() <= row["event_date"] <= COMPARISON_END.isoformat()
            )
            yahoo_keys = Counter(yahoo[function])
            matched = alpha_keys & yahoo_keys
            alpha_only = alpha_keys - yahoo_keys
            yahoo_only = yahoo_keys - alpha_keys
            public.append(
                {
                    "symbol": symbol,
                    "function": function,
                    "comparison_start": COMPARISON_START.isoformat(),
                    "comparison_end": COMPARISON_END.isoformat(),
                    "alpha_event_count": sum(alpha_keys.values()),
                    "yahoo_event_count": sum(yahoo_keys.values()),
                    "matched_event_count": sum(matched.values()),
                    "alpha_only_event_count": sum(alpha_only.values()),
                    "yahoo_only_event_count": sum(yahoo_only.values()),
                    "exact_match": not alpha_only and not yahoo_only,
                }
            )
            private.append(
                {
                    "symbol": symbol,
                    "function": function,
                    "alpha_only": _counter_rows(alpha_only),
                    "yahoo_only": _counter_rows(yahoo_only),
                }
            )
    public.sort(key=lambda row: (row["symbol"], row["function"]))
    private.sort(key=lambda row: (row["symbol"], row["function"]))
    return {"public": public, "private": private}


def _yahoo_events(path: Path) -> dict[str, list[tuple[str, str]]]:
    payload = load_json(path)
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    if timestamps and max(datetime.fromtimestamp(int(value), UTC).date() for value in timestamps) > COMPARISON_END:
        raise AcquisitionBlocked("existing_yahoo_market_data_crosses_locked_cutoff")
    dividends: list[tuple[str, str]] = []
    for row in result.get("events", {}).get("dividends", {}).values():
        event_date = datetime.fromtimestamp(int(row["date"]), UTC).date()
        if COMPARISON_START <= event_date <= COMPARISON_END:
            dividends.append((event_date.isoformat(), _decimal_text(row["amount"])))
    splits: list[tuple[str, str]] = []
    for row in result.get("events", {}).get("splits", {}).values():
        event_date = datetime.fromtimestamp(int(row["date"]), UTC).date()
        if COMPARISON_START <= event_date <= COMPARISON_END:
            splits.append((event_date.isoformat(), _ratio_text(row["splitRatio"])))
    return {"DIVIDENDS": dividends, "SPLITS": splits}


def _comparison_key(row: dict[str, Any]) -> tuple[str, str]:
    value = row["amount"] if row["event_type"] == "DIVIDENDS" else row["split_factor"]
    return row["event_date"], str(value)


def _counter_rows(counter: Counter[tuple[str, str]]) -> list[dict[str, Any]]:
    return [
        {"event_date": key[0], "value": key[1], "count": count}
        for key, count in sorted(counter.items())
    ]


def _attempt_fetch(
    fetcher: Fetcher,
    base_url: str,
    symbol: str,
    function: str,
    credential: str,
) -> tuple[int, bytes, str]:
    try:
        status, raw = fetcher(
            base_url + "?" + urllib.parse.urlencode(
                {"function": function, "symbol": symbol, "apikey": credential}
            ),
            USER_AGENT,
        )
    except TimeoutError:
        return 0, b"", "timeout"
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            return exc.code, b"", "http_429"
        if 500 <= exc.code <= 599:
            return exc.code, b"", "http_5xx"
        return exc.code, b"", "unexpected_service_message"
    except (OSError, urllib.error.URLError):
        return 0, b"", "timeout"
    if status == 429:
        return status, raw, "http_429"
    if 500 <= status <= 599:
        return status, raw, "http_5xx"
    if status != 200:
        return status, raw, "unexpected_service_message"
    category = _payload_category(raw)
    return status, raw, category


def _payload_category(raw: bytes) -> str:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return "schema_drift"
    if not isinstance(payload, dict):
        return "schema_drift"
    message = " ".join(
        str(payload.get(field, "")) for field in ("Information", "Note", "Error Message")
    ).strip().lower()
    if message:
        if any(term in message for term in ("rate", "frequency", "requests per", "call frequency")):
            return "rate_limit"
        if any(term in message for term in ("api key", "apikey", "invalid key")):
            return "invalid_key"
        if any(term in message for term in ("premium", "subscription")):
            return "premium_required"
        return "unexpected_service_message"
    return "success" if isinstance(payload.get("data"), list) else "schema_drift"


def _fetch(url: str, user_agent: str) -> FetchResult:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=30) as response:
        return int(response.status), response.read()


def _load_or_initialize_manifest(path: Path, now: datetime) -> dict[str, Any]:
    if path.exists():
        payload = load_json(path)
        if payload.get("schema_version") != "lily_alpha_vantage_request_manifest_v1":
            raise AcquisitionBlocked("request_manifest_schema_mismatch")
        return payload
    return {
        "schema_version": "lily_alpha_vantage_request_manifest_v1",
        "started_at_utc": _timestamp(now),
        "updated_at_utc": _timestamp(now),
        "network_used": True,
        "paid_amount_usd": 0,
        "key_provenance_label": "owner_supplied_free_key_lily_only",
        "containers": [],
    }


def _load_or_initialize_attempt_ledger(path: Path) -> dict[str, Any]:
    if path.exists():
        payload = load_json(path)
        if payload.get("schema_version") != "lily_alpha_vantage_attempt_ledger_v1":
            raise AcquisitionBlocked("attempt_ledger_schema_mismatch")
        return payload
    return {"schema_version": "lily_alpha_vantage_attempt_ledger_v1", "attempts": []}


def _verify_resumable_container(path: Path, metadata: dict[str, Any]) -> None:
    if not path.is_file() or file_sha256(path) != metadata.get("source_container_sha256"):
        raise AcquisitionBlocked("resumable_container_missing_or_hash_mismatch")


def _write_immutable(path: Path, payload: bytes) -> None:
    if path.exists():
        raise AcquisitionBlocked("immutable_container_already_exists")
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _decimal_text(value: Any) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise AcquisitionBlocked("invalid_decimal") from exc
    if not number.is_finite() or number < 0:
        raise AcquisitionBlocked("invalid_decimal")
    text = format(number.normalize(), "f")
    return "0" if text in {"-0", ""} else text


def _ratio_text(value: Any) -> str:
    text = str(value)
    if ":" not in text:
        return _decimal_text(text)
    numerator, denominator = text.split(":", 1)
    denominator_value = Decimal(denominator)
    if denominator_value == 0:
        raise AcquisitionBlocked("invalid_split_ratio")
    return _decimal_text(Decimal(numerator) / denominator_value)


def _iso_date(value: Any) -> str:
    if not isinstance(value, str):
        raise AcquisitionBlocked("invalid_event_date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise AcquisitionBlocked("invalid_event_date") from exc


def _optional_iso_date(value: Any) -> str | None:
    if value in (None, "", "None", "null", "0000-00-00"):
        return None
    return _iso_date(value)


def _duplicate_count(records: list[dict[str, Any]]) -> int:
    keys = [
        (row["symbol"], row["event_type"], row["event_date"], row["amount"], row["split_factor"])
        for row in records
    ]
    return len(keys) - len(set(keys))


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
