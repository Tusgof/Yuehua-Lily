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


GATE = PROJECT_ROOT / "experiments/l_2_falsification_capacity_gate_v2.json"
MANIFEST = PROJECT_ROOT / "experiments/locked_gates.jsonl"
GATE_ID = "l_2_falsification_capacity_gate_v2"
SOURCE_SPEC = {
    "l1": ("l1_baseline_path", "l1_baseline_sha256", "experiments/l_1_baseline_preregistration.json", "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29"),
    "l2": ("l2_v2_path", "l2_v2_sha256", "experiments/l_2_multi_lookback_tstat_preregistration_v2.json", "84a7bb45070b54846a709573506c8213a3bc62d28cfa25f4982415d40d94e1f3"),
    "b6": ("b6_2_path", "b6_2_sha256", "experiments/l_2_falsification_execution_contract_v2.json", "595f66b9bae804957dffc15cbe1d8e388cdef225d93c5396aa556ef8a7f639b7"),
}


def validate_gate(path: Path = GATE, *, require_manifest: bool = True) -> dict[str, Any]:
    try:
        gate = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"gate_unreadable:{exc.__class__.__name__}"])
    blockers: list[str] = []
    expected = {"schema_version": "lily_l2_falsification_capacity_gate_v2", "order_id": "B6.4", "hypothesis_id": "L-2", "supersedes_gate_id": "l_2_falsification_capacity_gate_v1", "status": "locked_underfunded_execution_forbidden", "evidence_ceiling": "E1", "edge_claim": "none", "capacity_outcome": "underfunded_scope_restricted", "market_returns_read": False, "execution_authorized": False}
    for key, value in expected.items():
        if gate.get(key) != value:
            blockers.append(f"field_mismatch:{key}")
    sources = gate.get("locked_sources")
    source_data: dict[str, Any] = {}
    if not isinstance(sources, dict):
        blockers.append("locked_sources_invalid")
    else:
        for name, (path_key, hash_key, required_path, required_hash) in SOURCE_SPEC.items():
            declared_path, declared_hash = sources.get(path_key), sources.get(hash_key)
            source_path = PROJECT_ROOT / str(declared_path)
            if declared_path != required_path or declared_hash != required_hash or not source_path.is_file() or _sha256(source_path) != declared_hash:
                blockers.append(f"locked_source_mismatch:{name}")
                continue
            try:
                source_data[name] = load_json(source_path)
            except json.JSONDecodeError:
                blockers.append(f"locked_source_unreadable:{name}")
        if "b6" in source_data and not _manifest_binds("l_2_falsification_execution_contract_v2", SOURCE_SPEC["b6"][2], SOURCE_SPEC["b6"][3]):
            blockers.append("b6_2_manifest_identity_or_hash_mismatch")
    if set(source_data) != {"l1", "l2", "b6"}:
        return _result(path, blockers)
    l1_window = source_data["l1"].get("sample_and_unlock_order", {}).get("falsification_window")
    b6_window = source_data["b6"].get("falsification_window")
    if not isinstance(l1_window, dict) or l1_window.get("start") != "2007-02-05" or l1_window.get("end") != "2015-12-31" or b6_window != {"start": l1_window["start"], "end": l1_window["end"]} or gate.get("falsification_window") != {"start": l1_window["start"], "end": l1_window["end"]}:
        blockers.append("locked_falsification_window_mismatch")
        return _result(path, blockers)
    instruments = source_data["l1"].get("universes", {}).get("research_signed", {}).get("instruments")
    required_ibe = source_data["l2"].get("dual_MinTRL", {}).get("falsify", {}).get("required_joint_independent_bet_equivalents")
    if not isinstance(instruments, list) or len(instruments) != 8 or not isinstance(required_ibe, int):
        blockers.append("locked_universe_or_mintrl_invalid")
        return _result(path, blockers)
    days = (date.fromisoformat(l1_window["end"]) - date.fromisoformat(l1_window["start"])).days + 1
    expected_capacity = {"calendar_days_inclusive": days, "fixed_research_asset_count": len(instruments), "maximum_time_effective_observations": days, "maximum_cross_sectional_effective_dimensions": len(instruments), "maximum_joint_independent_bet_equivalents": days * len(instruments), "required_mintrl_falsify": required_ibe}
    if gate.get("absolute_upper_bound") != expected_capacity:
        blockers.append("absolute_upper_bound_mismatch")
    if days * len(instruments) >= required_ibe:
        blockers.append("underfunded_conclusion_not_supported")
    required_stops = {"No falsification-container inspection or market-return parsing while this capacity gate is underfunded.", "No L-2 backtest, falsified, or not_falsified_not_validated report under the current preregistration.", "No validation-window access, broker/provider call, credential use, paid action, paper trade, or real-money action."}
    if not isinstance(gate.get("hard_stops"), list) or not required_stops.issubset(gate["hard_stops"]):
        blockers.append("hard_stops_incomplete")
    if require_manifest and not _manifest_binds(GATE_ID, relative_to_root(path, PROJECT_ROOT), _sha256(path), "scripts/validate_l_2_falsification_capacity_gate_v2.py", _sha256(Path(__file__)), "l_2_falsification_capacity_gate_v1"):
        blockers.append("manifest_hash_or_path_mismatch")
    return _result(path, blockers)


def _manifest_binds(gate_id: str, artifact_path: str, artifact_hash: str | None, validator_path: str | None = None, validator_hash: str | None = None, supersedes: str | None = None) -> bool:
    try: rows = load_jsonl(MANIFEST)
    except (FileNotFoundError, ValueError, json.JSONDecodeError): return False
    matches = [row for row in rows if isinstance(row, dict) and row.get("gate_id") == gate_id]
    if len(matches) != 1: return False
    row = matches[0]
    expected = {"artifact_path": artifact_path, "artifact_sha256": artifact_hash}
    if validator_path is not None: expected["validator_path"] = validator_path
    if validator_hash is not None: expected["validator_sha256"] = validator_hash
    if supersedes is not None: expected["supersedes_gate_id"] = supersedes
    return all(row.get(key) == value for key, value in expected.items())


def _sha256(path: Path) -> str | None: return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
def _result(path: Path, blockers: list[str]) -> dict[str, Any]: return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "gate_path": relative_to_root(path, PROJECT_ROOT)}
def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--gate", type=Path, default=GATE); args = parser.parse_args(); result = validate_gate(args.gate); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result["status"] == "pass" else 1
if __name__ == "__main__": raise SystemExit(main())
