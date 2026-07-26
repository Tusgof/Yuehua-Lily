from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import run_l_3_falsification as runner


class L3OneRunGuardTests(unittest.TestCase):
    def test_locked_weekly_window_excludes_pre_start_and_never_exceeds_ceiling(self) -> None:
        start = date(2006, 1, 1)
        end = date(2016, 1, 10)
        dates = []
        current = start
        while current <= end:
            if current.weekday() < 5:
                dates.append(current.isoformat())
            current += timedelta(days=1)
        chosen = runner._locked_weekly_decision_indices(dates)
        chosen_dates = [dates[index] for index in chosen]
        self.assertTrue(all("2007-02-05" <= value <= "2015-12-31" for value in chosen_dates))
        self.assertLessEqual(len(chosen_dates), 465)

    def test_mixed_date_container_hard_stops_before_return_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            container = Path(directory) / "mixed.json"
            container.write_text('{"metadata_date":"2016-01-04","returns":"not parsed"}', encoding="utf-8")
            with self.assertRaisesRegex(runner.HardStop, "mixed_or_validation_container_hard_stop"):
                runner._preflight(container)

    def test_second_real_run_is_rejected_without_container_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"
            ledger.write_text('{"event":"real_return_decision_run"}\n', encoding="utf-8")
            with patch.object(runner, "LEDGER", ledger), patch.object(
                runner, "validate_authorization", return_value={"status": "pass"}
            ), patch.object(runner, "_preflight") as preflight:
                with self.assertRaisesRegex(runner.HardStop, "second_real_return_decision_run_forbidden"):
                    runner.run()
            preflight.assert_not_called()


if __name__ == "__main__":
    unittest.main()
