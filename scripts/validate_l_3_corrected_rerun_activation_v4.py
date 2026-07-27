from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
GATE=ROOT/'experiments/l_3_corrected_rerun_activation_v4.json'
def validate(path:Path=GATE)->dict:
 try:p=json.loads(path.read_text())
 except Exception as e:return {'status':'blocked','blockers':[type(e).__name__]}
 top={'schema_version','order_id','gate_id','supersedes_gate_id','hypothesis_id','status','evidence_ceiling','edge_claim','source_binding','implementation','authorizations','attestation','hard_stops'}; b=[]
 if set(p)!=top or {k:p.get(k) for k in ('schema_version','order_id','gate_id','supersedes_gate_id','hypothesis_id','status','evidence_ceiling','edge_claim')}!={'schema_version':'lily_l3_corrected_rerun_activation_v4','order_id':'B7.8','gate_id':'l_3_corrected_rerun_activation_v4','supersedes_gate_id':'l_3_corrected_rerun_activation_v3','hypothesis_id':'L-3','status':'locked_synthetic_only_ci_portability_supersession','evidence_ceiling':'E0','edge_claim':'none'}:b.append('identity')
 s=p.get('source_binding',{});v=s.get('b7_8_v3',{}); old=ROOT/v.get('path','')
 if set(s)!={'b7_8_v3','whole_manifest_hash_binding','self_or_circular_hash_binding'} or not old.is_file() or file_sha256(old)!=v.get('sha256') or s.get('whole_manifest_hash_binding') is not False or s.get('self_or_circular_hash_binding') is not False:b.append('source_binding')
 for row in p.get('implementation',{}).values():
  if not isinstance(row,dict) or set(row)!={'path','sha256'} or not (ROOT/row.get('path','')).is_file() or file_sha256(ROOT/row['path'])!=row.get('sha256'):b.append('implementation')
 if set(p.get('implementation',{}))!={'runner','activation_validator','report_validator','report_schema','side_effect_library'} or not isinstance(p.get('authorizations'),dict) or any(p['authorizations'].values()) or p.get('attestation')!={'real_container_read_hash_count':0,'market_returns_read_count':0,'new_schedule_attestation_count':0,'fresh_ledger_row_count':0,'validation_status':'sealed_not_accessed'} or not isinstance(p.get('hard_stops'),list) or len(p['hard_stops'])!=5:b.append('zero_access_contract')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
