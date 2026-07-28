from __future__ import annotations
import json,re,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.draft202012_subset import ValidationError,validate as schema_validate
from lib.l4_b86r2_provisioning_scanner_v3 import CUTOFF,U8
SCHEMA=ROOT/"schemas/l_4_breadth_b86r2_u8_session_dates_v3.schema.json"
def validate(value):
 b=[]
 try:schema_validate(json.loads(SCHEMA.read_text("ascii")),value)
 except (OSError,ValueError,ValidationError):b.append("schema")
 try:
  rows=value["session_dates_by_symbol"]
  if set(rows)!=set(U8) or not re.fullmatch(r"[0-9a-f]{64}",value["dataset_sha256"]):raise ValueError
  for s in U8:
   dates=rows[s]
   if not isinstance(dates,list) or not dates or dates!=sorted(set(dates)) or any(not isinstance(x,str) or date.fromisoformat(x).isoformat()!=x or x>CUTOFF for x in dates):raise ValueError
 except (KeyError,TypeError,ValueError):b.append("semantic")
 return {"status":"pass" if not b else "blocked","blockers":b}
