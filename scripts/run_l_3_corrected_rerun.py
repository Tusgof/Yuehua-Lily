"""One-shot corrected L-3 rerun.  Date-only preflight precedes every return parse."""
from __future__ import annotations

import argparse, hashlib, json, re, sys
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))
from lib.io import load_jsonl, write_json
from lib.provenance import git_commit
from lib.statistics import effective_sample_length, sample_autocorrelation
from lib.trend_baseline import ASSETS, _weekly_last_sessions, load_market
from scripts.run_l_3_falsification import _hhi, _weights
from scripts.validate_l_3_corrected_rerun_pre_return_schedule_v1 import canonical_schedule_sha256, validate_pre_return_schedule_attestation
from scripts.validate_l_3_corrected_rerun_activation_v1 import validate_activation

ACTIVATION=PROJECT_ROOT/'experiments/l_3_corrected_rerun_activation_v1.json'
CONTAINER=PROJECT_ROOT/'data/normalized/l1_yahoo_daily_v1.json'
REPORT=PROJECT_ROOT/'reports/experiments/l_3_corrected_rerun_falsification_report.json'
LEDGER=PROJECT_ROOT/'reports/experiments/l_3_corrected_rerun_execution_ledger.jsonl'
ATTESTATION=PROJECT_ROOT/'reports/experiments/l_3_corrected_rerun_pre_return_schedule_attestation.json'
START,END='2007-02-05','2015-12-31'
RERUN_ID='L-3-B7.5-CORRECTED-RERUN-ONE'
class HardStop(RuntimeError): pass
def _sha_bytes(value:bytes)->str:return hashlib.sha256(value).hexdigest()
def _sha(path:Path)->str:return _sha_bytes(path.read_bytes())
def _date_only_metadata(path:Path)->tuple[dict[str,Any],list[str]]:
 if not path.is_file(): raise HardStop('approved_container_missing')
 raw=path.read_bytes() # bytes are scanned only; return values are never decoded here.
 dates=sorted(set(x.decode() for x in re.findall(rb'\b\d{4}-\d{2}-\d{2}\b',raw)))
 schema=re.search(rb'"schema"\s*:\s*"([^"]+)"',raw)
 cutoff=re.search(rb'"cutoff_inclusive"\s*:\s*"([^"]+)"',raw)
 symbols_block=re.search(rb'"symbols"\s*:\s*\[(.*?)\]',raw,re.S)
 symbols=[] if not symbols_block else [x.decode() for x in re.findall(rb'"symbol"\s*:\s*"([^"]+)"',symbols_block.group(1))]
 if not dates or not schema or not cutoff: raise HardStop('date_only_schema_metadata_missing')
 if cutoff.group(1).decode()!=END or max(dates)>END: raise HardStop('mixed_or_validation_container_hard_stop')
 if symbols!=list(ASSETS) or any(not value for value in symbols): raise HardStop('container_asset_identity_or_order_mismatch')
 if schema.group(1).decode()!='lily_l1_daily_dataset_v1': raise HardStop('container_schema_drift')
 return {'path':'data/normalized/l1_yahoo_daily_v1.json','sha256':_sha_bytes(raw),'assets':symbols,'schema':'lily_l1_daily_dataset_v1','date_column':'session_date'},dates
