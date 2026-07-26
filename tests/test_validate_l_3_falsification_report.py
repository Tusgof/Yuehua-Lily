from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json
from scripts.validate_l_3_falsification_report import AUTH, LEDGER, REPORT, validate_report


class L3FalsificationReportTests(unittest.TestCase):
    def test_produced_invalidated_report_passes(self) -> None:
        self.assertEqual("pass", validate_report()["status"])

    def test_rejects_forged_provenance_and_closed_world_drift(self) -> None:
        report = load_json(REPORT)
        cases = [
            (lambda value: value.update(extra_field=True), "unknown_field:extra_field"),
            (lambda value: value["validation_seal"].update(validation_access_authorized=True), "validation_seal_mismatch"),
            (lambda value: value["observation_counts"].update(asset_multiplier=8), "pseudo_replication"),
            (lambda value: value.update(authorization_sha256="0" * 64), "authorization_provenance_mismatch"),
            (lambda value: value.update(post_parse_hard_stop=None), "scope_restriction_reason_missing"),
        ]
        for mutate, blocker in cases:
            with self.subTest(blocker=blocker), tempfile.TemporaryDirectory() as directory:
                candidate = copy.deepcopy(report)
                mutate(candidate)
                path = Path(directory) / "report.json"
                path.write_text(json.dumps(candidate), encoding="utf-8")
                self.assertIn(blocker, validate_report(path)["blockers"])

    def test_rejects_fake_second_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"
            rows = LEDGER.read_text(encoding="utf-8")
            ledger.write_text(rows + rows, encoding="utf-8")
            self.assertIn("exactly_one_run_ledger_mismatch", validate_report(ledger_path=ledger)["blockers"])

    def test_rejects_forged_authorization_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authorization = Path(directory) / "authorization.json"
            authorization.write_text(AUTH.read_text(encoding="utf-8") + " ", encoding="utf-8")
            self.assertIn(
                "authorization_provenance_mismatch",
                validate_report(authorization_path=authorization)["blockers"],
            )


if __name__ == "__main__":
    unittest.main()
