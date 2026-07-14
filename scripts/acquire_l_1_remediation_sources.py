from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.environment import require_configured_path
from lib.remediation import (
    acquire_sec_fee_history,
    acquire_treasury_cash,
    fetch_bytes,
    html_text,
    reextract_cached_fee_history,
)
from lib.io import write_json
from lib.provenance import payload_sha256


WEBULL_SOURCES = [
    ("manual_fractional", "https://www.webull.co.th/help/faq/355-ฉันสามารถซื้อขายแบบเศษหุ้นได้หรือไม่"),
    ("openapi_landing", "https://www.webull.co.th/open-api"),
    ("openapi_stock", "https://developer.webull.co.th/apis/docs/trade-api/stock"),
    ("openapi_overview", "https://developer.webull.co.th/apis/docs/trade-api/overview"),
    ("pricing", "https://www.webull.co.th/pricing"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire the locked B4.1 public remediation sources.")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--reextract-fees-only", action="store_true")
    args = parser.parse_args()
    data_root = args.data_root.resolve() if args.data_root else require_configured_path("LILY_DATA_ROOT")
    if args.reextract_fees_only:
        print(json.dumps(reextract_cached_fee_history(data_root), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    acquired_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    treasury = acquire_treasury_cash(data_root, acquired_at=acquired_at)
    fees = acquire_sec_fee_history(data_root, acquired_at=acquired_at)
    webull = _acquire_webull(data_root, acquired_at=acquired_at)
    print(
        json.dumps(
            {
                "acquired_at": acquired_at,
                "treasury": {key: value for key, value in treasury.items() if key != "dataset"},
                "fees": {key: value for key, value in fees.items() if key != "dataset"},
                "fee_record_count": len(fees["dataset"]["records"]),
                "webull": webull,
                "maximum_data_date": "2015-12-31",
                "paid_amount_usd": 0,
                "credentials_used": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _acquire_webull(data_root: Path, *, acquired_at: str) -> dict[str, object]:
    raw_dir = data_root / "raw" / "webull_th_public_v1"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sources = []
    texts = {}
    for source_id, url in WEBULL_SOURCES:
        payload = fetch_bytes(url)
        path = raw_dir / f"{source_id}.html"
        path.write_bytes(payload)
        text = html_text(payload)
        texts[source_id] = text
        sources.append(
            {
                "source_id": source_id,
                "url": url,
                "sha256": __import__("hashlib").sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
        )
    findings = {
        "manual_mobile_fractional_documented": "Mobile Application" in texts["manual_fractional"] and "Fractional Shares" in texts["manual_fractional"],
        "manual_green_diamond_required": "เพชรสีเขียว" in texts["manual_fractional"],
        "manual_market_order_only": 'Order Type' in texts["manual_fractional"] and 'Market' in texts["manual_fractional"],
        "manual_four_decimal_precision": "4 หลัก" in texts["manual_fractional"],
        "openapi_us_stock_etf_documented": "หุ้นและ ETF สหรัฐฯ" in texts["openapi_landing"],
        "openapi_quantity_order_documented": "entrust_type" in texts["openapi_stock"] and "Number of shares" in texts["openapi_stock"],
        "openapi_fractional_or_notional_documented": any(term in texts["openapi_stock"].lower() for term in ("fractional", "notional")),
    }
    normalized = {
        "schema_version": "lily_webull_th_public_capability_v1",
        "acquired_at": acquired_at,
        "sources": sources,
        "findings": findings,
        "account_or_credentials_used": False,
    }
    normalized_path = data_root / "normalized" / "webull_th_public_capability_v1.json"
    write_json(normalized_path, normalized)
    return {
        "normalized_sha256": __import__("hashlib").sha256(normalized_path.read_bytes()).hexdigest(),
        "container_manifest_sha256": payload_sha256(sources),
        "request_specification_sha256": payload_sha256(WEBULL_SOURCES),
        "storage_reference": "${LILY_DATA_ROOT}/normalized/webull_th_public_capability_v1.json",
        "findings": findings,
    }


if __name__ == "__main__":
    raise SystemExit(main())
