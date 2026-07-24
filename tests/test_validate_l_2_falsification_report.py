from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json, write_json
from scripts.validate_l_2_falsification_report import validate_report

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "l2_falsification" / "report_not_run.json"


class L2FalsificationReportTests(unittest.TestCase):
    def test_not_run_fixture_passes(self) -> None:
        result = validate_report(FIXTURE)
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_validation_open_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(FIXTURE))
        payload["validation_return_seal"]["returns_opened"] = True
        self.assertIn("field_mismatch:validation_return_seal", _validate_temp(payload)["blockers"])

    def test_not_run_market_return_is_rejected(self) -> None:
        payload = copy.deepcopy(load_json(FIXTURE))
        payload["market_returns_read"] = True
        self.assertIn("not_run_must_not_read_market_returns", _validate_temp(payload)["blockers"])


def _validate_temp(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.json"
        write_json(path, payload)
        return validate_report(path)


if __name__ == "__main__":
    unittest.main()
