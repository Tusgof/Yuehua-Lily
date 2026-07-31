"""B8.8R in-memory-only L-4 engine.  It accepts explicit synthetic rows, never paths."""
from __future__ import annotations
import math
from datetime import date
from statistics import mean
from typing import Any, Sequence
from lib.statistics import newey_west_variance_of_mean, paired_mean_minimum_observations, sample_autocorrelation, symmetric_eigenvalues
from lib.trend_baseline import CURRENT_EXPENSE_RATIOS
from lib.l4_b88_scientific_contract_v1 import METRICS, USEFUL, U4, U8, component_hhi, correlation_n_eff, top_dependency

AUTHORIZATIONS={key:False for key in ("data","container","market","return","signal","position","covariance","regime","cost","pnl","validation","provider","network","credentials","broker","paid","paper_trade","real_money","activation","execution","report","research_decision","ledger")}
SEAL={"status":"sealed_not_accessed","accessed":False}; Z95=1.6448536269514722

def _iso(value: object)->bool:
 try: return isinstance(value,str) and date.fromisoformat(value).isoformat()==value
 except ValueError: return False

def timing_is_matched(row: dict[str,Any])->bool:
 """Exact weekly decision, next session execution, then exactly t+1..t+20 sessions."""
 required={"week_sessions","decision_date","execution_date","realized_dates","u4_date","u8_date"}
 if set(row)!=required or not all(_iso(row[k]) for k in ("decision_date","execution_date","u4_date","u8_date")): return False
 sessions=row["week_sessions"]; realized=row["realized_dates"]
 if not isinstance(sessions,list) or not sessions or any(not _iso(x) for x in sessions) or sessions!=sorted(set(sessions)): return False
 if row["decision_date"]!=sessions[-1] or row["u4_date"]!=row["decision_date"] or row["u8_date"]!=row["decision_date"]: return False
 if not isinstance(realized,list) or len(realized)!=20 or any(not _iso(x) for x in realized) or realized!=sorted(set(realized)): return False
 return row["execution_date"]==realized[0] and row["execution_date"]>row["decision_date"] and realized[0]>row["decision_date"] and realized[-1]<="2015-12-31"

def directional_q(returns: Sequence[float])->float|None:
 if len(returns)!=60 or any(type(x) not in (int,float) or not math.isfinite(x) for x in returns): return None
 return sum(1 if x>0 else -1 if x<0 else 0 for x in returns)/60

def ewma_covariance(rows: Sequence[Sequence[float]])->tuple[list[list[float]],float]|None:
 if len(rows)!=60 or not rows or any(len(row)!=len(rows[0]) or any(type(x) not in (int,float) or not math.isfinite(x) for x in row) for row in rows): return None
 n=len(rows[0]); alpha=2/61; mu=[0.0]*n; second=[[0.0]*n for _ in range(n)]
 for row in rows:
  mu=[(1-alpha)*mu[i]+alpha*row[i] for i in range(n)]; second=[[(1-alpha)*second[i][j]+alpha*row[i]*row[j] for j in range(n)] for i in range(n)]
 cov=[[second[i][j]-mu[i]*mu[j] for j in range(n)] for i in range(n)]
 values=symmetric_eigenvalues(cov); return cov,sum(-x for x in values if x<0)

def q_weights(q: Sequence[float], covariance: Sequence[Sequence[float]])->tuple[list[float],dict[str,bool]]|None:
 if len(q)!=len(covariance) or not q or sum(abs(x) for x in q)==0: return None
 weights=[.9*x/sum(abs(y) for y in q) for x in q]; capped=False
 while any(abs(x)>.25+1e-12 for x in weights):
  capped=True; over=sum(max(abs(x)-.25,0) for x in weights); free=[i for i,x in enumerate(weights) if 0<abs(x)<=.25]
  weights=[math.copysign(min(abs(x),.25),x) for x in weights]
  if not free: break
  base=sum(abs(weights[i]) for i in free)
  for i in free: weights[i]+=math.copysign(over*abs(weights[i])/base,weights[i])
 variance=sum(weights[i]*covariance[i][j]*weights[j] for i in range(len(q)) for j in range(len(q))); scale=min(1,.10/math.sqrt(max(variance*252,0))) if variance>0 else 1
 return [x*scale for x in weights],{"cap":capped,"cash":sum(abs(x) for x in weights)<.9,"scale_down":scale<1}

