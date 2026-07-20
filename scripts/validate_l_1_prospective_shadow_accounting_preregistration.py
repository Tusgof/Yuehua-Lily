from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root
from lib.provenance import file_sha256


DEFAULT_PATH = PROJECT_ROOT / "experiments" / "l_1_prospective_shadow_accounting_preregistration.json"
EXPECTED_SOURCE_HASHES = {
    "experiments/l_1_corporate_action_scope_decision.json": "5f9540d369e1d6aadcbabdb6e57268e42c7024625c748ed85880ecb905417b8a",
    "reports/feasibility/l_0_webull_th_read_only_capability.json": "365f0d4ce5db85cc9356f11457ac9776a79fc2ca290c85813f9428c89815f630",
    "reports/feasibility/l_0_sizing_feasibility.json": "b544759382b90d50dc76af4bc9752ea34eab2d946b616f6d286a41a4104a13c2",
}
EXPECTED_SYMBOLS = ["VTI", "VGK", "EWJ", "IPAC", "VWO", "IEF", "SCHP", "GLDM", "PDBC", "VNQI"]
EXPECTED_WEIGHTS = {
    "VTI": 0.07363636,
    "VGK": 0.07363636,
    "EWJ": 0.07363636,
    "IPAC": 0.07363636,
    "VWO": 0.07363636,
    "IEF": 0.14727273,
    "SCHP": 0.14727273,
    "GLDM": 0.08181818,
    "PDBC": 0.08181818,
    "VNQI": 0.07363636,
}