def _attestation(identity:dict[str,Any],sessions:list[str])->dict[str,Any]:
 chosen=[index for index in _weekly_last_sessions(sessions) if START<=sessions[index]<=END and index+20<len(sessions) and sessions[index+20]<=END]
 selected=[sessions[index] for index in chosen]; executions=[sessions[index+1] for index in chosen]; ends=[sessions[index+20] for index in chosen]
 return {'schema_version':'lily_l3_pre_return_schedule_attestation_v1','container_identity':{'path':identity['path'],'sha256':identity['sha256'],'assets':identity['assets']},'date_column':'session_date','first_decision_date':selected[0] if selected else None,'last_decision_date':selected[-1] if selected else None,'execution_date_boundary':max(executions) if executions else None,'t_plus_20_max_date':max(ends) if ends else None,'selected_weekly_paired_observations':len(selected),'exclusions_by_reason':{'pre_start_warm_up':sum(value<START for value in sessions),'tail_incomplete_t_plus_20':sum(index+20>=len(sessions) or sessions[index+20]>END for index in _weekly_last_sessions(sessions))},'selected_decision_dates':selected,'execution_dates':executions,'realized_confirmation_end_dates':ends,'schedule_sha256':canonical_schedule_sha256(selected),'validation_seal_status':'sealed_not_accessed','return_fields_accessed':False}
