from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];GATE=ROOT/"experiments/l_4_breadth_b86r2_provisioning_gate_v3.json"
if str(ROOT) not in __import__("sys").path: __import__("sys").path.insert(0,str(ROOT))
from lib.io import load_json
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def validate():
 try:g=json.loads(GATE.read_text("ascii"))
 except (OSError,ValueError) as e:return {"status":"blocked","blockers":[type(e).__name__]}
 required={"schema_version":"lily_l4_b86r2_provisioning_gate_v3","order_id":"B8.6R2","phase":"A","gate_id":"l_4_breadth_b86r2_provisioning_gate_v3","supersedes_gate_id":"l_4_breadth_b86r_provisioning_gate_v2","hypothesis_id":"L-4","evidence_ceiling":"E0","edge_claim":"none","validation_seal":{"status":"sealed_not_accessed","accessed":False}}
 b=[]
 if any(g.get(k)!=v for k,v in required.items()):b.append("identity")
 for group in ("source_binding","implementation"):
  if not g.get(group):b.append(group);continue
  for item in g[group].values():
   try:
    if not isinstance(item,dict) or sha(ROOT/item["path"])!=item["sha256"]:b.append(group)
   except (KeyError,OSError):b.append(group)
 return {"status":"pass" if not b else "blocked","blockers":sorted(set(b))}
if __name__=="__main__":r=validate();print(json.dumps(r));raise SystemExit(r["status"]!="pass")
