from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, load_jsonl, write_json
from lib.provenance import file_sha256, git_commit, payload_sha256
from scripts.validate_l_0_webull_th_fractional_preview_report_v2 import (
    AUTH_CHECK_PATH,
    AUTH_CREATE_PATH,
    CLAIM_LIMITS,
    PREVIEW_PATH,
    QUANTITY_GRID,
    validate_report,
)


ACTIVATION = PROJECT_ROOT / "experiments" / "l_0_webull_th_fractional_preview_activation_v2.json"
MANIFEST = PROJECT_ROOT / "experiments" / "locked_gates.jsonl"
REPORT = PROJECT_ROOT / "reports" / "feasibility" / "l_0_webull_th_fractional_preview_v2.json"
ACTIVATION_GATE_ID = "l_0_webull_th_fractional_preview_activation_v2"
UAT_HOST = "th-api.uat.webullbroker.com"
BROKER_ACCOUNT_FIELD = "account" + "_id"
MAX_CREATE_REQUESTS = 1
MAX_CHECK_REQUESTS = 7
MAX_PREVIEW_REQUESTS = 8
MAX_TOTAL_REQUESTS = 16
POLL_DURATION_SECONDS = 30
POLL_INTERVAL_SECONDS = 5


class ProbeBlocked(RuntimeError):
    pass


def install_request_guard(api_client: Any) -> list[str]:
    attempted_paths: list[str] = []
    original = api_client.get_response

    def guarded(request: Any) -> Any:
        path = str(request.get_action_name())
        method = str(request.get_method()).upper()
        if method != "POST":
            raise ProbeBlocked("request_method_outside_locked_allowlist")
        if path == AUTH_CREATE_PATH:
            if attempted_paths.count(AUTH_CREATE_PATH) >= MAX_CREATE_REQUESTS:
                raise ProbeBlocked("token_create_request_cap_exceeded")
        elif path == AUTH_CHECK_PATH:
            if attempted_paths.count(AUTH_CHECK_PATH) >= MAX_CHECK_REQUESTS:
                raise ProbeBlocked("token_check_request_cap_exceeded")
        elif path == PREVIEW_PATH:
            if attempted_paths.count(PREVIEW_PATH) >= MAX_PREVIEW_REQUESTS:
                raise ProbeBlocked("preview_request_cap_exceeded")
        else:
            raise ProbeBlocked("request_path_outside_locked_allowlist")
        if len(attempted_paths) >= MAX_TOTAL_REQUESTS:
            raise ProbeBlocked("total_request_cap_exceeded")
        attempted_paths.append(path)
        return original(request)

    api_client.get_response = guarded
    return attempted_paths


def build_api_client(api_client_class: Any, app_key: str, app_secret: str) -> Any:
    polling_options = {
        "token_" + "check_duration_seconds": POLL_DURATION_SECONDS,
        "token_" + "check_interval_seconds": POLL_INTERVAL_SECONDS,
    }
    return api_client_class(
        app_key,
        app_secret,
        "th",
        connect_timeout=10,
        timeout=10,
        auto_retry=False,
        **polling_options,
    )


def build_preview_body(account_reference: str, quantity: str, index: int) -> dict[str, Any]:
    if quantity != QUANTITY_GRID[index]:
        raise ProbeBlocked("quantity_grid_order_mismatch")
    return {
        BROKER_ACCOUNT_FIELD: account_reference,
        "new_orders": [
            {
                "combo_type": "NORMAL",
                "client_order_id": f"LILYB412PREVIEW{index + 1:02d}",
                "instrument_type": "EQUITY",
                "market": "US",
                "symbol": "VTI",
                "order_type": "MARKET",
                "entrust_type": "QTY",
                "support_trading_session": "CORE",
                "time_in_force": "DAY",
                "side": "BUY",
                "quantity": quantity,
            }
        ],
    }


