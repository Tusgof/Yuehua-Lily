"""CORE-1E-B2-R1 adapter for Lily's real normalized Yahoo schema.

The adapter accepts an already materialized mapping.  It does not resolve a
data root, open the future real container, call Yahoo, or inspect the sealed
validation window.  Its only numeric market-level decode is
``total_return_close``; the raw close, distribution, and split fields are
validated structurally and deliberately never used as return levels.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, time
from typing import Any, MutableMapping
from zoneinfo import ZoneInfo

from lib.core_1e_a_synthetic_engine import (
    CANDIDATES,
    DEVELOPMENT_END,
    NO_TRADE_BAND,
    PRIMARY_COMMISSION,
    PRIMARY_SELL_SURCHARGE,
    PRIMARY_SPREAD_SLIPPAGE,
    SLEEVE_WEIGHT,
    TRADING_SESSIONS_PER_YEAR,
    UNIVERSE,
    VALIDATION_END,
    VALIDATION_START,
    WARMUP_END,
    WARMUP_START,
    build_report as build_core_report,
    weekly_next_session_schedule,
)


ORDER_ID = "CORE-1E-B2-A"
WORK_ORDER_ID = "CORE-1E-B2-A-R1"
REPORT_SCHEMA_VERSION = "lily_core_1e_b2_empirical_report_v2"
NORMALIZED_SCHEMA_VERSION = "lily_l1_daily_dataset_v1"
SYMBOL_SCHEMA_VERSION = "lily_yahoo_daily_normalized_v1"
FIXTURE_PATH = "tests/fixtures/core1e_b2r1/normalized_market_v2.json"
POISON_FIXTURE_PATH = "tests/fixtures/core1e_b2r1/adversarial_post_cutoff_before_decode_v2.json"
NORMALIZED_SCHEMA_PATH = "schemas/core_1e_b2_normalized_container_v2.schema.json"
ENGINE_PATH = "lib/core_1e_a_synthetic_engine.py"
ADAPTER_PATH = "lib/core_1e_b2_empirical_adapter_v2.py"
YAHOO_NORMALIZER_PATH = "lib/yahoo_daily.py"
EXPENSE_INPUT_PATH = "experiments/inputs/core_1e_b2_expense_ratios_v1.json"
EXPENSE_INPUT_SCHEMA_VERSION = "lily_core_1e_etf_expense_input_v1"
EXPENSE_INPUT_ID = "core_1e_b2r1_etf_expense_ratios_v1"
EXPENSE_SOURCE_PATH = "lib/trend_baseline.py"
EXPENSE_SOURCE_SHA256 = "c2ea3a7462a88bb18bb3814d618f6738a9f1024c28cb5b50074184b05d648d28"
YAHOO_NORMALIZER_SHA256 = "c0e94c8e3b2dc11b4022ba6b93418c4d65a1305027d2bfe099c69e243b899417"
DEVELOPMENT_CUTOFF = DEVELOPMENT_END.isoformat()
VALIDATION_CUTOFF = VALIDATION_START.isoformat()
U8 = tuple(UNIVERSE)
YAHOO_NORMALIZER_CLOSE_TIME = time(16, 0)
YAHOO_NORMALIZER_TIMEZONE = ZoneInfo("America/New_York")
YAHOO_AVAILABILITY_TIMESTAMP_SEMANTICS = (
    "lib/yahoo_daily.py normalizer convention: fixed 16:00 America/New_York label for each session_date; "
    "conservative on exchange early-close sessions; not an assertion that every official NYSE close occurs at 16:00; "
    "timestamp date must equal session_date"
)

EXPENSE_RATIOS = {
    "VTI": 0.0003,
    "VGK": 0.0006,
    "EWJ": 0.005,
    "VWO": 0.0007,
    "IEF": 0.0015,
    "TIP": 0.0018,
    "GLD": 0.004,
    "DBC": 0.0085,
}
EXPENSE_LIMITATION = (
    "Current proxy expense ratios are not point-in-time historical observations; "
    "this limitation remains explicit in the future report contract."
)
ACCESS_COUNTS = {
    "real_dataset_access": 0,
    "real_container_access": 0,
    "real_return_decode": 0,
    "validation_access": 0,
    "provider_calls": 0,
    "credential_reads": 0,
    "broker_actions": 0,
    "paid_actions": 0,
}
VALIDATION_SEAL = {
    "start": VALIDATION_START.isoformat(),
    "end": VALIDATION_END.isoformat(),
    "status": "sealed_not_accessed",
    "accessed": False,
}
STOP_RULE = (
    "If no candidate passes every A-H gate, stop CORE-1 after CORE-1E, keep validation sealed, "
    "and require an owner/Inspector decision to reformulate or close this ETF trend family. "
    "No fourth candidate, parameter rescue, universe/date/timing/cost change, validation unlock, "
    "or remediation layering."
)

TOP_LEVEL_KEYS = {"schema_version", "acquired_at", "cutoff_inclusive", "symbols"}
SYMBOL_KEYS = {"schema_version", "provider", "symbol", "legal_inception", "coverage", "records", "limitations"}
COVERAGE_KEYS = {"start", "end"}
RECORD_KEYS = {
    "session_date",
    "availability_timestamp",
    "raw_close",
    "cash_distribution",
    "split",
    "total_return_close",
    "trading_currency",
    "provider_revision",
    "is_backfilled",
}


class DeferredNumber:
    """A JSON numeric token that has not yet been converted to a float."""

    __slots__ = ("token",)

    def __init__(self, token: str) -> None:
        self.token = token

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return f"DeferredNumber({self.token!r})"


def _defer_number(token: str) -> DeferredNumber:
    return DeferredNumber(token)


def _reject_constant(token: str) -> None:
    raise ValueError(f"nonfinite_json_number:{token}")


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def _parse_skeleton(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_closed_object,
            parse_int=_defer_number,
            parse_float=_defer_number,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("normalized_container_json_unreadable") from exc
    if not isinstance(value, dict):
        raise ValueError("normalized_container_must_be_object")
    return value


def _exact_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label}_must_be_object")
    unknown = sorted(set(value) - expected)
    missing = sorted(expected - set(value))
    if unknown:
        raise ValueError(f"{label}_unknown:{','.join(unknown)}")
    if missing:
        raise ValueError(f"{label}_missing:{','.join(missing)}")


def _check_iso_date(value: Any, label: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{label}_must_be_iso_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label}_must_be_iso_date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{label}_must_be_canonical_iso_date")
    return parsed


def _is_structural_number(value: Any) -> bool:
    if isinstance(value, DeferredNumber):
        return True
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _check_structural_number(value: Any, label: str, *, positive: bool = False, nonnegative: bool = False) -> None:
    if not _is_structural_number(value):
        raise ValueError(f"invalid_structural_number:{label}")
    if isinstance(value, DeferredNumber):
        return
    if positive and value <= 0.0:
        raise ValueError(f"invalid_structural_number:{label}")
    if nonnegative and value < 0.0:
        raise ValueError(f"invalid_structural_number:{label}")


def _check_availability(value: Any, session_date: date, label: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{label}_must_be_timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label}_must_be_timestamp") from exc
    if parsed.tzinfo is None or parsed.isoformat() != value:
        raise ValueError(f"{label}_must_be_offset_timestamp")
    normalizer_label = datetime.combine(session_date, YAHOO_NORMALIZER_CLOSE_TIME, YAHOO_NORMALIZER_TIMEZONE)
    if parsed != normalizer_label:
        raise ValueError(f"{label}_must_match_yahoo_normalizer_fixed_16_00_label")


def _check_acquired_at(value: Any) -> None:
    if not isinstance(value, str):
        raise ValueError("acquired_at_must_be_timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("acquired_at_must_be_timestamp") from exc
    if parsed.tzinfo is None or parsed.isoformat() != value:
        raise ValueError("acquired_at_must_be_offset_timestamp")


def preflight_normalized_payload(payload: Any) -> dict[str, Any]:
    """Validate every schema/date/timestamp field before return-number decode."""

    _exact_keys(payload, TOP_LEVEL_KEYS, "normalized_container")
    if payload.get("schema_version") != NORMALIZED_SCHEMA_VERSION:
        raise ValueError("normalized_schema_version_changed")
    _check_acquired_at(payload.get("acquired_at"))
    cutoff = _check_iso_date(payload.get("cutoff_inclusive"), "cutoff_inclusive")
    if cutoff != DEVELOPMENT_END:
        raise ValueError("top_level_cutoff_changed")

    symbols = payload.get("symbols")
    if not isinstance(symbols, list) or len(symbols) != len(U8):
        raise ValueError("normalized_symbols_must_contain_exact_u8")
    records_by_symbol: dict[str, dict[str, dict[str, Any]]] = {}
    dates_by_symbol: dict[str, list[str]] = {}
    availability_by_symbol: dict[str, dict[str, str]] = {}
    for position, symbol_payload in enumerate(symbols):
        _exact_keys(symbol_payload, SYMBOL_KEYS, f"symbol[{position}]")
        expected_symbol = U8[position]
        if symbol_payload.get("schema_version") != SYMBOL_SCHEMA_VERSION:
            raise ValueError(f"symbol_schema_version_changed:{expected_symbol}")
        if symbol_payload.get("provider") != "Yahoo Finance chart API":
            raise ValueError(f"symbol_provider_changed:{expected_symbol}")
        if symbol_payload.get("symbol") != expected_symbol:
            raise ValueError("normalized_symbols_membership_or_order_changed")
        legal_inception = _check_iso_date(symbol_payload.get("legal_inception"), f"{expected_symbol}.legal_inception")
        limitations = symbol_payload.get("limitations")
        if not isinstance(limitations, list) or not limitations or any(
            not isinstance(item, str) or not item for item in limitations
        ):
            raise ValueError(f"{expected_symbol}.limitations_invalid")
        coverage = symbol_payload.get("coverage")
        _exact_keys(coverage, COVERAGE_KEYS, f"{expected_symbol}.coverage")
        coverage_start = _check_iso_date(coverage.get("start"), f"{expected_symbol}.coverage.start")
        coverage_end = _check_iso_date(coverage.get("end"), f"{expected_symbol}.coverage.end")
        if coverage_start > coverage_end:
            raise ValueError(f"{expected_symbol}.coverage_order_invalid")
        records = symbol_payload.get("records")
        if not isinstance(records, list) or not records:
            raise ValueError(f"{expected_symbol}.records_must_be_nonempty")
        by_date: dict[str, dict[str, Any]] = {}
        ordered_dates: list[str] = []
        availability: dict[str, str] = {}
        for index, record in enumerate(records):
            _exact_keys(record, RECORD_KEYS, f"{expected_symbol}.record[{index}]")
            session_date = _check_iso_date(record.get("session_date"), f"{expected_symbol}.record[{index}].session_date")
            # This check intentionally occurs while values are still DeferredNumber
            # tokens.  A post-cutoff poison token can therefore never reach _number.
            if session_date > cutoff:
                raise ValueError("input_contains_date_after_2015-12-31")
            if session_date < legal_inception:
                raise ValueError(f"{expected_symbol}.record_before_legal_inception")
            if session_date.weekday() >= 5:
                raise ValueError(f"{expected_symbol}.weekend_session_date")
            if record["session_date"] in by_date:
                raise ValueError(f"{expected_symbol}.duplicate_session_date")
            if ordered_dates and session_date <= date.fromisoformat(ordered_dates[-1]):
                raise ValueError(f"{expected_symbol}.records_not_strictly_sorted")
            _check_availability(
                record.get("availability_timestamp"),
                session_date,
                f"{expected_symbol}.record[{index}].availability_timestamp",
            )
            _check_structural_number(record.get("raw_close"), f"{expected_symbol}.record[{index}].raw_close", positive=True)
            _check_structural_number(
                record.get("cash_distribution"),
                f"{expected_symbol}.record[{index}].cash_distribution",
                nonnegative=True,
            )
            split = record.get("split")
            if split is not None:
                _check_structural_number(split, f"{expected_symbol}.record[{index}].split", positive=True)
            _check_structural_number(
                record.get("total_return_close"),
                f"{expected_symbol}.record[{index}].total_return_close",
                positive=True,
            )
            if record.get("trading_currency") is not None and not isinstance(record.get("trading_currency"), str):
                raise ValueError(f"{expected_symbol}.trading_currency_invalid")
            if not isinstance(record.get("provider_revision"), str) or not record.get("provider_revision"):
                raise ValueError(f"{expected_symbol}.provider_revision_invalid")
            if not isinstance(record.get("is_backfilled"), bool):
                raise ValueError(f"{expected_symbol}.is_backfilled_invalid")
            by_date[record["session_date"]] = record
            ordered_dates.append(record["session_date"])
            availability[record["session_date"]] = record["availability_timestamp"]
        if coverage_start != date.fromisoformat(ordered_dates[0]) or coverage_end != date.fromisoformat(ordered_dates[-1]):
            raise ValueError(f"{expected_symbol}.coverage_does_not_match_records")
        if coverage_end > cutoff:
            raise ValueError("input_contains_date_after_2015-12-31")
        records_by_symbol[expected_symbol] = by_date
        dates_by_symbol[expected_symbol] = ordered_dates
        availability_by_symbol[expected_symbol] = availability

    common_dates = [
        session
        for session in dates_by_symbol[U8[0]]
        if all(session in records_by_symbol[symbol] for symbol in U8[1:])
    ]
    if not common_dates:
        raise ValueError("u8_common_session_intersection_empty")
    return {
        "session_dates": common_dates,
        "row_count": len(common_dates),
        "max_date": common_dates[-1],
        "records_by_symbol": records_by_symbol,
        "availability_by_symbol": availability_by_symbol,
        "dates_by_symbol": dates_by_symbol,
    }


def preflight_normalized_bytes(raw: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse with deferred numeric tokens and validate structure/date first."""

    payload = _parse_skeleton(raw)
    return payload, preflight_normalized_payload(payload)


