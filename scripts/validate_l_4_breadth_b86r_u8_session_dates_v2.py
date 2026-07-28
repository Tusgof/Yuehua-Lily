from __future__ import annotations
import json,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b86r_provisioning_scanner_v2 import CUTOFF,U8
PATH=ROOT/"experiments/provisioned/l_4_breadth_b86r_u8_session_dates_v2.json"
def validate(value=None):
 try:value=json.loads(PATH.read_text("ascii")) if value is None else value
 except (OSError,ValueError) as exc:return {"status":"blocked","blockers":[type(exc).__name__]}
 keys={"schema_version","dataset_sha256","u8_members_in_order","session_dates_by_symbol"};b=[]
 if not isinstance(value,dict) or set(value)!=keys or value.get("schema_version")!="lily_l4_b86r_u8_session_dates_v2" or value.get("u8_members_in_order")!=list(U8):b.append("shape")
 try:
  rows=value["session_dates_by_symbol"]
  if set(rows)!=set(U8) or any(not isinstance(rows[s],list) or not rows[s] or rows[s]!=sorted(set(rows[s])) or any(date.fromisoformat(x).isoformat()!=x or x>CUTOFF for x in rows[s]) for s in U8):b.append("sessions")
 except (KeyError,TypeError,ValueError):b.append("sessions")
 return {"status":"pass" if not b else "blocked","blockers":sorted(set(b))}
if __name__=="__main__":r=validate();print(json.dumps(r));raise SystemExit(r["status"]!="pass")
