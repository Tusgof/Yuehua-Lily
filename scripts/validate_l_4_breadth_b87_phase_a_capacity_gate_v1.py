"""Validate the locked L-4 B8.7 no-return capacity gate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/l_4_breadth_b87_phase_a_capacity_gate_v1.json"
LOCKED = ROOT / "experiments/locked_gates_v2.jsonl"

if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))
from lib.l4_b87_capacity_contract_v1 import AUTHORIZATIONS, SEAL, derive, sha256_path


def _sources() -> dict:
    paths = {
        "science": "experiments/l_4_breadth_preregistration_v4.json",
        "science_validator": "scripts/validate_l_4_breadth_preregistration_v4.py",
        "provisioning_gate": "experiments/l_4_breadth_b86r13_provisioning_gate_v15.json",
        "provisioning_report": "reports/experiments/l_4_breadth_b86r13_provisioning_report_v15.json",
        "structural_manifest": "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json",
        "u8_session_dates": "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json",
        "contract": "lib/l4_b87_capacity_contract_v1.py",
        "future_preflight": "scripts/run_l_4_breadth_b87_scientific_execution_preflight_v1.py",
        "report_schema": "schemas/l_4_breadth_b87_capacity_report_v1.schema.json",
        "validator": "scripts/validate_l_4_breadth_b87_phase_a_capacity_gate_v1.py",
    }
    return {name: {"path": path, "sha256": sha256_path(ROOT / path)} for name, path in paths.items()}


def validate(path: Path = GATE, *, require_manifest: bool = True) -> dict:
    blockers: list[str] = []
    try:
        gate = json.loads(path.read_text("ascii"))
        science = json.loads((ROOT / "experiments/l_4_breadth_preregistration_v4.json").read_text("ascii"))
        capacity = derive(science, ROOT / "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json", ROOT / "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json")
    except (OSError, ValueError, TypeError) as exc:
        return {"status": "blocked", "blockers": [f"unreadable_or_structural:{exc.__class__.__name__}"]}
    expected_keys = {"schema_version", "order_id", "gate_id", "depends_on_gate_id", "hypothesis_id", "status", "evidence_ceiling", "edge_claim", "source_binding", "source_git_provenance", "capacity", "validation_seal", "authorizations", "phase_a_access_counts", "lifecycle", "hard_stops"}
    identity = {"schema_version": "lily_l4_b87_phase_a_capacity_gate_v1", "order_id": "B8.7", "gate_id": "l_4_breadth_b87_phase_a_capacity_gate_v1", "depends_on_gate_id": "l_4_breadth_b86r13_provisioning_gate_v15", "hypothesis_id": "L-4", "status": "locked_E0_capacity_funded_execution_forbidden", "evidence_ceiling": "E0", "edge_claim": "none"}
    if not isinstance(gate, dict) or set(gate) != expected_keys:
        blockers.append("closed_world")
    if not isinstance(gate, dict) or any(gate.get(key) != value for key, value in identity.items()):
        blockers.append("identity")
    if not isinstance(gate, dict) or gate.get("source_binding") != _sources():
        blockers.append("source_binding")
    if gate.get("source_git_provenance") != {"structural_provisioning_commit": "d06001b54a80321b9b7be356ef808670b17dfba6", "phase_a_base_commit": "5079cdb145b9d0dacdad15933ce18fd5f740fa37"}:
        blockers.append("git_provenance")
    if gate.get("capacity") != capacity:
        blockers.append("capacity")
    if gate.get("validation_seal") != SEAL or gate.get("authorizations") != AUTHORIZATIONS:
        blockers.append("seals")
    if gate.get("phase_a_access_counts") != {"committed_structural_manifest_read_count": 0, "committed_u8_session_date_payload_read_count": 0, "market_return_signal_position_covariance_regime_cost_pnl_read_count": 0, "validation_access_count": 0, "activation_count": 0, "execution_count": 0}:
        blockers.append("access_counts")
    if gate.get("lifecycle") != {"phase_a_capacity_derivation": "locked_once_in_committed_report_only", "later_activation_authorized": False, "later_execution_authorized": False, "scientific_execution_preflight": "scripts/run_l_4_breadth_b87_scientific_execution_preflight_v1.py always blocks"}:
        blockers.append("lifecycle")
    required_stops = {"No price, return, signal, position, covariance, regime, cost, or PnL read or computation.", "No validation-window access, activation record, scientific execution, backtest, provider, network, credential, broker, paid, paper-trade, or real-money action.", "Do not treat weekly slots as assets, days, correlations, trades, or overlapping twenty-session windows; each metric funds its own MinTRL only.", "Capacity funding is planning-only and cannot replace each metric's actual weekly paired MinTRL recalculation or authorize an E1 outcome."}
    if set(gate.get("hard_stops", [])) != required_stops:
        blockers.append("hard_stops")
    if require_manifest:
        try:
            rows = [json.loads(line) for line in LOCKED.read_text("ascii").splitlines() if line]
            matches = [row for row in rows if row.get("gate_id") == identity["gate_id"]]
            if len(matches) != 1 or matches[0].get("artifact_path") != "experiments/l_4_breadth_b87_phase_a_capacity_gate_v1.json" or matches[0].get("artifact_sha256") != sha256_path(path) or matches[0].get("validator_path") != "scripts/validate_l_4_breadth_b87_phase_a_capacity_gate_v1.py" or matches[0].get("validator_sha256") != sha256_path(Path(__file__)):
                blockers.append("locked_manifest")
        except (OSError, ValueError, TypeError):
            blockers.append("locked_manifest")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate(); print(json.dumps(result, sort_keys=True)); raise SystemExit(result["status"] != "pass")
