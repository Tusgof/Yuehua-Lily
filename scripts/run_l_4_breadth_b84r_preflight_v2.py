"""Run only the committed B8.4 synthetic fixture; no container interface exists."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b84_preflight import canonical_fixture_sha256
from scripts.validate_l_4_breadth_b84r_preflight_report_v2 import materialize_fixture, validate
FIXTURE=ROOT/'tests/fixtures/l4_b84/synthetic_preflight_report_v2.json'
GATE=ROOT/'experiments/l_4_breadth_b84r_activation_contract_v2.json'
def fixture_matches_gate(payload:dict)->bool:
 try:return canonical_fixture_sha256(payload)==json.loads(GATE.read_text(encoding='utf-8'))['implementation']['synthetic_fixture']['canonical_payload_sha256']
 except (OSError,KeyError,json.JSONDecodeError):return False
def run(path:Path)->dict:
 try:
  resolved=path.resolve(strict=True)
  if resolved!=FIXTURE.resolve():return {"status":"blocked","blockers":["synthetic_fixture_path_required"]}
  payload=json.loads(resolved.read_text(encoding='utf-8'))
  materialized=materialize_fixture(payload)
  return validate(materialized if materialized is not None else payload,committed_fixture=materialized is not None and fixture_matches_gate(payload))
 except Exception as exc:return {"status":"blocked","blockers":[type(exc).__name__]}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--synthetic-report',type=Path,required=True);a=p.parse_args();r=run(a.synthetic_report);print(json.dumps(r));raise SystemExit(r['status']!='pass')