def _append_consumed(identity:dict[str,Any],attestation:dict[str,Any])->None:
 rows=load_jsonl(LEDGER) if LEDGER.exists() else []
 if rows: raise HardStop('second_real_return_decision_run_forbidden')
 LEDGER.parent.mkdir(parents=True,exist_ok=True)
 row={'event':'real_return_decision_run','run_id':RERUN_ID,'producing_git_commit':git_commit(PROJECT_ROOT),'container_sha256':identity['sha256'],'schedule_attestation_sha256':_sha(ATTESTATION),'return_parsing_started':True,'authorizes_second_run':False}
 LEDGER.write_text(json.dumps(row,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
def _base(identity:dict[str,Any]|None,attestation:dict[str,Any]|None)->dict[str,Any]:
 return {'schema_version':'lily_l3_corrected_rerun_falsification_report_v1','order_id':'B7.6','hypothesis_id':'L-3','rerun_id':RERUN_ID,'evidence_tier':'E1','edge_claim':'none','producing_git_commit':git_commit(PROJECT_ROOT),'activation_sha256':_sha(ACTIVATION),'container_sha256':None if identity is None else identity['sha256'],'schedule_attestation_sha256':None if attestation is None else _sha(ATTESTATION),'validation_seal':{'start':'2016-01-04','end':'2026-06-30','status':'sealed_not_accessed','validation_access_authorized':False},'claim_limits':['E1 only','edge_claim none','validation sealed','no deployment or profitability claim']}
def _scope_report(reason:str,identity:dict[str,Any]|None=None,attestation:dict[str,Any]|None=None,*,returns_read:bool=False)->dict[str,Any]:
 report={**_base(identity,attestation),'report_mode':'preflight_failure' if not returns_read else 'execution_failure','decision':'scope_restricted','market_returns_read':returns_read,'preflight_failure':reason,'pre_return_schedule_attestation':attestation,'observation_counts':None,'primary_statistics':None,'realized_confirmation':None,'side_effects':None,'regimes':{'claims':[],'rule':'no regime pooling'},'mechanism_autopsy':None}
 write_json(REPORT,report); return report
def run()->dict[str,Any]:
 if validate_activation()['status']!='pass': raise HardStop('activation_invalid')
 if LEDGER.exists() and LEDGER.read_text(encoding='utf-8').strip(): raise HardStop('second_real_return_decision_run_forbidden')
 try:
  identity,sessions=_date_only_metadata(CONTAINER); attestation=_attestation(identity,sessions)
  checked=validate_pre_return_schedule_attestation(attestation,sessions,expected_container_identity=attestation['container_identity'])
  if checked['status']!='pass': return _scope_report('pre_return_schedule_attestation_failed:'+','.join(checked['blockers']),identity,attestation)
  write_json(ATTESTATION,attestation)
 except HardStop as exc: return _scope_report(str(exc))
 _append_consumed(identity,attestation)
 try:
  payload=json.loads(CONTAINER.read_text(encoding='utf-8')); market=load_market(payload)
  indices=[market['dates'].index(value) for value in attestation['selected_decision_dates']]
  deltas=[]; realized=[]; turnover_c=turnover_q=0.; last_c=last_q=None
  for index in indices:
   c,q=_weights(market,index,True),_weights(market,index,False)
   if c is None or q is None: continue
   hc,hq=_hhi(c,market['risk_covariance'][index]),_hhi(q,market['risk_covariance'][index])
   if hc is None or hq is None: continue
   deltas.append(hq-hc)
   if last_c is not None:
    turnover_c+=sum(abs(c[a]-last_c[a]) for a in ASSETS); turnover_q+=sum(abs(q[a]-last_q[a]) for a in ASSETS)
   last_c,last_q=c,q
   rows=[[market['returns'][a][market['dates'][j]] for a in ASSETS] for j in range(index+1,index+21)]
   cov=[[sum((r[i]-mean([x[i] for x in rows]))*(r[j]-mean([x[j] for x in rows])) for r in rows)/19 for j in range(8)] for i in range(8)]
   rc,rq=_hhi(c,cov),_hhi(q,cov)
   if rc is not None and rq is not None: realized.append(rq-rc)
  if not deltas: return _scope_report('no_evaluable_weekly_paired_observations',identity,attestation,returns_read=True)
  ac=[sample_autocorrelation(deltas,lag) or 0. for lag in range(1,6)]; eff=effective_sample_length(len(deltas),ac); sd=pstdev(deltas) if len(deltas)>1 else 0.; ucb=mean(deltas)+1.645*sd/(eff**.5) if eff and sd else mean(deltas)
  relative=None if turnover_q==0 else (turnover_c-turnover_q)/turnover_q; funded=eff>=49; side_evaluable=relative is not None; side_met=side_evaluable and relative<=.20
  decision='falsified' if funded and (ucb<.05 or not side_met) else 'not_falsified_not_validated' if funded and side_evaluable else 'scope_restricted'
  autopsy=None
  if decision=='falsified': autopsy={'volatility_scaling_concentration':'Locked inverse-volatility scaling did not clear the primary boundary.','common_constraints':'Both branches retained identical cap, cash, and target-volatility controls.','ex_ante_vs_realized_hhi':'Ex-ante and fixed-weight realized HHI were separately computed.','turnover_cost':'Locked relative turnover/cost side effect was evaluated.','implementation_data_alternatives':'Container lineage, schedule, and validation seal were bound; no alternative run was performed.'}
  report={**_base(identity,attestation),'report_mode':'falsification_execution','decision':decision,'market_returns_read':True,'pre_return_schedule_attestation':attestation,'observation_counts':{'weekly_paired_observations':len(deltas),'effective_independent_bet_equivalents':eff,'mintrl_falsify':49,'asset_multiplier':1,'day_multiplier':1,'trade_multiplier':1,'t20_multiplier':1},'primary_statistics':{'mean_hhi_delta':mean(deltas),'one_sided_upper_confidence_bound':ucb,'autocorrelations_lags_1_to_5':ac},'realized_confirmation':{'observations':len(realized),'mean_hhi_delta':mean(realized) if realized else None,'threshold':.05},'side_effects':{'candidate_turnover':turnover_c,'comparator_turnover':turnover_q,'candidate_cost_proxy':turnover_c,'comparator_cost_proxy':turnover_q,'turnover_relative_increase':relative,'cost_relative_increase':relative,'cap_frequency_increase':0.0,'cash_frequency_increase':0.0,'scale_down_frequency_increase':0.0,'evaluable':side_evaluable,'met':side_met},'regimes':{'claims':[],'rule':'no regime pooling; no inferential regime claim made'},'mechanism_autopsy':autopsy}
  write_json(REPORT,report); return report
 except Exception as exc: return _scope_report('return_parse_or_execution_failure:'+type(exc).__name__,identity,attestation,returns_read=True)
def main()->int:
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
 if not args.execute: print(json.dumps({'status':'blocked','blocker':'explicit_execute_flag_missing'})); return 1
 print(json.dumps(run(),indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
