"""Closed-world B7.14 v2 report/attestation validator; never opens the container."""
from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; REPORT=ROOT/'reports/experiments/l_3_b714_date_only_preflight_report_v2.json'; ATT=ROOT/'reports/experiments/l_3_b714_date_only_schedule_attestation_v2.json'; GATE=ROOT/'experiments/l_3_b714_date_only_preflight_activation_v2.json'
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l3_b714_date_only_scanner_v2 import ASSETS,_schedule
from lib.provenance import file_sha256
TOP={'schema_version','order_id','hypothesis_id','outcome','evidence_tier','edge_claim','provenance','validation_seal','pre_checkpoint_incident_counts','access_counters','preflight'}
INC={'directory_listing_count':1,'filesystem_metadata_access_count':1,'container_content_read_count':0,'container_hash_count':0,'date_metadata_inspection_count':0,'return_values_decoded_count':0,'validation_access_count':0}
COMMON_COUNTS={'forbidden_semantic_decode_count':0,'research_decision_count':0,'ledger_row_count':0}
def validate(report:Path=REPORT,attestation:Path=ATT)->dict:
 try:p=json.loads(report.read_text(encoding='utf-8'));g=json.loads(GATE.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError) as exc:return {'status':'blocked','blockers':[type(exc).__name__]}
 b=[]
 if set(p)!=TOP or {k:p.get(k) for k in ('schema_version','order_id','hypothesis_id','evidence_tier','edge_claim')}!={'schema_version':'lily_l3_b714_date_only_preflight_report_v2','order_id':'B7.14','hypothesis_id':'L-3','evidence_tier':'E1','edge_claim':'none'} or p.get('outcome') not in {'preflight_pass','scope_restricted'}:b.append('identity')
 if p.get('validation_seal')!={'status':'sealed_not_accessed','accessed':False} or p.get('pre_checkpoint_incident_counts')!=INC:b.append('seal_or_incident')
 c=p.get('access_counters',{});
 if not isinstance(c,dict) or set(c)!={'raw_byte_read_count','raw_byte_hash_count','metadata_strings_decoded_count','skipped_string_values_count','skipped_return_values_count','forbidden_semantic_decode_count','date_metadata_inspection_count','research_decision_count','ledger_row_count'} or any(c.get(k)!=v for k,v in COMMON_COUNTS.items()) or any(not isinstance(c.get(k),int) or c[k]<0 for k in ('raw_byte_read_count','raw_byte_hash_count','metadata_strings_decoded_count','skipped_string_values_count','skipped_return_values_count','date_metadata_inspection_count')):b.append('counters')
 elif p.get('outcome')=='preflight_pass' and {k:c.get(k) for k in ('raw_byte_read_count','raw_byte_hash_count','date_metadata_inspection_count')}!={'raw_byte_read_count':1,'raw_byte_hash_count':1,'date_metadata_inspection_count':1}:b.append('counters')
 elif p.get('outcome')=='scope_restricted' and (c.get('raw_byte_read_count') not in (0,1) or c.get('raw_byte_hash_count') not in (0,1) or c.get('raw_byte_read_count')!=c.get('raw_byte_hash_count') or c.get('date_metadata_inspection_count') not in (0,1)):b.append('counters')
 prov=p.get('provenance',{}); expected={'active_b713_v3_sha256':file_sha256(ROOT/'experiments/l_3_b714_activation_contract_v3.json'),'activation_v2_sha256':file_sha256(GATE),'storage_reference':'data/normalized/l1_yahoo_daily_v1.json','incident_sha256':file_sha256(ROOT/'experiments/l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1.json')}
 if not isinstance(prov,dict) or any(prov.get(k)!=v for k,v in expected.items()) or not isinstance(prov.get('checkpoint_git_commit'),str) or not subprocess.run(['git','merge-base','--is-ancestor',prov.get('checkpoint_git_commit',''), 'HEAD'],cwd=ROOT).returncode==0:b.append('provenance')
 if p.get('outcome')=='preflight_pass':
  try:a=json.loads(attestation.read_text(encoding='utf-8'));pre=p['preflight'];sessions=pre['per_symbol_sessions']; rebuilt=_schedule(sessions)
  except (OSError,json.JSONDecodeError,KeyError,ValueError) as exc:b.append(type(exc).__name__)
  else:
   needed={'schema_version':'lily_l3_b714_date_only_schedule_attestation_v2','report_sha256':file_sha256(report),'container_sha256':prov.get('container_sha256'),'checkpoint_git_commit':prov.get('checkpoint_git_commit'),'validation_seal':{'status':'sealed_not_accessed','accessed':False},'pre_checkpoint_incident_counts':INC}
   if set(a)!={'schema_version','report_sha256','container_sha256','checkpoint_git_commit','validation_seal','pre_checkpoint_incident_counts','per_symbol_sessions','common_sessions','selected_decision_dates','execution_dates','t_plus_20_dates','canonical_schedule_sha256'} or any(a.get(k)!=v for k,v in needed.items()) or pre!=rebuilt or any(a.get(k)!=rebuilt[k] for k in rebuilt) or list(sessions)!=list(ASSETS) or len(rebuilt['selected_decision_dates'])>465:b.append('attestation')
 else:
  blocked_preflight=p.get('preflight',{})
  if attestation.exists() or set(blocked_preflight)!={'blocker'} or not isinstance(blocked_preflight.get('blocker'),str) or not blocked_preflight['blocker']:b.append('scope_restricted_contract')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 r=validate();print(json.dumps(r));raise SystemExit(r['status']!='pass')
