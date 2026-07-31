from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from lib.l4_b88_scientific_contract_v1 import *
from scripts.validate_l_4_breadth_b88_phase_a_execution_contract_v1 import validate as validate_gate
from scripts.validate_l_4_breadth_b88_scientific_report_v1 import validate as validate_report

ROOT=Path(__file__).resolve().parents[1]; FIXTURE=ROOT/"tests/fixtures/l4_b88/synthetic_blocked_report_v1.json"
class L4B88ContractTests(unittest.TestCase):
 def test_gate_and_synthetic_fixture_are_closed_world(self): self.assertEqual("pass",validate_gate()["status"]); self.assertEqual("pass",validate_report(FIXTURE)["status"])
 def test_u_equals_q_cap_scale_and_costs(self):
  weights,flags=gross_cap_scale([1.,1.,1.,1.],[[.01 if i==j else 0 for j in range(4)] for i in range(4)]); self.assertAlmostEqual(.9,sum(abs(x) for x in weights)); self.assertFalse(flags["scale_down"]); self.assertAlmostEqual(.00357,booked_cost([0.],[1.]),places=9)
 def test_hhi_top_dependency_and_n_eff(self):
  covariance=[[.04 if i==j else 0 for j in range(4)] for i in range(4)]; self.assertAlmostEqual(.25,component_hhi([.225]*4,covariance)); self.assertAlmostEqual(.25,top_dependency([.225]*4,covariance,U4)); result=correlation_n_eff([[float((week+asset)%7) for asset in range(4)] for week in range(52)]); self.assertIsNotNone(result); self.assertGreater(result[0],1); self.assertGreaterEqual(result[1],0)
 def test_non_evaluable_and_timing_no_lookahead(self):
  self.assertIsNone(correlation_n_eff([[1.,1.,1.,1.] for _ in range(52)])); good={"decision_date":"2015-01-02","execution_date":"2015-01-05","realized_dates":[f"2015-02-{day:02d}" for day in range(1,21)],"u4_date":"2015-01-02","u8_date":"2015-01-02"}; self.assertTrue(timing_is_matched([good])); good["execution_date"]="2015-01-02"; self.assertFalse(timing_is_matched([good]))
 def test_actual_mintrl_and_precedence(self):
  series=[.01+i*.0001 for i in range(60)]; stats={name:actual_statistics(series,name) for name in METRICS}; self.assertTrue(all(value and len(value["lags_1_to_5"])==5 and value["falsify_mintrl"]>0 for value in stats.values())); self.assertEqual("scope_restricted",classify_e1(stats,constraints_evaluable=False,constraints_pass=True)); self.assertEqual("falsified_E1_only",classify_e1(stats,constraints_evaluable=True,constraints_pass=False)); self.assertEqual("validation_scope_restricted",classify_validation(stats,regimes_funded=False,constraints_evaluable=True,constraints_pass=True,integrity_pass=True))
 def test_forged_report_unknown_key_or_outcome_rejected(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/"report.json"; payload=json.loads(FIXTURE.read_text("ascii")); payload["outcome"]="falsified_E1_only"; path.write_text(json.dumps(payload),encoding="ascii"); self.assertEqual("blocked",validate_report(path)["status"]); payload=json.loads(FIXTURE.read_text("ascii")); payload["forged"]=True; path.write_text(json.dumps(payload),encoding="ascii"); self.assertEqual("blocked",validate_report(path)["status"])
 def test_source_tamper_and_future_bootstrap_deny(self):
  from scripts.run_l_4_breadth_b88_committed_bootstrap_v1 import preflight
  self.assertEqual("blocked",preflight()["status"])
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/"gate.json"; payload=json.loads((ROOT/"experiments/l_4_breadth_b88_phase_a_execution_contract_v1.json").read_text("ascii")); payload["science"]["v4_sha256"]="0"*64; path.write_text(json.dumps(payload),encoding="ascii"); self.assertEqual("blocked",validate_gate(path,require_manifest=False)["status"])
if __name__=="__main__": unittest.main()
