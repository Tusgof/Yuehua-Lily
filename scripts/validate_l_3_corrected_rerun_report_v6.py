"""B7.10 prospective E0-only report validator; it cannot validate real execution."""
from __future__ import annotations
import argparse, json, math, subprocess, sys
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.l3_corrected_rerun_v6 import ADVERSE_DELTA, MINTRL_FLOOR, NULL_DELTA, Z_ONE_SIDED_95, Z_POWER_80, finite, recompute_statistics
from lib.provenance import file_sha256

GATE=ROOT/'experiments/l_3_corrected_rerun_activation_v6.json'
IMPLEMENTATION={'gate':'experiments/l_3_corrected_rerun_activation_v6.json','runner':'scripts/run_l_3_corrected_rerun_v6.py','report_validator':'scripts/validate_l_3_corrected_rerun_report_v6.py','report_schema':'schemas/l_3_corrected_rerun_report_v6.schema.json','side_effect_library':'lib/l3_corrected_rerun_v6.py'}
IDENTITIES={'container_identity':'tests/fixtures/l3_corrected_rerun_v5/identities/synthetic_container.json','schedule_identity':'tests/fixtures/l3_corrected_rerun_v5/identities/synthetic_schedule.json','ledger_identity':'tests/fixtures/l3_corrected_rerun_v5/identities/synthetic_ledger.json'}
TOP={'schema_version','order_id','hypothesis_id','report_mode','decision','evidence_tier','edge_claim','provenance','counts','primary','realized','side_effects','regimes','validation_seal','autopsy'}
AUTOPSY={'volatility_scaling_concentration','common_constraints','ex_ante_vs_realized_hhi','turnover_cost','implementation_data_alternatives'}
STAT={'paired_delta_mean','paired_delta_standard_deviation','lag_1_to_5_autocorrelations','autocorrelation_inflation','standard_error','one_sided_95_ucb','actual_mintrl_falsify','null_mean_delta','adverse_alternative_mean_delta','z_one_sided_95','z_power_80'}
BRANCH={'turnover','commission','spread_slippage','sell_surcharge','cap_events','cash_events','scale_down_events'}

def _head():
 r=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=False);return r.stdout.strip() if r.returncode==0 else None
def _exact(value:Any, keys:set[str], label:str, b:list[str]):
 if not isinstance(value,dict) or set(value)!=keys:b.append('shape:'+label);return None
 return value
def _identity(value:Any,path:str)->bool:return isinstance(value,dict) and value=={'path':path,'sha256':file_sha256(ROOT/path)}
def _bound(value:Any,path:str,present:bool)->bool:
 if not isinstance(value,dict) or set(value)!={'present','path','sha256'}:return False
 return value==({'present':True,'path':path,'sha256':file_sha256(ROOT/path)} if present else {'present':False,'path':None,'sha256':None})
def _close(a:float,b:float)->bool:return abs(a-b)<=1e-12

def _statistics(value:Any,n:Any,label:str,b:list[str])->dict|None:
 stat=_exact(value,STAT,label,b)
 if stat is None:return None
 if not (all(finite(stat.get(k)) for k in ('paired_delta_mean','paired_delta_standard_deviation','autocorrelation_inflation','standard_error','one_sided_95_ucb','null_mean_delta','adverse_alternative_mean_delta','z_one_sided_95','z_power_80')) and type(stat.get('actual_mintrl_falsify')) is int):b.append('statistics_nonfinite:'+label);return None
 expected=recompute_statistics(n,stat['paired_delta_standard_deviation'],stat['lag_1_to_5_autocorrelations'])
 if expected is None or stat['null_mean_delta']!=NULL_DELTA or stat['adverse_alternative_mean_delta']!=ADVERSE_DELTA or not _close(stat['z_one_sided_95'],Z_ONE_SIDED_95) or not _close(stat['z_power_80'],Z_POWER_80) or not _close(stat['autocorrelation_inflation'],expected['autocorrelation_inflation']) or not _close(stat['standard_error'],expected['standard_error']) or not _close(stat['one_sided_95_ucb'],stat['paired_delta_mean']+Z_ONE_SIDED_95*expected['standard_error']) or stat['actual_mintrl_falsify']!=expected['actual_mintrl_falsify']:
  b.append('statistics_recomputation_mismatch:'+label)
 return stat

def _hhi(value:Any,label:str,b:list[str]):
 if not finite(value) or value<.125 or value>1:b.append('hhi_domain:'+label)

