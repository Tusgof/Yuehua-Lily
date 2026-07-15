from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_1_validation_capacity import DEFAULT_JSON, DEFAULT_MARKDOWN, validate_report


class ValidationCapacityReportTests(unittest.TestCase):
    def test_current_report_passes(self) -> None:
        result = validate_report()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_tampered_capacity_is_rejected(self) -> None:
        payload = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
        payload["locked_actual_recalculation"]["joint_independent_bet_equivalents"] = 1
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            report.write_text(json.dumps(payload), encoding="utf-8")
            result = validate_report(report, DEFAULT_MARKDOWN)
        self.assertIn("joint_capacity_mismatch", result["blockers"])


if __name__ == "__main__":
    unittest.main()
