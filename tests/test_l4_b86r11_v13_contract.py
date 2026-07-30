from __future__ import annotations

import copy
import importlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/l4_b86r11/synthetic_blocked_report_v13.json"


class B86R11V13ContractTests(unittest.TestCase):
    def report(self):
        return json.loads(FIXTURE.read_text("ascii"))

    def validator(self):
        return importlib.import_module("scripts.validate_l_4_breadth_b86r11_provisioning_report_v13")

    def test_gate_and_report_validators_import_and_invoke(self):
        gate = importlib.import_module("scripts.validate_l_4_breadth_b86r11_provisioning_gate_v13")
        self.assertEqual("pass", gate.validate()["status"])
        self.assertEqual("pass", self.validator().validate(self.report())["status"])
        self.assertEqual(0, subprocess.run([sys.executable, "scripts/validate_l_4_breadth_b86r11_provisioning_gate_v13.py"], cwd=ROOT).returncode)
        self.assertEqual(0, subprocess.run([sys.executable, "scripts/validate_l_4_breadth_b86r11_provisioning_report_v13.py", str(FIXTURE)], cwd=ROOT).returncode)

    def test_unknown_or_missing_fields_at_all_important_objects_block(self):
        mutations = (
            lambda value: value.__setitem__("unknown", True),
            lambda value: value.pop("edge_claim"),
            lambda value: value["dataset_artifact"].__setitem__("unknown", True),
            lambda value: value["dataset_artifact"].pop("scan_count"),
            lambda value: value["contract_artifacts"].__setitem__("unknown", {}),
            lambda value: value["access_counters"].__setitem__("unknown", 0),
            lambda value: value["validation_seal"].__setitem__("unknown", False),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                value = self.report(); mutate(value)
                self.assertEqual("blocked", self.validator().validate(value)["status"])

    def test_forged_success_and_activation_provenance_block(self):
        forged = self.report(); forged.update({"mode":"real_one_shot", "outcome":"structural_provisioned", "real_provisioning_consumed":True, "producing_git_commit":"a" * 40, "activation_provenance":{}, "manifest":{}, "payload":{}, "output_artifacts":{}, "structural_summary_sha256":"a" * 64}); forged.pop("blocker")
        self.assertEqual("blocked", self.validator().validate(forged)["status"])
        forged = self.report(); forged.update({"mode":"real_one_shot", "real_provisioning_consumed":True, "producing_git_commit":"a" * 40, "activation_provenance":{"unknown":True}, "contract_artifacts":{"unknown":{}}})
        self.assertEqual("blocked", self.validator().validate(forged)["status"])

    def test_direct_worktree_runtime_refuses_and_dirty_bootstrap_stops_pre_import(self):
        runtime = ROOT / "scripts/run_l_4_breadth_b86r11_provisioning_v13.py"
        self.assertEqual(2, subprocess.run([sys.executable, str(runtime)], cwd=ROOT).returncode)
        bootstrap = importlib.import_module("scripts.run_l_4_breadth_b86r11_committed_bootstrap_v13")
        self.assertEqual({"outcome":"refused_execution_provenance", "dataset_read_count":0}, bootstrap.run(ROOT, "a" * 40))


if __name__ == "__main__":
    unittest.main()
