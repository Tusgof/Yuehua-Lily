"""Validate only a prospective B7.8 report contract; this script opens no data."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.provenance import file_sha256
GATE = ROOT / "experiments/l_3_corrected_rerun_activation_v3.json"
SCHEMA = ROOT / "schemas/l_3_corrected_rerun_report_v3.schema.json"
_IMPLEMENTATION_PATHS = {"gate": "experiments/l_3_corrected_rerun_activation_v3.json", "runner": "scripts/run_l_3_corrected_rerun_v3.py", "report_validator": "scripts/validate_l_3_corrected_rerun_report_v3.py", "report_schema": "schemas/l_3_corrected_rerun_report_v3.schema.json", "side_effect_library": "lib/l3_corrected_rerun_v3.py"}


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
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "blocked", "blockers": [f"schema_unreadable:{type(exc).__name__}"]}
    blockers.extend(f"schema:{error.message}" for error in Draft202012Validator(schema).iter_errors(payload))
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
