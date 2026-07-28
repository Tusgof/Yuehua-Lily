from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=ROOT/"experiments/l_4_breadth_b86r5_provisioning_gate_v6.json"
def validate():
 try:g=json.loads(P.read_text("ascii"));ok=g["gate_id"]=="l_4_breadth_b86r5_provisioning_gate_v6" and g["supersedes_gate_id"]=="l_4_breadth_b86r4_provisioning_gate_v5" and g["execution_flag"]=="--execute-one-shot" and not any(g["authorizations"].values()) and all(hashlib.sha256((ROOT/x["path"]).read_bytes()).hexdigest()==x["sha256"] for x in g["source_binding"].values())
 except Exception:ok=False
 return {"status":"pass" if ok else "blocked"}
if __name__=="__main__":
 r=validate();print(json.dumps(r));raise SystemExit(r["status"]!="pass")
