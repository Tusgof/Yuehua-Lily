from __future__ import annotations
import importlib
import unittest

from lib.l4_b86r10_contract_v12 import SEAL, artifact


class B86R10V12ContractTests(unittest.TestCase):
    def report(self):
        row=artifact();row["attempted_read_count"]=1
        return {"schema_version":"lily_l4_b86r10_provisioning_report_v12","order_id":"B8.6R10","hypothesis_id":"L-4","mode":"synthetic_fixture","outcome":"provisioning_blocked","blocker":"dataset_missing","evidence_tier":"E0","edge_claim":"none","real_provisioning_consumed":False,"dataset_reference":"data/normalized/l1_yahoo_daily_v1.json","expected_dataset_sha256":"6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd","dataset_artifact":row,"contract_artifacts":{},"activation_provenance":None,"access_counters":{"return_value_decode_count":0,"validation_access_count":0},"validation_seal":SEAL,"producing_git_commit":"synthetic_fixture"}
    def test_gate_and_report_validators_import_and_execute(self):
        gate=importlib.import_module("scripts.validate_l_4_breadth_b86r10_provisioning_gate_v12")
        report=importlib.import_module("scripts.validate_l_4_breadth_b86r10_provisioning_report_v12")
        self.assertEqual("pass",gate.validate()["status"])
        self.assertEqual("pass",report.validate(self.report())["status"])
    def test_empty_or_coherent_success_without_outputs_blocks(self):
        report=importlib.import_module("scripts.validate_l_4_breadth_b86r10_provisioning_report_v12")
        self.assertEqual("blocked",report.validate({})["status"])
        forged=self.report();forged.update({"mode":"real_one_shot","outcome":"structural_provisioned","real_provisioning_consumed":True,"producing_git_commit":"a"*40,"activation_provenance":{},"manifest":{},"payload":{},"output_artifacts":{},"structural_summary_sha256":"a"*64})
        self.assertEqual("blocked",report.validate(forged)["status"])

if __name__=="__main__":unittest.main()
