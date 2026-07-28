from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b86r4_output_contract_v5 import validate_outputs
def validate(manifest,payload):
 return {"status":"pass" if validate_outputs(manifest,payload) else "blocked"}
if __name__=="__main__":
 try: result=validate(json.loads(Path(sys.argv[1]).read_text("ascii")),json.loads(Path(sys.argv[2]).read_text("ascii")))
 except (IndexError,OSError,ValueError): result={"status":"blocked"}
 print(json.dumps(result));raise SystemExit(result["status"]!="pass")
