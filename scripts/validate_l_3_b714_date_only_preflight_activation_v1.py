"""Fail-closed B7.14 activation validator; it never opens the approved container."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
GATE=ROOT/'experiments/l_3_b714_date_only_preflight_activation_v1.json'
FILES={'runner':('scripts/run_l_3_b714_date_only_preflight_v1.py','91dc7cccd8f34c19a1ce59b6320693cc3a5f2922a1525c2c0cdc1592ee3a606e'),'scanner':('lib/l3_b714_date_only_scanner_v1.py','aa6eb9c0e9984bc70677c27a1d736d2cb348cb367fa3fa169b5db2533aa6bcf6'),'report_schema':('schemas/l_3_b714_date_only_preflight_report_v1.schema.json','5acfb236872f846143301412739228931410c2014719c606107ac13942f17e22'),'report_validator':('scripts/validate_l_3_b714_date_only_preflight_report_v1.py','8194d2016932500d5842a9a6a212911bf1516350a9953af09c5348ff98810577')}
AUTH={'exact_container_existence_check':True,'raw_byte_sha256':True,'structural_date_metadata_inspection':True,'return_parsing':False,'return_value_decoding':False,'signal_position_covariance_cost_pnl_computation':False,'research_decision':False,'ledger_write':False,'validation_access':False,'provider_network':False,'environment_credentials':False,'acquisition':False,'paid_action':False,'broker':False,'paper_trade':False,'real_money':False}
def validate()->dict:
 try:p=json.loads(GATE.read_text(encoding='utf-8'));rows=[json.loads(x) for x in (ROOT/'experiments/locked_gates.jsonl').read_text(encoding='utf-8').splitlines() if x]
 except (OSError,json.JSONDecodeError) as exc:return {'status':'blocked','blockers':[type(exc).__name__]}
 b=[]
 if {k:p.get(k) for k in ('schema_version','order_id','gate_id','hypothesis_id','status','evidence_ceiling','edge_claim')}!={'schema_version':'lily_l3_b714_date_only_preflight_activation_v1','order_id':'B7.14','gate_id':'l_3_b714_date_only_preflight_activation_v1','hypothesis_id':'L-3','status':'locked_date_only_preflight_authorized_after_checkpoint_ci','evidence_ceiling':'E1','edge_claim':'none'}:b.append('identity')
 s=p.get('source_binding',{});active=s.get('active_b713_v3',{});manifest=next((x for x in rows if x.get('gate_id')=='l_3_b714_activation_contract_v3'),{})
 if active.get('path')!='experiments/l_3_b714_activation_contract_v3.json' or active.get('sha256')!=file_sha256(ROOT/'experiments/l_3_b714_activation_contract_v3.json') or active.get('manifest_identity',{}).get('validator_sha256')!=manifest.get('validator_sha256'):b.append('active_b713_binding')
 if s.get('b7_5_schedule',{}).get('sha256')!=file_sha256(ROOT/'experiments/l_3_corrected_rerun_pre_return_schedule_v1.json') or p.get('approved_storage_reference')!='data/normalized/l1_yahoo_daily_v1.json':b.append('schedule_or_storage_binding')
 for key,(path,expected) in FILES.items():
  row=p.get('artifact_bindings',{}).get(key,{})
  if row.get('path')!=path or row.get('sha256')!=expected or expected=='PENDING' or file_sha256(ROOT/path)!=expected:b.append('artifact:'+key)
 if p.get('authorizations')!=AUTH or p.get('validation_seal')!={'status':'sealed_not_accessed','accessed':False}:b.append('authorization_or_seal')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
