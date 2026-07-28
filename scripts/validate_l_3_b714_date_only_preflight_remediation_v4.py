from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
P=ROOT/'experiments/l_3_b714_date_only_preflight_remediation_v4.json'
def validate()->dict:
 x=json.loads(P.read_text(encoding='utf8'));b=[]
 if x.get('evidence_ceiling')!='E0' or x.get('edge_claim')!='none' or any(v is not False for v in x.get('authorizations',{}).values()):b.append('authorizations')
 if x.get('source_binding',{}).get('v3_report_sha256')!=file_sha256(ROOT/'reports/experiments/l_3_b714_date_only_preflight_report_v3.json'):b.append('v3_report')
 for p in x.get('artifact_paths',{}).values():
  if not (ROOT/p).is_file():b.append('artifact_paths')
 return {'status':'pass' if not b else 'blocked','blockers':b}
if __name__=='__main__':
 r=validate();print(r);raise SystemExit(r['status']!='pass')
