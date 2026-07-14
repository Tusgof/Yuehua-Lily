from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json, write_json
from scripts.run_l_0_sizing_feasibility import DEFAULT_JSON, DEFAULT_MARKDOWN
from scripts.validate_l_0_sizing_feasibility_report import validate_report


class L0SizingReportValidatorTests(unittest.TestCase):
    def test_committed_report_passes(self) -> None:
        result = validate_report()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_minimum_capital_tamper_is_rejected(self) -> None:
        report = copy.deepcopy(load_json(DEFAULT_JSON))
        report["futures"]["micro"][0]["minimum_capital_usd"] = 2000
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "report.json"
            markdown_path = Path(tmp) / "report.md"
            write_json(report_path, report)
            markdown_path.write_text(DEFAULT_MARKDOWN.read_text(encoding="utf-8"), encoding="utf-8")
            result = validate_report(report_path, markdown_path)
        self.assertIn("machine_report_does_not_match_locked_calculation", result["blockers"])
        self.assertIn("unexpected_micro_minimum_capital", result["blockers"])

    def test_markdown_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            markdown_path = Path(tmp) / "report.md"
            markdown_path.write_text("stale summary\n", encoding="utf-8")
            result = validate_report(DEFAULT_JSON, markdown_path)
        self.assertIn("markdown_does_not_match_machine_report", result["blockers"])


if __name__ == "__main__":
    unittest.main()
