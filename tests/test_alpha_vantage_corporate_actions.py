from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from lib.alpha_vantage_corporate_actions import (
    AcquisitionBlocked,
    acquire_corporate_actions,
    validate_and_normalize_payload,
)
from lib.io import load_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = load_json(
    PROJECT_ROOT / "experiments" / "l_1_alpha_vantage_corporate_actions_acquisition.json"
)


class AlphaVantageCorporateActionsTests(unittest.TestCase):
    def test_payload_normalization_preserves_decimal_text(self) -> None:
        raw = json.dumps(
            {
                "data": [
                    {
                        "ex_dividend_date": "2015-01-02",
                        "declaration_date": "2014-12-01",
                        "record_date": "2015-01-05",
                        "payment_date": "2015-01-09",
                        "amount": "1.2300",
                    }
                ]
            }
        ).encode()
        summary, records = validate_and_normalize_payload(
            raw,
            symbol="VTI",
            function="DIVIDENDS",
            endpoint_contract=CONTRACT["request_universe"]["endpoints"]["DIVIDENDS"],
            retrieved_at_utc="2026-07-15T00:00:00Z",
        )
        self.assertEqual(1, summary["row_count"])
        self.assertEqual("1.23", records[0]["amount"])

    def test_service_message_is_not_a_success(self) -> None:
        with self.assertRaisesRegex(AcquisitionBlocked, "service_message_not_success"):
            validate_and_normalize_payload(
                json.dumps({"Information": "rate limit"}).encode(),
                symbol="VTI",
                function="SPLITS",
                endpoint_contract=CONTRACT["request_universe"]["endpoints"]["SPLITS"],
                retrieved_at_utc="2026-07-15T00:00:00Z",
            )

    def test_fake_acquisition_completes_locked_matrix_without_secret_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_yahoo_fixtures(root)
            clock = _Clock()

            def fetcher(url: str, user_agent: str) -> tuple[int, bytes]:
                self.assertIn("test-secret", url)
                self.assertTrue(user_agent)
                function = "DIVIDENDS" if "function=DIVIDENDS" in url else "SPLITS"
                return 200, _provider_payload(function)

            result = acquire_corporate_actions(
                CONTRACT,
                data_root=root,
                credential="test-secret",
                fetcher=fetcher,
                sleeper=clock.sleep,
                monotonic=clock.monotonic,
                now=clock.now,
            )
            raw_dir = root / "raw" / "alpha_vantage_corporate_actions_v1"
            all_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in raw_dir.glob("*.json")
            )
        self.assertEqual(16, result["successful_payload_count"])
        self.assertEqual(16, len(result["reconciliation_rows"]))
        self.assertEqual("sealed_not_accessed", result["validation_return_status"])
        self.assertNotIn("test-secret", all_text)
        self.assertGreaterEqual(sum(clock.sleeps), 15 * 15)

    def test_yahoo_history_crossing_cutoff_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_yahoo_fixtures(root, yahoo_date="2016-01-04")
            clock = _Clock()
            with self.assertRaisesRegex(
                AcquisitionBlocked, "existing_yahoo_market_data_crosses_locked_cutoff"
            ):
                acquire_corporate_actions(
                    CONTRACT,
                    data_root=root,
                    credential="test-secret",
                    fetcher=lambda url, user_agent: (
                        200,
                        _provider_payload("DIVIDENDS" if "DIVIDENDS" in url else "SPLITS"),
                    ),
                    sleeper=clock.sleep,
                    monotonic=clock.monotonic,
                    now=clock.now,
                )


class _Clock:
    def __init__(self) -> None:
        self.value = 0.0
        self.current = datetime(2026, 7, 15, tzinfo=UTC)
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds
        self.current += timedelta(seconds=seconds)

    def now(self) -> datetime:
        return self.current


def _provider_payload(function: str) -> bytes:
    if function == "DIVIDENDS":
        return json.dumps(
            {
                "data": [
                    {
                        "ex_dividend_date": "2015-01-02",
                        "declaration_date": "None",
                        "record_date": "None",
                        "payment_date": "None",
                        "amount": "1.0",
                    }
                ]
            }
        ).encode()
    return json.dumps({"data": []}).encode()


def _write_yahoo_fixtures(root: Path, *, yahoo_date: str = "2015-01-02") -> None:
    raw_dir = root / "raw" / "yahoo_l1_v1"
    raw_dir.mkdir(parents=True)
    epoch = int(datetime.fromisoformat(yahoo_date).replace(tzinfo=UTC).timestamp())
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [epoch],
                    "events": {
                        "dividends": {"a": {"date": epoch, "amount": 1.0}},
                        "splits": {},
                    },
                }
            ]
        }
    }
    for symbol in CONTRACT["request_universe"]["symbols"]:
        (raw_dir / f"{symbol}.json").write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
