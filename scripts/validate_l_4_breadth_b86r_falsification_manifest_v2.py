from __future__ import annotations
import json,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b86r_provisioning_scanner_v2 import CUTOFF,U8
PATH=ROOT/"experiments/provisioned/l_4_breadth_b86r_falsification_manifest_v2.json"
def validate(value=None):
 try: value=json.loads(PATH.read_text("ascii")) if value is None else value
 except (OSError,ValueError) as exc:return {"status":"blocked","blockers":[type(exc).__name__]}
 keys={"schema_version","dataset_reference","dataset_sha256","dataset_byte_count","u8_members_in_order","coverage_by_symbol","session_count","max_session_date","validation_seal"}; b=[]
 if not isinstance(value,dict) or set(value)!=keys or value.get("schema_version")!="lily_l4_b86r_falsification_manifest_v2" or value.get("dataset_reference")!="data/normalized/l1_yahoo_daily_v1.json" or value.get("u8_members_in_order")!=list(U8) or value.get("validation_seal")!={"status":"sealed_not_accessed","accessed":False}:b.append("shape")
 try:
  coverage=value["coverage_by_symbol"]; count=sum(coverage[s]["row_count"] for s in U8)
  if set(coverage)!=set(U8) or value["session_count"]!=count or value["max_session_date"]>CUTOFF or any(date.fromisoformat(coverage[s]["start"]).isoformat()!=coverage[s]["start"] or date.fromisoformat(coverage[s]["end"]).isoformat()!=coverage[s]["end"] or coverage[s]["start"]>coverage[s]["end"] or coverage[s]["end"]>CUTOFF or not isinstance(coverage[s]["row_count"],int) or coverage[s]["row_count"]<1 for s in U8):b.append("coverage")
 except (KeyError,TypeError,ValueError):b.append("coverage")
 return {"status":"pass" if not b else "blocked","blockers":sorted(set(b))}
if __name__=="__main__":r=validate();print(json.dumps(r));raise SystemExit(r["status"]!="pass")
