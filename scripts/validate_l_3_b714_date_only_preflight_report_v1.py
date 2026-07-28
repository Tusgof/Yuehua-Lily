"""Closed-world validator for the one B7.14 date-only preflight report."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.provenance import file_sha256

REPORT=ROOT/'reports/experiments/l_3_b714_date_only_preflight_report_v1.json'; GATE=ROOT/'experiments/l_3_b714_date_only_preflight_activation_v1.json'
TOP={'schema_version','order_id','hypothesis_id','outcome','evidence_tier','edge_claim','provenance','validation_seal','access_counters','preflight'}
def validate(path:Path=REPORT)->dict:
 try: p=json.loads(path.read_text(encoding='utf-8')); gate=json.loads(GATE.read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError) as exc:return {'status':'blocked','blockers':[type(exc).__name__]}
 b=[]
 if set(p)!=TOP or {k:p.get(k) for k in ('schema_version','order_id','hypothesis_id','evidence_tier','edge_claim')}!={'schema_version':'lily_l3_b714_date_only_preflight_report_v1','order_id':'B7.14','hypothesis_id':'L-3','evidence_tier':'E1','edge_claim':'none'}:b.append('identity')
 if p.get('outcome') not in {'preflight_pass','scope_restricted'}:b.append('outcome')
 expected={'active_b713_gate_id':'l_3_b714_activation_contract_v3','active_b713_gate_sha256':file_sha256(ROOT/'experiments/l_3_b714_activation_contract_v3.json'),'activation_gate_id':gate.get('gate_id'),'activation_gate_sha256':file_sha256(GATE),'storage_reference':'data/normalized/l1_yahoo_daily_v1.json'}
 if not isinstance(p.get('provenance'),dict) or any(p['provenance'].get(k)!=v for k,v in expected.items()) or not isinstance(p['provenance'].get('checkpoint_git_commit'),str) or len(p['provenance'].get('container_sha256',''))!=64:b.append('provenance')
 if p.get('validation_seal')!={'status':'sealed_not_accessed','accessed':False}:b.append('validation_seal')
 counters=p.get('access_counters',{}); expected_counts={'raw_container_hash_count':1,'date_metadata_inspection_count':1,'market_returns_read_count':0,'return_values_decoded_count':0,'research_decision_count':0,'ledger_row_count':0}
 if counters!=expected_counts:b.append('access_counters')
 pre=p.get('preflight',{})
 if not isinstance(pre,dict) or pre.get('status')!=p.get('outcome') or pre.get('return_values_decoded_count')!=0:b.append('preflight')
 if p.get('outcome')=='preflight_pass' and not all(k in pre for k in ('per_symbol','common_session_count','selected_decision_dates','execution_dates','t_plus_20_dates','canonical_schedule_sha256')):b.append('pass_evidence')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
def main()->int:
 a=argparse.ArgumentParser();a.add_argument('report',nargs='?',type=Path,default=REPORT);r=validate(a.parse_args().report);print(json.dumps(r));return r['status']!='pass'
if __name__=='__main__':raise SystemExit(main())
