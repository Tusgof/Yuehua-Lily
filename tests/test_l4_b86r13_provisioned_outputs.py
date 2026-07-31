from __future__ import annotations

import json
import unittest
from pathlib import Path

from lib.l4_b86r13_contract_v15 import EXPECTED_DATASET_SHA256, SEAL, U8, outputs_ok
from scripts.validate_l_4_breadth_b86r13_provisioning_report_v15 import validate


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/experiments/l_4_breadth_b86r13_provisioning_report_v15.json"


class B86R13ProvisionedOutputsTests(unittest.TestCase):
    def test_structural_outputs_are_closed_world_and_sealed(self) -> None:
        report = json.loads(REPORT.read_text("ascii"))
        self.assertEqual("pass", validate(report)["status"])
        self.assertEqual("structural_provisioned", report["outcome"])
        self.assertEqual({"return_value_decode_count": 0, "validation_access_count": 0}, report["access_counters"])
        self.assertEqual(SEAL, report["validation_seal"])
        self.assertTrue(outputs_ok(report["manifest"], report["payload"]))
        self.assertEqual(EXPECTED_DATASET_SHA256, report["manifest"]["dataset_sha256"])
        self.assertEqual(list(U8), report["manifest"]["u8_members_in_order"])
        self.assertEqual("2015-12-31", report["manifest"]["max_session_date"])


if __name__ == "__main__":
    unittest.main()