def validate_expense_input(mapping: Any) -> list[str]:
    """Return blockers for the separate, source-bound expense input."""

    blockers: list[str] = []
    if not isinstance(mapping, dict):
        return ["expense_input_must_be_object"]
    expected = {
        "schema_version",
        "input_id",
        "status",
        "evidence_tier",
        "edge_claim",
        "source",
        "expense_ratios",
        "point_in_time",
        "current_proxy",
        "limitation",
    }
    blockers.extend(f"expense_input_unknown:{key}" for key in sorted(set(mapping) - expected))
    blockers.extend(f"expense_input_missing:{key}" for key in sorted(expected - set(mapping)))
    if blockers:
        return sorted(set(blockers))
    if mapping.get("schema_version") != EXPENSE_INPUT_SCHEMA_VERSION:
        blockers.append("expense_input_schema_version_changed")
    if mapping.get("input_id") != EXPENSE_INPUT_ID:
        blockers.append("expense_input_id_changed")
    if mapping.get("status") != "locked_before_execution" or mapping.get("evidence_tier") != "E0" or mapping.get("edge_claim") != "none":
        blockers.append("expense_input_claim_boundary_changed")
    source = mapping.get("source")
    if not isinstance(source, dict) or set(source) != {"path", "sha256", "symbol", "derivation"}:
        blockers.append("expense_input_source_shape_changed")
    else:
        if source.get("path") != EXPENSE_SOURCE_PATH:
            blockers.append("expense_input_source_path_changed")
        if source.get("sha256") != EXPENSE_SOURCE_SHA256:
            blockers.append("expense_input_source_hash_changed")
        if source.get("symbol") != "CURRENT_EXPENSE_RATIOS":
            blockers.append("expense_input_source_symbol_changed")
        if source.get("derivation") != "Exact values copied from the existing CURRENT_EXPENSE_RATIOS mapping; no values inferred.":
            blockers.append("expense_input_derivation_changed")
    ratios = mapping.get("expense_ratios")
    if not isinstance(ratios, dict) or set(ratios) != set(U8):
        blockers.append("expense_input_symbol_set_changed")
    else:
        for symbol in U8:
            value = ratios.get(symbol)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0.0:
                blockers.append(f"expense_input_invalid_ratio:{symbol}")
            elif value != EXPENSE_RATIOS[symbol]:
                blockers.append(f"expense_input_ratio_changed:{symbol}")
    if mapping.get("point_in_time") is not False:
        blockers.append("expense_input_point_in_time_claim_changed")
    if mapping.get("current_proxy") is not True:
        blockers.append("expense_input_current_proxy_claim_changed")
    if mapping.get("limitation") != EXPENSE_LIMITATION:
        blockers.append("expense_input_limitation_changed")
    return sorted(set(blockers))


