"""Closed-world validation for the B7.6 fresh report and one-shot ledger."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.io import load_json, relative_to_root
REPORT=ROOT/'reports/experiments/l_3_corrected_rerun_falsification_report.json'
LEDGER=ROOT/'reports/experiments/l_3_corrected_rerun_execution_ledger.jsonl'
ACTIVATION=ROOT/'experiments/l_3_corrected_rerun_activation_v1.json'
ATTESTATION=ROOT/'reports/experiments/l_3_corrected_rerun_pre_return_schedule_attestation.json'
REQUIRED={'schema_version','order_id','hypothesis_id','rerun_id','evidence_tier','edge_claim','producing_git_commit','activation_sha256','container_sha256','schedule_attestation_sha256','validation_seal','report_mode','decision','market_returns_read','pre_return_schedule_attestation','observation_counts','primary_statistics','realized_confirmation','side_effects','regimes','mechanism_autopsy','claim_limits'}
def _sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def validate_report(path:Path=REPORT,ledger_path:Path=LEDGER)->dict[str,Any]:
 blockers=[]
 try:r=load_json(path)
 except Exception as e:return {'status':'blocked','blockers':[f'report_unreadable:{type(e).__name__}']}
 if not isinstance(r,dict):return {'status':'blocked','blockers':['report_not_object']}
 blockers += [f'unknown_field:{x}' for x in set(r)-REQUIRED]+[f'missing_field:{x}' for x in REQUIRED-set(r)]
 expected={'schema_version':'lily_l3_corrected_rerun_falsification_report_v1','order_id':'B7.6','hypothesis_id':'L-3','rerun_id':'L-3-B7.5-CORRECTED-RERUN-ONE','evidence_tier':'E1','edge_claim':'none'}
 blockers += [f'root_mismatch:{k}' for k,v in expected.items() if r.get(k)!=v]
 if r.get('activation_sha256')!=_sha(ACTIVATION):blockers.append('activation_hash_mismatch')
 if r.get('validation_seal')!={'start':'2016-01-04','end':'2026-06-30','status':'sealed_not_accessed','validation_access_authorized':False}:blockers.append('validation_seal_mismatch')
 decision=r.get('decision')
 if decision not in {'falsified','not_falsified_not_validated','scope_restricted'}:blockers.append('decision_invalid')
 if decision=='falsified' and (not isinstance(r.get('mechanism_autopsy'),dict) or set(r['mechanism_autopsy'])!={'volatility_scaling_concentration','common_constraints','ex_ante_vs_realized_hhi','turnover_cost','implementation_data_alternatives'}):blockers.append('falsification_autopsy_incomplete')
 if r.get('market_returns_read'):
  if not ATTESTATION.is_file() or r.get('schedule_attestation_sha256')!=_sha(ATTESTATION):blockers.append('schedule_attestation_provenance_mismatch')
  try:rows=[json.loads(line) for line in ledger_path.read_text(encoding='utf-8').splitlines() if line]
  except Exception:rows=[];blockers.append('ledger_unreadable')
  if len(rows)!=1 or rows[0].get('event')!='real_return_decision_run' or rows[0].get('run_id')!='L-3-B7.5-CORRECTED-RERUN-ONE' or rows[0].get('return_parsing_started') is not True:blockers.append('exactly_one_fresh_run_ledger_mismatch')
  counts=r.get('observation_counts')
  if not isinstance(counts,dict) or counts.get('weekly_paired_observations',0)>465 or any(counts.get(x)!=1 for x in ('asset_multiplier','day_multiplier','trade_multiplier','t20_multiplier')):blockers.append('observation_or_pseudoreplication_mismatch')
 return {'status':'pass' if not blockers else 'blocked','blockers':sorted(blockers),'report_path':relative_to_root(path,ROOT),'fresh_real_return_decision_run_count':1 if r.get('market_returns_read') else 0,'validation_status':'sealed_not_accessed'}
def main()->int:
 x=validate_report();print(json.dumps(x,indent=2,sort_keys=True));return 0 if x['status']=='pass' else 1
if __name__=='__main__':raise SystemExit(main())
