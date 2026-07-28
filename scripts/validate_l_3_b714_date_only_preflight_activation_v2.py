"""Fail-closed v2 gate validator; it never opens the designated container."""
from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; GATE=ROOT/'experiments/l_3_b714_date_only_preflight_activation_v2.json'
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256
TOP={'schema_version','order_id','gate_id','supersedes_gate_id','hypothesis_id','status','evidence_ceiling','edge_claim','owner_authorization','source_binding','approved_storage_reference','artifact_bindings','report_path','attestation_path','authorizations','validation_seal','incident_rule'}
AUTH={'exact_container_existence_check':True,'raw_byte_sha256':True,'structural_date_metadata_inspection':True,'return_parsing':False,'return_value_decoding':False,'research_decision':False,'ledger_write':False,'validation_access':False,'provider_network':False,'environment_credentials':False,'acquisition':False,'paid_action':False,'broker':False,'paper_trade':False,'real_money':False}
ARTIFACT_PATHS={'runner':'scripts/run_l_3_b714_date_only_preflight_v2.py','scanner':'lib/l3_b714_date_only_scanner_v2.py','report_schema':'schemas/l_3_b714_date_only_preflight_report_v2.schema.json','report_validator':'scripts/validate_l_3_b714_date_only_preflight_report_v2.py'}
def validate()->dict:
 try:p=json.loads(GATE.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError) as exc:return {'status':'blocked','blockers':[type(exc).__name__]}
 b=[]
 identity={'schema_version':'lily_l3_b714_date_only_preflight_activation_v2','order_id':'B7.14','gate_id':'l_3_b714_date_only_preflight_activation_v2','supersedes_gate_id':'l_3_b714_date_only_preflight_activation_v1','hypothesis_id':'L-3','status':'locked_date_only_preflight_authorized_after_checkpoint_ci','evidence_ceiling':'E1','edge_claim':'none'}
 if set(p)!=TOP or any(p.get(k)!=v for k,v in identity.items()) or p.get('approved_storage_reference')!='data/normalized/l1_yahoo_daily_v1.json' or not isinstance(p.get('owner_authorization'),str) or not p['owner_authorization'] or p.get('report_path')!='reports/experiments/l_3_b714_date_only_preflight_report_v2.json' or p.get('attestation_path')!='reports/experiments/l_3_b714_date_only_schedule_attestation_v2.json' or not isinstance(p.get('incident_rule'),str) or not p['incident_rule']:b.append('identity')
 if set(p.get('source_binding',{}))!={'active_b713_v3','b7_5_schedule','pre_checkpoint_incident'} or p.get('source_binding',{}).get('active_b713_v3')!=file_sha256(ROOT/'experiments/l_3_b714_activation_contract_v3.json') or p.get('source_binding',{}).get('b7_5_schedule')!=file_sha256(ROOT/'experiments/l_3_corrected_rerun_pre_return_schedule_v1.json'):b.append('source_binding')
 incident=p.get('source_binding',{}).get('pre_checkpoint_incident',{});
 if set(incident)!={'path','sha256','validator_path','validator_sha256'} or incident.get('path')!='experiments/l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1.json' or incident.get('sha256')!=file_sha256(ROOT/incident.get('path','')) or incident.get('validator_path')!='scripts/validate_l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1.py' or incident.get('validator_sha256')!=file_sha256(ROOT/incident.get('validator_path','')):b.append('incident_binding')
 if set(p.get('artifact_bindings',{}))!=set(ARTIFACT_PATHS) or any(not isinstance(p['artifact_bindings'].get(name),dict) or set(p['artifact_bindings'][name])!={'path','sha256'} or p['artifact_bindings'][name].get('path')!=path or p['artifact_bindings'][name].get('sha256')!=file_sha256(ROOT/path) for name,path in ARTIFACT_PATHS.items()):b.append('artifact_binding')
 if p.get('authorizations')!=AUTH or p.get('validation_seal')!={'status':'sealed_not_accessed','accessed':False}:b.append('authorizations')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