def expense_ratios_from_input(mapping: Any) -> dict[str, float]:
    blockers = validate_expense_input(mapping)
    if blockers:
        raise ValueError("expense_input_invalid:" + ",".join(blockers))
    return {symbol: float(mapping["expense_ratios"][symbol]) for symbol in U8}


def _number(
    value: Any,
    *,
    label: str,
    decode_counter: MutableMapping[str, int] | None,
) -> float:
    raw_numeric = value.token if isinstance(value, DeferredNumber) else value
    try:
        converted = float(raw_numeric)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"invalid_total_return_close:{label}") from exc
    if not math.isfinite(converted) or converted <= 0.0:
        raise ValueError(f"invalid_total_return_close:{label}")
    if decode_counter is not None:
        decode_counter["count"] = decode_counter.get("count", 0) + 1
    return converted


def decode_normalized_container(
    payload: dict[str, Any],
    expense_input: dict[str, Any] | None = None,
    *,
    expense_mapping: dict[str, Any] | None = None,
    decode_counter: MutableMapping[str, int] | None = None,
) -> dict[str, Any]:
    """Project only total-return levels into the accepted A-engine fixture."""

    if expense_input is not None and expense_mapping is not None:
        raise ValueError("expense_input_ambiguous")
    selected_expense_input = expense_input if expense_input is not None else expense_mapping
    if selected_expense_input is None:
        raise ValueError("separate_expense_input_required")
    metadata = preflight_normalized_payload(payload)
    expenses = expense_ratios_from_input(selected_expense_input)
    closes = {symbol: [] for symbol in U8}
    for session_date in metadata["session_dates"]:
        for symbol in U8:
            closes[symbol].append(
                _number(
                    metadata["records_by_symbol"][symbol][session_date]["total_return_close"],
                    label=f"{symbol}:{session_date}:total_return_close",
                    decode_counter=decode_counter,
                )
            )
    return {
        "schema_version": "lily_core_1e_a_synthetic_market_v1",
        "fixture_id": "core1e_a_synthetic_market_v1",
        "session_dates": list(metadata["session_dates"]),
        "closes": closes,
        "expense_ratios": expenses,
    }


