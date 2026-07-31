"""Validate the one locked, no-return B8.7 capacity report."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "experiments/l_4_breadth_b87_capacity_report_v1.json"

if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))
from scripts.validate_l_4_breadth_b87_phase_a_capacity_gate_v1 import GATE, validate as validate_gate
from lib.l4_b87_capacity_contract_v1 import sha256_path


def validate(path: Path = REPORT) -> dict:
    blockers: list[str] = []
    try:
        gate = json.loads(GATE.read_text("ascii"))
        report = json.loads(path.read_text("ascii"))
    except (OSError, ValueError):
        return {"status": "blocked", "blockers": ["unreadable"]}
    expected = {"schema_version", "order_id", "hypothesis_id", "evidence_tier", "edge_claim", "producing_git_commit", "source_binding", "capacity", "validation_seal", "authorizations", "access_counts", "lifecycle"}
    if set(report) != expected:
        blockers.append("closed_world")
    if {key: report.get(key) for key in ("schema_version", "order_id", "hypothesis_id", "evidence_tier", "edge_claim")} != {"schema_version": "lily_l4_b87_capacity_report_v1", "order_id": "B8.7", "hypothesis_id": "L-4", "evidence_tier": "E0", "edge_claim": "none"}:
        blockers.append("identity")
    expected_source = {"gate_path": "experiments/l_4_breadth_b87_phase_a_capacity_gate_v1.json", "gate_sha256": sha256_path(GATE)}
    expected_capacity = {"weekly_paired_capacity": gate["capacity"]["weekly_paired_capacity"], "planning_mintrl_falsify_by_metric": {name: plan["planning_mintrl_falsify"] for name, plan in gate["capacity"]["metric_plans"].items()}, "capacity_outcome": gate["capacity"]["capacity_outcome"]}
    if report.get("source_binding") != expected_source or report.get("capacity") != expected_capacity or report.get("validation_seal") != gate.get("validation_seal") or report.get("authorizations") != gate.get("authorizations") or report.get("lifecycle") != gate.get("lifecycle"):
        blockers.append("gate_binding")
    if report.get("access_counts") != {"committed_structural_manifest_read_count": 1, "committed_u8_session_date_payload_read_count": 1, "market_return_signal_position_covariance_regime_cost_pnl_read_count": 0, "validation_access_count": 0, "activation_count": 0, "execution_count": 0}:
        blockers.append("access_counts")
    commit = report.get("producing_git_commit")
    if not isinstance(commit, str) or len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        blockers.append("git_provenance")
    else:
        shown = subprocess.run(["git", "show", f"{commit}:experiments/l_4_breadth_b87_phase_a_capacity_gate_v1.json"], cwd=ROOT, capture_output=True, check=False)
        if shown.returncode != 0 or shown.stdout != GATE.read_bytes():
            blockers.append("git_provenance")
    if validate_gate().get("status") != "pass":
        blockers.append("gate")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate(); print(json.dumps(result, sort_keys=True)); raise SystemExit(result["status"] != "pass")
