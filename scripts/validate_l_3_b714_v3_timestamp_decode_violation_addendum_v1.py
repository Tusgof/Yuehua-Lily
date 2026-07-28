from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
P=ROOT/'experiments/l_3_b714_v3_timestamp_decode_violation_addendum_v1.json';R=ROOT/'reports/experiments/l_3_b714_date_only_preflight_report_v3.json'
def validate()->dict:
 try:x=json.loads(P.read_text(encoding='utf8'));r=json.loads(R.read_text(encoding='utf8'))
 except (OSError,json.JSONDecodeError) as e:return {'status':'blocked','blockers':[type(e).__name__]}
 b=[]
 if x.get('schema_version')!='lily_l3_b714_v3_timestamp_decode_violation_addendum_v1' or x.get('checkpoint_git_commit')!='99e33857064e6eec76baba21ea64d9aaecea578f' or x.get('v3_report',{}).get('sha256')!=file_sha256(R) or r.get('outcome')!='scope_restricted' or r.get('preflight',{}).get('blocker')!='unknown_structural_key':b.append('historical_identity')
 if x.get('violation',{}).get('forbidden_timestamp_utf8_text_decode_count')!=1 or x.get('violation',{}).get('semantic_timestamp_parsing_count')!=0 or x.get('attestation_created') is not False or x.get('zero_access_counts')!={'session_date':0,'return':0,'research_decision':0,'ledger':0,'validation':0,'provider':0,'broker':0}:b.append('violation_accounting')
 return {'status':'pass' if not b else 'blocked','blockers':b}
if __name__=='__main__':
 z=validate();print(json.dumps(z));raise SystemExit(z['status']!='pass')