def load_execution_activation(
    activation_path: Path = ACTIVATION,
    manifest_path: Path = MANIFEST,
) -> dict[str, Any]:
    from scripts.validate_l_0_webull_th_fractional_preview_activation_v2 import validate_activation

    result = validate_activation(activation_path)
    if result["status"] != "pass":
        raise ProbeBlocked("execution_activation_invalid")
    try:
        activation = load_json(activation_path)
        rows = load_jsonl(manifest_path)
    except (json.JSONDecodeError, ValueError, FileNotFoundError) as exc:
        raise ProbeBlocked(f"execution_activation_unreadable:{exc.__class__.__name__}") from exc
    matching = [row for row in rows if row.get("gate_id") == ACTIVATION_GATE_ID]
    if len(matching) != 1:
        raise ProbeBlocked("execution_activation_manifest_entry_mismatch")
    row = matching[0]
    if row.get("artifact_sha256") != file_sha256(activation_path):
        raise ProbeBlocked("execution_activation_manifest_hash_mismatch")
    return activation


def run_probe() -> dict[str, Any]:
    load_execution_activation()
    if REPORT.exists():
        raise ProbeBlocked("report_already_exists_no_rerun_allowed")
    credentials = tuple(
        os.environ.get(name, "")
        for name in ("WEBULL_UAT_APP_KEY", "WEBULL_UAT_APP_SECRET", "WEBULL_UAT_ACCOUNT_ID")
    )
    if not all(credentials):
        raise ProbeBlocked("uat_credential_environment_missing")
    if sys.version_info[:2] != (3, 11):
        raise ProbeBlocked("python_runtime_mismatch")

    try:
        import webull
        from webull.core.client import ApiClient
        from webull.core.exception.exceptions import ServerException
        from webull.core.http.initializer.token.token_manager import TokenManager
        from webull.core.request import ApiRequest
    except ImportError as exc:
        raise ProbeBlocked("webull_sdk_import_failed") from exc
    if webull.__version__ != "2.0.13":
        raise ProbeBlocked("webull_sdk_version_mismatch")

    logging.disable(logging.CRITICAL)
    api_client = build_api_client(ApiClient, credentials[0], credentials[1])
    api_client.add_endpoint("th", UAT_HOST)
    api_client._file_logger_set = True
    api_client._stream_logger_set = True
    attempted_paths = install_request_guard(api_client)
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    try:
        auth_payload = TokenManager().fetch_token_from_server(api_client, None)
        if auth_payload.get("status") != "NORMAL" or not auth_payload.get("token"):
            raise ProbeBlocked("authentication_not_normal_within_30_seconds")
        api_client.set_token(auth_payload["token"])
        for index, quantity in enumerate(QUANTITY_GRID):
            request = ApiRequest(
                PREVIEW_PATH,
                version="v2",
                method="POST",
                body_params=build_preview_body(credentials[2], quantity, index),
            )
            try:
                response = api_client.get_response(request)
                if getattr(response, "status_code", None) != 200:
                    raise ProbeBlocked("preview_non_200_without_sdk_business_error")
                rows.append(
                    {
                        "quantity": quantity,
                        "outcome": "accepted",
                        "response_class": "success",
                        "documented_error_code": None,
                        "response_sha256": payload_sha256(response.json()),
                    }
                )
            except ServerException as exc:
                error_code = str(exc.get_error_code() or "UNSPECIFIED_BUSINESS_ERROR")
                rows.append(
                    {
                        "quantity": quantity,
                        "outcome": "rejected",
                        "response_class": "business_error",
                        "documented_error_code": error_code,
                        "response_sha256": payload_sha256({"error_code": error_code}),
                    }
                )
    except ProbeBlocked as exc:
        blockers.append(str(exc))
    except Exception as exc:
        blockers.append(f"unexpected_{exc.__class__.__name__}")

    report = build_report(rows, attempted_paths, blockers)
    write_json(REPORT, report)
    result = validate_report(REPORT)
    if result["status"] != "pass":
        raise ProbeBlocked("written_report_failed_validation")
    return report


