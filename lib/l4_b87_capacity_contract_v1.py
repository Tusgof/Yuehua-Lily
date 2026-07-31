"""No-return capacity derivation for L-4 B8.7 Phase A."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

U8 = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
CUTOFF = "2015-12-31"
WINDOW = {"start": "2007-02-05", "end": CUTOFF}
OBSERVATION_UNIT = "one weekly paired portfolio observation; never assets, sleeves, correlations, days, trades, or overlapping realized windows."
METRICS = ("ex_ante_hhi_delta", "realized_hhi_delta", "top_dependency_delta", "n_eff_delta")
SEAL = {"status": "sealed_not_accessed", "accessed": False}
AUTHORIZATIONS = {
    "data": False, "container": False, "market": False, "return": False,
    "signal": False, "position": False, "covariance": False, "regime": False,
    "cost": False, "pnl": False, "validation": False, "provider": False,
    "network": False, "credentials": False, "broker": False, "paid": False,
    "paper_trade": False, "real_money": False, "activation": False,
    "execution": False, "report": False, "research_decision": False,
}


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def load_structural_payload(manifest_path: Path, payload_path: Path) -> tuple[dict, dict]:
    """Read only committed structural date metadata; no market values are accepted."""
    manifest = json.loads(manifest_path.read_text("ascii"))
    payload = json.loads(payload_path.read_text("ascii"))
    manifest_keys = {"coverage_by_symbol", "dataset_byte_count", "dataset_reference", "dataset_sha256", "max_session_date", "schema_version", "session_count", "u8_members_in_order", "validation_seal"}
    payload_keys = {"dataset_sha256", "schema_version", "session_dates_by_symbol", "u8_members_in_order"}
    if set(manifest) != manifest_keys or set(payload) != payload_keys:
        raise ValueError("structural_schema")
    if manifest["schema_version"] != "lily_l4_b86r13_falsification_manifest_v15" or payload["schema_version"] != "lily_l4_b86r13_u8_session_dates_v15":
        raise ValueError("structural_schema")
    if manifest["u8_members_in_order"] != list(U8) or payload["u8_members_in_order"] != list(U8) or manifest["dataset_sha256"] != payload["dataset_sha256"] or manifest["validation_seal"] != SEAL:
        raise ValueError("u8_or_seal")
    dates = payload["session_dates_by_symbol"]
    if not isinstance(dates, dict) or set(dates) != set(U8):
        raise ValueError("u8_or_dates")
    for symbol in U8:
        values = dates[symbol]
        if not isinstance(values, list) or not values or values != sorted(set(values)):
            raise ValueError("u8_or_dates")
        for value in values:
            try:
                valid = isinstance(value, str) and date.fromisoformat(value).isoformat() == value and value <= CUTOFF
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("cutoff_or_date")
        coverage = manifest["coverage_by_symbol"].get(symbol)
        if coverage != {"start": values[0], "end": values[-1], "row_count": len(values)}:
            raise ValueError("coverage")
    return manifest, payload


def weekly_paired_slots(payload: dict) -> list[str]:
    dates = payload["session_dates_by_symbol"]
    common = set(dates[U8[0]])
    for symbol in U8[1:]:
        common.intersection_update(dates[symbol])
    weeks: dict[tuple[int, int], str] = {}
    for value in sorted(day for day in common if WINDOW["start"] <= day <= WINDOW["end"]):
        parsed = date.fromisoformat(value)
        weeks.setdefault((parsed.isocalendar().year, parsed.isocalendar().week), value)
    return list(weeks.values())


def metric_requirements(science: dict) -> dict[str, int]:
    mandatory = science.get("mandatory_metrics")
    if not isinstance(mandatory, dict) or set(mandatory) != set(METRICS):
        raise ValueError("mandatory_metrics")
    values: dict[str, int] = {}
    for metric in METRICS:
        expected = mandatory[metric].get("falsify", {}).get("expected_mintrl")
        if not isinstance(expected, int) or isinstance(expected, bool) or expected <= 0:
            raise ValueError("metric_mintrl")
        values[metric] = expected
    return values


def derive(science: dict, manifest_path: Path, payload_path: Path) -> dict:
    manifest, payload = load_structural_payload(manifest_path, payload_path)
    slots = weekly_paired_slots(payload)
    static = science.get("static_capacity", {})
    expected_slots = static.get("maximum_weekly_slots_before_warmup_missingness_or_evaluable_pair_reductions")
    if science.get("timing_and_seal", {}).get("falsification_end") != CUTOFF or static.get("observation_unit") != OBSERVATION_UNIT or expected_slots != len(slots):
        raise ValueError("science_capacity")
    requirements = metric_requirements(science)
    plans = {name: {"observation_unit": OBSERVATION_UNIT, "maximum_weekly_paired_observations": len(slots), "planning_mintrl_falsify": required, "funded_by_capacity": len(slots) >= required, "actual_recalculation_required_before_any_E1_decision": True} for name, required in requirements.items()}
    all_funded = all(item["funded_by_capacity"] for item in plans.values())
    return {
        "falsification_window": WINDOW,
        "first_weekly_session_date": slots[0],
        "last_weekly_session_date": slots[-1],
        "weekly_paired_capacity": len(slots),
        "metric_plans": plans,
        "capacity_outcome": "capacity_funded_all_mandatory_falsification_plans_pending_actual_recalculation" if all_funded else "underfunded_scope_restricted",
        "structural_dataset_sha256": manifest["dataset_sha256"],
    }
