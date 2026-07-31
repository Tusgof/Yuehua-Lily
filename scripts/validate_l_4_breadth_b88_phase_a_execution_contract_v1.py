"""Validate B8.8's append-only E0 scientific-execution contract."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; GATE=ROOT/"experiments/l_4_breadth_b88_phase_a_execution_contract_v1.json"; LOCKED=ROOT/"experiments/locked_gates_v2.jsonl"
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.l4_b88_scientific_contract_v1 import AUTHORIZATIONS, SEAL, U8

def sha(path: Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def validate(path: Path=GATE, *, require_manifest: bool=True)->dict:
    blockers=[]
    try: gate=json.loads(path.read_text("ascii")); v4=json.loads((ROOT/"experiments/l_4_breadth_preregistration_v4.json").read_text("ascii"))
    except Exception: return {"status":"blocked","blockers":["unreadable"]}
    required={"schema_version","order_id","gate_id","depends_on_gate_id","hypothesis_id","status","evidence_ceiling","edge_claim","science","source_binding","activation","validation_seal","authorizations","phase_a_access_counts","hard_stops","partial_worker_reconciliation"}
    identity={"schema_version":"lily_l4_b88_phase_a_execution_contract_v1","order_id":"B8.8","gate_id":"l_4_breadth_b88_phase_a_execution_contract_v1","depends_on_gate_id":"l_4_breadth_b87_phase_a_capacity_gate_v1","hypothesis_id":"L-4","status":"locked_E0_synthetic_scientific_execution_machinery","evidence_ceiling":"E0","edge_claim":"none"}
    if set(gate)!=required: blockers.append("closed_world")
    if any(gate.get(k)!=v for k,v in identity.items()): blockers.append("identity")
    if gate.get("science")!={"v4_path":"experiments/l_4_breadth_preregistration_v4.json","v4_sha256":sha(ROOT/"experiments/l_4_breadth_preregistration_v4.json"),"u8":list(U8),"falsification_end":"2015-12-31","observation_unit":"one weekly paired portfolio observation; never assets, sleeves, correlations, days, trades, or overlapping realized windows."}: blockers.append("science")
    expected={name:{"path":name,"sha256":sha(ROOT/name)} for name in ("experiments/l_4_breadth_b87_phase_a_capacity_gate_v1.json","experiments/l_4_breadth_b87_capacity_report_v1.json","experiments/l_4_breadth_b86r13_provisioning_gate_v15.json","experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json","experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json","experiments/l_1_baseline_preregistration.json","experiments/l_3_inverse_volatility_sizing_preregistration_v2.json","lib/l4_b88_scientific_contract_v1.py","schemas/l_4_breadth_b88_scientific_report_v1.schema.json","scripts/validate_l_4_breadth_b88_phase_a_execution_contract_v1.py","scripts/validate_l_4_breadth_b88_scientific_report_v1.py","scripts/run_l_4_breadth_b88_committed_bootstrap_v1.py")}
    if gate.get("source_binding")!=expected: blockers.append("source_binding")
    if gate.get("activation")!={"schema_version":"lily_l4_b88_scientific_execution_activation_v1","owner_reference":"B8.8 Phase A owner authorization","committed_bootstrap_required":True,"one_shot_required":True,"caller_may_not_set_schema_or_owner_reference":True}: blockers.append("activation")
    if gate.get("validation_seal")!=SEAL or gate.get("authorizations")!=AUTHORIZATIONS or any(gate.get("phase_a_access_counts",{}).values()): blockers.append("seals_or_access")
    if v4.get("primary_sizing",{}).get("step_1")!="u[i,t] = q[i,t] with no division by volatility.": blockers.append("v4_q")
    if require_manifest:
      try:
       rows=[json.loads(line) for line in LOCKED.read_text("ascii").splitlines() if line]; row=[x for x in rows if x.get("gate_id")==identity["gate_id"]]
       if len(row)!=1 or row[0].get("artifact_sha256")!=sha(path) or row[0].get("validator_sha256")!=sha(Path(__file__)): blockers.append("locked_manifest")
      except Exception: blockers.append("locked_manifest")
    return {"status":"pass" if not blockers else "blocked","blockers":sorted(set(blockers))}
if __name__=="__main__":
 result=validate(); print(json.dumps(result,sort_keys=True)); raise SystemExit(result["status"]!="pass")
