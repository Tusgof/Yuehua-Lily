"""Shared B4.1 data-quality acquisition and audit helpers."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import math
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from lib.io import load_json, write_json
from lib.provenance import payload_sha256


USER_AGENT = "Yuehua-Lily research 4gust2005@gmail.com"
TREASURY_TEMPLATE = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all?type=daily_treasury_bill_rates&"
    "field_tdr_date_value={year}&page&_format=csv"
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def fetch_bytes(url: str, *, timeout_seconds: int = 60) -> bytes:
    quoted = urllib.parse.quote(url, safe=":/?=&%")
    request = urllib.request.Request(quoted, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def html_text(payload: bytes) -> str:
    parser = _TextExtractor()
    parser.feed(payload.decode("utf-8", errors="ignore"))
    return re.sub(r"\s+", " ", html.unescape(" ".join(parser.parts))).strip()


def acquire_treasury_cash(data_root: Path, *, acquired_at: str) -> dict[str, Any]:
    raw_dir = data_root / "raw" / "treasury_13week_v1"
    raw_dir.mkdir(parents=True, exist_ok=True)
    observations: dict[str, float] = {}
    containers: list[dict[str, Any]] = []
    for year in range(2006, 2016):
        url = TREASURY_TEMPLATE.format(year=year)
        payload = fetch_bytes(url)
        path = raw_dir / f"{year}.csv"
        path.write_bytes(payload)
        rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
        for row in rows:
            raw_value = row.get("13 WEEKS COUPON EQUIVALENT", "").strip()
            if not raw_value:
                continue
            session = datetime.strptime(row["Date"], "%m/%d/%Y").date().isoformat()
            if session > "2015-12-31":
                raise ValueError("Treasury source crossed the locked cutoff")
            observations[session] = float(raw_value)
        containers.append(
            {"year": year, "url": url, "sha256": hashlib.sha256(payload).hexdigest(), "rows": len(rows)}
        )
    normalized = {
        "schema_version": "lily_treasury_13week_cash_v1",
        "acquired_at": acquired_at,
        "source_field": "13 WEEKS COUPON EQUIVALENT",
        "unit": "annual_percent",
        "availability_rule": "usable_from_next_NYSE_session",
        "coverage": {"start": min(observations), "end": max(observations)},
        "observations": [{"date": key, "yield_percent": observations[key]} for key in sorted(observations)],
        "containers": containers,
    }
    normalized_path = data_root / "normalized" / "treasury_13week_cash_v1.json"
    write_json(normalized_path, normalized)
    return {
        "dataset": normalized,
        "normalized_sha256": hashlib.sha256(normalized_path.read_bytes()).hexdigest(),
        "request_specification_sha256": payload_sha256([row["url"] for row in containers]),
        "container_manifest_sha256": payload_sha256(containers),
        "storage_reference": "${LILY_DATA_ROOT}/normalized/treasury_13week_cash_v1.json",
    }


def cash_returns_for_sessions(cash_payload: dict[str, Any], sessions: list[str]) -> dict[str, float]:
    observations = [(row["date"], float(row["yield_percent"])) for row in cash_payload["observations"]]
    output: dict[str, float] = {}
    pointer = 0
    latest: tuple[str, float] | None = None
    previous_session: date | None = None
    for session_text in sessions:
        while pointer < len(observations) and observations[pointer][0] < session_text:
            latest = observations[pointer]
            pointer += 1
        session = date.fromisoformat(session_text)
        if latest is not None and previous_session is not None:
            calendar_days = (session - previous_session).days
            output[session_text] = (1.0 + latest[1] / 100.0) ** (calendar_days / 365.0) - 1.0
        else:
            output[session_text] = 0.0
        previous_session = session
    return output


def audit_corporate_actions(data_root: Path) -> dict[str, Any]:
    normalized = load_json(data_root / "normalized" / "l1_yahoo_daily_v1.json")
    normalized_by_symbol = {row["symbol"]: row for row in normalized["symbols"]}
    rows: list[dict[str, Any]] = []
    for symbol in ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"):
        raw_path = data_root / "raw" / "yahoo_l1_v1" / f"{symbol}.json"
        result = load_json(raw_path)["chart"]["result"][0]
        timestamps = result["timestamp"]
        close = result["indicators"]["quote"][0]["close"]
        adjusted = result["indicators"]["adjclose"][0]["adjclose"]
        dividends = {
            datetime.utcfromtimestamp(int(item["date"])).date().isoformat(): float(item["amount"])
            for item in result.get("events", {}).get("dividends", {}).values()
        }
        reconstruction = 1.0
        adjusted_start: float | None = None
        previous_close: float | None = None
        previous_reconstruction: float | None = None
        previous_adjusted_growth: float | None = None
        cumulative_errors: list[float] = []
        daily_errors: list[float] = []
        maximum_date = ""
        for epoch, close_value, adjusted_value in zip(timestamps, close, adjusted, strict=True):
            if close_value is None or adjusted_value is None:
                continue
            session = datetime.utcfromtimestamp(epoch).date().isoformat()
            maximum_date = max(maximum_date, session)
            if session > "2015-12-31":
                raise ValueError("corporate-action audit crossed the locked cutoff")
            if adjusted_start is None:
                adjusted_start = float(adjusted_value)
            if previous_close is not None:
                reconstruction *= (float(close_value) + dividends.get(session, 0.0)) / previous_close
            adjusted_growth = float(adjusted_value) / adjusted_start
            cumulative_errors.append(reconstruction / adjusted_growth - 1.0)
            if previous_reconstruction is not None and previous_adjusted_growth is not None:
                reconstructed_return = reconstruction / previous_reconstruction - 1.0
                adjusted_return = adjusted_growth / previous_adjusted_growth - 1.0
                daily_errors.append(reconstructed_return - adjusted_return)
            previous_close = float(close_value)
            previous_reconstruction = reconstruction
            previous_adjusted_growth = adjusted_growth
        normalized_records = normalized_by_symbol[symbol]["records"]
        rows.append(
            {
                "symbol": symbol,
                "raw_container_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                "maximum_session_date": maximum_date,
                "normalized_record_count": len(normalized_records),
                "dividend_event_count": len(dividends),
                "split_event_count": len(result.get("events", {}).get("splits", {})),
                "maximum_absolute_cumulative_relative_divergence": max(abs(value) for value in cumulative_errors),
                "maximum_absolute_daily_return_divergence": max(abs(value) for value in daily_errors),
            }
        )
    for row in rows:
        row["pass"] = (
            row["maximum_absolute_cumulative_relative_divergence"] <= 0.002
            and row["maximum_absolute_daily_return_divergence"] <= 0.0005
            and row["maximum_session_date"] <= "2015-12-31"
        )
    return {"status": "pass" if all(row["pass"] for row in rows) else "blocked", "rows": rows}


RIC_FUNDS = {
    "VTI": {
        "cik": "36405",
        "names": ["Vanguard Total Stock Market ETF", "Vanguard Total Stock Market VIPERs", "Total Stock Market ETF Shares"],
    },
    "VGK": {
        "cik": "857489",
        "names": ["Vanguard European Stock ETF", "Vanguard European ETF", "Vanguard European Stock Index Fund"],
    },
    "VWO": {
        "cik": "857489",
        "names": ["Vanguard Emerging Markets Stock ETF", "Vanguard Emerging Markets ETF", "Vanguard Emerging Markets Stock Index Fund"],
    },
    "EWJ": {
        "cik": "930667",
        "names": ["iShares MSCI Japan ETF", "iShares MSCI Japan Index Fund"],
    },
    "IEF": {
        "cik": "1100663",
        "names": ["iShares 7-10 Year Treasury Bond ETF", "iShares Barclays 7-10 Year Treasury Bond Fund", "iShares Lehman 7-10 Year Treasury Bond Fund"],
    },
    "TIP": {
        "cik": "1100663",
        "names": ["iShares TIPS Bond ETF", "iShares Barclays TIPS Bond Fund", "iShares Lehman TIPS Bond Fund"],
    },
}


def acquire_sec_fee_history(data_root: Path, *, acquired_at: str) -> dict[str, Any]:
    raw_dir = data_root / "raw" / "sec_fee_history_v1"
    raw_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    source_hashes: list[dict[str, Any]] = []
    for symbol, config in RIC_FUNDS.items():
        for year in range(2006, 2016):
            record = _find_ric_fee_record(symbol, config, year, raw_dir, source_hashes)
            if record is not None:
                records.append(record)
    records.extend(_acquire_trust_fee_records(raw_dir, source_hashes))
    normalized = {
        "schema_version": "lily_official_fee_history_v1",
        "acquired_at": acquired_at,
        "coverage_target": {"start": "2006-02-03", "end": "2015-12-31"},
        "records": sorted(records, key=lambda row: (row["symbol"], row["filing_date"])),
        "source_hashes": source_hashes,
    }
    normalized_path = data_root / "normalized" / "official_fee_history_v1.json"
    write_json(normalized_path, normalized)
    return {
        "dataset": normalized,
        "normalized_sha256": hashlib.sha256(normalized_path.read_bytes()).hexdigest(),
        "request_specification_sha256": payload_sha256({key: value["names"] for key, value in RIC_FUNDS.items()}),
        "container_manifest_sha256": payload_sha256(source_hashes),
        "storage_reference": "${LILY_DATA_ROOT}/normalized/official_fee_history_v1.json",
    }


def _find_ric_fee_record(
    symbol: str,
    config: dict[str, Any],
    year: int,
    raw_dir: Path,
    source_hashes: list[dict[str, Any]],
) -> dict[str, Any] | None:
    seen: set[str] = set()
    forms = ("497K", "497") if year >= 2012 else ("497", "497K")
    for name in config["names"]:
        for form in forms:
            query = urllib.parse.urlencode(
                {"q": f'"{name}"', "forms": form, "startdt": f"{year}-01-01", "enddt": f"{year}-12-31"}
            )
            search_url = "https://efts.sec.gov/LATEST/search-index?" + query
            try:
                search_payload = fetch_bytes(search_url)
                search_result = json.loads(search_payload)
            except (OSError, json.JSONDecodeError):
                continue
            time.sleep(0.12)
            for hit in search_result.get("hits", {}).get("hits", [])[:20]:
                hit_id = hit.get("_id", "")
                if hit_id in seen or ":" not in hit_id:
                    continue
                seen.add(hit_id)
                accession, document = hit_id.split(":", 1)
                filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/{int(config['cik'])}/"
                    f"{accession.replace('-', '')}/{document}"
                )
                try:
                    payload = fetch_bytes(filing_url)
                except OSError:
                    continue
                time.sleep(0.12)
                text = html_text(payload)
                fee = _extract_ric_fee(text, config["names"])
                if fee is None:
                    continue
                path = raw_dir / symbol / f"{year}-{accession.replace('-', '')}-{Path(document).name}"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
                digest = hashlib.sha256(payload).hexdigest()
                source_hashes.append({"symbol": symbol, "year": year, "url": filing_url, "sha256": digest})
                return {
                    "symbol": symbol,
                    "filing_date": hit["_source"]["file_date"],
                    "annual_fee_fraction": fee / 100.0,
                    "fee_kind": "total_annual_fund_operating_expenses",
                    "form": hit["_source"].get("form"),
                    "source_url": filing_url,
                    "source_sha256": digest,
                }
    return None


def _extract_ric_fee(text: str, names: list[str]) -> float | None:
    for name in names:
        for match in re.finditer(re.escape(name), text, flags=re.IGNORECASE):
            section = text[match.start() : match.start() + 30_000]
            fee = re.search(
                r"Total Annual Fund Operating Expenses.{0,800}?([0-9]+(?:\.[0-9]+)?)%",
                section,
                flags=re.IGNORECASE,
            )
            if fee:
                return float(fee.group(1))
    return None


def _acquire_trust_fee_records(raw_dir: Path, source_hashes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for symbol, cik in (("GLD", "0001222333"), ("DBC", "0001328237")):
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        submissions_payload = fetch_bytes(submissions_url)
        submissions = json.loads(submissions_payload)["filings"]["recent"]
        for index, form in enumerate(submissions["form"]):
            filing_date = submissions["filingDate"][index]
            if form != "10-K" or not "2006-01-01" <= filing_date <= "2015-12-31":
                continue
            accession = submissions["accessionNumber"][index]
            document = submissions["primaryDocument"][index]
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession.replace('-', '')}/{document}"
            )
            payload = fetch_bytes(filing_url)
            time.sleep(0.12)
            text = html_text(payload)
            if symbol == "GLD":
                match = re.search(r"ordinary expenses.{0,500}?0\.40% per year", text, flags=re.IGNORECASE)
                fee = 0.004 if match else None
                fee_kind = "ordinary_expense_cap"
            else:
                match = re.search(
                    r"management fee.{0,700}?equal to ([0-9]+(?:\.[0-9]+)?)% per annum",
                    text,
                    flags=re.IGNORECASE,
                )
                fee = float(match.group(1)) / 100.0 if match else None
                fee_kind = "management_fee"
            if fee is None:
                continue
            path = raw_dir / symbol / f"{filing_date[:4]}-{accession.replace('-', '')}-{Path(document).name}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            source_hashes.append({"symbol": symbol, "year": int(filing_date[:4]), "url": filing_url, "sha256": digest})
            output.append(
                {
                    "symbol": symbol,
                    "filing_date": filing_date,
                    "annual_fee_fraction": fee,
                    "fee_kind": fee_kind,
                    "form": "10-K",
                    "source_url": filing_url,
                    "source_sha256": digest,
                }
            )
    return output


def fee_coverage(fee_payload: dict[str, Any]) -> dict[str, Any]:
    rows_by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in fee_payload["records"]:
        rows_by_symbol.setdefault(row["symbol"], []).append(row)
    result: list[dict[str, Any]] = []
    for symbol in ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"):
        rows = sorted(rows_by_symbol.get(symbol, []), key=lambda row: row["filing_date"])
        gaps = []
        for left, right in zip(rows, rows[1:]):
            months = (date.fromisoformat(right["filing_date"]) - date.fromisoformat(left["filing_date"])).days / 30.4375
            if months > 18.0:
                gaps.append({"from": left["filing_date"], "to": right["filing_date"], "months": months})
        first_ok = bool(rows) and rows[0]["filing_date"] <= "2007-02-05"
        last_ok = bool(rows) and rows[-1]["filing_date"] >= "2015-01-01"
        full = first_ok and last_ok and not gaps and len(rows) >= 8
        result.append(
            {
                "symbol": symbol,
                "record_count": len(rows),
                "first_filing_date": rows[0]["filing_date"] if rows else None,
                "last_filing_date": rows[-1]["filing_date"] if rows else None,
                "gaps_over_18_months": gaps,
                "full_resolution": full,
                "observed_fee_range": [min(row["annual_fee_fraction"] for row in rows), max(row["annual_fee_fraction"] for row in rows)] if rows else None,
            }
        )
    return {"status": "fully_resolved" if all(row["full_resolution"] for row in result) else "partially_resolved", "rows": result}
