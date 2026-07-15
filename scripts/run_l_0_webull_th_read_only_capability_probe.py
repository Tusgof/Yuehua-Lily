from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, write_json
from lib.provenance import file_sha256, git_commit, payload_sha256
from scripts.validate_l_0_webull_th_read_only_capability_probe import validate_contract


CONTRACT = PROJECT_ROOT / "experiments" / "l_0_webull_th_read_only_capability_probe.json"
REPORT_JSON = PROJECT_ROOT / "reports" / "feasibility" / "l_0_webull_th_read_only_capability.json"
REPORT_MD = PROJECT_ROOT / "reports" / "feasibility" / "l_0_webull_th_read_only_capability.md"
EXPECTED_CONTRACT_SHA256 = "7307f6faf1fcbefa6f0e803311ac624901ed01cebb2d2d347c52d6186dfbbf82"
ALLOWED_AUTH_PATHS = {
    "/openapi/auth/token/create",
    "/openapi/auth/token/check",
    "/openapi/auth/token/refresh",
}
ALLOWED_READ_ONLY_PATHS = {
    "/openapi/account/list",
    "/openapi/assets/balance",
    "/openapi/assets/positions",
    "/openapi/instrument/stock/list",
}


class ProbeBlocked(RuntimeError):
    pass


def install_request_guard(api_client: Any) -> list[str]:
    attempted_paths: list[str] = []
    original = api_client.get_response

    def guarded(request: Any) -> Any:
        path = str(request.get_action_name())
        if path not in ALLOWED_AUTH_PATHS | ALLOWED_READ_ONLY_PATHS:
            raise ProbeBlocked("request_path_outside_locked_allowlist")
        if any(fragment in path.lower() for fragment in ("preview", "place", "replace", "cancel", "/order/", "/orders")):
            raise ProbeBlocked("order_path_forbidden")
        if path in ALLOWED_READ_ONLY_PATHS and sum(
            item in ALLOWED_READ_ONLY_PATHS for item in attempted_paths
        ) >= 4:
            raise ProbeBlocked("read_only_request_cap_exceeded")
        attempted_paths.append(path)
        return original(request)

    api_client.get_response = guarded
    return attempted_paths


def response_payload(response: Any, label: str) -> Any:
    if getattr(response, "status_code", None) != 200:
        raise ProbeBlocked(f"{label}_http_non_200")
    try:
        return response.json()
    except (TypeError, ValueError) as exc:
        raise ProbeBlocked(f"{label}_invalid_json") from exc


