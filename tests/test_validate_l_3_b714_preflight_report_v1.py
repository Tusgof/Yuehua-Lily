import json
import unittest
from datetime import date, timedelta
from pathlib import Path

from scripts.validate_l_3_b714_preflight_report_v1 import validate
from lib import l3_b714_preflight_v1

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
        x = report(); x["provenance"]["active_gate_sha256"] = "0" * 64; mutations.append(x)
        x = report(); x["provenance"]["fixture_metadata_sha256"] = "0" * 64; mutations.append(x)
        x = report(); x["synthetic_date_metadata"]["symbols"]["VTI"].append("2007-03-10"); mutations.append(x)
        for value in mutations: self.assertEqual("blocked", validate(value)["status"])

    def test_weekly_ceiling_boundaries(self):
        def weekdays(count):
            values, current = [], date(2007, 2, 5)
            while len(values) < count:
                if current.weekday() < 5: values.append(current.isoformat())
                current += timedelta(days=1)
            return values
        old_end = l3_b714_preflight_v1.END
        l3_b714_preflight_v1.END = date(2020, 1, 1)
        try:
            for weeks, expected in ((469, "pass"), (470, "blocked")):
                x = report(); values = weekdays(weeks * 5)
                for symbol in x["synthetic_date_metadata"]["symbols"]: x["synthetic_date_metadata"]["symbols"][symbol] = values
                x["provenance"]["fixture_metadata_sha256"] = __import__("scripts.validate_l_3_b714_preflight_report_v1", fromlist=["canonical_sha256"]).canonical_sha256(x["synthetic_date_metadata"])
                self.assertEqual(expected, validate(x)["status"])
        finally:
            l3_b714_preflight_v1.END = old_end

if __name__ == "__main__": unittest.main()
