"""Hermetic audit of B8.4 v1's immutable, CI-defective history."""
from __future__ import annotations
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1 = ("experiments/l_4_breadth_b84_activation_contract_v1.json", "scripts/validate_l_4_breadth_b84_preflight_report_v1.py", "tests/fixtures/l4_b84/synthetic_preflight_report.json")


class B84HistoricalTests(unittest.TestCase):
    def test_v1_bytes_match_published_ci_defective_history(self) -> None:
        for relative in V1:
            published = subprocess.run(["git", "show", f"8fea0bf:{relative}"], cwd=ROOT, text=True, capture_output=True, check=True).stdout
            self.assertEqual(published.encode(), (ROOT / relative).read_bytes())

    def test_v1_ci_failure_is_recorded_in_v2_gate(self) -> None:
        text = (ROOT / "experiments/l_4_breadth_b84r_activation_contract_v2.json").read_text(encoding="utf-8")
        self.assertIn("30363935144", text)
        self.assertIn("jsonschema", text)


if __name__ == "__main__":
    unittest.main()
