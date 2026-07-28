"""Run only an explicit committed B7.11 synthetic report; never executes research."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l3_corrected_rerun_v7 import MINTRL_FLOOR
from scripts.validate_l_3_corrected_rerun_report_v7 import validate
FIXTURES=ROOT/"tests"/"fixtures"/"l3_corrected_rerun_v7"
def main()->int:
 parser=argparse.ArgumentParser(description="Derive B7.11 synthetic observations only.");parser.add_argument("--synthetic-report",type=Path,required=True);args=parser.parse_args()
 try: path=args.synthetic_report.resolve(strict=True);path.relative_to(FIXTURES.resolve());payload=json.loads(path.read_text(encoding="utf-8"))
 except (OSError,ValueError,json.JSONDecodeError):print(json.dumps({"status":"blocked","blockers":["synthetic_report_path_required"]}));return 1
 result=validate(payload);print(json.dumps(result,sort_keys=True));return result["status"]!="pass"
if __name__=="__main__":raise SystemExit(main())
