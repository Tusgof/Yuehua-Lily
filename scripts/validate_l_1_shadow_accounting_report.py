from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root


EXPECTED_PAIRS = [
    "webull_vs_alpha_vantage",
    "webull_vs_lily_yahoo",
    "alpha_vantage_vs_lily_yahoo",
]
EXPECTED_EVENT_TYPES = {"cash_dividend", "capital_gains_distribution", "stock_split", "reverse_split"}
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DIMENSION_ORDER = [
    "cash_balance_difference",
    "unit_balance_difference",
    "target_weight_tracking_difference",
    "hypothetical_order_notional_difference",
    "event_detection_or_posting_delay",
]


def validate_report(path: Path) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        report = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"report_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l1_shadow_accounting_report_v1",
        "hypothesis_id": "L-1",
        "evidence_tier": "E0",
        "edge_claim": "none",
    }
    for field, value in expected.items():
        if report.get(field) != value:
            blockers.append(f"field_mismatch:{field}")
    if report.get("report_mode") not in {"synthetic_fixture", "prospective_observation"}:
        blockers.append("invalid_report_mode")

    attestation = report.get("request_attestation", {})
    for field in ("production_broker_calls", "preview_calls", "order_endpoint_calls", "orders_sent", "paid_spend_usd"):
        if attestation.get(field) != 0:
            blockers.append(f"request_attestation_must_be_zero:{field}")
    _validate_seal(report.get("validation_return_seal", {}), blockers)

    events = report.get("events", [])
    if not isinstance(events, list):
        blockers.append("events_must_be_list")
        events = []
    decision = report.get("decision")
    activation_blockers = report.get("activation_blockers", [])
    if decision == "activation_blocked_before_observation":
        _validate_blocked_report(report, events, activation_blockers, blockers)
        return _result(path, blockers)

    start = _parse_date(report.get("observation_start"), "observation_start", blockers)
    end = _parse_date(report.get("observation_end"), "observation_end", blockers)
    elapsed = (end - start).days if start is not None and end is not None and end >= start else None
    if start is not None and end is not None and end < start:
        blockers.append("observation_end_before_start")
    quantum = report.get("broker_fractional_quantum")
    if not isinstance(quantum, (int, float)) or isinstance(quantum, bool) or quantum <= 0:
        blockers.append("broker_fractional_quantum_missing_or_invalid")
        quantum = 0.0001
    for field in ("event_ledger_sha256", "container_registry_sha256"):
        if not HASH_PATTERN.fullmatch(str(report.get(field, ""))):
            blockers.append(f"invalid_hash:{field}")
    if activation_blockers != []:
        blockers.append("nonblocked_report_has_activation_blockers")

    event_breach_count = 0
    symbols: set[str] = set()
    seen_ids: set[str] = set()
    for index, event in enumerate(events):
        label = f"event_{index + 1}"
        if not isinstance(event, dict):
            blockers.append(f"{label}:must_be_object")
            continue
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id or event_id in seen_ids:
            blockers.append(f"{label}:invalid_or_duplicate_event_id")
        else:
            seen_ids.add(event_id)
        symbol = event.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            blockers.append(f"{label}:invalid_symbol")
        else:
            symbols.add(symbol)
        if event.get("event_type") not in EXPECTED_EVENT_TYPES:
            blockers.append(f"{label}:invalid_event_type")
        nav = event.get("reference_nav_usd")
        if not isinstance(nav, (int, float)) or isinstance(nav, bool) or nav <= 0:
            blockers.append(f"{label}:invalid_reference_nav")
            continue
        comparisons = event.get("comparisons", [])
        if not isinstance(comparisons, list) or [row.get("stream_pair") for row in comparisons if isinstance(row, dict)] != EXPECTED_PAIRS:
            blockers.append(f"{label}:comparison_pair_inventory_mismatch")
            continue
        event_has_breach = False
        for comparison in comparisons:
            pair = str(comparison["stream_pair"])
            expected_dimensions = _material_dimensions(comparison, float(nav), float(quantum), pair, blockers, label)
            if comparison.get("reported_material_dimensions") != expected_dimensions:
                blockers.append(f"{label}:{pair}:material_dimension_mismatch")
            event_has_breach = event_has_breach or bool(expected_dimensions)
        if event.get("reported_event_breach") is not event_has_breach:
            blockers.append(f"{label}:event_breach_mismatch")
        if event_has_breach:
            event_breach_count += 1

    summary = report.get("summary", {})
    expected_summary = {
        "elapsed_calendar_days": elapsed,
        "relevant_event_count": len(events),
        "distinct_symbol_count": len(symbols),
        "event_breach_count": event_breach_count,
    }
    if summary != expected_summary:
        blockers.append("summary_mismatch")

    expected_decision: str | None
    if event_breach_count:
        expected_decision = "material_operational_discrepancy_observed"
    elif elapsed is not None and elapsed >= 365 and (len(events) < 3 or len(symbols) < 2):
        expected_decision = "insufficient_operational_evidence"
    elif elapsed is not None and elapsed >= 180 and len(events) >= 3 and len(symbols) >= 2:
        expected_decision = "no_material_operational_discrepancy_observed_within_preregistered_scope"
    else:
        expected_decision = None
    if expected_decision is None:
        blockers.append("report_before_preregistered_decision_gate")
    elif decision != expected_decision:
        blockers.append(f"decision_mismatch:expected_{expected_decision}")
    return _result(path, blockers)


