from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from lib.l3_corrected_rerun_v2 import ASSETS,build_schedule,compute_side_effects,scan_synthetic_envelope
from scripts.validate_l_3_corrected_rerun_activation_v2 import validate as validate_activation
from scripts.validate_l_3_b76_preflight_provenance_addendum_v1 import validate as validate_addendum
ROOT=Path(__file__).resolve().parents[1]
class V2Tests(unittest.TestCase):
 def envelope(self):return json.loads((ROOT/'tests/fixtures/l3_corrected_rerun_v2/synthetic_envelope.json').read_text())
 def test_fixture_ignores_metadata_dates_and_intersects(self):
  r=scan_synthetic_envelope(self.envelope());self.assertEqual('pass',r['status']);self.assertEqual(['2007-02-05'],r['common_sessions']);self.assertFalse(r['return_values_exposed'])
 def test_structural_negative_cases(self):
  for mutate,blocker in ((lambda x:x.update(schema_version='wrong'),'schema_version_mismatch'),(lambda x:x['symbols'].reverse(),'symbol_identity_or_order_mismatch'),(lambda x:x['symbols'].append(copy.deepcopy(x['symbols'][0])),'symbol_envelope_count_mismatch')):
   x=self.envelope();mutate(x);self.assertIn(blocker,scan_synthetic_envelope(x)['blockers'])
  x=self.envelope()
  for symbol in x['symbols']:symbol['records'].append({'session_date':'2016-01-04','availability_timestamp':'x','total_return_close':1})
  self.assertIn('mixed_validation_session_hard_stop',scan_synthetic_envelope(x)['blockers'])
 def test_schedule_boundaries(self):
  sessions=[f'2007-02-{d:02d}' for d in range(5,29)];self.assertEqual('pass',build_schedule(sessions,['2007-02-05'])['status']);self.assertIn('pre_start_weekly_decision',build_schedule(sessions,['2007-02-04'])['blockers']);self.assertIn('weekly_observation_ceiling_exceeded',build_schedule(sessions,['2007-02-05']*466)['blockers'])
 def test_side_effects_are_explicit_and_zero_denominator_blocks(self):
  rows=[{'weights':{a:(.1 if a==ASSETS[0] else 0) for a in ASSETS},'cost':.01,'cap_binding':False,'cash_constraint':False,'scale_down':False},{'weights':{a:(.2 if a==ASSETS[0] else 0) for a in ASSETS},'cost':.02,'cap_binding':True,'cash_constraint':False,'scale_down':False}]
  r=compute_side_effects(rows,rows);self.assertTrue(r['evaluable']);self.assertTrue(r['met']);self.assertFalse(compute_side_effects(rows,[] )['evaluable'])
 def test_gate_and_addendum_pass(self):self.assertEqual('pass',validate_activation()['status']);self.assertEqual('pass',validate_addendum()['status'])
if __name__=='__main__':unittest.main()