def decode_normalized_bytes(
    raw: bytes,
    expense_input: dict[str, Any] | None = None,
    *,
    expense_mapping: dict[str, Any] | None = None,
    decode_counter: MutableMapping[str, int] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, metadata = preflight_normalized_bytes(raw)
    return (
        decode_normalized_container(
            payload,
            expense_input,
            expense_mapping=expense_mapping,
            decode_counter=decode_counter,
        ),
        metadata,
    )


def _compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in candidate.items() if key != "attribution"}


def _timing_attestation(metadata: dict[str, Any], schedule: list[dict[str, Any]]) -> dict[str, Any]:
    pairs: list[dict[str, Any]] = []
    all_available = True
    all_next = True
    for item in schedule:
        decision = item["decision_date"]
        decision_close = datetime.combine(
            date.fromisoformat(decision),
            YAHOO_NORMALIZER_CLOSE_TIME,
            YAHOO_NORMALIZER_TIMEZONE,
        )
        availability = {
            symbol: metadata["availability_by_symbol"][symbol][decision]
            for symbol in U8
        }
        available = all(datetime.fromisoformat(value) <= decision_close for value in availability.values())
        next_session = item["execution_index"] == item["decision_index"] + 1
        all_available = all_available and available
        all_next = all_next and next_session
        pairs.append(
            {
                "decision_index": item["decision_index"],
                "execution_index": item["execution_index"],
                "decision_date": decision,
                "execution_date": item["execution_date"],
                "decision_close_timestamp": decision_close.isoformat(),
                "availability_timestamps": availability,
                "data_available_at_decision_close": available,
                "execution_is_next_common_session": next_session,
                "same_close_pnl": False,
            }
        )
    return {
        "weekly_decisions": len(schedule),
        "all_execution_dates_after_decisions": all(item["execution_index"] > item["decision_index"] for item in schedule),
        "same_close_execution": False,
        "manufactured_sessions": False,
        "lookahead_detected": False,
        "common_session_count": metadata["row_count"],
        "availability_timestamp_semantics": YAHOO_AVAILABILITY_TIMESTAMP_SEMANTICS,
        "availability_validated": True,
        "decisions_use_only_data_available_at_weekly_decision_close": all_available,
        "execution_uses_next_u8_common_nyse_session_close": all_next,
        "pnl_starts_after_execution_close": True,
        "same_close_pnl": False,
        "decision_execution_pairs": pairs,
    }


