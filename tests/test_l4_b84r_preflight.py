"""Hermetic audit of immutable B8.4R v2 EOL-hash failure history."""
from __future__ import annotations
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATHS = ("experiments/l_4_breadth_b84r_activation_contract_v2.json", "scripts/run_l_4_breadth_b84r_preflight_v2.py", "schemas/l_4_breadth_b84r_preflight_report_v2.schema.json")


class B84RHistoricalTests(unittest.TestCase):
    def test_v2_bytes_match_published_failed_history(self) -> None:
        for relative in PATHS:
            expected = subprocess.run(["git", "show", f"49d07ce:{relative}"], cwd=ROOT, capture_output=True, check=True).stdout
            self.assertEqual(expected, (ROOT / relative).read_bytes())

    def test_v3_records_eol_failure(self) -> None:
        text = (ROOT / "experiments/l_4_breadth_b84r2_activation_contract_v3.json").read_text(encoding="utf-8")
        self.assertIn("30365332742", text)
        self.assertIn("CRLF", text)