def _blank(counts,primary,realized,side,regimes):
 return counts=={'paired_observations':0,'effective_independent_bets':0.0,'mintrl_falsify':49,'asset_multiplier':1,'day_multiplier':1,'trade_multiplier':1,'t20_multiplier':1} and primary=={'candidate_mean_hhi':None,'comparator_mean_hhi':None,'mean_delta':None,'threshold':None,'statistics':None} and realized=={'candidate_mean_hhi':None,'comparator_mean_hhi':None,'mean_delta':None,'threshold':None,'complete_t_plus_20_observations':0} and side=={'paired_observations':0,'candidate':None,'comparator':None} and regimes=={'claims':[],'unclassified_observations':0,'pooled':False,'claimed_regime_statement':'none'}

def validate(payload:Any)->dict:
 if not isinstance(payload,dict):return {'status':'blocked','blockers':['report_not_object']}
 b=[]
 if set(payload)!=TOP:b.append('shape:top')
 if {k:payload.get(k) for k in ('schema_version','order_id','hypothesis_id','edge_claim')}!={'schema_version':'lily_l3_corrected_rerun_report_v6','order_id':'B7.10','hypothesis_id':'L-3','edge_claim':'none'}:b.append('identity')
 p=_exact(payload.get('provenance'),{'producing_git_commit',*IMPLEMENTATION,*IDENTITIES},'provenance',b);c=_exact(payload.get('counts'),{'paired_observations','effective_independent_bets','mintrl_falsify','asset_multiplier','day_multiplier','trade_multiplier','t20_multiplier'},'counts',b);pr=_exact(payload.get('primary'),{'candidate_mean_hhi','comparator_mean_hhi','mean_delta','threshold','statistics'},'primary',b);rz=_exact(payload.get('realized'),{'candidate_mean_hhi','comparator_mean_hhi','mean_delta','threshold','complete_t_plus_20_observations'},'realized',b);side=_exact(payload.get('side_effects'),{'paired_observations','candidate','comparator'},'side_effects',b);reg=_exact(payload.get('regimes'),{'claims','unclassified_observations','pooled','claimed_regime_statement'},'regimes',b)
 mode,decision,tier=payload.get('report_mode'),payload.get('decision'),payload.get('evidence_tier');auto=payload.get('autopsy')
 allowed={'synthetic_not_run':('not_run','E0'),'pre_return_failure':('scope_restricted','E1')}
 if mode in allowed:
  if (decision,tier)!=allowed[mode] or auto is not None:b.append('mode_decision_tier_autopsy_matrix')
 elif mode=='future_execution':
  if decision not in {'falsified','not_falsified_not_validated'} or tier!='E1':b.append('mode_decision_tier_autopsy_matrix')
  if decision=='falsified' and (not isinstance(auto,dict) or set(auto)!=AUTOPSY or not all(isinstance(v,str) and v for v in auto.values())):b.append('five_part_autopsy_required')
  if decision=='not_falsified_not_validated' and auto is not None:b.append('mode_decision_tier_autopsy_matrix')
 else:b.append('mode_decision_tier_autopsy_matrix')
 if p:
  if p.get('producing_git_commit')!=_head():b.append('producing_checkout_head_mismatch')
  for n,path in IMPLEMENTATION.items():
   if not _identity(p.get(n),path):b.append('implementation_identity_mismatch:'+n)
  for n,path in IDENTITIES.items():
   if not _bound(p.get(n),path,mode=='future_execution'):b.append('synthetic_e0_identity_only:'+n)
 if payload.get('validation_seal')!={'status':'sealed_not_accessed','accessed':False}:b.append('validation_seal_broken')
 if not all(x is not None for x in (c,pr,rz,side,reg)):return {'status':'blocked','blockers':sorted(set(b))}
 if mode!='future_execution':
  if not _blank(c,pr,rz,side,reg):b.append('nonexecution_evidence_must_be_blank')
  return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}
 n=c.get('paired_observations')
 if not(type(n)is int and 49<=n<=465 and finite(c.get('effective_independent_bets'),nonnegative=True) and c['effective_independent_bets']>=49 and c.get('mintrl_falsify')==49 and all(c.get(k)==1 for k in ('asset_multiplier','day_multiplier','trade_multiplier','t20_multiplier'))):b.append('counts_or_multipliers_invalid')
 for x,label in ((pr,'primary'),(rz,'realized')):
  _hhi(x.get('candidate_mean_hhi'),label+'.candidate',b);_hhi(x.get('comparator_mean_hhi'),label+'.comparator',b)
  if not finite(x.get('mean_delta')) or not _close(x['mean_delta'],x['comparator_mean_hhi']-x['candidate_mean_hhi']) or x.get('threshold')!=.05:b.append('hhi_delta_mismatch:'+label)
 if rz.get('complete_t_plus_20_observations')!=n:b.append('realized_confirmation_incomplete')
 stat=_statistics(pr.get('statistics'),n,'primary',b)
 if stat is not None and not _close(stat['paired_delta_mean'],pr['mean_delta']):b.append('primary_mean_delta_statistics_mismatch')
 funded=stat is not None and n>=stat['actual_mintrl_falsify'] and c.get('effective_independent_bets',0)>=stat['actual_mintrl_falsify']
 if not funded:b.append('effective_funding_not_met')
 if side.get('paired_observations')!=n or not isinstance(side.get('candidate'),dict) or not isinstance(side.get('comparator'),dict) or set(side['candidate'])!=BRANCH or set(side['comparator'])!=BRANCH:b.append('side_effect_shape');metrics=None
 else:
  a,z=side['candidate'],side['comparator']; ok=all(finite(q.get(k),nonnegative=True) for q in (a,z) for k in ('turnover','commission','spread_slippage','sell_surcharge')) and all(type(q.get(k))is int and 0<=q[k]<=n for q in (a,z) for k in ('cap_events','cash_events','scale_down_events'))
  if not ok or z['turnover']==0 or sum(z[k] for k in ('commission','spread_slippage','sell_surcharge'))==0:b.append('side_effect_not_evaluable');metrics=None
  else:
   ac=sum(a[k] for k in ('commission','spread_slippage','sell_surcharge'));zc=sum(z[k] for k in ('commission','spread_slippage','sell_surcharge'));metrics=[(a['turnover']-z['turnover'])/z['turnover'],(ac-zc)/zc,*[(a[k]-z[k])/n for k in ('cap_events','cash_events','scale_down_events')]]
 claims=reg.get('claims'); names=[];regime_funded=0
 if reg.get('pooled') is not False or reg.get('claimed_regime_statement') not in {'none','two_of_three_inferential'} or type(reg.get('unclassified_observations')) is not int or not isinstance(claims,list):b.append('regime_shape')
 else:
  names=[q.get('name') for q in claims if isinstance(q,dict)]
  if len(names)!=len(claims) or names!=sorted(names,key=('low','middle','high').index) or len(set(names))!=len(names) or any(x not in {'low','middle','high'} for x in names):b.append('regime_inventory_invalid')
  total=reg['unclassified_observations']+sum(q.get('paired_observations',-1) for q in claims if isinstance(q,dict))
  if reg['unclassified_observations']<0 or total!=n:b.append('regime_observation_conservation')
  for q in claims:
   if not isinstance(q,dict) or set(q)!={'name','paired_observations','effective_independent_bets','statistics'}:b.append('regime_claim_shape');continue
   rs=_statistics(q['statistics'],q['paired_observations'],'regime:'+q['name'],b)
   if rs and type(q['paired_observations'])is int and q['paired_observations']>=rs['actual_mintrl_falsify'] and finite(q['effective_independent_bets'],nonnegative=True) and q['effective_independent_bets']>=rs['actual_mintrl_falsify']:regime_funded+=1
  if reg['claimed_regime_statement']=='two_of_three_inferential' and regime_funded<2:b.append('two_of_three_not_funded')
  if reg['claimed_regime_statement']=='none' and claims:b.append('unclaimed_regime_evidence')
 if reg.get('claimed_regime_statement')!='two_of_three_inferential':b.append('claimed_regime_funding_missing')
 breach=metrics is not None and any(v>lim for v,lim in zip(metrics,(.20,.20,.10,.10,.10),strict=True))
 ucb=stat['one_sided_95_ucb'] if stat else None
 if decision=='not_falsified_not_validated' and (ucb is None or ucb<.05 or breach):b.append('not_falsified_decision_contradicts_evidence')
 if decision=='falsified' and not (ucb is not None and ucb<.05 or breach):b.append('falsified_requires_ucb_or_numeric_side_breach')
 return {'status':'pass' if not b else 'blocked','blockers':sorted(set(b))}

def main():
 a=argparse.ArgumentParser(description='Validate a prospective B7.10 E0-only L-3 report.');a.add_argument('report',type=Path);x=a.parse_args()
 try:p=json.loads(x.report.read_text(encoding='utf-8'))
 except Exception as e:print(json.dumps({'status':'blocked','blockers':[f'unreadable:{type(e).__name__}']}));return 1
 r=validate(p);print(json.dumps(r,sort_keys=True));return r['status']!='pass'
if __name__=='__main__':raise SystemExit(main())
