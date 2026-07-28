from __future__ import annotations
import json,re,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.draft202012_subset import ValidationError,validate as schema_validate
from lib.l4_b86r2_provisioning_scanner_v3 import CUTOFF,U8
SCHEMA=ROOT/"schemas/l_4_breadth_b86r2_falsification_manifest_v3.schema.json"
def validate(value):
 b=[]
 try:schema_validate(json.loads(SCHEMA.read_text("ascii")),value)
 except (OSError,ValueError,ValidationError):b.append("schema")
 try:
  c=value["coverage_by_symbol"]
  if set(c)!=set(U8) or not re.fullmatch(r"[0-9a-f]{64}",value["dataset_sha256"]) or not isinstance(value["dataset_byte_count"],int) or value["dataset_byte_count"]<1:raise ValueError
  total=0
  for symbol in U8:
   row=c[symbol]
   if not isinstance(row,dict) or set(row)!={"start","end","row_count"} or not isinstance(row["row_count"],int) or row["row_count"]<1:raise ValueError
   for key in ("start","end"):
    if not isinstance(row[key],str) or date.fromisoformat(row[key]).isoformat()!=row[key] or row[key]>CUTOFF:raise ValueError
   if row["start"]>row["end"]:raise ValueError
   total+=row["row_count"]
  if total!=value["session_count"]:raise ValueError
 except (KeyError,TypeError,ValueError):b.append("semantic")
 return {"status":"pass" if not b else "blocked","blockers":b}
