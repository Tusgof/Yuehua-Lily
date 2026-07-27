"""Validate only a prospective B7.8 report contract; this script opens no data."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.provenance import file_sha256
GATE = ROOT / "experiments/l_3_corrected_rerun_activation_v3.json"
SCHEMA = ROOT / "schemas/l_3_corrected_rerun_report_v3.schema.json"
_IMPLEMENTATION_PATHS = {"gate": "experiments/l_3_corrected_rerun_activation_v3.json", "runner": "scripts/run_l_3_corrected_rerun_v3.py", "report_validator": "scripts/validate_l_3_corrected_rerun_report_v3.py", "report_schema": "schemas/l_3_corrected_rerun_report_v3.schema.json", "side_effect_library": "lib/l3_corrected_rerun_v3.py"}
_TOP = {"schema_version", "order_id", "hypothesis_id", "report_mode", "decision", "evidence_tier", "edge_claim", "provenance", "counts", "primary", "realized", "side_effects", "regimes", "validation_seal", "autopsy"}


def _sha(path: Path) -> str:
    return file_sha256(path)


def _finite_tree(value: Any, location: str = "$") -> list[str]:
    if type(value) in (int, float) and not math.isfinite(value):
        return [f"nonfinite:{location}"]
    if isinstance(value, dict):
        return [item for key, child in value.items() for item in _finite_tree(child, f"{location}.{key}")]
    if isinstance(value, list):
        return [item for index, child in enumerate(value) for item in _finite_tree(child, f"{location}[{index}]")]
    return []


def _shape_errors(payload: dict[str, Any]) -> list[str]:
    """Portable closed-world enforcement mirroring the committed JSON Schema."""
    errors = ["schema:top_level_closed_world" for _ in [0] if set(payload) != _TOP]
    if payload.get("schema_version") != "lily_l3_corrected_rerun_report_v3" or payload.get("order_id") != "B7.8" or payload.get("hypothesis_id") != "L-3" or payload.get("edge_claim") != "none": errors.append("schema:identity")
    if payload.get("report_mode") not in {"synthetic_not_run", "pre_return_failure", "future_execution"} or payload.get("decision") not in {"not_run", "scope_restricted", "falsified", "not_falsified_not_validated"} or payload.get("evidence_tier") not in {"E0", "E1"}: errors.append("schema:mode_decision_tier")
    def exact(name: str, keys: set[str]) -> dict[str, Any] | None:
        value = payload.get(name)
        if not isinstance(value, dict) or set(value) != keys:
            errors.append(f"schema:{name}_closed_world")
            return None
        return value
    provenance = exact("provenance", {"producing_git_commit", "gate", "runner", "report_validator", "report_schema", "side_effect_library", "container_identity", "schedule_identity", "ledger_identity"})
    if provenance:
        for name in _IMPLEMENTATION_PATHS:
            value = provenance[name]
            if not isinstance(value, dict) or set(value) != {"path", "sha256"} or not isinstance(value["path"], str) or not isinstance(value["sha256"], str): errors.append(f"schema:{name}_identity")
        for name in ("container_identity", "schedule_identity", "ledger_identity"):
            value = provenance[name]
            if not isinstance(value, dict) or set(value) != {"present", "path", "sha256"} or type(value["present"]) is not bool: errors.append(f"schema:{name}_identity")
    counts = exact("counts", {"paired_observations", "effective_independent_bets", "mintrl_falsify", "asset_multiplier", "day_multiplier", "trade_multiplier", "t20_multiplier"})
    if counts and (type(counts["paired_observations"]) is not int or not 0 <= counts["paired_observations"] <= 465 or type(counts["effective_independent_bets"]) not in (int, float) or counts["mintrl_falsify"] != 49 or any(counts[key] != 1 for key in ("asset_multiplier", "day_multiplier", "trade_multiplier", "t20_multiplier"))): errors.append("schema:counts")
    primary = exact("primary", {"ucb", "autocorrelation_ucb_trace"})
    if primary and (primary["ucb"] is not None and type(primary["ucb"]) not in (int, float) or not isinstance(primary["autocorrelation_ucb_trace"], list)): errors.append("schema:primary")
    realized = exact("realized", {"evaluable", "complete_t_plus_20", "observations"})
    if realized and (type(realized["evaluable"]) is not bool or type(realized["complete_t_plus_20"]) is not bool or type(realized["observations"]) is not int or realized["observations"] < 0): errors.append("schema:realized")
    side = exact("side_effects", {"evaluable", "met", "cost_alias_turnover", "turnover_relative_increase", "cost_relative_increase", "cap_frequency_increase", "cash_frequency_increase", "scale_down_frequency_increase"})
    if side and (type(side["evaluable"]) is not bool or type(side["met"]) is not bool or side["cost_alias_turnover"] is not False): errors.append("schema:side_effects")
    regimes = exact("regimes", {"claims", "pooled"})
    if regimes and (not isinstance(regimes["claims"], list) or regimes["pooled"] is not False): errors.append("schema:regimes")
    for claim in regimes["claims"] if regimes and isinstance(regimes["claims"], list) else []:
        if not isinstance(claim, dict) or set(claim) != {"name", "evaluable", "funded", "observations"} or not isinstance(claim["name"], str) or type(claim["evaluable"]) is not bool or type(claim["funded"]) is not bool or type(claim["observations"]) is not int: errors.append("schema:regime_claim")
    seal = exact("validation_seal", {"status", "accessed"})
    if seal and seal != {"status": "sealed_not_accessed", "accessed": False}: errors.append("schema:validation_seal")
    autopsy = payload.get("autopsy")
    if autopsy is not None and (not isinstance(autopsy, dict) or set(autopsy) != {"volatility_scaling_concentration", "common_constraints", "ex_ante_vs_realized_hhi", "turnover_cost", "implementation_data_alternatives"}): errors.append("schema:autopsy_closed_world")
    return errors


def _head() -> str | None:
    run = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
    return run.stdout.strip() if run.returncode == 0 else None


def _identity_matches(value: Any, path: str) -> bool:
    return isinstance(value, dict) and value == {"path": path, "sha256": _sha(ROOT / path)}


def _optional_identity_ok(value: Any, *, require_present: bool) -> bool:
    if not isinstance(value, dict) or set(value) != {"present", "path", "sha256"}:
        return False
    if value["present"] is not require_present:
        return False
    if require_present:
        return isinstance(value["path"], str) and value["path"].startswith("reports/experiments/") and isinstance(value["sha256"], str) and len(value["sha256"]) == 64 and value["sha256"] != "0" * 64
    return value["path"] is None and value["sha256"] is None


def _side_breach(side: dict[str, Any]) -> bool:
    limits = {"turnover_relative_increase": 0.20, "cost_relative_increase": 0.20, "cap_frequency_increase": 0.10, "cash_frequency_increase": 0.10, "scale_down_frequency_increase": 0.10}
    return any(type(side.get(key)) in (int, float) and math.isfinite(side[key]) and side[key] > limit for key, limit in limits.items())


def validate(payload: Any) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(payload, dict):
        return {"status": "blocked", "blockers": ["report_not_object"]}
    try:
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "blocked", "blockers": [f"schema_unreadable:{type(exc).__name__}"]}
    blockers.extend(_shape_errors(payload))
    blockers.extend(_finite_tree(payload))
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        blockers.append("provenance_not_object")
    else:
        if provenance.get("producing_git_commit") != _head():
            blockers.append("producing_checkout_head_mismatch")
        for name, expected_path in _IMPLEMENTATION_PATHS.items():
            if not _identity_matches(provenance.get(name), expected_path):
                blockers.append(f"implementation_identity_mismatch:{name}")
    mode = payload.get("report_mode")
    decision = payload.get("decision")
    counts = payload.get("counts")
    primary = payload.get("primary")
    realized = payload.get("realized")
    side = payload.get("side_effects")
    regimes = payload.get("regimes")
    if not all(isinstance(value, dict) for value in (counts, primary, realized, side, regimes)):
        blockers.append("nested_evidence_not_object")
    else:
        funded = type(counts.get("effective_independent_bets")) in (int, float) and math.isfinite(counts["effective_independent_bets"]) and counts["effective_independent_bets"] >= 49 and counts.get("paired_observations", -1) >= 49
        trace = primary.get("autocorrelation_ucb_trace")
        ucb = primary.get("ucb")
        trace_ok = isinstance(trace, list) and trace and all(type(item) in (int, float) and math.isfinite(item) for item in trace) and type(ucb) in (int, float) and math.isfinite(ucb) and abs(trace[-1] - ucb) <= 1e-12
        if mode == "future_execution" and not funded:
            blockers.append("effective_funding_not_met")
        if mode == "future_execution" and not trace_ok:
            blockers.append("autocorrelation_ucb_trace_invalid")
        if mode == "future_execution" and (realized.get("evaluable") is not True or realized.get("complete_t_plus_20") is not True or realized.get("observations") != counts.get("paired_observations")):
            blockers.append("realized_confirmation_incomplete")
        claims = regimes.get("claims")
        if regimes.get("pooled") is not False:
            blockers.append("regime_pooling_forbidden")
        if mode == "future_execution" and (not isinstance(claims, list) or not claims or any(item.get("evaluable") is not True or item.get("funded") is not True or item.get("observations", 0) < 49 for item in claims if isinstance(item, dict)) or any(not isinstance(item, dict) for item in claims)):
            blockers.append("regime_evidence_not_separately_funded")
        if decision == "not_falsified_not_validated" and (side.get("evaluable") is not True or side.get("met") is not True or side.get("cost_alias_turnover") is not False):
            blockers.append("not_falsified_requires_complete_met_side_effect_evidence")
        if decision == "falsified" and (side.get("evaluable") is not True or side.get("cost_alias_turnover") is not False or not (type(ucb) in (int, float) and math.isfinite(ucb) and ucb < 0.05 or _side_breach(side))):
            blockers.append("falsified_requires_ucb_or_numeric_side_breach")
    if isinstance(provenance, dict):
        future = mode == "future_execution"
        for name in ("container_identity", "schedule_identity", "ledger_identity"):
            if not _optional_identity_ok(provenance.get(name), require_present=future):
                blockers.append(f"identity_binding_invalid:{name}")
    seal = payload.get("validation_seal")
    if not isinstance(seal, dict) or seal != {"status": "sealed_not_accessed", "accessed": False}:
        blockers.append("validation_seal_broken")
    autopsy = payload.get("autopsy")
    exact_autopsy = {"volatility_scaling_concentration", "common_constraints", "ex_ante_vs_realized_hhi", "turnover_cost", "implementation_data_alternatives"}
    if decision == "falsified" and (not isinstance(autopsy, dict) or set(autopsy) != exact_autopsy or not all(isinstance(value, str) and value for value in autopsy.values())):
        blockers.append("five_part_autopsy_required")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a prospective B7.8 report.")
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.report.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"status": "blocked", "blockers": [f"unreadable:{type(exc).__name__}"]}, sort_keys=True))
        return 1
    result = validate(payload)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
