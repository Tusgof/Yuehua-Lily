from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from lib.core_1e_b2_empirical_adapter_v2 import (
    EXPENSE_INPUT_PATH,
    FIXTURE_PATH,
    U8,
    decode_normalized_container,
    decode_normalized_bytes,
    preflight_normalized_bytes,
    preflight_normalized_payload,
)
from lib.core_1e_a_synthetic_engine import weekly_next_session_schedule
from lib.io import load_json
from scripts.validate_core_1e_b2_development_execution_contract_v2 import validate_contract
from scripts.validate_core_1e_b2_empirical_report_v2 import validate_report


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / FIXTURE_PATH
EXPENSE_INPUT = ROOT / EXPENSE_INPUT_PATH
POISON = ROOT / "tests/fixtures/core1e_b2r1/adversarial_post_cutoff_before_decode_v2.json"
CONTRACT = ROOT / "experiments/core_1e_b2_development_execution_contract_v2.json"
BOOTSTRAP = ROOT / "scripts/run_core_1e_b2_committed_bootstrap_v2.py"


class Core1EB2R1ContractAdapterReportTests(unittest.TestCase):
    def test_contract_report_and_project_bootstrap_are_e0_deny_only(self) -> None:
        self.assertEqual("pass", validate_contract()["status"])
        self.assertEqual("pass", validate_report()["status"])
        completed = subprocess.run(
            [sys.executable, str(BOOTSTRAP)], cwd=ROOT, text=True, capture_output=True, check=False
        )
        self.assertEqual(1, completed.returncode)
        self.assertEqual(
            {
                "data_accessed": False,
                "input_read_count": 0,
                "one_shot_consumed": False,
                "outcome": "canonical_activation_absent",
                "paths_resolved": [],
                "project_artifacts_created": False,
                "real_data_accessed": False,
                "status": "blocked",
                "validation_accessed": False,
            },
            json.loads(completed.stdout),
        )

    def test_actual_yahoo_shape_intersects_u8_and_decodes_only_total_return_close(self) -> None:
        raw = FIXTURE.read_bytes()
        payload, metadata = preflight_normalized_bytes(raw)
        self.assertGreaterEqual(metadata["row_count"], 201)
        self.assertEqual("2015-12-31", payload["cutoff_inclusive"])
        self.assertEqual(list(U8), [item["symbol"] for item in payload["symbols"]])
        self.assertNotIn("expense_ratios", payload)

        expense = load_json(EXPENSE_INPUT)
        original_close = load_json(FIXTURE)["symbols"][0]["records"][0]["total_return_close"]
        altered = copy.deepcopy(payload)
        altered["symbols"][0]["records"][0]["raw_close"] = 999999.0
        counter: dict[str, int] = {}
        fixture = decode_normalized_container(altered, expense, decode_counter=counter)
        self.assertEqual(list(U8), list(fixture["closes"]))
        self.assertEqual(original_close, fixture["closes"]["VTI"][0])
        self.assertEqual(metadata["session_dates"], fixture["session_dates"])
        self.assertEqual(metadata["row_count"] * len(U8), counter["count"])

        schedule = weekly_next_session_schedule(metadata["session_dates"])
        self.assertTrue(schedule)
        self.assertTrue(all(item["execution_index"] == item["decision_index"] + 1 for item in schedule))
        self.assertTrue(all(item["execution_date"] != item["decision_date"] for item in schedule))

    def test_post_cutoff_poison_fails_before_any_return_decode(self) -> None:
        counter: dict[str, int] = {}
        with self.assertRaisesRegex(ValueError, "input_contains_date_after_2015-12-31"):
            decode_normalized_bytes(POISON.read_bytes(), load_json(EXPENSE_INPUT), decode_counter=counter)
        self.assertEqual({}, counter)

    def test_actual_schema_unknown_fields_and_bad_availability_fail_closed(self) -> None:
        payload = load_json(FIXTURE)
        cases: list[tuple[dict[str, object], str]] = []

        unknown_top = copy.deepcopy(payload)
        unknown_top["unexpected"] = True
        cases.append((unknown_top, "normalized_container_unknown"))

        unknown_symbol = copy.deepcopy(payload)
        unknown_symbol["symbols"][0]["unexpected"] = True
        cases.append((unknown_symbol, r"symbol\[0\]_unknown"))

        unknown_record = copy.deepcopy(payload)
        unknown_record["symbols"][0]["records"][0]["unexpected"] = True
        cases.append((unknown_record, r"VTI.record\[0\]_unknown"))

        bad_availability = copy.deepcopy(payload)
        bad_availability["symbols"][0]["records"][0]["availability_timestamp"] = "2006-02-03T17:00:00-05:00"
        cases.append((bad_availability, "must_match_yahoo_normalizer_fixed_16_00_label"))

        for candidate, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    preflight_normalized_payload(candidate)

    def test_contract_binds_future_e1_mode_without_opening_validation(self) -> None:
        contract = load_json(CONTRACT)
        self.assertEqual("e1_empirical_development_only", contract["future_development_execution"]["mode"])
        self.assertEqual(
            "separate owner-approved CORE-1E-B2-B activation reference",
            contract["future_development_execution"]["activation_reference_requirement"],
        )
        self.assertFalse(contract["future_development_execution"]["final_validation"]["accessed"])
        self.assertEqual("none", contract["future_development_execution"]["edge_claim"])


if __name__ == "__main__":
    unittest.main()