def build_empirical_report(
    normalized: dict[str, Any],
    expense_input: dict[str, Any] | None = None,
    *,
    expense_mapping: dict[str, Any] | None = None,
    contract_sha256: str,
    fixture_sha256: str,
    expense_input_sha256: str,
    producing_commit: str,
    engine_sha256: str,
    adapter_sha256: str,
    yahoo_normalizer_sha256: str = YAHOO_NORMALIZER_SHA256,
    stop_rule: str = STOP_RULE,
) -> dict[str, Any]:
    """Build the E0 report through the accepted A calculation kernel."""

    if expense_input is not None and expense_mapping is not None:
        raise ValueError("expense_input_ambiguous")
    selected_expense_input = expense_input if expense_input is not None else expense_mapping
    if selected_expense_input is None:
        raise ValueError("separate_expense_input_required")
    metadata = preflight_normalized_payload(normalized)
    fixture = decode_normalized_container(normalized, selected_expense_input)
    calculation = build_core_report(
        fixture,
        contract_sha256=contract_sha256,
        fixture_sha256=fixture_sha256,
        producing_commit=producing_commit,
        engine_sha256=engine_sha256,
        stop_rule=stop_rule,
    )
    schedule = weekly_next_session_schedule(fixture["session_dates"])
    expense_ratios_from_input(selected_expense_input)
    locked_inputs = {
        "universe_symbols_in_order": list(U8),
        "candidate_ids_in_order": list(CANDIDATES),
        "candidate_lookbacks_complete_sessions": {
            "CORE1_DC60": 60,
            "CORE1_DC120": 120,
            "CORE1_SMA200": 200,
        },
        "fixed_sleeve_weight": SLEEVE_WEIGHT,
        "no_trade_band": NO_TRADE_BAND,
        "primary_execution_costs": {
            "commission_one_way_traded_notional": PRIMARY_COMMISSION,
            "spread_slippage_one_way": PRIMARY_SPREAD_SLIPPAGE,
            "sell_surcharge": PRIMARY_SELL_SURCHARGE,
        },
        "stress_execution_multiplier": 2.0,
        "stress_expense_multiplier": 1.0,
        "etf_expense_accrual": f"annual_ratio_divided_by_{TRADING_SESSIONS_PER_YEAR}_on_held_notional",
        "benchmark_id": "equal_weight_always_long_fixed_sleeves",
        "gate_ids": list("ABCDEFGH"),
        "selection_rule": "discard_failed_candidates_then_highest_worst_subperiod_sharpe_with_locked_near_tie_turnover_rule",
        "stop_rule": stop_rule,
    }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "order_id": ORDER_ID,
        "work_order_id": WORK_ORDER_ID,
        "status": "synthetic_completed",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "result_kind": "synthetic_fixture_only",
        "empirical_result_created": False,
        "contract_sha256": contract_sha256,
        "source": {
            "path": FIXTURE_PATH,
            "sha256": fixture_sha256,
            "schema_version": NORMALIZED_SCHEMA_VERSION,
            "symbol_schema_version": SYMBOL_SCHEMA_VERSION,
            "cutoff_inclusive": DEVELOPMENT_CUTOFF,
            "common_session_count": metadata["row_count"],
            "max_common_session_date": metadata["max_date"],
            "symbols_in_order": list(U8),
        },
        "expense_input": {
            "path": EXPENSE_INPUT_PATH,
            "sha256": expense_input_sha256,
            "input_id": EXPENSE_INPUT_ID,
            "source_path": EXPENSE_SOURCE_PATH,
            "source_sha256": EXPENSE_SOURCE_SHA256,
            "current_proxy": True,
            "point_in_time": False,
            "limitation": EXPENSE_LIMITATION,
        },
        "windows": calculation["windows"],
        "timing_attestation": _timing_attestation(metadata, schedule),
        "calculation_attestation": calculation["calculation_attestation"],
        "locked_inputs": locked_inputs,
        "trial_inventory": calculation["trial_inventory"],
        "trial_statistics": calculation["trial_statistics"],
        "candidates": [_compact_candidate(item) for item in calculation["candidates"]],
        "benchmark": calculation["benchmark"],
        "selection": calculation["selection"],
        "access_counts": dict(ACCESS_COUNTS),
        "validation_seal": dict(VALIDATION_SEAL),
        "lifecycle": {
            "marker_first": True,
            "input_read_count": 1,
            "expense_input_read_count": 1,
            "temporary_git_proof": True,
            "project_artifacts_created": False,
            "real_data_accessed": False,
            "validation_accessed": False,
            "second_execution_refused": False,
        },
        "provenance": {
            "producing_commit": producing_commit,
            "contract_sha256": contract_sha256,
            "engine_path": ENGINE_PATH,
            "engine_sha256": engine_sha256,
            "adapter_path": ADAPTER_PATH,
            "adapter_sha256": adapter_sha256,
            "yahoo_normalizer_path": YAHOO_NORMALIZER_PATH,
            "yahoo_normalizer_sha256": yahoo_normalizer_sha256,
            "expense_input_path": EXPENSE_INPUT_PATH,
            "expense_input_sha256": expense_input_sha256,
            "source_kind": "committed_synthetic_fixture_only",
        },
    }


adapt_normalized_container = decode_normalized_container
build_synthetic_report = build_empirical_report
