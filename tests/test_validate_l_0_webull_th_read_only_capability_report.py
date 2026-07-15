from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_0_webull_th_read_only_capability_report import DEFAULT_PATH, MARKDOWN_PATH, validate_report


class L0WebullThailandReadOnlyCapabilityReportTests(unittest.TestCase):
    def test_current_report_passes(self) -> None:
        result = validate_report()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_order_call_is_blocked(self) -> None:
        report = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        report["request_attestation"]["order_endpoint_calls"] = 1
        result = _validate_temporary(report)
        self.assertIn("forbidden_action_nonzero:order_endpoint_calls", result["blockers"])

    def test_private_value_persistence_is_blocked(self) -> None:
        report = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        report["account_capability"]["private_values_persisted"] = True
        result = _validate_temporary(report)
        self.assertIn("private_values_must_not_be_persisted", result["blockers"])

    def test_fractional_failure_is_blocked(self) -> None:
        report = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        report["instrument_capability"]["symbols"][0]["fractionable"] = False
        result = _validate_temporary(report)
        self.assertIn("candidate_not_tradable_fractionable:VTI", result["blockers"])

    def test_validation_access_is_blocked(self) -> None:
        report = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        report["validation_return_seal"]["returns_opened"] = True
        result = _validate_temporary(report)
        self.assertIn("validation_seal_false_field_mismatch:returns_opened", result["blockers"])


def _validate_temporary(report: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report_path = root / "report.json"
        markdown_path = root / "report.md"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        markdown_path.write_text(MARKDOWN_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        return validate_report(report_path, markdown_path)


if __name__ == "__main__":
    unittest.main()
