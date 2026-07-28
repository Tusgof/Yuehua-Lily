"""Independent B7.14 v3 report validator; it never opens the container."""
from __future__ import annotations
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l3_b714_date_only_scanner_v3 import ASSETS,_schedule
from lib.provenance import file_sha256
REPORT=ROOT/'reports/experiments/l_3_b714_date_only_preflight_report_v3.json';ATT=ROOT/'reports/experiments/l_3_b714_date_only_schedule_attestation_v3.json';GATE=ROOT/'experiments/l_3_b714_date_only_preflight_activation_v3.json';INC=ROOT/'experiments/l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1.json'
EXPECTED='6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd'; TOP={'schema_version','order_id','hypothesis_id','outcome','evidence_tier','edge_claim','provenance','validation_seal','pre_checkpoint_incident_counts','access_counters','preflight'}; INC_COUNTS={'directory_listing_count':1,'filesystem_metadata_access_count':1,'container_content_read_count':0,'container_hash_count':0,'date_metadata_inspection_count':0,'return_values_decoded_count':0,'validation_access_count':0}; COUNTS={'raw_byte_read_attempt_count','raw_byte_read_count','raw_byte_hash_count','allowed_metadata_string_decode_count','session_date_values_decoded_count','date_metadata_inspection_count','skipped_timestamp_string_lexeme_count','skipped_return_number_lexeme_count','forbidden_semantic_decode_count','research_decision_count','ledger_row_count'}
def _show(commit:str,path:str)->bytes:
 return subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=ROOT)
def _manifest(commit:str,gate_id:str)->dict:
 return next(x for x in (json.loads(line) for line in _show(commit,'experiments/locked_gates.jsonl').decode().splitlines() if line) if x.get('gate_id')==gate_id)
def validate(report:Path=REPORT,attestation:Path=ATT)->dict:
 try:r=json.loads(report.read_text(encoding='utf-8'));g=json.loads(GATE.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError) as e:return {'status':'blocked','blockers':[type(e).__name__]}
 b=[]
 if set(r)!=TOP or {k:r.get(k) for k in ('schema_version','order_id','hypothesis_id','evidence_tier','edge_claim')}!={'schema_version':'lily_l3_b714_date_only_preflight_report_v3','order_id':'B7.14','hypothesis_id':'L-3','evidence_tier':'E1','edge_claim':'none'} or r.get('outcome') not in {'preflight_pass','scope_restricted'}:b.append('identity')
 if r.get('validation_seal')!={'status':'sealed_not_accessed','accessed':False} or r.get('pre_checkpoint_incident_counts')!=INC_COUNTS:b.append('seal_or_incident')
 c=r.get('access_counters',{})
 if not isinstance(c,dict) or set(c)!=COUNTS or c.get('raw_byte_read_attempt_count')!=1 or any(not isinstance(c.get(k),int) or c[k]<0 for k in COUNTS) or c.get('raw_byte_read_count') not in (0,1) or c.get('raw_byte_hash_count')!=c.get('raw_byte_read_count') or c.get('forbidden_semantic_decode_count')!=0 or c.get('research_decision_count')!=0 or c.get('ledger_row_count')!=0 or c.get('session_date_values_decoded_count')!=c.get('date_metadata_inspection_count'):b.append('counters')
 p=r.get('provenance',{}); keys={'active_b713','activation','incident','checkpoint_git_commit','storage_reference','expected_historical_container_sha256','actual_container_sha256','attestation_path','attestation_sha256'}
 if not isinstance(p,dict) or set(p)!=keys or p.get('storage_reference')!='data/normalized/l1_yahoo_daily_v1.json' or p.get('expected_historical_container_sha256')!=EXPECTED or not isinstance(p.get('checkpoint_git_commit'),str) or not re.fullmatch('[0-9a-f]{40}',p['checkpoint_git_commit']):b.append('provenance')
 else:
  try:
   subprocess.check_call(['git','cat-file','-e',p['checkpoint_git_commit']+'^{commit}'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   for label,path,gate_id,sha in [('active_b713','experiments/l_3_b714_activation_contract_v3.json','l_3_b714_activation_contract_v3',file_sha256(ROOT/'experiments/l_3_b714_activation_contract_v3.json')),('activation','experiments/l_3_b714_date_only_preflight_activation_v3.json','l_3_b714_date_only_preflight_activation_v3',file_sha256(GATE))]:
    x=p[label]
    if set(x)!={'gate_id','path','sha256','manifest_row'} or x!={'gate_id':gate_id,'path':path,'sha256':sha,'manifest_row':_manifest(p['checkpoint_git_commit'],gate_id)} or hashlib.sha256(_show(p['checkpoint_git_commit'],path)).hexdigest()!=sha:b.append('checkpoint_provenance')
   x=p['incident']
   if x!={'id':'l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1','path':'experiments/l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1.json','sha256':file_sha256(INC)}:b.append('incident_provenance')
  except (subprocess.CalledProcessError,StopIteration,KeyError,json.JSONDecodeError):b.append('checkpoint_provenance')
 if r.get('outcome')=='preflight_pass':
  try:a=json.loads(attestation.read_text(encoding='utf-8'));pre=r['preflight'];rebuilt=_schedule(pre['per_symbol_sessions'])
  except (OSError,json.JSONDecodeError,KeyError,ValueError):b.append('attestation')
  else:
   need={'schema_version':'lily_l3_b714_date_only_schedule_attestation_v3','order_id':'B7.14','hypothesis_id':'L-3','checkpoint_git_commit':p.get('checkpoint_git_commit'),'container_sha256':EXPECTED,'validation_seal':{'status':'sealed_not_accessed','accessed':False},'pre_checkpoint_incident_counts':INC_COUNTS}
   if set(a)!={'schema_version','order_id','hypothesis_id','checkpoint_git_commit','container_sha256','validation_seal','pre_checkpoint_incident_counts','per_symbol_sessions','common_sessions','selected_decision_dates','execution_dates','t_plus_20_dates','canonical_schedule_sha256','date_evidence_sha256'} or any(a.get(k)!=v for k,v in need.items()) or pre!=rebuilt or any(a.get(k)!=rebuilt[k] for k in rebuilt) or p.get('actual_container_sha256')!=EXPECTED or p.get('attestation_path')!='reports/experiments/l_3_b714_date_only_schedule_attestation_v3.json' or p.get('attestation_sha256')!=file_sha256(attestation) or list(pre['per_symbol_sessions'])!=list(ASSETS):b.append('attestation')
 else:
  if attestation.exists() or p.get('attestation_path') is not None or p.get('attestation_sha256') is not None or set(r.get('preflight',{}))!={'blocker'} or not isinstance(r['preflight'].get('blocker'),str) or not r['preflight']['blocker']:b.append('scope_restricted_contract')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
if __name__=='__main__':
 x=validate();print(json.dumps(x));raise SystemExit(x['status']!='pass')
