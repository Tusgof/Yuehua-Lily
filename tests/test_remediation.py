from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from lib.remediation import (
    _extract_ric_fee,
    cash_returns_for_sessions,
    html_text,
    reextract_cached_fee_history,
)


class RemediationTests(unittest.TestCase):
    def test_cash_yield_is_lagged_and_accrues_calendar_days(self) -> None:
        payload = {
            "observations": [
                {"date": "2015-12-24", "yield_percent": 1.0},
                {"date": "2015-12-28", "yield_percent": 2.0},
            ]
        }
        result = cash_returns_for_sessions(payload, ["2015-12-24", "2015-12-28", "2015-12-29"])
        self.assertEqual(0.0, result["2015-12-24"])
        self.assertAlmostEqual((1.01 ** (4 / 365)) - 1.0, result["2015-12-28"])
        self.assertAlmostEqual((1.02 ** (1 / 365)) - 1.0, result["2015-12-29"])

    def test_fee_extraction_uses_nearest_fund_heading_not_table_of_contents(self) -> None:
        text = (
            "Target Fund Other Fund Total Annual Fund Operating Expenses 0.19% "
            + "x " * 100
            + "Target Fund Fees and Expenses Total Annual Fund Operating Expenses 0.07%"
        )
        self.assertEqual(0.07, _extract_ric_fee(text, ["Target Fund"]))

    def test_html_text_normalizes_sec_decimal_whitespace(self) -> None:
        payload = b"<p>Total Annual Fund Operating Expenses 0. 16%</p>"
        self.assertEqual(
            "Total Annual Fund Operating Expenses 0.16%",
            html_text(payload),
        )

    def test_fee_reextraction_keeps_symbols_for_shared_sec_filing(self) -> None:
        filing = (
            b"<p>Vanguard FTSE Europe ETF Fees and Expenses "
            b"Total Annual Fund Operating Expenses 0. 16%</p>"
            b"<p>Vanguard FTSE Emerging Markets ETF Fees and Expenses "
            b"Total Annual Fund Operating Expenses 0. 27%</p>"
        )
        digest = hashlib.sha256(filing).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            data_root = Path(tmp)
            normalized = data_root / "normalized"
            normalized.mkdir()
            sources = []
            records = []
            for symbol in ("VGK", "VWO"):
                raw = data_root / "raw" / "sec_fee_history_v1" / symbol
                raw.mkdir(parents=True)
                (raw / "2010-shared.htm").write_bytes(filing)
                sources.append({"symbol": symbol, "year": 2010, "url": "https://example.test", "sha256": digest})
                records.append(
                    {
                        "symbol": symbol,
                        "filing_date": "2010-03-02",
                        "annual_fee_fraction": 0.0,
                        "fee_kind": "total_annual_fund_operating_expenses",
                        "form": "497",
                        "source_url": "https://example.test",
                        "source_sha256": digest,
                    }
                )
            (normalized / "official_fee_history_v1.json").write_text(
                json.dumps({"records": records, "source_hashes": sources}),
                encoding="utf-8",
            )
            reextract_cached_fee_history(data_root)
            corrected = json.loads(
                (normalized / "official_fee_history_v1.json").read_text(encoding="utf-8")
            )["records"]
        self.assertEqual(
            [("VGK", 0.0016), ("VWO", 0.0027)],
            [(row["symbol"], row["annual_fee_fraction"]) for row in corrected],
        )


if __name__ == "__main__":
    unittest.main()