def validate_preregistration(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        payload = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"artifact_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l1_prospective_shadow_accounting_preregistration_v1",
        "order_id": "B4.7",
        "hypothesis_id": "L-1",
        "status": "locked_before_observation",
        "evidence_tier": "E0",
        "edge_claim": "none",
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            blockers.append(f"field_mismatch:{field}")

    state = payload.get("execution_state", {})
    expected_state = {
        "design_and_lock_only": True,
        "dry_run_status": "planned_not_started",
        "activation_authorized_by_this_gate": False,
        "broker_or_provider_called_in_B4_7": False,
        "paper_order_authorized_by_this_gate": False,
        "real_order_authorized": False,
        "prospective_event_observed": False,
        "validation_window_status": "sealed_not_accessed",
    }
    if state != expected_state:
        blockers.append("execution_state_boundary_mismatch")

    scope = payload.get("scope", {})
    if scope.get("symbols") != EXPECTED_SYMBOLS:
        blockers.append("symbol_inventory_mismatch")
    if scope.get("included_event_types") != [
        "cash_dividend",
        "capital_gains_distribution",
        "stock_split",
        "reverse_split",
    ]:
        blockers.append("event_type_inventory_mismatch")
    for field in (
        "historical_backfill_allowed",
        "validation_prices_or_returns_allowed",
        "strategy_signal_allowed",
        "performance_measurement_allowed",
    ):
        if scope.get(field) is not False:
            blockers.append(f"scope_false_field_mismatch:{field}")

    streams = payload.get("comparison_streams", [])
    if [row.get("stream_id") for row in streams if isinstance(row, dict)] != [
        "webull_th_paper_ledger",
        "alpha_vantage_current_snapshot_shadow_ledger",
        "lily_yahoo_event_strategy_accounting",
    ]:
        blockers.append("comparison_stream_inventory_mismatch")
    stream_text = json.dumps(streams, ensure_ascii=False)
    for required in (
        "operational_reference_not_research_ground_truth",
        "current snapshot",
        "adjusted close alone is forbidden",
        "do not calculate a trend signal",
        "do not substitute a production or real-money account",
    ):
        if required not in stream_text:
            blockers.append(f"stream_rule_missing:{required}")

    portfolio = payload.get("common_shadow_portfolio", {})
    if portfolio.get("reference_capital_usd") != 1000.0:
        blockers.append("reference_capital_mismatch")
    if portfolio.get("cash_target_weight") != 0.1 or portfolio.get("gross_target_weight") != 0.9:
        blockers.append("cash_or_gross_target_mismatch")
    weights = portfolio.get("target_weights", {})
    if weights != EXPECTED_WEIGHTS:
        blockers.append("target_weight_inventory_mismatch")
    elif not math.isclose(sum(weights.values()), 0.9, rel_tol=0.0, abs_tol=1e-7):
        blockers.append("target_weights_do_not_sum_to_gross")
    for required in ("forward-only", "never use a pre-activation quote", "never transmit an order"):
        if required not in json.dumps(portfolio, ensure_ascii=False):
            blockers.append(f"portfolio_rule_missing:{required}")

    record = payload.get("event_record_contract", {})
    required_fields = set(record.get("required_fields", []))
    expected_fields = {
        "symbol",
        "event_type",
        "provider_or_broker_event_identifier_when_available",
        "effective_or_ex_date",
        "record_date_when_available",
        "payment_date_when_available",
        "cash_delta_usd",
        "unit_delta",
        "target_weight_tracking_delta",
        "hypothetical_rebalance_order_delta_usd",
        "source_observed_at",
        "source_container_sha256",
        "source_payload_sha256",
        "reference_nav_usd",
        "reference_quote_sha256",
    }
    if not expected_fields.issubset(required_fields):
        blockers.append("event_record_fields_incomplete")
    if "never as the sole key" not in str(record.get("event_match_key", "")):
        blockers.append("event_match_rule_incomplete")
    if "may not be imputed" not in str(record.get("missing_field_rule", "")):
        blockers.append("missing_field_rule_incomplete")

    thresholds = payload.get("materiality_thresholds", {})
    expected_threshold_fragments = {
        "cash_balance_difference_usd": "max(USD 1.00, 0.0005 times reference NAV)",
        "unit_balance_difference": "max(0.0001 share, the broker-reported minimum fractional share quantum",
        "target_weight_tracking_difference": "0.0010, equal to 10 basis points",
        "hypothetical_order_notional_difference_usd": "max(USD 1.00, 0.0010 times reference NAV)",
        "event_detection_or_posting_delay": "more than two US trading sessions",
    }
    for field, fragment in expected_threshold_fragments.items():
        if fragment not in str(thresholds.get(field, "")):
            blockers.append(f"materiality_threshold_mismatch:{field}")
    if "strictly greater" not in str(thresholds.get("strict_comparison_rule", "")):
        blockers.append("strict_comparison_rule_missing")
    if "activation is blocked" not in str(thresholds.get("unknown_broker_precision_rule", "")):
        blockers.append("unknown_precision_rule_missing")

    decisions = payload.get("breach_and_decision_rules", {})
    expected_numbers = {
        "minimum_relevant_event_count": 3,
        "minimum_distinct_symbol_count": 2,
        "minimum_calendar_days": 180,
        "maximum_calendar_days": 365,
    }
    for field, value in expected_numbers.items():
        if decisions.get(field) != value:
            blockers.append(f"decision_number_mismatch:{field}")
    decision_text = json.dumps(decisions, ensure_ascii=False)
    for required in (
        "One or more event-level breaches",
        "Never net opposite",
        "insufficient_operational_evidence",
        "do not extend automatically",
        "no_material_operational_discrepancy_observed_within_preregistered_scope",
        "material_operational_discrepancy_observed",
    ):
        if required not in decision_text:
            blockers.append(f"decision_rule_missing:{required}")

    prerequisites = payload.get("activation_prerequisites", [])
    if len(prerequisites) != 7:
        blockers.append("activation_prerequisite_inventory_mismatch")
    prerequisite_text = json.dumps(prerequisites, ensure_ascii=False)
    for required in ("separate owner-approved activation", "paper environment", "365-day stop", "no provider request"):
        if required not in prerequisite_text:
            blockers.append(f"activation_prerequisite_missing:{required}")

    stops = payload.get("stop_conditions", [])
    if len(stops) != 8:
        blockers.append("stop_condition_inventory_mismatch")
    stop_text = json.dumps(stops, ensure_ascii=False)
    for required in ("production or real-money", "validation prices or returns", "separate activation order", "365-day hard stop"):
        if required not in stop_text:
            blockers.append(f"stop_condition_missing:{required}")

    seal = payload.get("validation_return_seal", {})
    if seal.get("untouched_start") != "2016-01-04" or seal.get("untouched_end") != "2026-06-30":
        blockers.append("validation_window_mismatch")
    if seal.get("status") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
    for field in (
        "prices_opened",
        "adjusted_prices_opened",
        "returns_opened",
        "signals_opened",
        "positions_opened",
        "regimes_opened",
        "benchmarks_opened",
        "pnl_opened",
    ):
        if seal.get(field) is not False:
            blockers.append(f"validation_seal_false_field_mismatch:{field}")

    claim_text = json.dumps(payload.get("claim_limits", []), ensure_ascii=False)
    for required in (
        "not research ground truth",
        "cannot prove",
        "strategy edge",
        "E2 validation",
        "insufficient operational evidence",
    ):
        if required not in claim_text:
            blockers.append(f"claim_limit_missing:{required}")

    source_rows = payload.get("source_lineage", [])
    source_by_path = {row.get("path"): row for row in source_rows if isinstance(row, dict)}
    for relative, expected_hash in EXPECTED_SOURCE_HASHES.items():
        source = PROJECT_ROOT / relative
        if not source.is_file() or file_sha256(source) != expected_hash:
            blockers.append(f"source_file_hash_mismatch:{relative}")
        if source_by_path.get(relative, {}).get("sha256") != expected_hash:
            blockers.append(f"source_lineage_hash_mismatch:{relative}")

    if "B4.8 activation contract" not in str(payload.get("next_safe_action", "")):
        blockers.append("next_safe_action_mismatch")
    return _result(path, blockers)


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "preregistration_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Lily B4.7 shadow-accounting preregistration.")
    parser.add_argument("--preregistration", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    result = validate_preregistration(args.preregistration)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
