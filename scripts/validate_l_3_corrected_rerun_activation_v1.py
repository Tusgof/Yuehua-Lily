"""Fail-closed B7.6 activation validator; it never opens the approved container."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.io import load_jsonl,relative_to_root
GATE=ROOT/'experiments/l_3_corrected_rerun_activation_v1.json'; MANIFEST=ROOT/'experiments/locked_gates.jsonl'
PATHS={'b7_5_gate':('experiments/l_3_corrected_rerun_pre_return_schedule_v1.json','1202f477bf6d890dfb0b926b3bff9c775215762209627cb53e9c55b5c18957eb'),'l3_v2':('experiments/l_3_inverse_volatility_sizing_preregistration_v2.json','83a68792614ee0def3ddb96349d6d95c7f0aeb0ac8b1c984c1e3d29ed74e709e'),'l3_v1':('experiments/l_3_inverse_volatility_sizing_preregistration_v1.json','0e0aaf281c75a450bbdf1015c1f400fc7ce8a398952ea25ddbb0ba2f4557c2b0'),'b7_4_remediation':('experiments/l_3_invalid_run_ledger_remediation_v1.json','c36194863346290c01583ef362a38fb64b2eb397145067fbbeec888ebcdaa51d')}
IMPL={'runner_path':'scripts/run_l_3_corrected_rerun.py','runner_sha256':'1c214fc90a0aad48152005d386adc1d7ddc7c236a5a67ffd4e1edc5a6da8a379','report_validator_path':'scripts/validate_l_3_corrected_rerun_report.py','report_validator_sha256':'1179ca61dfdf70cd53a85ebaca386a7b9046a5d80beb67272cf8ff307679edd5','report_schema_path':'schemas/l_3_corrected_rerun_falsification_report.schema.json','report_schema_sha256':'f76008643cdf0d292c62fa5bcc79fa61624f650537c3fd27541c5e33453a39db'}
AUTH={'data_access_authorized':True,'container_inspection_authorized':True,'date_column_inspection_authorized':True,'return_parsing_authorized_after_attestation':True,'execution_authorized':True,'report_decision_authorized':True,'validation_access_authorized':False,'provider_network_authorized':False,'credentials_environment_authorized':False,'acquisition_authorized':False,'paid_action_authorized':False,'broker_authorized':False,'paper_trade_authorized':False,'real_money_authorized':False}
KEYS={'schema_version','order_id','gate_id','hypothesis_id','status','evidence_ceiling','edge_claim','owner_authorization','source_binding','approved_container','fresh_namespace','execution_implementation','authorizations','hard_stops'}
def _sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def validate_activation(path:Path=GATE)->dict[str,Any]:
 b=[]
 try:p=json.loads(path.read_text(encoding='utf-8'))
 except Exception as e:return {'status':'blocked','blockers':[f'activation_unreadable:{type(e).__name__}']}
 b += [f'unknown_top_level_field:{x}' for x in set(p)-KEYS]+[f'missing_top_level_field:{x}' for x in KEYS-set(p)]
 root={'schema_version':'lily_l3_corrected_rerun_activation_v1','order_id':'B7.6','gate_id':'l_3_corrected_rerun_activation_v1','hypothesis_id':'L-3','status':'locked_exactly_one_corrected_falsification_rerun_authorized','evidence_ceiling':'E1','edge_claim':'none'}
 b += [f'root_mismatch:{k}' for k,v in root.items() if p.get(k)!=v]
 if p.get('authorizations')!=AUTH:b.append('authorization_drift')
 if p.get('execution_implementation')!=IMPL:b.append('implementation_declaration_drift')
 for key,(rel,digest) in PATHS.items():
  value=p.get('source_binding',{}).get(key,{})
  if value.get('path')!=rel or value.get('sha256')!=digest or not (ROOT/rel).is_file() or _sha(ROOT/rel)!=digest:b.append(f'source_binding_mismatch:{key}')
 if p.get('source_binding',{}).get('whole_manifest_hash_binding') is not False or p.get('source_binding',{}).get('self_or_circular_hash_binding') is not False:b.append('circular_or_whole_manifest_binding')
 try: rows=load_jsonl(MANIFEST)
 except Exception:rows=[];b.append('manifest_unreadable')
 identity=p.get('source_binding',{}).get('b7_5_gate',{}).get('manifest_identity')
 match=[x for x in rows if x.get('gate_id')=='l_3_corrected_rerun_pre_return_schedule_v1']
 if len(match)!=1 or identity is None or any(match[0].get(k)!=v for k,v in identity.items()):b.append('b7_5_manifest_identity_mismatch')
 for key,value in IMPL.items():
  if key.endswith('_path') and (not (ROOT/value).is_file()):b.append(f'implementation_missing:{key}')
  if key.endswith('_sha256'):
   source=ROOT/IMPL[key[:-7]+'_path']
   if not source.is_file() or _sha(source)!=value:b.append(f'implementation_hash_mismatch:{key}')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(b),'gate_path':relative_to_root(path,ROOT)}
def main()->int:
 r=validate_activation();print(json.dumps(r,indent=2,sort_keys=True));return 0 if r['status']=='pass' else 1
if __name__=='__main__':raise SystemExit(main())
