from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, load_jsonl, relative_to_root


GATE = PROJECT_ROOT / "experiments" / "l_2_falsification_capacity_gate_v1.json"
L1 = PROJECT_ROOT / "experiments" / "l_1_baseline_preregistration.json"
L2 = PROJECT_ROOT / "experiments" / "l_2_multi_lookback_tstat_preregistration_v2.json"
MANIFEST = PROJECT_ROOT / "experiments" / "locked_gates.jsonl"
GATE_ID = "l_2_falsification_capacity_gate_v1"
L1_SHA256 = "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29"
L2_SHA256 = "84a7bb45070b54846a709573506c8213a3bc62d28cfa25f4982415d40d94e1f3"
B6_2_SHA256 = "595f66b9bae804957dffc15cbe1d8e388cdef225d93c5396aa556ef8a7f639b7"


def validate_gate(path: Path = GATE, *, require_manifest: bool = True) -> dict[str, Any]:
    try:
        gate, l1, l2 = load_json(path), load_json(L1), load_json(L2)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"gate_or_source_unreadable:{exc.__class__.__name__}"])
    blockers: list[str] = []
    expected = {"schema_version": "lily_l2_falsification_capacity_gate_v1", "order_id": "B6.3", "hypothesis_id": "L-2", "supersedes_gate_id": "l_2_falsification_execution_contract_v2", "status": "locked_underfunded_execution_forbidden", "evidence_ceiling": "E1", "edge_claim": "none", "capacity_outcome": "underfunded_scope_restricted", "market_returns_read": False, "execution_authorized": False}
    for field, value in expected.items():
        if gate.get(field) != value:
            blockers.append(f"field_mismatch:{field}")
    sources = gate.get("locked_sources")
    expected_sources = {"l1_baseline_sha256": L1_SHA256, "l2_v2_sha256": L2_SHA256, "b6_2_sha256": B6_2_SHA256}
    if not isinstance(sources, dict) or any(sources.get(key) != value for key, value in expected_sources.items()) or _sha256(L1) != L1_SHA256 or _sha256(L2) != L2_SHA256:
        blockers.append("locked_source_hash_mismatch")
    start, end = gate.get("falsification_window", {}).get("start"), gate.get("falsification_window", {}).get("end")
    instruments = l1.get("universes", {}).get("research_signed", {}).get("instruments", [])
    required_ibe = l2.get("dual_MinTRL", {}).get("falsify", {}).get("required_joint_independent_bet_equivalents")
    try:
        calendar_days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    except (TypeError, ValueError):
        blockers.append("falsification_window_invalid")
        calendar_days = None
    asset_count = len(instruments) if isinstance(instruments, list) else None
    if not isinstance(required_ibe, int) or required_ibe <= 0:
        blockers.append("mintrl_falsify_missing")
    if calendar_days is None or not isinstance(asset_count, int):
        return _result(path, blockers)
    upper_bound = calendar_days * asset_count
    capacity = gate.get("absolute_upper_bound", {})
    expected_capacity = {"calendar_days_inclusive": calendar_days, "fixed_research_asset_count": asset_count, "maximum_time_effective_observations": calendar_days, "maximum_cross_sectional_effective_dimensions": asset_count, "maximum_joint_independent_bet_equivalents": upper_bound, "required_mintrl_falsify": required_ibe}
    if capacity != expected_capacity:
        blockers.append("absolute_upper_bound_mismatch")
    if not isinstance(required_ibe, int) or upper_bound >= required_ibe:
        blockers.append("underfunded_conclusion_not_supported")
    hard_stops = gate.get("hard_stops")
    required_stops = {"No falsification-container inspection or market-return parsing while this capacity gate is underfunded.", "No L-2 backtest, falsified, or not_falsified_not_validated report under the current preregistration.", "No validation-window access, broker/provider call, credential use, paid action, paper trade, or real-money action."}
    if not isinstance(hard_stops, list) or not required_stops.issubset(hard_stops):
        blockers.append("hard_stops_incomplete")
    if require_manifest:
        blockers.extend(_validate_manifest(path))
    return _result(path, blockers)


def _validate_manifest(path: Path) -> list[str]:
    try:
        rows = load_jsonl(MANIFEST)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return ["manifest_unreadable"]
    matches = [row for row in rows if isinstance(row, dict) and row.get("gate_id") == GATE_ID]
    if len(matches) != 1:
        return ["manifest_gate_entry_mismatch"]
    row = matches[0]
    expected = {"artifact_path": relative_to_root(path, PROJECT_ROOT), "artifact_sha256": _sha256(path), "validator_path": "scripts/validate_l_2_falsification_capacity_gate.py", "validator_sha256": _sha256(Path(__file__)), "supersedes_gate_id": "l_2_falsification_execution_contract_v2"}
    return [] if all(row.get(key) == value for key, value in expected.items()) else ["manifest_hash_or_path_mismatch"]


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "gate_path": relative_to_root(path, PROJECT_ROOT)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=Path, default=GATE)
    args = parser.parse_args()
    result = validate_gate(args.gate)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
