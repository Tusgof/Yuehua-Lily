"""Validate v4's closed E0 gate without touching a market container."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/l_4_breadth_b88r3_phase_a_execution_contract_v4.json"
REQUIRED = {"schema_version", "order_id", "gate_id", "supersedes_gate_id", "hypothesis_id", "status", "evidence_ceiling", "edge_claim", "v3_rejection", "owner_literal", "sources", "science", "activation", "execution_dependencies", "execution_binding", "validation_seal", "authorizations", "access_counts", "hard_stops"}

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def validate() -> dict:
    try: value = json.loads(GATE.read_text("ascii"))
    except Exception: return {"status":"blocked","blockers":["unreadable"]}
    blockers=[]
    if set(value)!=REQUIRED: blockers.append("closed_world")
    if {key:value.get(key) for key in ("schema_version","order_id","gate_id","supersedes_gate_id","hypothesis_id","evidence_ceiling","edge_claim","owner_literal")} != {"schema_version":"lily_l4_b88r3_phase_a_execution_contract_v4","order_id":"B8.8R3","gate_id":"l_4_breadth_b88r3_phase_a_execution_contract_v4","supersedes_gate_id":"l_4_breadth_b88r2_phase_a_execution_contract_v3","hypothesis_id":"L-4","evidence_ceiling":"E0","edge_claim":"none","owner_literal":"continue the work till we complete L4"}: blockers.append("identity")
    if value.get("validation_seal")!={"status":"sealed_not_accessed","accessed":False} or any(value.get("authorizations",{}).values()) or any(value.get("access_counts",{}).values()): blockers.append("seals")
    activation=value.get("activation",{})
    if activation.get("gate_owns_schema_owner_and_literal") is not True or activation.get("one_read_after_atomic_marker_only") is not True or activation.get("no_retry") is not True: blockers.append("future_contract")
    sources=value.get("sources",{})
    if not isinstance(sources,dict) or not sources or any(not isinstance(path,str) or not isinstance(digest,str) or len(digest)!=64 or not (ROOT/path).is_file() or sha(ROOT/path)!=digest for path,digest in sources.items()): blockers.append("source_binding")
    dependencies=value.get("execution_dependencies")
    binding=value.get("execution_binding")
    if not isinstance(dependencies,list) or not dependencies or not isinstance(binding,dict) or set(dependencies)!=set(binding) or any(not isinstance(path,str) or binding.get(path)!={"path":path,"sha256":binding.get(path,{}).get("sha256")} or not isinstance(binding[path].get("sha256"),str) or len(binding[path]["sha256"])!=64 or not (ROOT/path).is_file() or sha(ROOT/path)!=binding[path]["sha256"] for path in dependencies): blockers.append("execution_binding")
    science=value.get("science",{})
    if science != {"preregistration_path":"experiments/l_4_breadth_preregistration_v4.json","universe":["VTI","VGK","EWJ","VWO","IEF","TIP","GLD","DBC"],"u4":["VTI","IEF","GLD","DBC"],"cutoff_inclusive":"2015-12-31","timing":"actual last eligible U8 weekly session; next U8 common/NYSE session; next 20 sessions strictly after execution"}: blockers.append("science")
    return {"status":"pass" if not blockers else "blocked","blockers":blockers,"gate_sha256":sha(GATE)}
if __name__ == "__main__":
    result=validate(); print(json.dumps(result,sort_keys=True)); raise SystemExit(result["status"]!="pass")
