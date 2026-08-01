from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from lib.l4_b88r4_scientific_engine_v5 import CURRENT_EXPENSE_RATIOS, METRICS, U4, U8, _costs, classify_outcome, derive, drift_weights, l1_ewma_cross_check, psd_clip, threshold_changes
from lib.l4_b88r_scientific_engine_v2 import actual_statistics

ROOT = Path(__file__).resolve().parents[1]


def container(days: int = 430) -> dict:
    sessions=[]; cursor=date(2013,1,2)
    while len(sessions)<days:
        if cursor.weekday()<5: sessions.append(cursor.isoformat())
        cursor += timedelta(days=1)
    returns={symbol:[((index*(asset+3)+index*index*(asset+1))%17-8)/1000 for index in range(days)] for asset,symbol in enumerate(U8)}
    return {"schema_version":"lily_l4_normalized_container_v1","cutoff_inclusive":"2015-12-31","universe":list(U8),"sessions":sessions,"returns":returns,"cash_returns":[.00001]*days}


class B88R4V5(unittest.TestCase):
    def test_l1_ewma_and_u4_cost_map(self):
        rows=[[.001*(asset+1) if (day+asset)%3 else -.0005*(asset+1) for asset in range(8)] for day in range(60)]
        self.assertTrue(l1_ewma_cross_check(rows))
        costs=_costs([.1,.2,.3,.4],[0,0,0,0],U4,0)
        self.assertAlmostEqual(costs["expense_ratio"],sum(weight*CURRENT_EXPENSE_RATIOS[symbol]/252 for weight,symbol in zip([.1,.2,.3,.4],U4)))

    def test_cash_inclusive_drift_and_rejected_helper_goldens(self):
        # The cash sleeve earns its own return in the denominator; omitting it
        # changes the post-close weights even when asset prices are unchanged.
        drift=drift_weights([.2,.3],[.10,-.05],.02)
        self.assertAlmostEqual(drift[0],.22/1.015)
        self.assertAlmostEqual(drift[1],.285/1.015)
        self.assertIsNone(drift_weights([1.0],[-2.0],0.0))
        # These exact values preserve the remediations for the rejected helper
        # line: inclusive 2% trade threshold and ticker-specific U4 expenses.
        self.assertAlmostEqual(threshold_changes([.102],[.1])[0],.002)
        self.assertNotAlmostEqual(_costs([.1,.2,.3,.4],[0,0,0,0],U4,0)["expense_ratio"],sum(weight*CURRENT_EXPENSE_RATIOS[symbol]/252 for weight,symbol in zip([.1,.2,.3,.4],U8[:4])))

    def test_threshold_is_inclusive_and_container_has_no_reporter_state(self):
        self.assertAlmostEqual(threshold_changes([.102],[.1])[0],.002)
        self.assertEqual(threshold_changes([.101999999],[.1]),[0.0])
        value=container(); value["weights"]=[]
        self.assertIsNone(derive(value,config={"u8_sessions":value["sessions"]}))

    def test_structural_calendar_and_post_cutoff_fail_before_derivation(self):
        value=container(); self.assertIsNone(derive(value,config={"u8_sessions":value["sessions"][:-1]}))
        value=container(); value["sessions"][-1]="2016-01-04"
        self.assertIsNone(derive(value,config={"u8_sessions":value["sessions"]}))

    def test_timing_is_next_session_and_realized_is_strictly_after_execution(self):
        value=container(); result=derive(value,config={"u8_sessions":value["sessions"]})
        self.assertIsNotNone(result)
        for row in result["weekly_observations"]:
            timing=row["timing"]
            self.assertLess(timing["decision_date"],timing["execution_date"])
            self.assertEqual(len(timing["realized_dates"]),20)
            self.assertGreater(timing["realized_dates"][0],timing["execution_date"])

    def test_psd_clip_and_stateful_output_reject_reporter_owned_fields(self):
        clipped, mass=psd_clip([[1.0,2.0],[2.0,1.0]])
        self.assertGreater(mass, 0.0)
        self.assertGreaterEqual(clipped[0][0]+clipped[1][1]-2*abs(clipped[0][1]), -1e-12)
        value=container(); result=derive(value,config={"u8_sessions":value["sessions"]})
        self.assertTrue(result["weekly_observations"])
        row=result["weekly_observations"][0]
        self.assertEqual(set(row["state"]), {"u4","u8"})
        self.assertEqual(set(row["state"]["u4"]), {"weights","covariance","hhi"})
        self.assertNotIn("weights_u4", row)
        self.assertEqual(len(row["changes_u4"]),4)
        self.assertEqual(len(row["changes_u8"]),8)

    def test_forged_future_report_is_blocked_before_any_claim(self):
        spec=importlib.util.spec_from_file_location("report_validator",ROOT/"scripts/validate_l_4_breadth_b88r4_scientific_report_v5.py")
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        value=container(); report={"schema_version":"lily_l4_b88r4_scientific_report_v5","order_id":"B8.8R3","hypothesis_id":"L-4","mode":"future_falsification_only","evidence_tier":"E1","edge_claim":"none","provenance":{},"validation_seal":{"status":"sealed_not_accessed","accessed":False},"access_counts":{},"container_sha256":"0"*64,"derived":{},"outcome":"falsified_E1_only"}
        self.assertEqual(module.validate_value(report,value,b"forged")["status"],"blocked")

    def test_direct_runtime_refuses_without_preflight_or_marker(self):
        spec=importlib.util.spec_from_file_location("runtime",ROOT/"scripts/run_l_4_breadth_b88r4_scientific_execution_v5.py")
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            result=module.run_one_shot({},root=Path(temporary))
            self.assertEqual(result["outcome"],"refused_preflight")
            self.assertFalse((Path(temporary)/"reports").exists())

    def test_stateful_constraints_and_next_session_execution_are_derived(self):
        value=container(); result=derive(value,config={"u8_sessions":value["sessions"]})
        for row in result["weekly_observations"]:
            for branch in ("u4","u8"):
                weights=row["state"][branch]["weights"]
                self.assertLessEqual(max(abs(item) for item in weights),.25+1e-12)
                self.assertLessEqual(sum(abs(item) for item in weights),.90+1e-12)
            execution=value["sessions"].index(row["timing"]["execution_date"])
            self.assertEqual(row["timing"]["realized_dates"],value["sessions"][execution+1:execution+21])

    def test_actual_mintrl_regimes_and_constraint_precedence(self):
        value=container(); result=derive(value,config={"u8_sessions":value["sessions"]})
        self.assertEqual(set(result["statistics"]),set(METRICS))
        for metric in METRICS:
            expected=actual_statistics([row[metric] for row in result["weekly_observations"]],metric)
            self.assertEqual(result["statistics"][metric],expected)
            self.assertEqual(len(expected["values"]),len(result["weekly_observations"]))
        self.assertEqual(classify_outcome(result["statistics"],constraints_pass=False),"scope_restricted")
        self.assertIn("crisis:GFC",result["regimes"])
        self.assertEqual(result["regimes"]["crisis:COVID_sealed"]["weekly_observations"],0)
        self.assertEqual(result["outcome"],"scope_restricted")

    def test_phase_a_bootstrap_refuses_without_activation(self):
        spec=importlib.util.spec_from_file_location("bootstrap",ROOT/"scripts/run_l_4_breadth_b88r4_committed_bootstrap_v5.py")
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        checked=module.preflight(ROOT, __import__("subprocess").check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip())
        self.assertIn(checked["outcome"], {"canonical_activation_absent", "dirty_checkout", "refused_activation", "refused_execution_provenance"})
        self.assertFalse((ROOT/"reports/experiments/l_4_breadth_b88r4_one_shot_marker_v5.json").exists())


if __name__=="__main__": unittest.main()
