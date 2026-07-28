from __future__ import annotations
import copy,hashlib,subprocess,unittest
from pathlib import Path
from lib.l3_corrected_rerun_v6 import Z_ONE_SIDED_95,recompute_statistics
from scripts.validate_l_3_corrected_rerun_report_v6 import IDENTITIES,IMPLEMENTATION,validate
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def statistics(n,mean=.10):
 r=recompute_statistics(n,.1,[.25,.125,.0625,.03125,.015625]);return {'paired_delta_mean':mean,'paired_delta_standard_deviation':.1,'lag_1_to_5_autocorrelations':[.25,.125,.0625,.03125,.015625],'autocorrelation_inflation':r['autocorrelation_inflation'],'standard_error':r['standard_error'],'one_sided_95_ucb':mean+Z_ONE_SIDED_95*r['standard_error'],'actual_mintrl_falsify':r['actual_mintrl_falsify'],'null_mean_delta':.05,'adverse_alternative_mean_delta':0.0,'z_one_sided_95':Z_ONE_SIDED_95,'z_power_80':.8416212335729143}
def fixture(decision='not_falsified_not_validated',n=98):
 p={'producing_git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()};p.update({k:{'path':v,'sha256':sha(v)} for k,v in IMPLEMENTATION.items()});p.update({k:{'present':True,'path':v,'sha256':sha(v)} for k,v in IDENTITIES.items()});s=statistics(n)
 branch=lambda turn,events:{'turnover':turn,'commission':.3,'spread_slippage':.3,'sell_surcharge':.4,'cap_events':events,'cash_events':events,'scale_down_events':events}
 half=n//2;claim=lambda name:{'name':name,'paired_observations':half,'effective_independent_bets':float(half),'statistics':statistics(half)}
 return {'schema_version':'lily_l3_corrected_rerun_report_v6','order_id':'B7.10','hypothesis_id':'L-3','report_mode':'future_execution','decision':decision,'evidence_tier':'E1','edge_claim':'none','provenance':p,'counts':{'paired_observations':n,'effective_independent_bets':float(n),'mintrl_falsify':49,'asset_multiplier':1,'day_multiplier':1,'trade_multiplier':1,'t20_multiplier':1},'primary':{'candidate_mean_hhi':.4,'comparator_mean_hhi':.5,'mean_delta':.1,'threshold':.05,'statistics':s},'realized':{'candidate_mean_hhi':.4,'comparator_mean_hhi':.5,'mean_delta':.1,'threshold':.05,'complete_t_plus_20_observations':n},'side_effects':{'paired_observations':n,'candidate':branch(12,10),'comparator':branch(10,5)},'regimes':{'claims':[claim('low'),claim('middle')],'unclassified_observations':0,'pooled':False,'claimed_regime_statement':'two_of_three_inferential'},'validation_seal':{'status':'sealed_not_accessed','accessed':False},'autopsy':None}
class B710ReportTests(unittest.TestCase):
 def test_golden_statistics_and_positive(self):
  s=statistics(49);self.assertAlmostEqual(1.96875,s['autocorrelation_inflation']);self.assertEqual(49,s['actual_mintrl_falsify']);self.assertGreater(s['one_sided_95_ucb'],s['paired_delta_mean']);self.assertEqual('pass',validate(fixture())['status'],validate(fixture()))
 def test_ucb_mutual_exclusion_below_equal_above(self):
  for desired,decision,ok in ((.049,'falsified',True),(.05,'not_falsified_not_validated',True),(.051,'not_falsified_not_validated',True),(.049,'not_falsified_not_validated',False),(.05,'falsified',False),(.051,'falsified',False)):
   r=fixture(decision);s=r['primary']['statistics'];s['paired_delta_mean']=desired-Z_ONE_SIDED_95*s['standard_error'];s['one_sided_95_ucb']=desired
   r['primary']['mean_delta']=s['paired_delta_mean'];r['primary']['candidate_mean_hhi']=.5-s['paired_delta_mean']
   if decision=='falsified':r['autopsy']={k:'a' for k in ('volatility_scaling_concentration','common_constraints','ex_ante_vs_realized_hhi','turnover_cost','implementation_data_alternatives')}
   self.assertEqual('pass' if ok else 'blocked',validate(r)['status'],(desired,decision,validate(r)))
 def test_tamper_hhi_events_regimes_statistics_and_real_identity_fail(self):
  cases=[]
  for bad in (-.1,1.1):
   r=fixture();r['primary']['candidate_mean_hhi']=bad;r['primary']['mean_delta']=r['primary']['comparator_mean_hhi']-bad;cases.append(r)
  r=fixture();r['primary']['statistics']['one_sided_95_ucb']+=.01;cases.append(r)
  r=fixture();r['side_effects']['candidate']['cap_events']=99;cases.append(r)
  r=fixture(n=100);r['side_effects']['candidate']['cash_events']=15;r['side_effects']['comparator']['cash_events']=5;self.assertEqual('pass',validate(r)['status'])
  r=fixture();r['regimes']['claims'][0]['paired_observations']=50;cases.append(r)
  r=fixture();r['provenance']['container_identity']['path']='reports/experiments/real.json';cases.append(r)
  for r in cases:self.assertEqual('blocked',validate(r)['status'],validate(r))
