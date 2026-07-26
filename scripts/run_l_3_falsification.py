"""One-shot L-3 falsification runner; it never resolves an environment variable or provider."""
from __future__ import annotations
import argparse, hashlib, json, math, re, sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any
PROJECT_ROOT=Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:sys.path.insert(0,str(PROJECT_ROOT))
from lib.io import load_json, load_jsonl, write_json
from lib.provenance import git_commit
from lib.statistics import effective_sample_length, sample_autocorrelation
from lib.trend_baseline import ANNUALIZATION, ASSETS, _cap_and_redistribute, _direction, _weekly_last_sessions, load_market
from scripts.validate_l_3_one_run_falsification_authorization_v1 import GATE as AUTHORIZATION, validate_authorization
REPORT=PROJECT_ROOT/'reports/experiments/l_3_falsification_report.json'
LEDGER=PROJECT_ROOT/'reports/experiments/l_3_falsification_execution_ledger.jsonl'
CONTAINER=PROJECT_ROOT/'data/normalized/l1_yahoo_daily_v1.json'
class HardStop(RuntimeError):pass
def _sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def _preflight(path:Path)->dict[str,Any]:
 if not path.is_file():raise HardStop('approved_container_missing')
 raw=path.read_bytes(); dates=[m.decode() for m in re.findall(rb'\b\d{4}-\d{2}-\d{2}\b',raw)]
 if not dates:raise HardStop('schema_date_column_missing')
 if max(dates)>'2015-12-31':raise HardStop('mixed_or_validation_container_hard_stop')
 payload=json.loads(raw.decode('utf-8'))
 if payload.get('cutoff_inclusive')!='2015-12-31':raise HardStop('container_cutoff_metadata_mismatch')
 symbols=[x.get('symbol') for x in payload.get('symbols',[])]
 if symbols!=list(ASSETS):raise HardStop('container_asset_identity_or_order_mismatch')
 if any(not isinstance(x,str) or not x for x in symbols):raise HardStop('nonfinite_identifier')
 return {'container_sha256':hashlib.sha256(raw).hexdigest(),'date_column':'session_date','minimum_date':min(dates),'maximum_date':max(dates),'assets':symbols,'schema':'lily_l1_daily_dataset_v1','raw_payload':payload}
def _weights(market:dict[str,Any],idx:int,inverse:bool)->dict[str,float]|None:
 dates=market['dates']; rets=market['returns']; cov=market['risk_covariance'].get(idx)
 if cov is None or idx<60:return None
 q={a:sum(_direction(rets[a][dates[i]]) for i in range(idx-59,idx+1))/60 for a in ASSETS}
 scores={a:q[a]/max(math.sqrt(max(cov[j][j],0)*ANNUALIZATION),.05) if inverse else q[a] for j,a in enumerate(ASSETS)}
 gross=sum(abs(v) for v in scores.values())
 if gross==0:return {a:0.0 for a in ASSETS}
 capped=_cap_and_redistribute({a:.9*scores[a]/gross for a in ASSETS},cap=.25,gross_limit=.9)
 var=sum(capped[a]*capped[b]*cov[i][j]*ANNUALIZATION for i,a in enumerate(ASSETS) for j,b in enumerate(ASSETS))
 scale=min(1,.1/math.sqrt(var)) if var>0 else 1
 return {a:capped[a]*scale for a in ASSETS}
def _hhi(weights:dict[str,float],cov:list[list[float]])->float|None:
 c=[]
 for i,a in enumerate(ASSETS):c.append(weights[a]*sum(cov[i][j]*weights[b] for j,b in enumerate(ASSETS)))
 denom=sum(abs(x) for x in c)
 return None if denom<=0 or not math.isfinite(denom) else sum((abs(x)/denom)**2 for x in c)
def _append_ledger(row:dict[str,Any])->None:
 rows=load_jsonl(LEDGER) if LEDGER.exists() else []
 if any(r.get('event')=='real_return_decision_run' for r in rows):raise HardStop('second_real_return_decision_run_forbidden')
 LEDGER.parent.mkdir(parents=True,exist_ok=True)
 with LEDGER.open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps(row,sort_keys=True)+'\n')
def _real_run_already_recorded()->bool:
 return LEDGER.exists() and any(row.get('event')=='real_return_decision_run' for row in load_jsonl(LEDGER))
