"""Hermetic B7.8 structural contracts; this module has no container I/O."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from typing import Any

ASSETS = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
START = "2007-02-05"
END = "2015-12-31"
VALIDATION = "2016-01-04"
_ENVELOPE_KEYS = {"schema_version", "acquired_at", "cutoff_inclusive", "symbols"}
_RECORD_KEYS = {"session_date", "availability_timestamp", "total_return_close"}
_ROW_KEYS = {
    "date", "weights", "commission", "spread_slippage", "sell_surcharge",
    "cap_binding", "excess_cash", "scale_down", "pre_scale_volatility", "target_volatility",
}


def _finite_number(value: Any, *, nonnegative: bool = False) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and (not nonnegative or value >= 0)


def scan_synthetic_envelope(envelope: Any) -> dict[str, Any]:
    """Validate exact synthetic date structure without inspecting return values.

    Metadata timestamps are intentionally ignored.  The function has neither a
    path argument nor a hashing/container API, so it cannot be used on a real
    data container by this E0 order.
    """
    blockers: list[str] = []
    sessions: dict[str, list[str]] = {}
    if not isinstance(envelope, dict) or set(envelope) != _ENVELOPE_KEYS:
        return {"status": "blocked", "blockers": ["envelope_shape"], "return_values_exposed": False}
    if envelope["schema_version"] != "lily_l1_daily_dataset_v1":
        blockers.append("schema_version_mismatch")
    if envelope["cutoff_inclusive"] != END:
        blockers.append("cutoff_inclusive_mismatch")
    symbols = envelope["symbols"]
    if not isinstance(symbols, list) or len(symbols) != len(ASSETS):
        blockers.append("symbol_count_mismatch")
        symbols = []
    names = [row.get("symbol") for row in symbols if isinstance(row, dict)]
    if names != list(ASSETS):
        blockers.append("symbol_identity_or_order_mismatch")
    for item in symbols:
        if not isinstance(item, dict) or set(item) != {"symbol", "records"}:
            blockers.append("symbol_shape_mismatch")
            continue
        symbol, records = item["symbol"], item["records"]
        if not isinstance(symbol, str) or not isinstance(records, list):
            blockers.append("records_shape_mismatch")
            continue
        dates: list[str] = []
        for record in records:
            if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
                blockers.append("record_shape_mismatch")
                continue
            session = record["session_date"]
            if not isinstance(session, str):
                blockers.append("session_date_invalid")
                continue
            try:
                date.fromisoformat(session)
            except ValueError:
                blockers.append("session_date_invalid")
                continue
            # These hard stops are evaluated for every symbol before any
            # intersection. availability_timestamp and total_return_close stay unread.
            if session in {END, VALIDATION}:
                blockers.append("forbidden_boundary_session_before_intersection")
            dates.append(session)
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            blockers.append("per_symbol_sessions_not_strictly_monotonic")
        sessions[symbol] = dates
    common = sorted(set.intersection(*(set(sessions.get(asset, [])) for asset in ASSETS))) if set(sessions) == set(ASSETS) else []
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "assets": list(ASSETS),
        "common_session_count": len(common),
        "common_sessions": common,
        "return_values_exposed": False,
    }


def canonical_schedule_sha256(decisions: list[str]) -> str:
    """Hash only canonical selected decision dates, per the B7.5 contract."""
    return hashlib.sha256(json.dumps({"selected_decision_dates": decisions}, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_canonical_schedule(common_sessions: list[str], selected_decision_dates: list[str] | None = None) -> dict[str, Any]:
    """Select the final eligible session in each ISO week and require complete t+20."""
    blockers: list[str] = []
    if not isinstance(common_sessions, list) or any(not isinstance(item, str) for item in common_sessions):
        return {"status": "blocked", "blockers": ["common_sessions_shape"]}
    parsed: list[date] = []
    for item in common_sessions:
        try:
            parsed.append(date.fromisoformat(item))
        except ValueError:
            blockers.append("common_session_invalid")
    if common_sessions != sorted(common_sessions) or len(common_sessions) != len(set(common_sessions)):
        blockers.append("common_sessions_not_strictly_monotonic")
    if any(item >= VALIDATION for item in common_sessions):
        blockers.append("mixed_validation_session_hard_stop")
    eligible = [item for item in common_sessions if START <= item <= END]
    candidate_decisions: list[str] = []
    for item in eligible:
        week = date.fromisoformat(item).isocalendar()[:2]
        if not candidate_decisions or date.fromisoformat(candidate_decisions[-1]).isocalendar()[:2] != week:
            candidate_decisions.append(item)
        else:
            candidate_decisions[-1] = item
    if len(candidate_decisions) > 465:
        blockers.append("weekly_observation_ceiling_exceeded")
    decisions: list[str] = []
    executions: list[str] = []
    confirmations: list[str] = []
    supplied = selected_decision_dates is not None
    if supplied and (not isinstance(selected_decision_dates, list) or selected_decision_dates != sorted(selected_decision_dates) or len(selected_decision_dates) != len(set(selected_decision_dates))):
        blockers.append("duplicate_or_noncanonical_week")
        selected_decision_dates = []
    decisions_to_check = selected_decision_dates if supplied else candidate_decisions
    if supplied and selected_decision_dates != candidate_decisions:
        blockers.append("noncanonical_weekly_selection")
    for decision in decisions_to_check:
        if decision not in common_sessions or decision < START or decision > END:
            blockers.append("decision_outside_falsification_window")
            continue
        index = common_sessions.index(decision)
        if index + 20 >= len(common_sessions) or common_sessions[index + 20] > END:
            if supplied:
                blockers.append("incomplete_t_plus_20_interval")
            continue
        decisions.append(decision)
        executions.append(common_sessions[index + 1])
        confirmations.append(common_sessions[index + 20])
    if candidate_decisions and candidate_decisions[0] < START:
        blockers.append("pre_start_weekly_decision")
    if any(execution <= decision for decision, execution in zip(decisions, executions, strict=True)):
        blockers.append("execution_not_next_eligible_session")
    if any(end > END for end in confirmations):
        blockers.append("incomplete_t_plus_20_interval")
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "candidate_week_count": len(candidate_decisions),
        "first_eligible_session": eligible[0] if eligible else None,
        "falsification_end": END,
        "all_confirmations_within_falsification_end": all(item <= END for item in confirmations),
        "selected_decision_dates": decisions,
        "execution_dates": executions,
        "realized_confirmation_end_dates": confirmations,
        "schedule_sha256": canonical_schedule_sha256(decisions),
    }


def derive_side_effects(candidate: Any, comparator: Any) -> dict[str, Any]:
    """Derive L1 components, turnover, and constraints from exact paired diagnostics."""
    def branch(rows: Any) -> tuple[dict[str, Any] | None, str | None]:
        if not isinstance(rows, list) or not rows:
            return None, "missing_diagnostics"
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != _ROW_KEYS:
                return None, "diagnostic_shape"
            if not isinstance(row["date"], str):
                return None, "date_type"
            try:
                date.fromisoformat(row["date"])
            except ValueError:
                return None, "date_type"
            if not isinstance(row["weights"], dict) or set(row["weights"]) != set(ASSETS):
                return None, "weight_shape"
            if not all(_finite_number(value, nonnegative=True) for value in row["weights"].values()):
                return None, "weight_values"
            if not all(_finite_number(row[key], nonnegative=True) for key in ("commission", "spread_slippage", "sell_surcharge", "pre_scale_volatility")) or not _finite_number(row["target_volatility"], nonnegative=True) or row["target_volatility"] == 0:
                return None, "nonfinite_or_negative_component"
            if not all(type(row[key]) is bool for key in ("cap_binding", "excess_cash", "scale_down")):
                return None, "boolean_type"
            cap = any(weight >= 0.25 for weight in row["weights"].values())
            cash = sum(row["weights"].values()) < 0.90
            scale = row["pre_scale_volatility"] > row["target_volatility"]
            if (row["cap_binding"], row["excess_cash"], row["scale_down"]) != (cap, cash, scale):
                return None, "underivable_constraint_boolean"
            normalized.append(row)
        dates = [row["date"] for row in normalized]
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            return None, "dates_not_unique_monotonic"
        turnover = sum(sum(abs(row["weights"][asset] - normalized[index - 1]["weights"][asset]) for asset in ASSETS) for index, row in enumerate(normalized) if index)
        components = {key: sum(row[key] for row in normalized) for key in ("commission", "spread_slippage", "sell_surcharge")}
        return {
            "dates": dates,
            "turnover": turnover,
            "commission": components["commission"],
            "spread_slippage": components["spread_slippage"],
            "sell_surcharge": components["sell_surcharge"],
            "cost": sum(components.values()),
            "cap_frequency": sum(row["cap_binding"] for row in normalized) / len(normalized),
            "cash_frequency": sum(row["excess_cash"] for row in normalized) / len(normalized),
            "scale_down_frequency": sum(row["scale_down"] for row in normalized) / len(normalized),
        }, None

    left, left_error = branch(candidate)
    right, right_error = branch(comparator)
    if left_error or right_error or left is None or right is None:
        return {"evaluable": False, "met": False, "decision": "scope_restricted", "reason": left_error or right_error}
    if left["dates"] != right["dates"]:
        return {"evaluable": False, "met": False, "decision": "scope_restricted", "reason": "paired_dates_mismatch"}
    if right["turnover"] == 0 or right["cost"] == 0:
        return {"evaluable": False, "met": False, "decision": "scope_restricted", "reason": "zero_denominator"}
    result = {
        "evaluable": True,
        "decision": "evaluable",
        "candidate": left,
        "comparator": right,
        "turnover_relative_increase": (left["turnover"] - right["turnover"]) / right["turnover"],
        "cost_relative_increase": (left["cost"] - right["cost"]) / right["cost"],
        "cap_frequency_increase": left["cap_frequency"] - right["cap_frequency"],
        "cash_frequency_increase": left["cash_frequency"] - right["cash_frequency"],
        "scale_down_frequency_increase": left["scale_down_frequency"] - right["scale_down_frequency"],
        "cost_alias_turnover": False,
    }
    result["met"] = result["turnover_relative_increase"] <= 0.20 and result["cost_relative_increase"] <= 0.20 and all(result[key] <= 0.10 for key in ("cap_frequency_increase", "cash_frequency_increase", "scale_down_frequency_increase"))
    return result
