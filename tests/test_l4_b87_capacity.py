from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lib.l4_b87_capacity_contract_v1 import derive, load_structural_payload
from scripts.validate_l_4_breadth_b87_phase_a_capacity_gate_v1 import GATE, ROOT, validate
from scripts.validate_l_4_breadth_b87_capacity_report_v1 import REPORT, validate as validate_report


class B87CapacityTests(unittest.TestCase):
    def test_gate_and_all_four_metric_plans_pass_before_manifest_append(self):
        result = validate(require_manifest=False)
        self.assertEqual("pass", result["status"])
        capacity = json.loads(GATE.read_text("ascii"))["capacity"]
        self.assertEqual(465, capacity["weekly_paired_capacity"])
        self.assertEqual({49}, {plan["planning_mintrl_falsify"] for plan in capacity["metric_plans"].values()})
        self.assertTrue(all(plan["funded_by_capacity"] for plan in capacity["metric_plans"].values()))

    def test_closed_world_source_and_capacity_tampering_block(self):
        base = json.loads(GATE.read_text("ascii"))
        for mutate, blocker in (
            (lambda value: value.update(unexpected=True), "closed_world"),
            (lambda value: value["source_binding"]["science"].update(sha256="0" * 64), "source_binding"),
            (lambda value: value["capacity"].update(weekly_paired_capacity=466), "capacity"),
            (lambda value: value["authorizations"].update(execution=True), "seals"),
            (lambda value: value["validation_seal"].update(accessed=True), "seals"),
        ):
            value = copy.deepcopy(base); mutate(value)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "gate.json"; path.write_text(json.dumps(value), encoding="ascii")
                self.assertIn(blocker, validate(path, require_manifest=False)["blockers"])

    def test_adversarial_cutoff_and_u8_order_are_rejected(self):
        manifest_path = ROOT / "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json"
        payload_path = ROOT / "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json"
        manifest = json.loads(manifest_path.read_text("ascii")); payload = json.loads(payload_path.read_text("ascii"))
        with tempfile.TemporaryDirectory() as tmp:
            changed = copy.deepcopy(payload); changed["u8_members_in_order"] = list(reversed(changed["u8_members_in_order"]))
            path = Path(tmp) / "payload.json"; path.write_text(json.dumps(changed), encoding="ascii")
            with self.assertRaises(ValueError): load_structural_payload(manifest_path, path)
            changed = copy.deepcopy(payload); changed["session_dates_by_symbol"]["VTI"][-1] = "2016-01-04"
            path.write_text(json.dumps(changed), encoding="ascii")
            with self.assertRaises(ValueError): load_structural_payload(manifest_path, path)

    def test_underfunded_metric_branch_never_borrows_another_metric_capacity(self):
        science = json.loads((ROOT / "experiments/l_4_breadth_preregistration_v4.json").read_text("ascii"))
        science["mandatory_metrics"]["n_eff_delta"]["falsify"]["expected_mintrl"] = 466
        result = derive(science, ROOT / "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json", ROOT / "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json")
        self.assertEqual("underfunded_scope_restricted", result["capacity_outcome"])
        self.assertFalse(result["metric_plans"]["n_eff_delta"]["funded_by_capacity"])
        self.assertTrue(result["metric_plans"]["ex_ante_hhi_delta"]["funded_by_capacity"])

    def test_future_execution_preflight_always_denies(self):
        result = subprocess.run([sys.executable, "scripts/run_l_4_breadth_b87_scientific_execution_preflight_v1.py"], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(1, result.returncode)
        self.assertEqual("activation_and_execution_not_authorized_in_B8_7_phase_A", json.loads(result.stdout)["blocker"])

    def test_report_rejects_unknown_fields_and_forbidden_access(self):
        report = json.loads(REPORT.read_text("ascii")) if REPORT.exists() else None
        if report is None:
            self.skipTest("report is committed in the Phase-A result commit")
        self.assertEqual("pass", validate_report()["status"])
        for mutate, blocker in ((lambda value: value.update(extra=True), "closed_world"), (lambda value: value["access_counts"].update(execution_count=1), "access_counts")):
            value = copy.deepcopy(report); mutate(value)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "report.json"; path.write_text(json.dumps(value), encoding="ascii")
                self.assertIn(blocker, validate_report(path)["blockers"])


if __name__ == "__main__":
    unittest.main()
