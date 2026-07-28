"""Fail-closed B7.14 v3 activation validator; never opens the container."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
G=ROOT/'experiments/l_3_b714_date_only_preflight_activation_v3.json'; EXPECTED='6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd'
TOP={'schema_version','order_id','gate_id','supersedes_gate_id','hypothesis_id','status','evidence_ceiling','edge_claim','owner_authorization','source_binding','approved_storage_reference','expected_historical_container_sha256','artifact_bindings','report_path','attestation_path','authorizations','validation_seal'}; AUTH={'exact_container_existence_check':True,'raw_byte_sha256':True,'structural_date_metadata_inspection':True,'return_parsing':False,'return_value_decoding':False,'research_decision':False,'ledger_write':False,'validation_access':False,'provider_network':False,'environment_credentials':False,'acquisition':False,'paid_action':False,'broker':False,'paper_trade':False,'real_money':False}; PATHS={'runner':'scripts/run_l_3_b714_date_only_preflight_v3.py','scanner':'lib/l3_b714_date_only_scanner_v3.py','report_schema':'schemas/l_3_b714_date_only_preflight_report_v3.schema.json','report_validator':'scripts/validate_l_3_b714_date_only_preflight_report_v3.py'}
def validate()->dict:
 try:p=json.loads(G.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError) as e:return {'status':'blocked','blockers':[type(e).__name__]}
 b=[]
 if set(p)!=TOP or {k:p.get(k) for k in ('schema_version','order_id','gate_id','supersedes_gate_id','hypothesis_id','status','evidence_ceiling','edge_claim')}!={'schema_version':'lily_l3_b714_date_only_preflight_activation_v3','order_id':'B7.14','gate_id':'l_3_b714_date_only_preflight_activation_v3','supersedes_gate_id':'l_3_b714_date_only_preflight_activation_v2','hypothesis_id':'L-3','status':'locked_date_only_preflight_authorized_after_checkpoint_ci','evidence_ceiling':'E1','edge_claim':'none'} or not isinstance(p.get('owner_authorization'),str) or not p['owner_authorization']:b.append('identity')
 if p.get('approved_storage_reference')!='data/normalized/l1_yahoo_daily_v1.json' or p.get('expected_historical_container_sha256')!=EXPECTED or p.get('report_path')!='reports/experiments/l_3_b714_date_only_preflight_report_v3.json' or p.get('attestation_path')!='reports/experiments/l_3_b714_date_only_schedule_attestation_v3.json' or p.get('authorizations')!=AUTH or p.get('validation_seal')!={'status':'sealed_not_accessed','accessed':False}:b.append('authorization')
 if set(p.get('artifact_bindings',{}))!=set(PATHS) or any(p['artifact_bindings'].get(k)!={'path':v,'sha256':file_sha256(ROOT/v)} for k,v in PATHS.items()):b.append('artifact_binding')
 s=p.get('source_binding',{})
 required={'active_b713','b75','v2_predecessor','incident','b73_original_ledger_row'}
 if set(s)!=required or s.get('active_b713',{}).get('path')!='experiments/l_3_b714_activation_contract_v3.json' or s.get('b75',{}).get('path')!='experiments/l_3_corrected_rerun_pre_return_schedule_v1.json' or s.get('v2_predecessor',{}).get('path')!='experiments/l_3_b714_date_only_preflight_activation_v2.json' or s.get('incident',{}).get('path')!='experiments/l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1.json' or s.get('b73_original_ledger_row',{}).get('sha256')!='594b8cbbdf7c27769191ab9495275803478481121372cd3bfc6f7e6d3a8a556a':b.append('source_binding')
 else:
  for x in ('active_b713','b75','v2_predecessor','incident'):
   if s[x].get('sha256')!=file_sha256(ROOT/s[x]['path']):b.append('source_binding')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
