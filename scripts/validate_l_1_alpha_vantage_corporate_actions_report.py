from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root
from lib.provenance import file_sha256, payload_sha256


DEFAULT_JSON = PROJECT_ROOT / "reports" / "data_quality" / "l_1_alpha_vantage_corporate_actions.json"
DEFAULT_MARKDOWN = PROJECT_ROOT / "reports" / "data_quality" / "l_1_alpha_vantage_corporate_actions.md"
DEFAULT_REGISTRY = PROJECT_ROOT / "datasets" / "registry.json"
DEFAULT_COST_LEDGER = PROJECT_ROOT / "datasets" / "cost_ledger.json"
CONTRACT = PROJECT_ROOT / "experiments" / "l_1_alpha_vantage_corporate_actions_acquisition.json"
EXPECTED_CONTRACT_SHA256 = "562e06914be4e651c73017009f51c26cab83cb4ff6bb26d1c28c2be32c441c96"
EXPECTED_SYMBOLS = {"VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"}
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def validate_report(
    report_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MARKDOWN,
    registry_path: Path = DEFAULT_REGISTRY,
    cost_ledger_path: Path = DEFAULT_COST_LEDGER,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        report = load_json(report_path)
        markdown = markdown_path.read_text(encoding="utf-8")
        registry = load_json(registry_path)
        ledger = load_json(cost_ledger_path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(report_path, [f"artifact_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l1_alpha_vantage_corporate_actions_report_v1",
        "order_id": "B4.4",
        "hypothesis_id": "L-1",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "decision": "scope_restricted_no_point_in_time_revision_archive",
    }
    for field, value in expected.items():
        if report.get(field) != value:
            blockers.append(f"field_mismatch:{field}")
    if file_sha256(CONTRACT) != EXPECTED_CONTRACT_SHA256:
        blockers.append("locked_contract_file_hash_mismatch")
    if report.get("contract_sha256") != EXPECTED_CONTRACT_SHA256:
        blockers.append("locked_contract_report_hash_mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", str(report.get("producing_git_commit", ""))):
        blockers.append("producing_git_commit_invalid")

    acquisition = report.get("acquisition", {})
    if acquisition.get("provider") != "Alpha Vantage":
        blockers.append("provider_mismatch")
    if acquisition.get("successful_payload_count") != 16:
        blockers.append("successful_payload_count_mismatch")
    attempts = acquisition.get("network_attempt_count")
    if not isinstance(attempts, int) or not 16 <= attempts <= 25:
        blockers.append("network_attempt_count_out_of_bounds")
    if acquisition.get("actual_paid_amount_usd") != 0:
        blockers.append("paid_spend_must_be_zero")
    if acquisition.get("key_environment_name") != "ALPHAVANTAGE_API_FREE":
        blockers.append("key_environment_name_mismatch")
    if acquisition.get("credential_value_recorded") is not False:
        blockers.append("credential_value_must_not_be_recorded")

    coverage = report.get("coverage", {})
    coverage_rows = coverage.get("rows", [])
    if coverage.get("pair_count") != 16 or len(coverage_rows) != 8:
        blockers.append("coverage_inventory_mismatch")
    if {row.get("symbol") for row in coverage_rows if isinstance(row, dict)} != EXPECTED_SYMBOLS:
        blockers.append("coverage_symbol_inventory_mismatch")
    total_rows = 0
    empty_payloads = 0
    for row in coverage_rows:
        if not isinstance(row, dict):
            blockers.append("coverage_row_must_be_object")
            continue
        for endpoint in ("dividends", "splits"):
            item = row.get(endpoint, {})
            count = item.get("row_count")
            if not isinstance(count, int) or count < 0:
                blockers.append(f"coverage_invalid_row_count:{row.get('symbol')}:{endpoint}")
                continue
            total_rows += count
            empty_payloads += int(count == 0)
            if not HASH_PATTERN.fullmatch(str(item.get("sha256", ""))):
                blockers.append(f"coverage_invalid_hash:{row.get('symbol')}:{endpoint}")
            if count == 0 and (item.get("earliest") is not None or item.get("latest") is not None):
                blockers.append(f"coverage_empty_date_mismatch:{row.get('symbol')}:{endpoint}")
    if total_rows != acquisition.get("total_provider_rows") or empty_payloads != acquisition.get("empty_payload_count"):
        blockers.append("coverage_aggregate_mismatch")

    reconciliation = report.get("reconciliation", {})
    reconciliation_rows = reconciliation.get("rows", [])
    if reconciliation.get("comparison_start") != "2006-02-03" or reconciliation.get("comparison_end") != "2015-12-31":
        blockers.append("reconciliation_window_mismatch")
    if reconciliation.get("pair_count") != 16 or len(reconciliation_rows) != 8:
        blockers.append("reconciliation_inventory_mismatch")
    exact_pairs = 0
    sums = {"matched": 0, "alpha_only": 0, "yahoo_only": 0}
    for row in reconciliation_rows:
        if not isinstance(row, dict):
            blockers.append("reconciliation_row_must_be_object")
            continue
        for endpoint in ("dividends", "splits"):
            item = row.get(endpoint, {})
            values = [item.get(field) for field in ("alpha", "yahoo", "matched", "alpha_only", "yahoo_only")]
            if not all(isinstance(value, int) and value >= 0 for value in values):
                blockers.append(f"reconciliation_invalid_count:{row.get('symbol')}:{endpoint}")
                continue
            if item["alpha"] != item["matched"] + item["alpha_only"]:
                blockers.append(f"reconciliation_alpha_count_mismatch:{row.get('symbol')}:{endpoint}")
            if item["yahoo"] != item["matched"] + item["yahoo_only"]:
                blockers.append(f"reconciliation_yahoo_count_mismatch:{row.get('symbol')}:{endpoint}")
            exact = item.get("exact") is True
            if exact != (item["alpha_only"] == 0 and item["yahoo_only"] == 0):
                blockers.append(f"reconciliation_exact_flag_mismatch:{row.get('symbol')}:{endpoint}")
            exact_pairs += int(exact)
            for field in sums:
                sums[field] += item[field]
    if exact_pairs != reconciliation.get("exact_pair_count"):
        blockers.append("reconciliation_exact_pair_aggregate_mismatch")
    if 16 - exact_pairs != reconciliation.get("mismatched_pair_count"):
        blockers.append("reconciliation_mismatch_pair_aggregate_mismatch")
    if reconciliation.get("all_pairs_exact") is not False:
        blockers.append("reconciliation_must_not_claim_all_exact")
    for field, report_field in (
        ("matched", "matched_event_count"),
        ("alpha_only", "alpha_only_event_count"),
        ("yahoo_only", "yahoo_only_event_count"),
    ):
        if sums[field] != reconciliation.get(report_field):
            blockers.append(f"reconciliation_aggregate_mismatch:{field}")

    hashes = report.get("datasets", {}).get("hashes", {})
    if set(hashes) != {
        "aggregate_container_sha256",
        "request_manifest_sha256",
        "normalized_output_sha256",
        "request_and_normalization_specification_sha256",
        "private_reconciliation_sha256",
    } or any(not HASH_PATTERN.fullmatch(str(value)) for value in hashes.values()):
        blockers.append("dataset_hash_inventory_invalid")

    guardrails = report.get("guardrails", {})
    if guardrails.get("validation_window_status") != "sealed_not_accessed":
        blockers.append("validation_seal_mismatch")
    if guardrails.get("maximum_existing_market_or_return_date_accessed") != "2015-12-31":
        blockers.append("maximum_existing_market_date_mismatch")
    required_false = (
        "validation_prices_opened",
        "validation_adjusted_prices_opened",
        "validation_returns_opened",
        "validation_signals_opened",
        "validation_positions_opened",
        "validation_regimes_opened",
        "validation_benchmarks_opened",
        "validation_pnl_opened",
        "credential_value_recorded",
        "absolute_local_path_recorded",
        "paid_data_used",
        "orders_or_broker_actions",
        "validation_unlock",
    )
    if any(guardrails.get(field) is not False for field in required_false):
        blockers.append("guardrail_false_field_mismatch")
    if guardrails.get("provider_corporate_action_events_after_2015_isolated") is not True:
        blockers.append("post_2015_event_isolation_mismatch")
    if not report.get("tier_blockers") or not report.get("exact_next_safe_action"):
        blockers.append("tier_blockers_or_next_action_missing")

    datasets = {row.get("dataset_id"): row for row in registry.get("datasets", []) if isinstance(row, dict)}
    raw = datasets.get("l1.alpha_vantage.corporate_actions.raw.v1", {})
    normalized = datasets.get("l1.alpha_vantage.corporate_actions.normalized.v1", {})
    if raw.get("status") != "scope_restricted" or normalized.get("status") != "scope_restricted":
        blockers.append("registry_scope_status_mismatch")
    if normalized.get("parent_dataset_ids") != ["l1.alpha_vantage.corporate_actions.raw.v1"]:
        blockers.append("registry_parent_mismatch")
    if raw.get("hashes", {}).get("source_container_sha256") != hashes.get("aggregate_container_sha256"):
        blockers.append("registry_raw_hash_mismatch")
    if normalized.get("hashes", {}).get("normalized_output_sha256") != hashes.get("normalized_output_sha256"):
        blockers.append("registry_normalized_hash_mismatch")

    ledger_rows = [row for row in ledger.get("entries", []) if isinstance(row, dict) and row.get("order_id") == "B4.4"]
    if len(ledger_rows) != 1:
        blockers.append("cost_ledger_B4_4_entry_count_mismatch")
    else:
        ledger_row = ledger_rows[0]
        if ledger_row.get("actual_paid_amount_usd") != 0 or ledger_row.get("network_attempt_count") != attempts:
            blockers.append("cost_ledger_B4_4_value_mismatch")
        if ledger_row.get("market_price_or_return_data_downloaded") is not False or ledger_row.get("validation_returns_opened") is not False:
            blockers.append("cost_ledger_B4_4_boundary_mismatch")
    if ledger.get("actual_cumulative_paid_spend_usd") != 0:
        blockers.append("cumulative_paid_spend_must_be_zero")

    digest = report.get("report_digest_sha256")
    digest_payload = dict(report)
    digest_payload.pop("report_digest_sha256", None)
    if digest != payload_sha256(digest_payload):
        blockers.append("report_digest_mismatch")
    for required in (
        str(digest),
        str(report.get("producing_git_commit", "")),
        "E1",
        "scope_restricted_no_point_in_time_revision_archive",
        "sealed_not_accessed",
        "USD 0",
    ):
        if not required or required not in markdown:
            blockers.append(f"markdown_missing_machine_value:{required}")
    return _result(report_path, blockers)


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "report_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Lily B4.4 report pack.")
    parser.add_argument("--report", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    result = validate_report(args.report, args.markdown)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
