"""Fail-closed B7.12 E0-only fixture-bound remediation gate."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
GATE=ROOT/'experiments/l_3_corrected_rerun_activation_v8.json'
IDENTITY={'schema_version':'lily_l3_corrected_rerun_activation_v8','order_id':'B7.12','gate_id':'l_3_corrected_rerun_activation_v8','supersedes_gate_id':'l_3_corrected_rerun_activation_v7','hypothesis_id':'L-3','status':'locked_synthetic_only_deterministic_boundary_remediation','evidence_ceiling':'E0','edge_claim':'none'}
IMPLEMENTATION={'runner':'scripts/run_l_3_corrected_rerun_v8.py','activation_validator':'scripts/validate_l_3_corrected_rerun_activation_v8.py','report_validator':'scripts/validate_l_3_corrected_rerun_report_v8.py','report_schema':'schemas/l_3_corrected_rerun_report_v8.schema.json','observation_derivation_library':'lib/l3_corrected_rerun_v8.py'}
FIXTURE={'path':'tests/fixtures/l3_corrected_rerun_v8/synthetic_evaluation.json','sha256':'52a62468f94eb87c9df07c3d89bb8094e209671d1fa427d849c4cbd2d1f40007','observations_sha256':'c15133d1989a12e47f084b4db5ff66d72273829dc175d3a7ae8c0d13162c4cab'}
AUTH={'real_container_access','container_hashing','date_column_inspection','return_parsing','execution','report_decision','validation_access','provider_network','credentials_environment','acquisition','paid_action','broker','paper_trade','real_money'}
ATTEST={'real_container_read_hash_count':0,'market_returns_read_count':0,'new_schedule_attestation_count':0,'fresh_ledger_row_count':0,'validation_status':'sealed_not_accessed'}
STOPS=['Synthetic observations only; no real container API, path, or hash is available in B7.12.','No return parsing, schedule attestation, execution, report decision, or ledger row is authorized.','Validation, provider, credential, broker, paid, paper-trade, and real-money access remain forbidden.','The locked L-3 universe, scientific semantics, MinTRL 49, 465 ceiling, and validation seal are unchanged.','No future run is authorized until Inspector acceptance and a new owner order.']
def manifest():
 for line in (ROOT/'experiments/locked_gates.jsonl').read_text(encoding='utf-8').splitlines():
  row=json.loads(line)
  if row.get('gate_id')=='l_3_corrected_rerun_activation_v7':return {key:row.get(key) for key in ('gate_id','artifact_path','artifact_sha256','validator_path','validator_sha256')}
 return None
def validate(path:Path=GATE)->dict:
 try:p=json.loads(path.read_text(encoding='utf-8'))
 except Exception as exc:return {'status':'blocked','blockers':[type(exc).__name__]}
 blockers=[];top=set(IDENTITY)|{'source_binding','implementation','synthetic_fixture','authorizations','attestation','hard_stops'}
 if set(p)!=top:blockers.append('top_shape')
 if any(p.get(key)!=value for key,value in IDENTITY.items()):blockers.append('identity')
 source=p.get('source_binding',{});prior=source.get('b7_11_v7',{});old=ROOT/prior.get('path','')
 if set(source)!={'b7_11_v7','whole_manifest_hash_binding','self_or_circular_hash_binding'} or not isinstance(prior,dict) or set(prior)!={'path','sha256','manifest_identity'} or prior.get('path')!='experiments/l_3_corrected_rerun_activation_v7.json' or not old.is_file() or file_sha256(old)!=prior.get('sha256') or prior.get('manifest_identity')!=manifest() or source.get('whole_manifest_hash_binding') is not False or source.get('self_or_circular_hash_binding') is not False:blockers.append('source_binding')
 implementation=p.get('implementation')
 if not isinstance(implementation,dict) or set(implementation)!=set(IMPLEMENTATION):blockers.append('implementation_shape')
 else:
  for name,relative in IMPLEMENTATION.items():
   row=implementation.get(name)
   if not isinstance(row,dict) or set(row)!={'path','sha256'} or row.get('path')!=relative or not (ROOT/relative).is_file() or file_sha256(ROOT/relative)!=row.get('sha256'):blockers.append('implementation:'+name)
 fixture=p.get('synthetic_fixture');fixture_path=ROOT/FIXTURE['path']
 if fixture!=FIXTURE or not fixture_path.is_file() or file_sha256(fixture_path)!=FIXTURE['sha256'] or json.loads(fixture_path.read_text(encoding='utf-8')).get('closed_world_observations_sha256')!=FIXTURE['observations_sha256']:blockers.append('synthetic_fixture')
 if not isinstance(p.get('authorizations'),dict) or set(p['authorizations'])!=AUTH or any(type(value)is not bool or value for value in p['authorizations'].values()):blockers.append('authorizations')
 if p.get('attestation')!=ATTEST:blockers.append('attestation')
 if p.get('hard_stops')!=STOPS:blockers.append('hard_stops')
 return {'status':'pass' if not blockers else 'blocked','blockers':sorted(set(blockers))}
if __name__=='__main__':
 result=validate();print(json.dumps(result));raise SystemExit(result['status']!='pass')
