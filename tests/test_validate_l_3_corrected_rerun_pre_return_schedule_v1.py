from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from lib.io import load_json, write_json
from scripts.validate_l_3_corrected_rerun_pre_return_schedule_v1 import (
    END,
    GATE,
    MANIFEST,
    canonical_schedule_sha256,
    validate_gate,
    validate_pre_return_schedule_attestation,
)


class CorrectedRerunScheduleGateTests(unittest.TestCase):
    def test_gate_passes_without_market_or_date_column_access(self) -> None:
        result = validate_gate()
        self.assertEqual("pass", result["status"])
        self.assertEqual(0, result["market_data_or_date_column_read_count"])
        self.assertEqual(0, result["market_returns_read_count"])
        self.assertEqual(0, result["new_real_return_decision_run_count"])
        self.assertEqual("sealed_not_accessed", result["validation_status"])

    def test_rejects_source_semantic_authorization_and_namespace_drift(self) -> None:
        payload = load_json(GATE)
        cases = [
            (lambda value: value["source_binding"]["b7_4_invalidation_event"].update(sha256="0" * 64), "b7_4_invalidation_event_binding_mismatch"),
            (lambda value: value["source_binding"]["b7_3_final_invalidated_report"].update(unknown=True), "unknown_source_binding_b7_3_final_invalidated_report_field:unknown"),
            (lambda value: value["source_binding"].update(whole_manifest_sha256="0" * 64), "unknown_source_binding_field:whole_manifest_sha256"),
            (lambda value: value["preserved_research_semantics"]["research_universe_tickers_in_order"].reverse(), "research_semantics_mismatch:research_universe_tickers_in_order"),
            (lambda value: value["preserved_research_semantics"].update(candidate_raw_score="q[i,t]"), "research_semantics_mismatch:candidate_raw_score"),
            (lambda value: value["corrected_execution_window_control"].update(falsification_start="2007-02-04"), "execution_window_control_mismatch:falsification_start"),
            (lambda value: value["authorizations"].update(return_parsing_authorized=True), "authorization_drift"),
            (lambda value: value["future_rerun_namespace"].update(report_path="reports/experiments/l_3_falsification_report.json"), "future_namespace_mismatch:report_path"),
            (lambda value: value["hard_stops"].pop(), "hard_stops_incomplete_or_open"),
            (lambda value: value.update(unapproved=True), "unknown_top_level_field:unapproved"),
        ]
        for mutate, blocker in cases:
            with self.subTest(blocker=blocker):
                candidate = copy.deepcopy(payload)
                mutate(candidate)
                self.assertIn(blocker, self._validate_temporary_gate(candidate)["blockers"])

    def test_rejects_forged_manifest_identity(self) -> None:
        rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line]
        row = next(item for item in rows if item["gate_id"] == "l_3_inverse_volatility_sizing_v2")
        row["artifact_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "locked_gates.jsonl"
            manifest.write_text("\n".join(json.dumps(item, sort_keys=True) for item in rows) + "\n", encoding="utf-8")
            result = validate_gate(manifest_path=manifest)
        self.assertIn("source_manifest_identity_mismatch:active_l3_v2", result["blockers"])

    def test_positive_synthetic_date_only_schedule_passes_within_ceiling(self) -> None:
        sessions = self._sessions(date(2007, 1, 1), date(2015, 12, 31))
        decisions = [value for value in sessions if date.fromisoformat(value).weekday() == 4 and value >= "2007-02-05"]
        decisions = [value for value in decisions if sessions.index(value) + 20 < len(sessions)]
        attestation, identity = self._attestation(sessions, decisions)
        result = validate_pre_return_schedule_attestation(attestation, sessions, expected_container_identity=identity)
        self.assertEqual("pass", result["status"])
        self.assertLessEqual(len(decisions), 465)
        self.assertLessEqual(attestation["t_plus_20_max_date"], END)

    def test_synthetic_schedule_rejects_pre_start_incomplete_over_capacity_duplicate_mixed_and_hash_drift(self) -> None:
        sessions = self._sessions(date(2007, 1, 1), date(2016, 1, 8))
        decisions = [value for value in sessions if date.fromisoformat(value).weekday() == 4 and "2007-02-05" <= value <= "2015-11-30"]
        base, identity = self._attestation(sessions, decisions)
        cases = []
        pre_start = copy.deepcopy(base)
        pre_start["selected_decision_dates"][0] = "2007-02-02"
        cases.append((pre_start, "pre_start_weekly_decision"))
        incomplete = copy.deepcopy(base)
        incomplete["selected_decision_dates"][-1] = "2015-12-25"
        incomplete["execution_dates"][-1] = "2015-12-28"
        incomplete["realized_confirmation_end_dates"][-1] = "2016-01-22"
        incomplete["last_decision_date"] = "2015-12-25"
        incomplete["execution_date_boundary"] = "2015-12-28"
        incomplete["t_plus_20_max_date"] = "2016-01-22"
        incomplete["schedule_sha256"] = canonical_schedule_sha256(incomplete["selected_decision_dates"])
        cases.append((incomplete, "t_plus_20_crosses_falsification_end"))
        over_capacity = copy.deepcopy(base)
        over_capacity["selected_decision_dates"] = sessions[30:496]
        over_capacity["execution_dates"] = sessions[31:497]
        over_capacity["realized_confirmation_end_dates"] = sessions[50:516]
        over_capacity["selected_weekly_paired_observations"] = 466
        over_capacity["first_decision_date"] = over_capacity["selected_decision_dates"][0]
        over_capacity["last_decision_date"] = over_capacity["selected_decision_dates"][-1]
        over_capacity["execution_date_boundary"] = over_capacity["execution_dates"][-1]
        over_capacity["t_plus_20_max_date"] = over_capacity["realized_confirmation_end_dates"][-1]
        over_capacity["schedule_sha256"] = canonical_schedule_sha256(over_capacity["selected_decision_dates"])
        cases.append((over_capacity, "weekly_paired_observation_ceiling_exceeded"))
        duplicate_week = copy.deepcopy(base)
        duplicate_week["selected_decision_dates"][1] = duplicate_week["selected_decision_dates"][0]
        duplicate_week["schedule_sha256"] = canonical_schedule_sha256(duplicate_week["selected_decision_dates"])
        cases.append((duplicate_week, "duplicate_weekly_decision"))
        mixed = copy.deepcopy(base)
        cases.append((mixed, "mixed_validation_date_hard_stop", sessions + ["2016-01-04"]))
        non_monotonic_sessions = copy.deepcopy(base)
        cases.append((non_monotonic_sessions, "date_only_sessions_not_strictly_monotonic", sessions[:-2] + [sessions[-1], sessions[-2]]))
        forged_hash = copy.deepcopy(base)
        forged_hash["schedule_sha256"] = "0" * 64
        cases.append((forged_hash, "attestation_schedule_sha256_mismatch"))
        missing_field = copy.deepcopy(base)
        missing_field.pop("t_plus_20_max_date")
        cases.append((missing_field, "missing_attestation_field:t_plus_20_max_date"))
        for item in cases:
            candidate, blocker, *date_override = item
            with self.subTest(blocker=blocker):
                result = validate_pre_return_schedule_attestation(candidate, date_override[0] if date_override else sessions, expected_container_identity=identity)
                self.assertIn(blocker, result["blockers"])

    def test_rejects_missing_or_extra_assets(self) -> None:
        sessions = self._sessions(date(2007, 1, 1), date(2007, 4, 30))
        decisions = [value for value in sessions if date.fromisoformat(value).weekday() == 4 and value >= "2007-02-05"]
        decisions = [value for value in decisions if sessions.index(value) + 20 < len(sessions)]
        attestation, identity = self._attestation(sessions, decisions)
        attestation["container_identity"]["assets"] = ["VTI"]
        result = validate_pre_return_schedule_attestation(attestation, sessions, expected_container_identity=identity)
        self.assertIn("attestation_container_identity_mismatch", result["blockers"])

    @staticmethod
    def _sessions(start: date, end: date) -> list[str]:
        values = []
        current = start
        while current <= end:
            if current.weekday() < 5:
                values.append(current.isoformat())
            current += timedelta(days=1)
        return values

    @staticmethod
    def _attestation(sessions: list[str], decisions: list[str]) -> tuple[dict[str, object], dict[str, object]]:
        identity: dict[str, object] = {
            "path": "synthetic/date_only_schedule_fixture.json", "sha256": "1" * 64,
            "assets": ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"],
        }
        executions = [sessions[sessions.index(value) + 1] for value in decisions]
        ends = [sessions[sessions.index(value) + 20] for value in decisions]
        return {
            "schema_version": "lily_l3_pre_return_schedule_attestation_v1", "container_identity": copy.deepcopy(identity),
            "date_column": "session_date", "first_decision_date": decisions[0], "last_decision_date": decisions[-1],
            "execution_date_boundary": max(executions), "t_plus_20_max_date": max(ends),
            "selected_weekly_paired_observations": len(decisions), "exclusions_by_reason": {"pre_start_warm_up": 5},
            "selected_decision_dates": decisions, "execution_dates": executions, "realized_confirmation_end_dates": ends,
            "schedule_sha256": canonical_schedule_sha256(decisions), "validation_seal_status": "sealed_not_accessed",
            "return_fields_accessed": False,
        }, identity

    @staticmethod
    def _validate_temporary_gate(payload: dict[str, object]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "b7_5_gate.json"
            write_json(path, payload)
            return validate_gate(path)


if __name__ == "__main__":
    unittest.main()
