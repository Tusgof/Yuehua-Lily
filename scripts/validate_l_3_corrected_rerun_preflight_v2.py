"""Validate B7.7 synthetic-only structural scanning and schedule construction."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l3_corrected_rerun_v2 import scan_synthetic_envelope
FIXTURE=ROOT/'tests/fixtures/l3_corrected_rerun_v2/synthetic_envelope.json'
def validate(path:Path=FIXTURE)->dict:
 try: payload=json.loads(path.read_text(encoding='utf-8'))
 except Exception as exc:return {'status':'blocked','blockers':[f'fixture_unreadable:{type(exc).__name__}']}
 result=scan_synthetic_envelope(payload)
 if result.get('return_values_exposed') is not False:result.setdefault('blockers',[]).append('return_values_exposed')
 return result
def main()->int:
 r=validate();print(json.dumps(r,indent=2,sort_keys=True));return 0 if r['status']=='pass' else 1
if __name__=='__main__':raise SystemExit(main())
