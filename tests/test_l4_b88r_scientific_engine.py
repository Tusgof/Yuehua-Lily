from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from lib.l4_b88r_scientific_engine_v2 import *
from scripts.validate_l_4_breadth_b88r_phase_a_execution_contract_v2 import validate as gate
from scripts.validate_l_4_breadth_b88r_scientific_report_v2 import validate as report
ROOT=Path(__file__).resolve().parents[1]; FIX=ROOT/'tests/fixtures/l4_b88r/synthetic_blocked_report_v2.json'
class B88R(unittest.TestCase):
 def test_gate_report_and_bootstrap(self):
  self.assertEqual('pass',gate()['status']);self.assertEqual('pass',report(FIX)['status'])
  from scripts.run_l_4_breadth_b88r_committed_bootstrap_v2 import preflight
  self.assertEqual('blocked',preflight()['status'])
 def test_timing_strict_tplus_one(self):
  r={'week_sessions':['2015-01-02'],'decision_date':'2015-01-02','execution_date':'2015-01-05','realized_dates':[f'2015-02-{x:02d}' for x in range(1,21)],'u4_date':'2015-01-02','u8_date':'2015-01-02'}
  self.assertFalse(timing_is_matched(r));r['realized_dates']=['2015-01-05']+[f'2015-02-{x:02d}' for x in range(1,20)];self.assertTrue(timing_is_matched(r))
 def test_q_covariance_costs_and_validation_equality(self):
  self.assertAlmostEqual(0,directional_q([.1,-.1]*30));cov,mass=ewma_covariance([[.01*(i+j+1) for j in range(4)] for i in range(60)]);self.assertEqual(4,len(cov));self.assertGreaterEqual(mass,0);w,f=q_weights([1,1,1,1],cov);self.assertLessEqual(sum(abs(x) for x in w),.9);self.assertIn('expense_ratio',daily_costs(w,[.02]*4,0))
  s={m:{'validation_lcb':USEFUL[m]} for m in METRICS};self.assertEqual('not_validated_E1',classify_validation(s,funded=True,constraints_evaluable=True,constraints_pass=True,integrity_pass=True,breach=False));self.assertEqual('validation_falsified_E1_only',classify_validation(s,funded=True,constraints_evaluable=True,constraints_pass=True,integrity_pass=True,breach=True))
 def test_closed_world_rejects_forgery(self):
  p=json.loads(FIX.read_text('ascii'));p['unknown']=True
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'x.json';f.write_text(json.dumps(p),encoding='ascii');self.assertEqual('blocked',report(f)['status'])
if __name__=='__main__':unittest.main()
