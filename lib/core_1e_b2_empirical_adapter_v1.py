"""Minimal CORE-1E-B2 normalized-container adapter.

The adapter is deliberately narrower than a data loader.  It accepts only the
closed synthetic normalized-container shape declared by the B2 contract,
checks every row date before converting any return number, and then projects
``total_return_close`` into the already accepted CORE-1E-A engine input.  It
does not resolve a project data root, open a real container, call a provider,
or know how to open the sealed validation window.
"""

from __future__ import annotations

import json
import math
from datetime import date
from typing import Any, MutableMapping

from lib.core_1e_a_synthetic_engine import (
    DEVELOPMENT_END,
    VALIDATION_END,
    VALIDATION_START,
    WARMUP_END,
    WARMUP_START,
    UNIVERSE,
    build_report as build_core_report,
)


REPORT_SCHEMA_VERSION = "lily_core_1e_b2_empirical_report_v1"
NORMALIZED_SCHEMA_VERSION = "lily_l1_yahoo_daily_v1"
NORMALIZED_CONTAINER_ID = "l1_yahoo_daily_v1"
FIXTURE_PATH = "tests/fixtures/core1e_b2/normalized_market_v1.json"
NORMALIZED_SCHEMA_PATH = "schemas/core_1e_b2_normalized_container_v1.schema.json"
ENGINE_PATH = "lib/core_1e_a_synthetic_engine.py"
ADAPTER_PATH = "lib/core_1e_b2_empirical_adapter_v1.py"
DEVELOPMENT_CUTOFF = DEVELOPMENT_END.isoformat()
VALIDATION_CUTOFF = VALIDATION_START.isoformat()
U8 = tuple(UNIVERSE)

TOP_LEVEL_KEYS = {
    "schema_version",
    "container_id",
    "symbols_in_order",
    "rows",
    "expense_ratios",
}
ROW_KEYS = {"session_date", "observations"}
OBSERVATION_KEYS = {"total_return_close"}

VALIDATION_SEAL = {
    "start": "2016-01-04",
    "end": "2026-06-30",
    "status": "sealed_not_accessed",
    "accessed": False,
}
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
STOP_RULE = (
    "If no candidate passes every A-H gate, stop CORE-1 after CORE-1E, keep validation sealed, "
    "and require an owner/Inspector decision to reformulate or close this ETF trend family. "
    "No fourth candidate, parameter rescue, universe/date/cost change, or validation unlock."
)


class DeferredNumber:
    """A JSON number token that has not yet been converted to a float."""

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
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing:
        raise ValueError(f"{label}_missing:{','.join(missing)}")
    if unknown:
        raise ValueError(f"{label}_unknown:{','.join(unknown)}")


def _check_session_date(value: Any, index: int) -> date:
    if not isinstance(value, str):
        raise ValueError(f"invalid_session_date:{index}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid_session_date:{index}") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"noncanonical_session_date:{index}")
    if parsed.weekday() >= 5:
        raise ValueError(f"weekend_session_date:{value}")
    if parsed < WARMUP_START:
        raise ValueError("input_precedes_warmup_start")
    if parsed > DEVELOPMENT_END:
        # This check is intentionally made while values are still deferred.
        raise ValueError("input_contains_date_after_2015-12-31")
    if VALIDATION_START <= parsed <= VALIDATION_END:
        raise ValueError("input_contains_validation_date")
    return parsed


def preflight_normalized_payload(payload: Any) -> dict[str, Any]:
    """Validate structure and every session date without decoding returns.

    The returned metadata contains only dates and structural counts.  In
    particular, no ``total_return_close`` value or expense-ratio number is
    converted or inspected for numeric validity here.
    """

    _exact_keys(payload, TOP_LEVEL_KEYS, "normalized_container")
    if payload.get("schema_version") != NORMALIZED_SCHEMA_VERSION:
        raise ValueError("normalized_schema_version_changed")
    if payload.get("container_id") != NORMALIZED_CONTAINER_ID:
        raise ValueError("normalized_container_id_changed")
    if payload.get("symbols_in_order") != list(U8):
        raise ValueError("normalized_universe_order_changed")

    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("normalized_rows_must_be_nonempty_list")
    expenses = payload.get("expense_ratios")
    _exact_keys(expenses, set(U8), "expense_ratios")

    # Date/cutoff checks are a separate first pass.  This is the key safety
    # boundary: a later post-cutoff row fails before any return token is
    # converted by decode_normalized_container().
    parsed_dates: list[date] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"row_must_be_object:{index}")
        parsed_dates.append(_check_session_date(row.get("session_date"), index))
    if parsed_dates != sorted(set(parsed_dates)):
        raise ValueError("session_dates_must_be_strictly_sorted_unique")

    # Only after every date has passed do we inspect the non-value structure.
    for index, row in enumerate(rows):
        _exact_keys(row, ROW_KEYS, f"row:{index}")
        observations = row.get("observations")
        _exact_keys(observations, set(U8), f"row_observations:{index}")
        for symbol in U8:
            _exact_keys(observations[symbol], OBSERVATION_KEYS, f"observation:{index}:{symbol}")

    return {
        "session_dates": [item.isoformat() for item in parsed_dates],
        "max_date": parsed_dates[-1].isoformat(),
        "row_count": len(rows),
    }


