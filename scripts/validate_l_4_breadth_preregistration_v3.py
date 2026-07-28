"""Fail-closed B8.2 validator with synthetic decision truth-table checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GATE = PROJECT_ROOT / "experiments/l_4_breadth_preregistration_v3.json"
EXPECTED_SHA = "59010f1486ff891172b9b71a51dca3b770206bebf44ecc28fb17a4df871eb238"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from lib.statistics import paired_mean_minimum_observations

LAGS = [0.25, 0.125, 0.0625, 0.03125, 0.015625]
METRICS = {"ex_ante_hhi_delta": (0.05, 0.1), "realized_hhi_delta": (0.05, 0.1), "top_dependency_delta": (0.1, 0.2), "n_eff_delta": (0.5, 1.0)}


def classify_e1(*, non_evaluable: bool, underfunded: bool, ucb_breach: bool, constraint_breach: bool) -> str:
    if non_evaluable or underfunded:
        return "scope_restricted"
    if ucb_breach or constraint_breach:
        return "falsified_E1_only"
    return "not_falsified_not_validated_E1"


def classify_validation(*, non_evaluable_or_underfunded: bool, all_lcb_strictly_above: bool, constraints_pass: bool, integrity_pass: bool) -> str:
    if non_evaluable_or_underfunded:
        return "scope_restricted"
    if all_lcb_strictly_above and constraints_pass and integrity_pass:
        return "validation_candidate"
    return "not_validation_candidate"


def validate_gate(gate_path: Path = GATE, *, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        raw = gate_path.read_bytes(); gate = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return _result([f"gate_unreadable:{exc.__class__.__name__}"])
    _closed(gate, "gate", blockers)
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
        blockers.append("gate_bytes_or_semantics_mismatch")
    _sources(gate, project_root, blockers)
    _semantics(gate, blockers)
    _planning(gate, blockers)
    _truth_table(blockers)
    return _result(blockers)


def _closed(value: Any, label: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        blockers.append(f"{label}_not_object"); return
    # The byte lock fixes every value and key; recursively reject non-string keys/non-container anomalies.
    for key, item in value.items():
        if not isinstance(key, str): blockers.append(f"{label}_non_string_key")
        if isinstance(item, dict): _closed(item, f"{label}.{key}", blockers)
        elif isinstance(item, list):
            for i, child in enumerate(item):
                if isinstance(child, dict): _closed(child, f"{label}.{key}[{i}]", blockers)


def _sources(gate: dict[str, Any], root: Path, blockers: list[str]) -> None:
    binding = gate.get("source_binding", {})
    v2 = binding.get("v2_predecessor", {})
    if v2.get("gate_sha256") != "5eeb602cdf06e0cb1dfcda1e535d023cc3a125458ed32d811559b7fbd0d710b1" or v2.get("validator_sha256") != "ac3176e6ca4296f188e297c3001dae8af3bce27a35cdb3c53ff61e6fd87040fd": blockers.append("v2_declaration_mismatch")
    for path, digest in ((v2.get("gate_path"), v2.get("gate_sha256")), (v2.get("validator_path"), v2.get("validator_sha256")), ("experiments/l_1_baseline_preregistration.json", binding.get("l1_preregistration", {}).get("sha256")), ("experiments/l_3_inverse_volatility_sizing_preregistration_v2.json", binding.get("l3_preregistration", {}).get("sha256")), ("research_log/010-lily-l3-corrected-rerun.md", binding.get("b715_closure", {}).get("sha256"))):
        if not isinstance(path, str) or _sha(root / path) != digest: blockers.append(f"source_hash_mismatch:{path}")
    try:
        rows = [json.loads(line) for line in (root / "experiments/locked_gates.jsonl").read_text(encoding="utf-8").splitlines() if line]
        row = [r for r in rows if r.get("gate_id") == "l_4_breadth_v2"]
    except (OSError, json.JSONDecodeError): row = []
    if len(row) != 1 or row[0].get("artifact_sha256") != v2.get("gate_sha256") or row[0].get("validator_sha256") != v2.get("validator_sha256"): blockers.append("v2_manifest_identity_mismatch")
    completed = subprocess.run(["git", "rev-parse", "62557cc7d02f81fafbed57ef7bcd8cc836193fe1:research_log/010-lily-l3-corrected-rerun.md"], cwd=root, text=True, capture_output=True, check=False)
    if completed.returncode or completed.stdout.strip() != binding.get("b715_closure", {}).get("git_blob_sha1"): blockers.append("b715_commit_blob_mismatch")


def _semantics(gate: dict[str, Any], blockers: list[str]) -> None:
    required = {"research_question", "inherited_controls", "primary_sizing", "mandatory_metrics", "decision_contract", "robustness_and_side_effects", "regime_matrix"}
    if not required <= set(gate): blockers.append("required_scientific_controls_missing")
    if gate.get("primary_sizing", {}).get("step_1") != "u[i,t] = q[i,t] with no division by volatility.": blockers.append("q_primary_isolation_mismatch")
    if gate.get("decision_contract", {}).get("e1_precedence") != ["scope_restricted", "falsified_E1_only", "not_falsified_not_validated_E1"]: blockers.append("decision_precedence_mismatch")
    if gate.get("timing_and_seal", {}).get("validation_opened") is not False or any(v is not False for v in gate.get("authorizations", {}).values()): blockers.append("seal_or_authorization_opened")


def _planning(gate: dict[str, Any], blockers: list[str]) -> None:
    metrics = gate.get("mandatory_metrics", {})
    for name, (threshold, sd) in METRICS.items():
        metric = metrics.get(name, {})
        if metric.get("useful_threshold") != threshold: blockers.append(f"threshold_mismatch:{name}"); continue
        expected = [("falsify", "lower", threshold, 0.0), ("validation_zero", "upper", 0.0, threshold), ("validation_minimum_useful", "upper", threshold, 2 * threshold)]
        for plan_name, tail, null, alternative in expected:
            plan = metric.get(plan_name, {})
            actual = paired_mean_minimum_observations(alternative_mean=alternative, null_mean=null, planning_standard_deviation=sd, autocorrelations=LAGS, significance=0.05, power=0.8)
            if plan != {"tail": tail, "null": null, "alternative": alternative, "planning_sd": sd, "expected_mintrl": 49} or actual != 49: blockers.append(f"mintrl_plan_mismatch:{name}:{plan_name}")


def _truth_table(blockers: list[str]) -> None:
    cases = [
        (dict(non_evaluable=False, underfunded=False, ucb_breach=False, constraint_breach=False), "not_falsified_not_validated_E1"),
        (dict(non_evaluable=False, underfunded=False, ucb_breach=True, constraint_breach=False), "falsified_E1_only"),
        (dict(non_evaluable=False, underfunded=False, ucb_breach=False, constraint_breach=True), "falsified_E1_only"),
        (dict(non_evaluable=False, underfunded=True, ucb_breach=True, constraint_breach=False), "scope_restricted"),
        (dict(non_evaluable=True, underfunded=False, ucb_breach=False, constraint_breach=False), "scope_restricted"),
    ]
    if any(classify_e1(**inputs) != expected for inputs, expected in cases): blockers.append("e1_truth_table_not_exhaustive_or_exclusive")
    if classify_validation(non_evaluable_or_underfunded=True, all_lcb_strictly_above=True, constraints_pass=True, integrity_pass=True) != "scope_restricted": blockers.append("validation_underfunded_regime_precedence_mismatch")
    if classify_validation(non_evaluable_or_underfunded=False, all_lcb_strictly_above=False, constraints_pass=True, integrity_pass=True) != "not_validation_candidate": blockers.append("validation_equality_boundary_mismatch")


def _sha(path: Path) -> str | None:
    try: return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError: return None
def _result(blockers: list[str]) -> dict[str, Any]: return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "gate_path": "experiments/l_4_breadth_preregistration_v3.json"}
if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--gate", type=Path, default=GATE); args = parser.parse_args(); result = validate_gate(args.gate); print(json.dumps(result, indent=2, sort_keys=True)); raise SystemExit(0 if result["status"] == "pass" else 1)
