"""Synthetic-only structural preflight and side-effect diagnostics for future L-3 work."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

ASSETS = ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]
START, END, VALIDATION_START = "2007-02-05", "2015-12-31", "2016-01-04"


def scan_synthetic_envelope(envelope: Any) -> dict[str, Any]:
    """Validate only structural/date fields from a synthetic decoded envelope.

    This accepts a mapping supplied by hermetic fixtures only. It deliberately has
    no file/path API, so B7.7 cannot open, hash, or decode a real container.
    """
    blockers: list[str] = []
    if not isinstance(envelope, dict):
        return {"status": "blocked", "blockers": ["envelope_not_object"]}
    if envelope.get("schema_version") != "lily_l1_daily_dataset_v1":
        blockers.append("schema_version_mismatch")
    if envelope.get("cutoff_inclusive") != END:
        blockers.append("cutoff_inclusive_mismatch")
    symbols = envelope.get("symbols")
    if not isinstance(symbols, list) or len(symbols) != len(ASSETS):
        blockers.append("symbol_envelope_count_mismatch")
        symbols = []
    names = [item.get("symbol") for item in symbols if isinstance(item, dict)]
    if names != ASSETS or len(set(names)) != len(ASSETS):
        blockers.append("symbol_identity_or_order_mismatch")
    per_symbol: dict[str, list[str]] = {}
    for item in symbols:
        if not isinstance(item, dict) or set(item) != {"symbol", "records"}:
            blockers.append("symbol_object_shape_mismatch")
            continue
        symbol, records = item["symbol"], item["records"]
        if not isinstance(symbol, str) or not isinstance(records, list):
            blockers.append("records_shape_mismatch")
            continue
        dates: list[str] = []
        for record in records:
            if not isinstance(record, dict) or set(record) != {"session_date", "availability_timestamp", "total_return_close"}:
                blockers.append("record_shape_mismatch")
                continue
            session = record.get("session_date")
            if not isinstance(session, str):
                blockers.append("session_date_missing")
                continue
            try:
                date.fromisoformat(session)
            except ValueError:
                blockers.append("session_date_invalid")
                continue
            dates.append(session)
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            blockers.append("per_symbol_sessions_not_strictly_monotonic")
        per_symbol[symbol] = dates
    common = sorted(set.intersection(*(set(per_symbol.get(asset, [])) for asset in ASSETS))) if len(per_symbol) == len(ASSETS) else []
    if any(value >= VALIDATION_START for value in common):
        blockers.append("mixed_validation_session_hard_stop")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers)), "schema_version": envelope.get("schema_version"), "date_column": "session_date", "assets": names, "per_symbol_sessions": per_symbol, "common_sessions": common, "return_values_exposed": False}


def canonical_schedule_sha256(decisions: list[str]) -> str:
    return hashlib.sha256(json.dumps(decisions, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_schedule(common_sessions: list[str], decisions: list[str]) -> dict[str, Any]:
    blockers: list[str] = []
    if common_sessions != sorted(common_sessions) or len(common_sessions) != len(set(common_sessions)):
        blockers.append("common_sessions_not_strictly_monotonic")
    if any(value >= VALIDATION_START for value in common_sessions): blockers.append("mixed_validation_session_hard_stop")
    if decisions != sorted(decisions) or len(decisions) != len(set(decisions)): blockers.append("duplicate_or_non_monotonic_week")
    if len(decisions) > 465: blockers.append("weekly_observation_ceiling_exceeded")
    execution, ends = [], []
    for decision in decisions:
        if decision < START: blockers.append("pre_start_weekly_decision")
        if decision > END or decision not in common_sessions: blockers.append("decision_outside_common_falsification_sessions"); continue
        index = common_sessions.index(decision)
        if index + 20 >= len(common_sessions): blockers.append("incomplete_t_plus_20_interval"); continue
        execution.append(common_sessions[index + 1]); ends.append(common_sessions[index + 20])
    if any(value > END for value in execution + ends): blockers.append("post_end_execution_or_confirmation")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers)), "selected_decision_dates": decisions, "execution_dates": execution, "realized_confirmation_end_dates": ends, "schedule_sha256": canonical_schedule_sha256(decisions)}


def compute_side_effects(candidate: list[dict[str, Any]], comparator: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute each locked side effect from explicit diagnostic states and costs."""
    def branch(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        required = {"weights", "cost", "cap_binding", "cash_constraint", "scale_down"}
        if not rows or any(not isinstance(row, dict) or set(row) != required or not isinstance(row["cost"], (int, float)) for row in rows): return None
        turnover = sum(sum(abs(row["weights"].get(asset, 0.0) - rows[i-1]["weights"].get(asset, 0.0)) for asset in ASSETS) for i,row in enumerate(rows) if i)
        return {"turnover": turnover, "cost": sum(row["cost"] for row in rows), "cap_frequency": sum(bool(r["cap_binding"]) for r in rows)/len(rows), "cash_frequency": sum(bool(r["cash_constraint"]) for r in rows)/len(rows), "scale_down_frequency": sum(bool(r["scale_down"]) for r in rows)/len(rows)}
    c, q = branch(candidate), branch(comparator)
    if c is None or q is None or q["turnover"] == 0 or q["cost"] == 0:
        return {"evaluable": False, "met": False, "reason": "missing_diagnostics_or_zero_denominator", "candidate": c, "comparator": q}
    result = {"evaluable": True, "candidate": c, "comparator": q, "turnover_relative_increase": (c["turnover"]-q["turnover"])/q["turnover"], "cost_relative_increase": (c["cost"]-q["cost"])/q["cost"], "cap_frequency_increase": c["cap_frequency"]-q["cap_frequency"], "cash_frequency_increase": c["cash_frequency"]-q["cash_frequency"], "scale_down_frequency_increase": c["scale_down_frequency"]-q["scale_down_frequency"]}
    result["met"] = result["turnover_relative_increase"] <= .20 and result["cost_relative_increase"] <= .20 and all(result[key] <= .10 for key in ("cap_frequency_increase", "cash_frequency_increase", "scale_down_frequency_increase"))
    return result
