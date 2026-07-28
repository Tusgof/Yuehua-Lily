from __future__ import annotations
import copy, unittest
from lib.l3_corrected_rerun_v7 import Z_ONE_SIDED_95, derive
from scripts.validate_l_3_corrected_rerun_report_v7 import validate

def observation(index:int, regime:str)->dict:
 delta=.07+.001*index;candidate=.40+(.01*((index-1)%4));comparator=candidate+delta
 side=lambda turnover,events:{'turnover':turnover,'commission':.10,'spread_slippage':.10,'sell_surcharge':.10,'cap_event':events,'cash_event':False,'scale_down_event':False}
 return {'observation_index':index,'observation_id':f'synthetic-week-{index:03d}','regime':regime,'primary_candidate_hhi':candidate,'primary_comparator_hhi':comparator,'realized_candidate_hhi':candidate,'realized_comparator_hhi':comparator,'side_effects':{'candidate':side(6.0,False),'comparator':side(5.0,False)}}
def report(n:int=54)->dict:
 regimes=('low',)*18+('middle',)*18+('high',)*18
 return {'schema_version':'lily_l3_corrected_rerun_report_v7','order_id':'B7.11','hypothesis_id':'L-3','report_mode':'synthetic_evaluation','decision':'not_run','evidence_tier':'E0','edge_claim':'none','weekly_observations':[observation(i,regimes[i-1]) for i in range(1,n+1)],'closed_world_observations_sha256':'66cd843cde8e0af108f7e9abae0a62b667f9e6c002aa6698406ab9da8d140bd6','synthetic_expected_classification':'non_authoritative_synthetic_only','validation_seal':{'status':'sealed_not_accessed','accessed':False}}

class B711ClosedWorldTests(unittest.TestCase):
 def test_golden_fixed_vector_derives_all_inputs(self):
  payload=report();result=validate(payload);self.assertEqual('pass',result['status'],result)
  primary=result['derived']['primary'];self.assertEqual(54,primary['raw_weekly_paired_observations']);self.assertAlmostEqual(.0975,primary['paired_delta_mean']);self.assertAlmostEqual(0.015732132722553,primary['paired_delta_standard_deviation']);self.assertEqual(5,len(primary['lag_1_to_5_sample_autocorrelations']));self.assertGreater(primary['locked_asymptotic_autocorrelation_inflation'],0);self.assertEqual(49,primary['actual_raw_observation_mintrl_falsify']);self.assertGreater(primary['one_sided_95_ucb'],.0975);self.assertTrue(primary['raw_n_meets_actual_mintrl']);self.assertEqual(3,len(result['derived']['regimes']));self.assertFalse(result['derived']['two_of_three_regimes_funded'])
 def test_adversarial_observation_identity_order_regime_and_hhi_fail(self):
  cases=[]
  altered=report();altered['weekly_observations'][0]['primary_comparator_hhi']+=.01;cases.append(altered)
  ordered=report();ordered['weekly_observations'][0],ordered['weekly_observations'][1]=ordered['weekly_observations'][1],ordered['weekly_observations'][0];cases.append(ordered)
  regime=report();regime['weekly_observations'][0]['regime']='unknown';cases.append(regime)
  hhi=report();hhi['weekly_observations'][0]['primary_candidate_hhi']=1.1;cases.append(hhi)
  identity=report();identity['weekly_observations'][0]['observation_id']='tampered';cases.append(identity)
  for payload in cases:self.assertEqual('blocked',validate(payload)['status'],validate(payload))
 def test_adversarial_side_effect_boundaries_and_zero_denominator(self):
  exact=report()
  for item in exact['weekly_observations']:item['side_effects']['candidate']['turnover']=6.0
  self.assertTrue(validate(exact)['derived']['side_effect_limits_met'])
  breached=copy.deepcopy(exact);breached['weekly_observations'][0]['side_effects']['candidate']['turnover']=6.0001;self.assertEqual('blocked',validate(breached)['status'])
  side=report();side['weekly_observations'][0]['side_effects']['candidate']['cap_event']=1;self.assertEqual('blocked',validate(side)['status'])
  zero=report();[item['side_effects']['comparator'].update({'turnover':0.0,'commission':0.0,'spread_slippage':0.0,'sell_surcharge':0.0}) for item in zero['weekly_observations']];self.assertEqual('blocked',validate(zero)['status'])
 def test_direct_derivation_checks_exact_twenty_percent_and_ten_point_boundaries(self):
  observations=report()['weekly_observations']
  for index in range(55,61):observations.append(observation(index,('low','middle','high')[(index-1)%3]))
  for item in observations[-6:]:item['side_effects']['candidate']['cap_event']=True
  derived,errors=derive(observations);self.assertEqual([],errors);self.assertTrue(derived['side_effect_limits_met']);self.assertAlmostEqual(10.0,derived['side_effects']['cap_event_increase_percentage_points'])
  for item in observations[-7:]:item['side_effects']['candidate']['cash_event']=True
  derived,errors=derive(observations);self.assertEqual([],errors);self.assertFalse(derived['side_effect_limits_met']);self.assertGreater(derived['side_effects']['cash_event_increase_percentage_points'],10.0)
 def test_fail_closed_for_short_variance_nan_inf_and_e1_or_execution_attempts(self):
  short=report();short['weekly_observations']=short['weekly_observations'][:5]
  flat=report();[item.update({'primary_candidate_hhi':.4,'primary_comparator_hhi':.5}) for item in flat['weekly_observations']]
  nan=report();nan['weekly_observations'][0]['primary_candidate_hhi']=float('nan')
  infinite=report();infinite['weekly_observations'][0]['side_effects']['candidate']['turnover']=float('inf')
  e1=report();e1['evidence_tier']='E1'
  execution=report();execution['report_mode']='future_execution';execution['decision']='falsified';execution['evidence_tier']='E1'
  for payload in (short,flat,nan,infinite,e1,execution):self.assertEqual('blocked',validate(payload)['status'],validate(payload))
 def test_extra_missing_and_mintrl_mismatch_cannot_be_reporter_supplied(self):
  extra=report();extra['derived']={};missing=report();del missing['weekly_observations'][0]['regime']
  supplied=report();supplied['actual_mintrl_falsify']=1
  for payload in (extra,missing,supplied):self.assertEqual('blocked',validate(payload)['status'],validate(payload))

if __name__=='__main__':unittest.main()
