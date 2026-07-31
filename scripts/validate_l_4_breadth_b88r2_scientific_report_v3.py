"""Closed-world report validator that recomputes all future E1 evidence from raw weeks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.l4_b88_scientific_contract_v1 import METRICS, USEFUL
from lib.l4_b88r_scientific_engine_v2 import AUTHORIZATIONS, SEAL
from lib.l4_b88r2_scientific_engine_v3 import classify_outcome, constraints as derive_constraints, metric_statistics, regime_funding, robustness as derive_robustness, side_effects as derive_side_effects
from scripts.validate_l_4_breadth_b88r2_phase_a_execution_contract_v3 import GATE, sha, validate as gate

FIELDS = {"schema_version", "order_id", "hypothesis_id", "mode", "evidence_tier", "edge_claim", "provenance", "validation_seal", "authorizations", "access_counts", "weekly_observations", "metric_statistics", "constraints", "robustness", "side_effects", "regimes", "outcome", "autopsy"}


def validate(path: Path) -> dict:
    blockers = []
    try: report = json.loads(Path(path).read_text("ascii"))
    except Exception: return {"status": "blocked", "blockers": ["unreadable"]}
    if set(report) != FIELDS: blockers.append("closed_world")
    if {key: report.get(key) for key in ("schema_version", "order_id", "hypothesis_id", "edge_claim")} != {"schema_version": "lily_l4_b88r2_scientific_report_v3", "order_id": "B8.8R2", "hypothesis_id": "L-4", "edge_claim": "none"}: blockers.append("identity")
    if report.get("validation_seal") != SEAL or report.get("authorizations") != AUTHORIZATIONS or any(report.get("access_counts", {}).values()): blockers.append("seals")
    expected_provenance = {"gate_path": "experiments/l_4_breadth_b88r2_phase_a_execution_contract_v3.json", "gate_sha256": "synthetic_fixture" if report.get("mode") == "synthetic_fixture" else sha(GATE), "activation_schema": "lily_l4_b88r2_activation_v3"}
    if report.get("provenance") != expected_provenance: blockers.append("provenance")
    if report.get("mode") == "synthetic_fixture":
        if report.get("evidence_tier") != "E0" or report.get("outcome") != "blocked_before_activation" or report.get("weekly_observations") != [] or any(report.get(name) != {} for name in ("metric_statistics", "constraints", "robustness", "side_effects", "regimes")) or report.get("autopsy") is not None: blockers.append("synthetic")
    elif report.get("mode") == "future_falsification_only":
        rows = report.get("weekly_observations")
        statistics = metric_statistics(rows) if isinstance(rows, list) else None
        derived_constraints = derive_constraints(rows) if isinstance(rows, list) else None
        derived_side_effects = derive_side_effects(rows) if isinstance(rows, list) else None
        derived_robustness = derive_robustness(rows, statistics) if isinstance(rows, list) and statistics is not None else None
        derived_regimes = regime_funding(rows, statistics) if isinstance(rows, list) and statistics is not None else None
        if report.get("evidence_tier") != "E1" or None in (statistics, derived_constraints, derived_side_effects, derived_robustness, derived_regimes): blockers.append("raw_evidence")
        else:
            if report.get("metric_statistics") != statistics: blockers.append("metric_statistics")
            if report.get("constraints") != derived_constraints: blockers.append("constraints")
            if report.get("side_effects") != derived_side_effects: blockers.append("side_effects")
            if report.get("robustness") != derived_robustness: blockers.append("robustness")
            if report.get("regimes") != derived_regimes: blockers.append("regimes")
            constraints_pass = derived_constraints["pass"] and derived_side_effects["pass"] and all(item["pass"] for item in derived_robustness.values())
            expected = classify_outcome(statistics, constraints_evaluable=derived_constraints["evaluable"], constraints_pass=constraints_pass)
            if report.get("outcome") != expected: blockers.append("outcome_precedence")
            expected_autopsy = {"classification": "falsified_E1_only", "metric_breaches": [metric for metric in METRICS if statistics[metric]["falsify_ucb"] < USEFUL[metric]], "constraint_breach": not constraints_pass} if expected == "falsified_E1_only" else None
            if report.get("autopsy") != expected_autopsy: blockers.append("autopsy")
    else: blockers.append("mode")
    if gate().get("status") != "pass": blockers.append("gate")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("report", type=Path); argument = parser.parse_args()
    result = validate(argument.report); print(json.dumps(result, sort_keys=True)); raise SystemExit(result["status"] != "pass")
