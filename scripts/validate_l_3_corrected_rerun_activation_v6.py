"""Fail-closed B7.10 E0-only superseding gate."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
GATE=ROOT/'experiments/l_3_corrected_rerun_activation_v6.json'
IDENTITY={'schema_version':'lily_l3_corrected_rerun_activation_v6','order_id':'B7.10','gate_id':'l_3_corrected_rerun_activation_v6','supersedes_gate_id':'l_3_corrected_rerun_activation_v5','hypothesis_id':'L-3','status':'locked_synthetic_only_decision_integrity_remediation','evidence_ceiling':'E0','edge_claim':'none'}
IMPLEMENTATION={'runner':'scripts/run_l_3_corrected_rerun_v6.py','activation_validator':'scripts/validate_l_3_corrected_rerun_activation_v6.py','report_validator':'scripts/validate_l_3_corrected_rerun_report_v6.py','report_schema':'schemas/l_3_corrected_rerun_report_v6.schema.json','side_effect_library':'lib/l3_corrected_rerun_v6.py'}
AUTH={'real_container_access','container_hashing','date_column_inspection','return_parsing','execution','report_decision','validation_access','provider_network','credentials_environment','acquisition','paid_action','broker','paper_trade','real_money'}
ATTEST={'real_container_read_hash_count':0,'market_returns_read_count':0,'new_schedule_attestation_count':0,'fresh_ledger_row_count':0,'validation_status':'sealed_not_accessed'}
STOPS=['Synthetic fixtures only; no real container API, path, or hash is available in B7.10.','No return parsing, schedule attestation, execution, report decision, or ledger row is authorized.','Validation, provider, credential, broker, paid, paper-trade, and real-money access remain forbidden.','The locked L-3 universe, scientific semantics, MinTRL 49, 465 ceiling, and validation seal are unchanged.','No future run is authorized until Inspector acceptance and a new owner order.']
def manifest():
 for line in (ROOT/'experiments/locked_gates.jsonl').read_text().splitlines():
  x=json.loads(line)
  if x.get('gate_id')=='l_3_corrected_rerun_activation_v5':return {k:x.get(k) for k in ('gate_id','artifact_path','artifact_sha256','validator_path','validator_sha256')}
 return None
def validate(path:Path=GATE)->dict:
 try:p=json.loads(path.read_text())
 except Exception as e:return {'status':'blocked','blockers':[type(e).__name__]}
 b=[];top=set(IDENTITY)|{'source_binding','implementation','authorizations','attestation','hard_stops'}
 if set(p)!=top:b.append('top_shape')
 if any(p.get(k)!=v for k,v in IDENTITY.items()):b.append('identity')
 s=p.get('source_binding',{}); src=s.get('b7_9_v5',{}); old=ROOT/src.get('path','')
 if set(s)!={'b7_9_v5','whole_manifest_hash_binding','self_or_circular_hash_binding'} or not isinstance(src,dict) or set(src)!={'path','sha256','manifest_identity'} or src.get('path')!='experiments/l_3_corrected_rerun_activation_v5.json' or not old.is_file() or file_sha256(old)!=src.get('sha256') or src.get('manifest_identity')!=manifest() or s.get('whole_manifest_hash_binding') is not False or s.get('self_or_circular_hash_binding') is not False:b.append('source_binding')
 impl=p.get('implementation')
 if not isinstance(impl,dict) or set(impl)!=set(IMPLEMENTATION):b.append('implementation_shape')
 else:
  for k,path in IMPLEMENTATION.items():
   row=impl.get(k)
   if not isinstance(row,dict) or set(row)!={'path','sha256'} or row.get('path')!=path or not (ROOT/path).is_file() or file_sha256(ROOT/path)!=row.get('sha256'):b.append('implementation:'+k)
 if not isinstance(p.get('authorizations'),dict) or set(p['authorizations'])!=AUTH or any(type(v)is not bool or v is not False for v in p['authorizations'].values()):b.append('authorizations')
 if p.get('attestation')!=ATTEST:b.append('attestation')
 if p.get('hard_stops')!=STOPS:b.append('hard_stops')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