def daily_costs(weights: Sequence[float], changes: Sequence[float], cash_return:float)->dict[str,float]:
 if len(weights)!=len(changes): raise ValueError("weight_change_shape")
 commission=sum(abs(x)*.00107 for x in changes); spread=sum(abs(x)*.0025 for x in changes); sell=sum(max(-x,0)*.0001 for x in changes)
 expense=sum(abs(w)*CURRENT_EXPENSE_RATIOS[s] / 252 for w,s in zip(weights,U8[:len(weights)])); borrow=sum(max(-w,0)*.03/252 for w in weights); cash=max(0,1-sum(abs(w) for w in weights))*cash_return
 return {"commission":commission,"spread_slippage":spread,"sell_surcharge":sell,"expense_ratio":expense,"short_borrow":borrow,"cash_yield":cash,"total":commission+spread+sell+expense+borrow-cash}

def actual_statistics(values:Sequence[float],metric:str)->dict[str,Any]|None:
 if metric not in METRICS or len(values)<6: return None
 lags=[sample_autocorrelation(values,k) for k in range(1,6)]
 if any(x is None for x in lags): return None
 sd=math.sqrt(sum((x-mean(values))**2 for x in values)/(len(values)-1)); hac=math.sqrt(newey_west_variance_of_mean(values,5)); useful=USEFUL[metric]
 plans={"falsify":(0.,useful),"validation_zero":(useful,0.),"validation_minimum_useful":(2*useful,useful)}
 try: mins={name:paired_mean_minimum_observations(alternative_mean=a,null_mean=n,planning_standard_deviation=sd,autocorrelations=lags,significance=.05,power=.8) for name,(a,n) in plans.items()}
 except ValueError:return None
 return {"values":list(values),"mean":mean(values),"sample_sd":sd,"lags_1_to_5":lags,"dependence_inflation":1+2*sum(lags),"hac_standard_error_lags_5":hac,"mintrl":mins,"falsify_ucb":mean(values)+Z95*hac,"validation_lcb":mean(values)-Z95*hac}

def classify_validation(stats:dict[str,dict[str,Any]],*,funded:bool,constraints_evaluable:bool,constraints_pass:bool,integrity_pass:bool,breach:bool)->str:
 if set(stats)!=set(METRICS) or not funded or not constraints_evaluable:return "validation_scope_restricted"
 if breach or not constraints_pass:return "validation_falsified_E1_only"
 if all(stats[name]["validation_lcb"]>USEFUL[name] for name in METRICS) and integrity_pass:return "validation_candidate"
 return "not_validated_E1"

def derive_weekly_observation(row:dict[str,Any])->dict[str,Any]|None:
 if set(row)!={"timing","q_u4","q_u8","covariance_u4","covariance_u8","q_history_u4","q_history_u8","weights_u4","weights_u8","changes_u4","changes_u8","cash_return"} or not timing_is_matched(row["timing"]): return None
 h4=component_hhi(row["weights_u4"],row["covariance_u4"]); h8=component_hhi(row["weights_u8"],row["covariance_u8"]); n4=correlation_n_eff(row["q_history_u4"]); n8=correlation_n_eff(row["q_history_u8"])
 d4=top_dependency(row["weights_u4"],row["covariance_u4"],U4); d8=top_dependency(row["weights_u8"],row["covariance_u8"],U8)
 if None in (h4,h8,n4,n8,d4,d8):return None
 return {"date":row["timing"]["decision_date"],"ex_ante_hhi_delta":h4-h8,"realized_hhi_delta":h4-h8,"top_dependency_delta":d4-d8,"n_eff_delta":n8[0]-n4[0],"costs_u4":daily_costs(row["weights_u4"],row["changes_u4"],row["cash_return"]),"costs_u8":daily_costs(row["weights_u8"],row["changes_u8"],row["cash_return"]),"covariance_clipped_mass":n4[1]+n8[1]}