def preflight_normalized_bytes(raw: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse only deferred JSON numbers, then perform structural/date checks."""

    skeleton = _parse_skeleton(raw)
    metadata = preflight_normalized_payload(skeleton)
    return skeleton, metadata


def _number(value: Any, *, label: str, positive: bool, decode_counter: MutableMapping[str, int] | None) -> float:
    if decode_counter is not None:
        decode_counter["count"] = decode_counter.get("count", 0) + 1
    raw_value = value
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float, DeferredNumber)):
        raise ValueError(f"invalid_number:{label}")
    converted_input = raw_value.token if isinstance(raw_value, DeferredNumber) else raw_value
    try:
        converted = float(converted_input)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"invalid_number:{label}") from exc
    if not math.isfinite(converted) or (positive and converted <= 0.0) or (not positive and converted < 0.0):
        raise ValueError(f"invalid_number:{label}")
    return converted


def decode_normalized_container(
    payload: dict[str, Any],
    *,
    decode_counter: MutableMapping[str, int] | None = None,
) -> dict[str, Any]:
    """Convert a validated normalized payload into the accepted A-engine input."""

    metadata = preflight_normalized_payload(payload)
    rows = payload["rows"]
    closes = {symbol: [] for symbol in U8}
    for index, row in enumerate(rows):
        observations = row["observations"]
        for symbol in U8:
            closes[symbol].append(
                _number(
                    observations[symbol]["total_return_close"],
                    label=f"{index}:{symbol}:total_return_close",
                    positive=True,
                    decode_counter=decode_counter,
                )
            )
    expense_ratios = {
        symbol: _number(
            payload["expense_ratios"][symbol],
            label=f"expense_ratios:{symbol}",
            positive=False,
            decode_counter=decode_counter,
        )
        for symbol in U8
    }
    return {
        "schema_version": "lily_core_1e_a_synthetic_market_v1",
        "fixture_id": "core1e_a_synthetic_market_v1",
        "session_dates": list(metadata["session_dates"]),
        "closes": closes,
        "expense_ratios": expense_ratios,
    }


def decode_normalized_bytes(
    raw: bytes,
    *,
    decode_counter: MutableMapping[str, int] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the date-first preflight and only then decode return values."""

    payload, metadata = preflight_normalized_bytes(raw)
    return decode_normalized_container(payload, decode_counter=decode_counter), metadata


def _compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    # The engine's daily attribution is a useful internal reconciliation but is
    # not needed for the B2 decision contract.  Aggregate contributions,
    # concentration, costs, gates, and every reported metric remain intact.
    return {key: value for key, value in candidate.items() if key != "attribution"}


def build_empirical_report(
    normalized: dict[str, Any],
    *,
    contract_sha256: str,
    fixture_sha256: str,
    producing_commit: str,
    engine_sha256: str,
    adapter_sha256: str,
    stop_rule: str = STOP_RULE,
) -> dict[str, Any]:
    """Build an E0 machinery report through the accepted A engine."""

    metadata = preflight_normalized_payload(normalized)
    fixture = decode_normalized_container(normalized)
    calculation = build_core_report(
        fixture,
        contract_sha256=contract_sha256,
        fixture_sha256=fixture_sha256,
        producing_commit=producing_commit,
        engine_sha256=engine_sha256,
        stop_rule=stop_rule,
    )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "order_id": "CORE-1E-B2-A",
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
            "container_id": NORMALIZED_CONTAINER_ID,
            "max_date": metadata["max_date"],
            "row_count": metadata["row_count"],
            "symbols_in_order": list(U8),
            "expense_ratios": dict(fixture["expense_ratios"]),
        },
        "windows": calculation["windows"],
        "timing_attestation": calculation["timing_attestation"],
        "calculation_attestation": calculation["calculation_attestation"],
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
            "source_kind": "committed_synthetic_fixture_only",
        },
    }


adapt_normalized_container = decode_normalized_container
build_synthetic_report = build_empirical_report
