from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_1_data_quality_remediation import DEFAULT_PATH, validate_contract


class L1DataQualityRemediationContractTests(unittest.TestCase):
    def test_current_contract_passes(self) -> None:
        result = validate_contract()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_opening_validation_is_blocked(self) -> None:
        payload = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
        payload["data_boundary"]["maximum_market_or_cash_date_inclusive"] = "2026-06-30"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "contract.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = validate_contract(path)
        self.assertIn("maximum_data_date_mismatch", result["blockers"])


if __name__ == "__main__":
    unittest.main()
