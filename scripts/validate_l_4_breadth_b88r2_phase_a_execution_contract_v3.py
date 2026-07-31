from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/l_4_breadth_b88r2_phase_a_execution_contract_v3.json"
LOCKED = ROOT / "experiments/locked_gates_v2.jsonl"
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.l4_b88r2_lifecycle_v3 import DEPENDENCIES, GATE as GATE_REL
from lib.l4_b88r_scientific_engine_v2 import AUTHORIZATIONS, SEAL


def sha(path: Path) -> str: return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(path: Path = GATE, *, require_manifest: bool = True) -> dict:
    blockers = []
    try: gate = json.loads(Path(path).read_text("ascii"))
    except Exception: return {"status": "blocked", "blockers": ["unreadable"]}
    required = {"schema_version", "order_id", "gate_id", "supersedes_gate_id", "hypothesis_id", "status", "evidence_ceiling", "edge_claim", "v2_rejection", "science", "activation", "execution_dependencies", "execution_binding", "e1_report_required", "validation_seal", "authorizations", "access_counts", "hard_stops"}
    if set(gate) != required: blockers.append("closed_world")
    if {key: gate.get(key) for key in ("schema_version", "order_id", "gate_id", "supersedes_gate_id", "hypothesis_id", "status", "evidence_ceiling", "edge_claim")} != {"schema_version": "lily_l4_b88r2_phase_a_execution_contract_v3", "order_id": "B8.8R2", "gate_id": "l_4_breadth_b88r2_phase_a_execution_contract_v3", "supersedes_gate_id": "l_4_breadth_b88r_phase_a_execution_contract_v2", "hypothesis_id": "L-4", "status": "locked_E0_synthetic_complete_future_contract_v3", "evidence_ceiling": "E0", "edge_claim": "none"}: blockers.append("identity")
    activation = gate.get("activation", {})
    if activation.get("schema_version") != "lily_l4_b88r2_activation_v3" or activation.get("owner_reference") != "B8.8R2 Phase A owner authorization" or activation.get("activation_path") != "experiments/activation_records/l_4_breadth_b88r2_scientific_execution_activation_v3.json" or any(activation.get(name) is not True for name in ("builder_has_no_schema_or_owner_arguments", "git_show_pre_import_blob_check", "dirty_dependencies_rejected")): blockers.append("activation")
    expected = {relative: {"path": relative, "sha256": sha(ROOT / relative)} for relative in DEPENDENCIES if relative != GATE_REL}
    if gate.get("execution_dependencies") != list(DEPENDENCIES) or gate.get("execution_binding") != expected: blockers.append("source_binding")
    if gate.get("science") != {"v4_path": "experiments/l_4_breadth_preregistration_v4.json", "falsification_end": "2015-12-31", "observation_unit": "one matched U4/U8 weekly portfolio observation"}: blockers.append("science")
    if gate.get("validation_seal") != SEAL or gate.get("authorizations") != AUTHORIZATIONS or any(gate.get("access_counts", {}).values()): blockers.append("seals")
    if not isinstance(gate.get("e1_report_required"), dict) or set(gate["e1_report_required"]) != {"weekly_observation_unit", "raw_evidence", "derived"}: blockers.append("e1_shape")
    if require_manifest:
        try:
            rows = [json.loads(line) for line in LOCKED.read_text("ascii").splitlines() if line]
            matched = [row for row in rows if row.get("gate_id") == gate.get("gate_id")]
            if not matched or matched[-1].get("artifact_sha256") != sha(path) or matched[-1].get("validator_sha256") != sha(Path(__file__)): blockers.append("locked_manifest")
        except Exception: blockers.append("locked_manifest")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate(); print(json.dumps(result, sort_keys=True)); raise SystemExit(result["status"] != "pass")