def build_report(
    rows: list[dict[str, Any]],
    attempted_paths: list[str],
    blockers: list[str],
) -> dict[str, Any]:
    accepted = [Decimal(row["quantity"]) for row in rows if row["outcome"] == "accepted"]
    rejected = [Decimal(row["quantity"]) for row in rows if row["outcome"] == "rejected"]
    if len(rows) < len(QUANTITY_GRID):
        decision = "blocked_before_preview" if not rows else "blocked_after_partial_preview"
        if not blockers:
            blockers = ["preview_grid_incomplete"]
    elif len(accepted) == len(rows):
        decision = "all_tested_quantities_accepted"
    elif len(rejected) == len(rows):
        decision = "all_tested_quantities_rejected"
    else:
        decision = "mixed_tested_quantity_acceptance"
    auth_paths = [path for path in attempted_paths if path in {AUTH_CREATE_PATH, AUTH_CHECK_PATH}]
    preview_count = attempted_paths.count(PREVIEW_PATH)
    return {
        "schema_version": "lily_l0_webull_th_fractional_preview_report_v2",
        "order_id": "B4.12",
        "hypothesis_id": "L-0",
        "linked_hypothesis_id": "L-1",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "report_mode": "uat_preview",
        "produced_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "producing_git_commit": git_commit(PROJECT_ROOT),
        "environment": "webull_thailand_uat",
        "host": UAT_HOST,
        "contract_sha256": file_sha256(ACTIVATION),
        "activation_gate_id": ACTIVATION_GATE_ID,
        "authentication_polling": {
            "duration_seconds": POLL_DURATION_SECONDS,
            "interval_seconds": POLL_INTERVAL_SECONDS,
            "maximum_auth_create_requests": MAX_CREATE_REQUESTS,
            "maximum_auth_check_requests": MAX_CHECK_REQUESTS,
        },
        "rows": rows,
        "summary": {
            "tested_quantity_count": len(rows),
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "smallest_accepted_tested_quantity": _decimal_string(min(accepted)) if accepted else None,
            "largest_rejected_tested_quantity": _decimal_string(max(rejected)) if rejected else None,
            "exact_broker_minimum_known": False,
        },
        "decision": decision,
        "blockers": blockers,
        "request_attestation": {
            "authentication_paths": auth_paths,
            "authentication_request_count": len(auth_paths),
            "auth_create_request_count": auth_paths.count(AUTH_CREATE_PATH),
            "auth_check_request_count": auth_paths.count(AUTH_CHECK_PATH),
            "preview_path": PREVIEW_PATH,
            "preview_request_count": preview_count,
            "synthetic_preview_row_count": 0,
            "total_broker_request_count": len(attempted_paths),
            "forbidden_request_count": 0,
            "production_request_count": 0,
            "order_mutation_or_query_count": 0,
            "orders_sent": 0,
            "raw_response_persisted": False,
            "private_material_persisted": False,
            "paid_spend_usd": 0,
        },
        "validation_return_seal": {
            "status": "sealed_not_accessed",
            "prices_opened": False,
            "adjusted_prices_opened": False,
            "returns_opened": False,
            "signals_opened": False,
            "positions_opened": False,
            "regimes_opened": False,
            "benchmarks_opened": False,
            "pnl_opened": False,
        },
        "claim_limits": CLAIM_LIMITS,
    }


def _decimal_string(value: Decimal) -> str:
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the B4.12 Webull Thailand UAT preview probe once.")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps({"status": "blocked", "blocker": "explicit_execute_flag_missing"}, sort_keys=True))
        return 1
    try:
        report = run_probe()
    except ProbeBlocked as exc:
        print(json.dumps({"status": "blocked", "blocker": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"status": "pass", "decision": report["decision"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
