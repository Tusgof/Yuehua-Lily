import json
import unittest
from pathlib import Path

from scripts.validate_l_3_b714_preflight_report_v1 import validate

ROOT = Path(__file__).resolve().parents[1]

def report(): return json.loads((ROOT / "tests/fixtures/l3_b714_preflight_v1/report.json").read_text())

class Tests(unittest.TestCase):
    def test_fixture_passes(self): self.assertEqual("pass", validate(report())["status"])
    def test_adversarial_fail_closed(self):
        mutations = []
        x = report(); x["synthetic_date_metadata"]["symbols"]["VTI"].append("2016-01-01"); mutations.append(x)
        x = report(); x["synthetic_date_metadata"]["schema_version"] = "wrong"; mutations.append(x)
        x = report(); del x["synthetic_date_metadata"]["symbols"]["VTI"]; mutations.append(x)
        x = report(); x["evidence_tier"] = "E1"; mutations.append(x)
        x = report(); x["decision"] = "falsified"; mutations.append(x)
        x = report(); del x["validation_seal"]; mutations.append(x)
        for value in mutations: self.assertEqual("blocked", validate(value)["status"])

if __name__ == "__main__": unittest.main()