def _material_dimensions(
    comparison: dict[str, Any],
    nav: float,
    quantum: float,
    pair: str,
    blockers: list[str],
    label: str,
) -> list[str]:
    numeric_fields = (
        "cash_difference_usd",
        "unit_difference",
        "target_weight_tracking_difference",
        "order_notional_difference_usd",
    )
    values: dict[str, float] = {}
    for field in numeric_fields:
        value = comparison.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            blockers.append(f"{label}:{pair}:invalid_numeric_field:{field}")
            value = 0.0
        values[field] = abs(float(value))
    delay = comparison.get("posting_delay_us_sessions")
    if pair == "alpha_vantage_vs_lily_yahoo":
        if delay is not None:
            blockers.append(f"{label}:{pair}:posting_delay_must_be_null")
        delay_breach = False
    else:
        if not isinstance(delay, int) or isinstance(delay, bool) or delay < 0:
            blockers.append(f"{label}:{pair}:invalid_posting_delay")
            delay = 0
        delay_breach = delay > 2
    checks = {
        "cash_balance_difference": values["cash_difference_usd"] > max(1.0, 0.0005 * nav),
        "unit_balance_difference": values["unit_difference"] > max(0.0001, quantum),
        "target_weight_tracking_difference": values["target_weight_tracking_difference"] > 0.001,
        "hypothetical_order_notional_difference": values["order_notional_difference_usd"] > max(1.0, 0.001 * nav),
        "event_detection_or_posting_delay": delay_breach,
    }
    return [name for name in DIMENSION_ORDER if checks[name]]


def _validate_blocked_report(
    report: dict[str, Any],
    events: list[Any],
    activation_blockers: Any,
    blockers: list[str],
) -> None:
    for field in ("observation_start", "observation_end", "broker_fractional_quantum", "event_ledger_sha256", "container_registry_sha256"):
        if report.get(field) is not None:
            blockers.append(f"blocked_report_field_must_be_null:{field}")
    if events:
        blockers.append("blocked_report_must_have_no_events")
    if not isinstance(activation_blockers, list) or not activation_blockers:
        blockers.append("blocked_report_requires_activation_blocker")
    if report.get("summary") != {"elapsed_calendar_days": 0, "relevant_event_count": 0, "distinct_symbol_count": 0, "event_breach_count": 0}:
        blockers.append("blocked_report_summary_mismatch")


def _validate_seal(seal: dict[str, Any], blockers: list[str]) -> None:
    if seal.get("status") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
    for field in ("prices_opened", "returns_opened", "signals_opened", "positions_opened", "regimes_opened", "benchmarks_opened", "pnl_opened"):
        if seal.get(field) is not False:
            blockers.append(f"validation_seal_false_field_mismatch:{field}")


def _parse_date(value: Any, field: str, blockers: list[str]) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        blockers.append(f"invalid_date:{field}")
        return None


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "report_path": relative_to_root(path, PROJECT_ROOT)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an L-1 prospective shadow-accounting report.")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate_report(args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
