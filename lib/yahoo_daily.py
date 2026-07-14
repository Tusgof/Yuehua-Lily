"""Bounded Yahoo daily-bar acquisition and normalization for Lily L-1."""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from lib.io import write_json


ENDPOINT = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
USER_AGENT = "Yuehua-Lily-research/1.0"
NEW_YORK = ZoneInfo("America/New_York")


def request_specification(symbol: str, start: date, end_inclusive: date) -> dict[str, Any]:
    return {
        "provider": "Yahoo Finance chart API",
        "symbol": symbol,
        "period1_utc": datetime.combine(start, time.min, UTC).isoformat(),
        "period2_exclusive_utc": datetime.combine(end_inclusive + timedelta(days=1), time.min, UTC).isoformat(),
        "interval": "1d",
        "events": "div,splits",
        "include_prepost": False,
    }


def fetch_chart(specification: dict[str, Any], *, timeout_seconds: int = 30) -> bytes:
    symbol = str(specification["symbol"])
    period1 = int(datetime.fromisoformat(specification["period1_utc"]).timestamp())
    period2 = int(datetime.fromisoformat(specification["period2_exclusive_utc"]).timestamp())
    query = urllib.parse.urlencode(
        {
            "period1": period1,
            "period2": period2,
            "interval": specification["interval"],
            "events": specification["events"],
            "includePrePost": "false",
        }
    )
    request = urllib.request.Request(
        ENDPOINT.format(symbol=urllib.parse.quote(symbol)) + "?" + query,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def normalize_chart(
    raw_payload: bytes,
    specification: dict[str, Any],
    *,
    legal_inception: date,
    cutoff_inclusive: date,
) -> dict[str, Any]:
    payload = json.loads(raw_payload)
    chart = payload.get("chart", {})
    if chart.get("error") is not None or not chart.get("result"):
        raise ValueError(f"provider chart error for {specification['symbol']}")
    result = chart["result"][0]
    timestamps = result.get("timestamp", [])
    quotes = result.get("indicators", {}).get("quote", [])
    if len(quotes) != 1:
        raise ValueError("provider quote schema drift")
    closes = quotes[0].get("close")
    if not isinstance(closes, list) or len(closes) != len(timestamps):
        raise ValueError("provider close schema drift")

    dividends = _events_by_date(result, "dividends", "amount")
    splits = _events_by_date(result, "splits", "splitRatio")
    records: list[dict[str, Any]] = []
    total_return_close = 1.0
    previous_close: float | None = None
    for epoch, close_value in zip(timestamps, closes, strict=True):
        session = datetime.fromtimestamp(epoch, UTC).date()
        if session < legal_inception:
            raise ValueError("provider returned pre-inception history")
        if session > cutoff_inclusive:
            raise ValueError("provider returned data beyond locked cutoff")
        if close_value is None:
            continue
        close = float(close_value)
        distribution = float(dividends.get(session.isoformat(), 0.0))
        if previous_close is not None:
            total_return_close *= (close + distribution) / previous_close
        available = datetime.combine(session, time(16, 0), NEW_YORK).isoformat()
        records.append(
            {
                "session_date": session.isoformat(),
                "availability_timestamp": available,
                "raw_close": close,
                "cash_distribution": distribution,
                "split": splits.get(session.isoformat()),
                "total_return_close": total_return_close,
                "trading_currency": result.get("meta", {}).get("currency"),
                "provider_revision": "download_timestamp_container",
                "is_backfilled": False,
            }
        )
        previous_close = close
    if not records:
        raise ValueError("provider returned no usable records")
    if records[-1]["session_date"] > cutoff_inclusive.isoformat():
        raise ValueError("normalized data crossed locked cutoff")
    return {
        "schema_version": "lily_yahoo_daily_normalized_v1",
        "provider": "Yahoo Finance chart API",
        "symbol": specification["symbol"],
        "legal_inception": legal_inception.isoformat(),
        "coverage": {"start": records[0]["session_date"], "end": records[-1]["session_date"]},
        "records": records,
        "limitations": [
            "Provider close appears split-normalized; cash distributions are reconstructed from event records.",
            "The public endpoint is not a point-in-time revision archive.",
        ],
    }


def acquire_symbols(
    symbols: list[tuple[str, date]],
    *,
    start: date,
    cutoff_inclusive: date,
    data_root: Path,
    acquired_at: str,
) -> dict[str, Any]:
    raw_dir = data_root / "raw" / "yahoo_l1_v1"
    normalized_dir = data_root / "normalized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    containers: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    for symbol, inception in symbols:
        spec = request_specification(symbol, start, cutoff_inclusive)
        raw = fetch_chart(spec)
        raw_path = raw_dir / f"{symbol}.json"
        raw_path.write_bytes(raw)
        normalized.append(
            normalize_chart(raw, spec, legal_inception=inception, cutoff_inclusive=cutoff_inclusive)
        )
        containers.append(
            {
                "symbol": symbol,
                "container_sha256": hashlib.sha256(raw).hexdigest(),
                "request_specification": spec,
                "request_specification_sha256": _payload_sha256(spec),
            }
        )
    request_manifest = {
        "schema_version": "lily_yahoo_l1_request_manifest_v1",
        "acquired_at": acquired_at,
        "network_used": True,
        "paid_amount_usd": 0,
        "credentials_used": False,
        "containers": containers,
    }
    write_json(raw_dir / "request_manifest.json", request_manifest)
    normalized_payload = {
        "schema_version": "lily_l1_daily_dataset_v1",
        "acquired_at": acquired_at,
        "cutoff_inclusive": cutoff_inclusive.isoformat(),
        "symbols": normalized,
    }
    normalized_path = normalized_dir / "l1_yahoo_daily_v1.json"
    write_json(normalized_path, normalized_payload)
    return {
        "request_manifest": request_manifest,
        "request_manifest_sha256": _file_sha256(raw_dir / "request_manifest.json"),
        "normalized_sha256": _file_sha256(normalized_path),
        "normalized_storage_reference": "${LILY_DATA_ROOT}/normalized/l1_yahoo_daily_v1.json",
        "max_session_date": max(item["coverage"]["end"] for item in normalized),
        "min_session_date": min(item["coverage"]["start"] for item in normalized),
        "row_counts": {item["symbol"]: len(item["records"]) for item in normalized},
    }


def _events_by_date(result: dict[str, Any], event_name: str, value_name: str) -> dict[str, Any]:
    rows = result.get("events", {}).get(event_name, {})
    output: dict[str, Any] = {}
    for row in rows.values():
        session = datetime.fromtimestamp(int(row["date"]), UTC).date().isoformat()
        value = row.get(value_name)
        if event_name == "dividends":
            output[session] = float(output.get(session, 0.0)) + float(value)
        else:
            output[session] = value
    return output


def _payload_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