def canonical_response_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def field_inventory(payload: Any) -> list[str]:
    fields: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            fields.update(str(key) for key in value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return sorted(fields)


def find_first_private_identifier(payload: Any) -> str:
    if isinstance(payload, dict):
        value = payload.get("account_id")
        if value not in (None, ""):
            return str(value)
        for child in payload.values():
            found = find_first_private_identifier(child)
            if found:
                return found
    elif isinstance(payload, list):
        for child in payload:
            found = find_first_private_identifier(child)
            if found:
                return found
    return ""


def candidate_rows(payload: Any, symbols: list[str]) -> list[dict[str, Any]]:
    wanted = set(symbols)
    rows: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if str(value.get("symbol", "")) in wanted:
                rows.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    by_symbol: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = str(row["symbol"])
        if symbol in by_symbol and by_symbol[symbol] != row:
            raise ProbeBlocked("duplicate_candidate_instrument")
        by_symbol[symbol] = row
    return [by_symbol[symbol] for symbol in symbols if symbol in by_symbol]


def public_instrument_summary(rows: list[dict[str, Any]], symbols: list[str]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for symbol, row in zip(symbols, rows, strict=True):
        if str(row.get("symbol")) != symbol:
            raise ProbeBlocked("candidate_instrument_order_mismatch")
        if "fractionable" not in row or "status" not in row:
            raise ProbeBlocked("candidate_instrument_schema_missing")
        summaries.append(
            {
                "symbol": symbol,
                "instrument_type": row.get("instrument_type"),
                "status": row.get("status"),
                "fractionable": row.get("fractionable"),
            }
        )
    return summaries


def run_probe() -> dict[str, Any]:
    if file_sha256(CONTRACT) != EXPECTED_CONTRACT_SHA256:
        raise ProbeBlocked("locked_contract_hash_mismatch")
    if validate_contract(CONTRACT)["status"] != "pass":
        raise ProbeBlocked("locked_contract_invalid")
    if sys.version_info[:2] != (3, 11):
        raise ProbeBlocked("python_runtime_mismatch")
    credentials = tuple(os.environ.get(name, "") for name in ("WEBULL_APP_KEY", "WEBULL_APP_SECRET"))
    if not all(credentials):
        raise ProbeBlocked("credential_environment_missing")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not local_app_data:
        raise ProbeBlocked("local_app_data_missing")

    try:
        import webull
        from webull.core.client import ApiClient
        from webull.core.http.initializer.token.token_manager import TokenManager
        from webull.core.request import ApiRequest
        from webull.trade.trade.v2.account_info_v2 import AccountV2
    except ImportError as exc:
        raise ProbeBlocked("webull_sdk_import_failed") from exc
    if webull.__version__ != "2.0.13":
        raise ProbeBlocked("webull_sdk_version_mismatch")

    logging.disable(logging.CRITICAL)
    api_client = ApiClient(
        credentials[0],
        credentials[1],
        "th",
        None,
        443,
        15,
        15,
        None,
        None,
        False,
        None,
        None,
        300,
        5,
    )
    api_client.add_endpoint("th", "api.webull.co.th")
    api_client._file_logger_set = True
    api_client._stream_logger_set = True
    attempted_paths = install_request_guard(api_client)
    auth_storage = Path(local_app_data) / "Yuehua-Lily" / "webull-token"
    TokenManager(str(auth_storage)).init_token(api_client)

    account_api = AccountV2(api_client)
    account_payload = response_payload(account_api.get_account_list(), "account_list")
    selected_account = find_first_private_identifier(account_payload)
    if not selected_account:
        raise ProbeBlocked("account_list_missing_identifier")
    balance_payload = response_payload(account_api.get_account_balance(selected_account), "balance")
    positions_payload = response_payload(account_api.get_account_position(selected_account), "positions")

    contract = load_json(CONTRACT)
    symbols = contract["candidate_universe"]["symbols"]
    instrument_request = ApiRequest(
        "/openapi/instrument/stock/list",
        version="v2",
        method="GET",
        query_params={"symbols": ",".join(symbols), "category": "US_STOCK", "page_size": 100},
    )
    instrument_payload = response_payload(api_client.get_response(instrument_request), "instruments")
    rows = candidate_rows(instrument_payload, symbols)
    if len(rows) != len(symbols):
        raise ProbeBlocked("candidate_instrument_count_mismatch")
    instruments = public_instrument_summary(rows, symbols)

    read_only_attempts = [path for path in attempted_paths if path in ALLOWED_READ_ONLY_PATHS]
    if read_only_attempts != [
        "/openapi/account/list",
        "/openapi/assets/balance",
        "/openapi/assets/positions",
        "/openapi/instrument/stock/list",
    ]:
        raise ProbeBlocked("read_only_request_sequence_mismatch")
    all_fractionable = all(row["fractionable"] is True for row in instruments)
    all_tradable = all(row["status"] == "OC" for row in instruments)
    decision = (
        "verified_read_only_and_fractional_candidate_set"
        if all_fractionable and all_tradable
        else "scope_restricted_account_or_candidate_capability"
    )
    report: dict[str, Any] = {
        "schema_version": "lily_l0_webull_th_read_only_capability_report_v1",
        "order_id": "B4.6",
        "hypothesis_id": "L-0",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "produced_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "producing_git_commit": git_commit(PROJECT_ROOT),
        "runtime": {"python": ".".join(map(str, sys.version_info[:3])), "webull_sdk": webull.__version__, "region": "th", "environment": "production"},
        "decision": decision,
        "account_capability": {
            "authentication_succeeded": True,
            "account_list_endpoint_succeeded": True,
            "balance_endpoint_succeeded": True,
            "positions_endpoint_succeeded": True,
            "account_list_field_inventory": field_inventory(account_payload),
            "balance_field_inventory": field_inventory(balance_payload),
            "positions_field_inventory": field_inventory(positions_payload),
            "account_list_response_sha256": canonical_response_hash(account_payload),
            "balance_response_sha256": canonical_response_hash(balance_payload),
            "positions_response_sha256": canonical_response_hash(positions_payload),
            "private_values_persisted": False,
        },
        "instrument_capability": {"symbols": instruments, "all_fractionable": all_fractionable, "all_tradable": all_tradable, "response_sha256": canonical_response_hash(instrument_payload)},
        "request_attestation": {"read_only_paths": read_only_attempts, "read_only_request_count": len(read_only_attempts), "order_endpoint_calls": 0, "preview_calls": 0, "orders_sent": 0, "paid_spend_usd": 0},
        "validation_return_seal": {"status": "sealed_not_accessed", "prices_opened": False, "returns_opened": False, "signals_opened": False, "positions_opened": False, "regimes_opened": False, "benchmarks_opened": False, "pnl_opened": False},
        "claim_limits": [
            "This E0 probe verifies operational read-only and instrument metadata capability only; it does not establish strategy edge or E2 evidence.",
            "Fractionable metadata does not prove minimum order, fill quality, slippage, funding FX cost, or deployment readiness.",
            "This result does not authorize order preview, paper trading, the prospective shadow-accounting dry run, or real money.",
        ],
        "next_safe_action": "Design and obtain owner approval for a separately hash-locked E0 prospective shadow-accounting dry-run preregistration. Do not call preview or order endpoints.",
    }
    report["report_digest_sha256"] = payload_sha256(report)
    return report


def markdown_report(report: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {row['symbol']} | {row['status']} | {str(row['fractionable']).lower()} |"
        for row in report["instrument_capability"]["symbols"]
    )
    return f"""# Webull Thailand Read-only Capability Probe

- หลักฐาน: `E0` — ตรวจความสามารถด้านการทำงานเท่านั้น
- ผล: `{report['decision']}`
- validation returns: `sealed_not_accessed`

## ผลการตรวจบัญชีแบบไม่เปิดเผยข้อมูลส่วนตัว

Authentication, account list, balance และ positions ตอบกลับสำเร็จทั้งหมด รายงานนี้เก็บเฉพาะชื่อฟิลด์และ hash ของ response ไม่เก็บ Account ID, ยอดเงิน, buying power, หลักทรัพย์ที่ถือ หรือจำนวนหน่วย

## ETF Candidate Set

| Symbol | Status | Fractionable |
|:--|:--|:--|
{rows}

## ขอบเขตของผล

ผลนี้ยืนยันเพียงว่า Webull Thailand production API อ่านบัญชีได้และคืน metadata ของ ETF ตามตาราง ไม่ได้ยืนยันขั้นต่ำต่อคำสั่ง, คุณภาพราคา, slippage, ค่าแลกเงิน, edge, E2 หรือความพร้อมใช้เงินจริง

ไม่มีการเรียก preview/place/replace/cancel order ไม่มี paper trade และไม่ได้เปิด validation returns

## งานถัดไปที่ปลอดภัย

ออกแบบ preregistration แยกสำหรับ `E0 prospective shadow accounting dry run` และขออนุมัติเจ้าของก่อนเริ่ม โดยยังห้ามเรียก preview หรือ order endpoint
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the locked Webull Thailand read-only capability probe.")
    parser.parse_args()
    try:
        report = run_probe()
    except Exception as exc:
        blocker = str(exc) if isinstance(exc, ProbeBlocked) else f"unexpected_{exc.__class__.__name__}"
        print(json.dumps({"status": "blocked", "blocker": blocker}, sort_keys=True))
        return 1
    write_json(REPORT_JSON, report)
    REPORT_MD.write_text(markdown_report(report), encoding="utf-8", newline="\n")
    print(json.dumps({"status": "pass", "decision": report["decision"], "report_digest_sha256": report["report_digest_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
