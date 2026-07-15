from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_1_alpha_vantage_corporate_actions_report import (
    DEFAULT_COST_LEDGER,
    DEFAULT_JSON,
    DEFAULT_MARKDOWN,
    DEFAULT_REGISTRY,
    validate_report,
)


class L1AlphaVantageCorporateActionsReportTests(unittest.TestCase):
    def test_current_report_passes(self) -> None:
        result = validate_report()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_validation_return_opening_is_blocked(self) -> None:
        report = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
        report["guardrails"]["validation_returns_opened"] = True
        result = _validate_temporary(report)
        self.assertIn("guardrail_false_field_mismatch", result["blockers"])

    def test_point_in_time_overstatement_is_blocked(self) -> None:
        report = json.loads(DEFAULT_JSON.read_text(encoding="utf-8"))
        report["decision"] = "point_in_time_verified"
        result = _validate_temporary(report)
        self.assertIn("field_mismatch:decision", result["blockers"])


def _validate_temporary(report: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        return validate_report(path, DEFAULT_MARKDOWN, DEFAULT_REGISTRY, DEFAULT_COST_LEDGER)


if __name__ == "__main__":
    unittest.main()
