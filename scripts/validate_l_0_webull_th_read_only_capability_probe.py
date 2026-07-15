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


DEFAULT_PATH = PROJECT_ROOT / "experiments" / "l_0_webull_th_read_only_capability_probe.json"
EXPECTED_SYMBOLS = ["VTI", "VGK", "EWJ", "IPAC", "VWO", "IEF", "SCHP", "GLDM", "PDBC", "VNQI"]
EXPECTED_READ_ONLY_PATHS = [
    "/openapi/account/list",
    "/openapi/assets/balance",
    "/openapi/assets/positions",
    "/openapi/instrument/stock/list",
]


def validate_contract(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        payload = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"contract_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l0_webull_th_read_only_capability_probe_v1",
        "order_id": "B4.6",
        "hypothesis_id": "L-0",
        "status": "locked_before_probe",
        "evidence_ceiling": "E0",
        "edge_claim": "none",
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            blockers.append(f"field_mismatch:{field}")

    environment = payload.get("environment", {})
    if environment.get("region") != "th" or environment.get("api_endpoint") != "api.webull.co.th":
        blockers.append("thailand_production_endpoint_mismatch")
    if environment.get("sdk_version_required") != "2.0.13":
        blockers.append("sdk_version_mismatch")
    if environment.get("python_runtime") != "3.11":
        blockers.append("python_runtime_mismatch")
    if environment.get("credential_environment_names") != ["WEBULL_APP_KEY", "WEBULL_APP_SECRET"]:
        blockers.append("credential_environment_inventory_mismatch")
    if environment.get("credential_values_may_be_persisted_or_logged") is not False:
        blockers.append("credential_persistence_must_be_false")
    if environment.get("selected_account_may_be_persisted_or_logged") is not False:
        blockers.append("account_id_persistence_must_be_false")

    requests = payload.get("allowed_requests", {})
    if requests.get("read_only_paths") != EXPECTED_READ_ONLY_PATHS:
        blockers.append("read_only_path_inventory_mismatch")
    if requests.get("maximum_read_only_requests") != 4:
        blockers.append("request_cap_mismatch")
    if requests.get("automatic_retry") is not False:
        blockers.append("automatic_retry_must_be_false")
    if requests.get("spend_usd") != 0:
        blockers.append("zero_spend_rule_mismatch")
    forbidden = set(requests.get("forbidden_path_fragments", []))
    if forbidden != {"preview", "place", "replace", "cancel", "/orders", "/order/"}:
        blockers.append("forbidden_path_inventory_mismatch")

    universe = payload.get("candidate_universe", {})
    if universe.get("symbols") != EXPECTED_SYMBOLS:
        blockers.append("candidate_symbol_inventory_mismatch")
    if universe.get("instrument_category") != "US_STOCK":
        blockers.append("instrument_category_mismatch")
    if universe.get("instrument_query_count") != 1:
        blockers.append("instrument_query_count_mismatch")
    if universe.get("required_public_fields") != ["symbol", "instrument_type", "status", "fractionable"]:
        blockers.append("instrument_field_inventory_mismatch")

    privacy = payload.get("account_privacy", {})
    if privacy.get("raw_account_retention") != "hash_in_memory_then_discard":
        blockers.append("raw_account_retention_mismatch")
    if privacy.get("sdk_logging") != "disabled_before_client_construction":
        blockers.append("sdk_logging_rule_mismatch")
    forbidden_outputs = set(privacy.get("forbidden_tracked_outputs", []))
    required_private = {"App Key", "App Secret", "access token", "account_id", "cash or balance values", "position symbols or quantities", "raw account responses", "absolute local paths"}
    if not required_private.issubset(forbidden_outputs):
        blockers.append("account_privacy_inventory_incomplete")

    classification = payload.get("success_and_classification", {})
    if set(classification.get("allowed_outcomes", [])) != {
        "verified_read_only_and_fractional_candidate_set",
        "scope_restricted_account_or_candidate_capability",
        "blocked_authentication_or_schema",
    }:
        blockers.append("outcome_inventory_mismatch")
    if "does not authorize" not in str(classification.get("paper_trade_rule", "")):
        blockers.append("paper_trade_boundary_incomplete")
    if "not proof" not in str(classification.get("current_capital_rule", "")):
        blockers.append("claim_limit_incomplete")

    sources = payload.get("source_snapshots", [])
    if len(sources) != 8 or any(len(str(row.get("sha256", ""))) != 64 for row in sources):
        blockers.append("source_snapshot_inventory_mismatch")

    seal = payload.get("validation_return_seal", {})
    if seal.get("untouched_start") != "2016-01-04" or seal.get("untouched_end") != "2026-06-30":
        blockers.append("validation_window_mismatch")
    if seal.get("status_required") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
    if seal.get("forbidden_inputs") != ["prices", "adjusted prices", "returns", "signals", "positions", "regimes", "benchmarks", "PnL"]:
        blockers.append("validation_forbidden_input_inventory_mismatch")

    if len(payload.get("required_outputs", [])) != 5:
        blockers.append("required_output_inventory_mismatch")
    hard_stops = " ".join(str(value) for value in payload.get("hard_stops", []))
    for term in ("credential", "preview", "balance value", "open validation returns"):
        if term not in hard_stops:
            blockers.append(f"hard_stop_missing:{term}")

    serialized = json.dumps(payload, ensure_ascii=False)
    if "WEBULL_APP_KEY=" in serialized or "WEBULL_APP_SECRET=" in serialized:
        blockers.append("credential_assignment_forbidden")
    return _result(path, blockers)


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "contract_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the locked Webull Thailand read-only capability probe.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    result = validate_contract(args.contract)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
