"""Fail-closed B7.7 no-data activation validator."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.io import relative_to_root
GATE=ROOT/'experiments/l_3_corrected_rerun_activation_v2.json'
def _sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def validate(path:Path=GATE)->dict:
 try:p=json.loads(path.read_text(encoding='utf-8'))
 except Exception as e:return {'status':'blocked','blockers':[f'unreadable:{type(e).__name__}']}
 keys={'schema_version','order_id','gate_id','supersedes_gate_id','hypothesis_id','status','evidence_ceiling','edge_claim','source_binding','implementation','authorizations','attestation','hard_stops'}
 b=[f'unknown:{x}' for x in set(p)-keys]+[f'missing:{x}' for x in keys-set(p)]
 expected={'schema_version':'lily_l3_corrected_rerun_activation_v2','order_id':'B7.7','gate_id':'l_3_corrected_rerun_activation_v2','supersedes_gate_id':'l_3_corrected_rerun_activation_v1','hypothesis_id':'L-3','status':'locked_synthetic_only_execution_contract_remediation','evidence_ceiling':'E0','edge_claim':'none'}
 b += [f'mismatch:{k}' for k,v in expected.items() if p.get(k)!=v]
 source=p.get('source_binding',{}); bound={'b7_5_path':'experiments/l_3_corrected_rerun_pre_return_schedule_v1.json','b7_5_sha256':'1202f477bf6d890dfb0b926b3bff9c775215762209627cb53e9c55b5c18957eb','b76_activation_path':'experiments/l_3_corrected_rerun_activation_v1.json','b76_activation_sha256':'f224afd2049f242413fb6db29ff6dfcee7802e9b50a05d860c0cdedefbd778df','b76_report_path':'reports/experiments/l_3_corrected_rerun_falsification_report.json','b76_report_sha256':'5ee3b970c39ab8bbefb18bf1427b7e960d19b5f58a759f0ef1654096e7974108','b74_path':'experiments/l_3_invalid_run_ledger_remediation_v1.json','b74_sha256':'c36194863346290c01583ef362a38fb64b2eb397145067fbbeec888ebcdaa51d'}
 b += [f'source_mismatch:{k}' for k,v in bound.items() if source.get(k)!=v]
 for key in ('b7_5','b76_activation','b76_report','b74'):
  rel=source.get(key+'_path'); digest=source.get(key+'_sha256')
  if not isinstance(rel,str) or not (ROOT/rel).is_file() or _sha(ROOT/rel)!=digest:b.append(f'source_hash_mismatch:{key}')
 if source.get('whole_manifest_hash_binding') is not False or source.get('self_or_circular_hash_binding') is not False:b.append('circular_binding')
 impl=p.get('implementation',{})
 for name,row in impl.items():
  if not isinstance(row,dict) or set(row)!={'path','sha256'} or not (ROOT/row.get('path','')).is_file() or _sha(ROOT/row['path'])!=row.get('sha256'):b.append(f'implementation_mismatch:{name}')
 if not isinstance(p.get('authorizations'),dict) or any(p['authorizations'].values()):b.append('authorization_drift')
 if p.get('attestation')!={'real_container_read_hash_count':0,'market_returns_read_count':0,'new_schedule_attestation_count':0,'fresh_ledger_row_count':0,'validation_status':'sealed_not_accessed'}:b.append('zero_access_attestation_mismatch')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r,sort_keys=True));raise SystemExit(0 if r['status']=='pass' else 1)
