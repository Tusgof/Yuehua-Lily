"""Run the sole gate-bound B7.12 fixture; no research execution interface exists."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
from scripts.validate_l_3_corrected_rerun_report_v8 import validate
GATE=ROOT/'experiments/l_3_corrected_rerun_activation_v8.json'
FIXTURE_ROOT=ROOT/'tests'/'fixtures'/'l3_corrected_rerun_v8'
def fixture_identity()->dict:
 return json.loads(GATE.read_text(encoding='utf-8'))['synthetic_fixture']
def run_fixture(path:Path)->dict:
 try:resolved=path.resolve(strict=True);expected=FIXTURE_ROOT/'synthetic_evaluation.json';identity=fixture_identity();resolved.relative_to(FIXTURE_ROOT.resolve())
 except (OSError,ValueError,KeyError,json.JSONDecodeError):return {'status':'blocked','blockers':['synthetic_fixture_path_required']}
 if resolved!=expected.resolve() or set(identity)!={'path','sha256','observations_sha256'} or identity.get('path')!='tests/fixtures/l3_corrected_rerun_v8/synthetic_evaluation.json' or file_sha256(resolved)!=identity.get('sha256'):return {'status':'blocked','blockers':['synthetic_fixture_identity_mismatch']}
 try:return validate(json.loads(resolved.read_text(encoding='utf-8')))
 except Exception as exc:return {'status':'blocked','blockers':[f'unreadable:{type(exc).__name__}']}
def main()->int:
 parser=argparse.ArgumentParser(description='Run only B7.12 gate-bound synthetic fixture.');parser.add_argument('--synthetic-report',type=Path,required=True);args=parser.parse_args();result=run_fixture(args.synthetic_report);print(json.dumps(result,sort_keys=True));return result['status']!='pass'
if __name__=='__main__':raise SystemExit(main())
