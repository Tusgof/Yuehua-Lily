"""B7.7 synthetic-only v2 contract demonstrator; it cannot resolve a real container."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.l3_corrected_rerun_v2 import scan_synthetic_envelope
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--synthetic-fixture',type=Path,required=True);a=p.parse_args()
 payload=json.loads(a.synthetic_fixture.read_text(encoding='utf-8'))
 result=scan_synthetic_envelope(payload);print(json.dumps(result,sort_keys=True));return 0 if result['status']=='pass' else 1
if __name__=='__main__':raise SystemExit(main())