def run()->dict[str,Any]:
 if validate_authorization()['status']!='pass':raise HardStop('one_run_authorization_invalid')
 if _real_run_already_recorded():raise HardStop('second_real_return_decision_run_forbidden')
 auth=load_json(AUTHORIZATION)
 base={'schema_version':'lily_l3_falsification_report_v1','order_id':'B7.3','hypothesis_id':'L-3','evidence_tier':'E1','edge_claim':'none','producing_git_commit':git_commit(PROJECT_ROOT),'authorization_sha256':_sha(AUTHORIZATION),'validation_seal':{'start':'2016-01-04','end':'2026-06-30','status':'sealed_not_accessed','validation_access_authorized':False}}
 try: pre=_preflight(CONTAINER)
 except HardStop as e:
  report={**base,'report_mode':'preflight_failure','execution_status':'scope_restricted','decision':'scope_restricted','market_returns_read':False,'preflight_failure':str(e),'claim_limits':['E1 only','edge_claim none','validation sealed']};write_json(REPORT,report);return report
 market=load_market(pre.pop('raw_payload'))
 deltas=[]; realized=[]; turnover_c=turnover_q=0.; side_dates=0
 for idx in _weekly_last_sessions(market['dates']):
  if market['dates'][idx]<'2007-02-05':continue
  if idx+20>=len(market['dates']):continue
  c,q=_weights(market,idx,True),_weights(market,idx,False)
  if c is None or q is None:continue
  hc,hq=_hhi(c,market['risk_covariance'][idx]),_hhi(q,market['risk_covariance'][idx])
  if hc is None or hq is None:continue
  deltas.append(hq-hc);side_dates+=1
  if len(deltas)>1:
   turnover_c+=sum(abs(c[a]-last_c[a]) for a in ASSETS);turnover_q+=sum(abs(q[a]-last_q[a]) for a in ASSETS)
  last_c,last_q=c,q
  rows=[[market['returns'][a][market['dates'][j]] for a in ASSETS] for j in range(idx+1,idx+21)]
  cov=[[sum((r[i]-mean([x[i] for x in rows]))*(r[j]-mean([x[j] for x in rows])) for r in rows)/19 for j in range(8)] for i in range(8)]
  rc,rq=_hhi(c,cov),_hhi(q,cov)
  if rc is not None and rq is not None:realized.append(rq-rc)
 ac=[sample_autocorrelation(deltas,l) or 0. for l in range(1,6)]
 eff=effective_sample_length(len(deltas),ac); sd=pstdev(deltas) if len(deltas)>1 else 0.; ucb=mean(deltas)+1.645*sd/math.sqrt(eff) if eff and sd else mean(deltas)
 funded=eff>=49
 side_ok=(turnover_q>0 and (turnover_c-turnover_q)/turnover_q<=.2)
 falsified=funded and (ucb<.05 or not side_ok)
 decision='falsified' if falsified else 'not_falsified_not_validated' if funded else 'scope_restricted'
 post_parse_hard_stop=None
 report_mode='falsification_execution'
 if len(deltas)>465:
  decision='scope_restricted';falsified=False;report_mode='execution_invalidated_post_parse'
  post_parse_hard_stop='The sole run exceeded the locked 465 weekly-observation ceiling; no rerun is authorized.'
 report={**base,'report_mode':report_mode,'execution_status':decision,'decision':decision,'market_returns_read':True,'preflight':pre,'observation_counts':{'weekly_paired_observations':len(deltas),'effective_independent_bet_equivalents':eff,'mintrl_falsify':49,'asset_multiplier':1,'trade_multiplier':1},'primary_statistics':{'mean_hhi_delta':mean(deltas),'one_sided_upper_confidence_bound':ucb,'autocorrelations_lags_1_to_5':ac},'realized_confirmation':{'observations':len(realized),'mean_hhi_delta':mean(realized) if realized else None,'threshold':.05},'side_effects':{'candidate_turnover':turnover_c,'comparator_turnover':turnover_q,'relative_increase':None if turnover_q==0 else (turnover_c-turnover_q)/turnover_q,'met':side_ok},'regimes':{'claims':[],'rule':'no regime pooling; no inferential regime claim made'},'mechanism_autopsy':({'required':True,'summary':'Falsification triggered under the locked composite rule; inspect volatility concentration, turnover, constraints, and covariance mechanism before any new hypothesis.'} if falsified else None),'claim_limits':['E1 only','edge_claim none','validation sealed','no validation pooled'],'post_parse_hard_stop':post_parse_hard_stop}
 _append_ledger({'event':'real_return_decision_run','run_id':'B7.3-L3-ONE','producing_git_commit':base['producing_git_commit'],'container_sha256':pre['container_sha256'],'decision':decision})
 write_json(REPORT,report);return report
def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args()
 if not a.execute:print(json.dumps({'status':'blocked','blocker':'explicit_execute_flag_missing'}));return 1
 print(json.dumps(run(),indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
