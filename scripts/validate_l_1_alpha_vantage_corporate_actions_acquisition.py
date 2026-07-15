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


DEFAULT_PATH = (
    PROJECT_ROOT / "experiments" / "l_1_alpha_vantage_corporate_actions_acquisition.json"
)
EXPECTED_SYMBOLS = ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]
EXPECTED_FORBIDDEN_INPUTS = [
    "validation prices",
    "validation adjusted prices",
    "validation returns",
    "validation signals",
    "validation positions",
    "validation regimes",
    "validation benchmarks",
    "validation PnL",
]


def validate_contract(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        payload = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"contract_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l1_alpha_vantage_corporate_actions_acquisition_v1",
        "order_id": "B4.3",
        "execution_order_id": "B4.4",
        "hypothesis_id": "L-1",
        "status": "locked_before_acquisition",
        "evidence_ceiling": "E1",
        "edge_claim": "none",
        "validation_unlock_authorized": False,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            blockers.append(f"field_mismatch:{field}")

    attestation = payload.get("design_only_attestation", {})
    expected_attestation = {
        "alpha_vantage_requests_in_B4_3": 0,
        "lily_etf_requests_in_B4_3": 0,
        "validation_prices_or_returns_opened_in_B4_3": False,
        "credentials_read_or_recorded_in_B4_3": False,
        "paid_spend_usd_in_B4_3": 0,
    }
    if attestation != expected_attestation:
        blockers.append("design_only_attestation_mismatch")

    source = payload.get("source", {})
    if source.get("provider") != "Alpha Vantage":
        blockers.append("provider_mismatch")
    if source.get("base_url") != "https://www.alphavantage.co/query":
        blockers.append("base_url_mismatch")
    if source.get("key_environment_name") != "ALPHAVANTAGE_API_FREE":
        blockers.append("credential_environment_name_mismatch")
    if source.get("credential_value_may_be_persisted") is not False:
        blockers.append("credential_persistence_must_be_false")
    if source.get("credential_value_may_appear_in_logs_or_request_metadata") is not False:
        blockers.append("credential_logging_must_be_false")
    if source.get("documented_free_daily_request_limit") != 25:
        blockers.append("free_daily_request_limit_mismatch")
    if source.get("documented_date_filter_available") is not False:
        blockers.append("date_filter_assumption_mismatch")
    if source.get("point_in_time_revision_archive_documented") is not False:
        blockers.append("point_in_time_archive_assumption_mismatch")

    universe = payload.get("request_universe", {})
    if universe.get("symbols") != EXPECTED_SYMBOLS:
        blockers.append("symbol_inventory_mismatch")
    endpoints = universe.get("endpoints", {})
    if set(endpoints) != {"DIVIDENDS", "SPLITS"}:
        blockers.append("endpoint_inventory_mismatch")
    if endpoints.get("DIVIDENDS", {}).get("required_nonempty_row_fields") != [
        "ex_dividend_date",
        "declaration_date",
        "record_date",
        "payment_date",
        "amount",
    ]:
        blockers.append("dividend_schema_mismatch")
    if endpoints.get("SPLITS", {}).get("required_nonempty_row_fields") != [
        "effective_date",
        "split_factor",
    ]:
        blockers.append("split_schema_mismatch")
    if universe.get("allowed_query_parameter_names") != ["function", "symbol", "apikey"]:
        blockers.append("query_parameter_inventory_mismatch")
    if universe.get("successful_payload_target") != 16:
        blockers.append("successful_payload_target_mismatch")

    requests = payload.get("request_guardrails", {})
    if requests.get("network_authorized_only_in_execution_order") != "B4.4":
        blockers.append("network_order_boundary_mismatch")
    if requests.get("concurrency") != 1 or requests.get("minimum_seconds_between_attempts") != 15:
        blockers.append("throttle_mismatch")
    if requests.get("daily_total_attempt_cap") != 25:
        blockers.append("daily_attempt_cap_mismatch")
    if requests.get("spend_rule") != (
        "Actual and cumulative paid spend must remain USD 0; no premium upgrade, purchase, "
        "or paid fallback is authorized."
    ):
        blockers.append("zero_spend_rule_mismatch")
    success_rule = str(requests.get("success_rule", ""))
    if not all(field in success_rule for field in ("data array", "Information", "Note", "Error Message")):
        blockers.append("service_message_detection_incomplete")
    if "25 daily attempts" not in str(requests.get("quota_stop_rule", "")):
        blockers.append("quota_stop_rule_incomplete")

    seal = payload.get("validation_return_seal", {})
    if seal.get("untouched_validation_start") != "2016-01-04":
        blockers.append("validation_start_mismatch")
    if seal.get("untouched_validation_end") != "2026-06-30":
        blockers.append("validation_end_mismatch")
    if seal.get("validation_status_required") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
    if seal.get("maximum_existing_market_or_return_date_allowed") != "2015-12-31":
        blockers.append("existing_market_data_boundary_mismatch")
    if seal.get("forbidden_inputs") != EXPECTED_FORBIDDEN_INPUTS:
        blockers.append("forbidden_validation_input_inventory_mismatch")
    if "individual event amounts or rows remain outside tracked outputs" not in str(
        seal.get("output_exposure_rule", "")
    ):
        blockers.append("tracked_output_exposure_rule_incomplete")

    storage = payload.get("storage_and_integrity", {})
    if storage.get("raw_storage_reference") != (
        "${LILY_DATA_ROOT}/raw/alpha_vantage_corporate_actions_v1"
    ):
        blockers.append("raw_storage_reference_mismatch")
    if storage.get("normalized_storage_reference") != (
        "${LILY_DATA_ROOT}/normalized/alpha_vantage_corporate_actions_v1.json"
    ):
        blockers.append("normalized_storage_reference_mismatch")
    if set(storage.get("hash_policy", {})) != {
        "per_response",
        "aggregate_raw",
        "normalized",
        "specification",
    }:
        blockers.append("hash_policy_incomplete")
    forbidden_metadata = storage.get("forbidden_request_metadata", [])
    if forbidden_metadata != ["apikey", "credential_value", "authorization_header", "absolute_local_path"]:
        blockers.append("forbidden_request_metadata_mismatch")
    if "no existing dataset entry is overwritten" not in str(storage.get("registry_rule", "")):
        blockers.append("append_only_registry_rule_incomplete")

    normalization = payload.get("normalization", {})
    if "decimal arithmetic" not in str(normalization.get("decimal_rule", "")):
        blockers.append("decimal_boundary_rule_incomplete")
    if "silently deduplicating" not in str(normalization.get("ordering_rule", "")):
        blockers.append("duplicate_handling_rule_incomplete")
    if "new reviewed gate" not in str(normalization.get("schema_drift_rule", "")):
        blockers.append("schema_drift_stop_rule_incomplete")

    decision = payload.get("reconciliation_and_decision", {})
    if decision.get("comparison_window_end") != "2015-12-31":
        blockers.append("comparison_window_mismatch")
    if set(decision.get("allowed_outcomes", [])) != {
        "accept_for_independent_current_snapshot_reconciliation",
        "scope_restricted_no_point_in_time_revision_archive",
        "reject_provider_or_schema",
    }:
        blockers.append("outcome_inventory_mismatch")
    mandatory_restriction = str(decision.get("mandatory_scope_restriction", ""))
    if not all(
        term in mandatory_restriction
        for term in ("cannot by itself", "point-in-time blocker", "unlock validation", "E2")
    ):
        blockers.append("mandatory_scope_restriction_incomplete")
    if "Do not choose the provider value that improves performance" not in str(
        decision.get("mismatch_rule", "")
    ):
        blockers.append("anti_selection_rule_incomplete")

    outputs = payload.get("required_B4_4_outputs", [])
    if len(outputs) != 9 or not any("research_log/005" in str(item) for item in outputs):
        blockers.append("B4_4_output_inventory_incomplete")
    hard_stops = payload.get("hard_stops", [])
    if len(hard_stops) != 7:
        blockers.append("hard_stop_inventory_mismatch")
    joined_stops = " ".join(str(item) for item in hard_stops)
    for required in ("API key", "validation price", "Paid spend", "point-in-time verified"):
        if required not in joined_stops:
            blockers.append(f"hard_stop_missing:{required}")

    serialized = json.dumps(payload, ensure_ascii=False)
    if "ALPHAVANTAGE_API_FREE=" in serialized or "apikey=" in serialized:
        blockers.append("credential_assignment_or_query_string_forbidden")
    return _result(path, blockers)


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "contract_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the locked L-1 Alpha Vantage corporate-actions acquisition contract."
    )
    parser.add_argument("--contract", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    result = validate_contract(args.contract)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
