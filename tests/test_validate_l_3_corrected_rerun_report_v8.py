from __future__ import annotations
import copy,json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from lib.l3_corrected_rerun_v8 import derive
from scripts.run_l_3_corrected_rerun_v8 import run_fixture
from scripts.validate_l_3_corrected_rerun_report_v8 import validate
ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/l3_corrected_rerun_v8/synthetic_evaluation.json'
def payload():return json.loads(FIXTURE.read_text(encoding='utf-8'))
def funded_vector():
 base=payload()['weekly_observations'];rows=[]
 for index in range(1,148):
  row=copy.deepcopy(base[(index-1)%len(base)]);row['observation_index']=index;row['observation_id']=f'synthetic-week-{index:03d}';row['regime']=('low','middle','high')[(index-1)//49];rows.append(row)
 return rows
class B712ReportTests(unittest.TestCase):
 def test_committed_fixture_and_runner_success(self):
  self.assertEqual('pass',validate(payload())['status']);self.assertEqual('pass',run_fixture(FIXTURE)['status'])
 def test_golden_fixed_vector_all_statistics(self):
  primary=validate(payload())['derived']['primary'];expected=[.9444444444444444,.888965122927387,.8336382694873262,.7785401181627597,.7237469029921859]
  self.assertAlmostEqual(.0975,primary['paired_delta_mean']);self.assertAlmostEqual(.01573213272255227,primary['paired_delta_standard_deviation'])
  for actual,want in zip(primary['lag_1_to_5_sample_autocorrelations'],expected,strict=True):self.assertAlmostEqual(want,actual)
  self.assertAlmostEqual(9.338669716028207,primary['locked_asymptotic_autocorrelation_inflation']);self.assertAlmostEqual(.006542341797740515,primary['standard_error']);self.assertAlmostEqual(.10826119463476969,primary['one_sided_95_ucb']);self.assertEqual(49,primary['actual_raw_observation_mintrl_falsify'])
 def test_inclusive_relative_and_event_boundaries_are_deterministic(self):
  rows=payload()['weekly_observations'];derived,errors=derive(rows);self.assertEqual([],errors);self.assertTrue(derived['side_effect_limits_met']);self.assertEqual(.2,derived['side_effects']['turnover_increase']);self.assertEqual(.2,derived['side_effects']['cost_increase'])
  cost=copy.deepcopy(rows);cost[0]['side_effects']['candidate']['commission']=math.nextafter(.12,math.inf);derived,errors=derive(cost);self.assertEqual([],errors);self.assertFalse(derived['side_effect_limits_met'])
  turnover=copy.deepcopy(rows);turnover[0]['side_effects']['candidate']['turnover']=math.nextafter(6.0,math.inf);derived,errors=derive(turnover);self.assertEqual([],errors);self.assertFalse(derived['side_effect_limits_met'])
  event=copy.deepcopy(rows)
  for index in range(55,61):row=copy.deepcopy(rows[(index-1)%54]);row['observation_index']=index;row['observation_id']=f'synthetic-week-{index:03d}';row['regime']=('low','middle','high')[(index-1)%3];event.append(row)
  for key in ('cap_event','cash_event','scale_down_event'):
   exact=copy.deepcopy(event)
   for row in exact[-6:]:row['side_effects']['candidate'][key]=True
   derived,errors=derive(exact);self.assertEqual([],errors);self.assertTrue(derived['side_effect_limits_met']);self.assertEqual(10.0,derived['side_effects'][f'{key}_increase_percentage_points'])
   breached=copy.deepcopy(exact);breached[-7]['side_effects']['candidate'][key]=True
   derived,errors=derive(breached);self.assertEqual([],errors);self.assertFalse(derived['side_effect_limits_met'])
 def test_mintrl_and_two_of_three_regime_funding_boundaries(self):
  rows=funded_vector();derived,errors=derive(rows);self.assertEqual([],errors);self.assertTrue(derived['primary']['raw_n_meets_actual_mintrl']);self.assertTrue(derived['two_of_three_regimes_funded'])
  for row in rows:
   if row['regime'] in {'middle','high'} and row['observation_index']%49==0:row['regime']='low'
  derived,errors=derive(rows);self.assertEqual([],errors);self.assertFalse(derived['two_of_three_regimes_funded'])
 def test_runner_rejects_outside_path_and_fixture_tamper(self):
  with tempfile.TemporaryDirectory() as tmp:self.assertEqual('blocked',run_fixture(Path(tmp)/'synthetic_evaluation.json')['status'])
  with patch('scripts.run_l_3_corrected_rerun_v8.file_sha256',return_value='tampered'):
   self.assertEqual('blocked',run_fixture(FIXTURE)['status'])
 def test_report_rejects_e1_execution_and_observation_tamper(self):
  for mutate in (lambda item:item.update({'evidence_tier':'E1'}),lambda item:item.update({'report_mode':'future_execution','decision':'falsified','evidence_tier':'E1'}),lambda item:item['weekly_observations'][0].update({'primary_candidate_hhi':.9})):
   item=payload();mutate(item);self.assertEqual('blocked',validate(item)['status'])
if __name__=='__main__':unittest.main()
