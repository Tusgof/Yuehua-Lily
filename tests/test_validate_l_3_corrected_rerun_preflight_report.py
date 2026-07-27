from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_3_corrected_rerun_preflight_report import REPORT, validate


class CorrectedRerunPreflightReportTests(unittest.TestCase):
    def _report(self) -> dict:
        return json.loads(REPORT.read_text(encoding="utf-8"))

    def test_produced_preflight_report_passes(self) -> None:
        self.assertEqual("pass", validate()["status"])

    def test_unknown_field_and_claim_limit_drift_fail_closed(self) -> None:
        for mutate, blocker in (
            (lambda report: report.update(forged=True), "unknown_field:forged"),
            (lambda report: report.update(claim_limits=["E1 only"]), "claim_limits_mismatch"),
        ):
            with self.subTest(blocker=blocker), tempfile.TemporaryDirectory() as directory:
                report = copy.deepcopy(self._report())
                mutate(report)
                path = Path(directory) / "report.json"
                path.write_text(json.dumps(report), encoding="utf-8")
                self.assertIn(blocker, validate(path)["blockers"])


if __name__ == "__main__":
    unittest.main()
