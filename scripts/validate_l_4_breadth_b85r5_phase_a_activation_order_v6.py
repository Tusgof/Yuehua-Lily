from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b85r5_structural_scanner_v6 import MAX_BYTES
GATE=ROOT/"experiments/l_4_breadth_b85r5_phase_a_activation_order_v6.json"
PATHS={"scanner":"lib/l4_b85r5_structural_scanner_v6.py","runner":"scripts/run_l_4_breadth_b85r5_phase_b_preflight_v6.py","report_schema":"schemas/l_4_breadth_b85r5_structural_preflight_report_v6.schema.json","activation_schema":"schemas/l_4_breadth_b85r5_phase_b_activation_v6.schema.json","report_validator":"scripts/validate_l_4_breadth_b85r5_structural_preflight_report_v6.py","synthetic_manifest":"tests/fixtures/l4_b85r5/structural_manifest_v6.json","synthetic_payload":"tests/fixtures/l4_b85r5/u8_symbol_session_dates_v6.json"}
def sha(path:Path)->str|None:
 try:
  raw=path.read_bytes()
  return hashlib.sha256(raw).hexdigest() if len(raw)<=MAX_BYTES else None
 except OSError:return None
def validate(path=GATE):
 try:g=json.loads(path.read_text(encoding="utf-8"))
 except Exception as exc:return {"status":"blocked","blockers":[type(exc).__name__]}
 expected={"schema_version":"lily_l4_b85r5_phase_a_activation_order_v6","order_id":"B8.5R5","phase":"A","gate_id":"l_4_breadth_b85r5_phase_a_activation_order_v6","supersedes_gate_id":"l_4_breadth_b85r4_phase_a_activation_order_v5","hypothesis_id":"L-4","evidence_ceiling":"E0","edge_claim":"none","validation_seal":{"status":"sealed_not_accessed","accessed":False}}
 bad=[]
 if not isinstance(g,dict) or any(g.get(k)!=v for k,v in expected.items()):bad.append("identity")
 if set(g.get("implementation",{}))!=set(PATHS):bad.append("implementation_shape")
 for key,path in PATHS.items():
  if g.get("implementation",{}).get(key)!={"path":path,"sha256":sha(ROOT/path)}:bad.append(key)
 lifecycle=g.get("future_phase_b_contract",{})
 if lifecycle.get("repo_relative_activation_record_path")!="experiments/activation_records/l_4_breadth_b85r5_phase_b_activation_v6.json" or lifecycle.get("exact_execution_flag")!="--execute-one-shot" or "accepted_gate_head_sha" not in lifecycle.get("activation_lifecycle",""):bad.append("lifecycle")
 if not isinstance(g.get("phase_a_authorizations"),dict) or not g["phase_a_authorizations"] or any(x is not False for x in g["phase_a_authorizations"].values()) or any(x!=0 for x in g.get("phase_a_access_counts",{}).values()):bad.append("sealed")
 return {"status":"pass" if not bad else "blocked","blockers":bad}
if __name__=="__main__":
 r=validate();print(json.dumps(r));raise SystemExit(r["status"]!="pass")
