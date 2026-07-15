from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root
from lib.provenance import payload_sha256


DEFAULT_PATH = PROJECT_ROOT / "reports" / "feasibility" / "l_0_webull_th_read_only_capability.json"
MARKDOWN_PATH = PROJECT_ROOT / "reports" / "feasibility" / "l_0_webull_th_read_only_capability.md"
EXPECTED_SYMBOLS = ["VTI", "VGK", "EWJ", "IPAC", "VWO", "IEF", "SCHP", "GLDM", "PDBC", "VNQI"]
EXPECTED_COMMIT = "4d109be190ff28339c5d142958623f0b7e06299e"
EXPECTED_DIGEST = "12ca642bf56406d53cc05dffba695cdc588e707afc827dd64db906e6f919e068"


def validate_report(path: Path = DEFAULT_PATH, markdown_path: Path = MARKDOWN_PATH) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        report = load_json(path)
        markdown = markdown_path.read_text(encoding="utf-8")
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return _result(path, [f"report_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l0_webull_th_read_only_capability_report_v1",
        "order_id": "B4.6",
        "hypothesis_id": "L-0",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "decision": "verified_read_only_and_fractional_candidate_set",
        "producing_git_commit": EXPECTED_COMMIT,
    }
    for field, value in expected.items():
        if report.get(field) != value:
            blockers.append(f"field_mismatch:{field}")

    digest = report.get("report_digest_sha256")
    content = dict(report)
    content.pop("report_digest_sha256", None)
    if digest != EXPECTED_DIGEST or payload_sha256(content) != EXPECTED_DIGEST:
        blockers.append("report_digest_mismatch")

    runtime = report.get("runtime", {})
    if runtime.get("webull_sdk") != "2.0.13" or runtime.get("region") != "th" or runtime.get("environment") != "production":
        blockers.append("runtime_mismatch")

    account = report.get("account_capability", {})
    for field in (
        "authentication_succeeded",
        "account_list_endpoint_succeeded",
        "balance_endpoint_succeeded",
        "positions_endpoint_succeeded",
    ):
        if account.get(field) is not True:
            blockers.append(f"account_capability_failed:{field}")
    if account.get("private_values_persisted") is not False:
        blockers.append("private_values_must_not_be_persisted")
    for field in (
        "account_list_response_sha256",
        "balance_response_sha256",
        "positions_response_sha256",
    ):
        if len(str(account.get(field, ""))) != 64:
            blockers.append(f"response_hash_invalid:{field}")
    expected_account_keys = {
        "authentication_succeeded",
        "account_list_endpoint_succeeded",
        "balance_endpoint_succeeded",
        "positions_endpoint_succeeded",
        "account_list_field_inventory",
        "balance_field_inventory",
        "positions_field_inventory",
        "account_list_response_sha256",
        "balance_response_sha256",
        "positions_response_sha256",
        "private_values_persisted",
    }
    if set(account) != expected_account_keys:
        blockers.append("account_output_inventory_mismatch")

    instrument = report.get("instrument_capability", {})
    rows = instrument.get("symbols", [])
    if [row.get("symbol") for row in rows if isinstance(row, dict)] != EXPECTED_SYMBOLS:
        blockers.append("candidate_symbol_inventory_mismatch")
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"symbol", "instrument_type", "status", "fractionable"}:
            blockers.append("candidate_public_field_inventory_mismatch")
            continue
        if row.get("status") != "OC" or row.get("fractionable") is not True:
            blockers.append(f"candidate_not_tradable_fractionable:{row.get('symbol')}")
    if instrument.get("all_fractionable") is not True or instrument.get("all_tradable") is not True:
        blockers.append("candidate_aggregate_classification_mismatch")

    requests = report.get("request_attestation", {})
    if requests.get("read_only_paths") != [
        "/openapi/account/list",
        "/openapi/assets/balance",
        "/openapi/assets/positions",
        "/openapi/instrument/stock/list",
    ]:
        blockers.append("read_only_path_sequence_mismatch")
    for field in ("order_endpoint_calls", "orders_sent", "preview_calls", "paid_spend_usd"):
        if requests.get(field) != 0:
            blockers.append(f"forbidden_action_nonzero:{field}")
    if requests.get("read_only_request_count") != 4:
        blockers.append("read_only_request_count_mismatch")

    if report.get("tier_blockers") != [
        "minimum_order_unverified",
        "funding_fx_cost_unverified",
        "execution_quality_unverified",
        "realized_cost_unverified",
        "instrument_type_not_returned",
    ]:
        blockers.append("tier_blocker_inventory_mismatch")

    seal = report.get("validation_return_seal", {})
    if seal.get("status") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
    for field, value in seal.items():
        if field != "status" and value is not False:
            blockers.append(f"validation_seal_false_field_mismatch:{field}")

    required_markdown = [
        "verified_read_only_and_fractional_candidate_set",
        "validation returns: `sealed_not_accessed`",
        "ไม่เก็บ Account ID",
        "| VNQI | OC | true |",
        "ไม่มีการเรียก preview/place/replace/cancel order",
        "E0 prospective shadow accounting dry run",
    ]
    for value in required_markdown:
        if value not in markdown:
            blockers.append(f"markdown_missing:{value}")
    return _result(path, blockers)


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "report_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Webull Thailand read-only capability report.")
    parser.add_argument("--report", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--markdown", type=Path, default=MARKDOWN_PATH)
    args = parser.parse_args()
    result = validate_report(args.report, args.markdown)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
