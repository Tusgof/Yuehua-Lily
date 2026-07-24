from __future__ import annotations

import copy
import math
import tempfile
import unittest
from pathlib import Path

from lib.io import write_json
from lib.provenance import file_sha256, git_commit
from scripts.validate_l_2_falsification_report_v2 import CLAIM_LIMITS, CONTRACT, SEALED, V2, V3, WINDOW, validate_report


class L2FalsificationReportV2Tests(unittest.TestCase):
    def test_synthetic_fixture_passes_without_data(self) -> None:
        result = _validate(_synthetic_report())
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_forged_falsified_without_data_is_rejected(self) -> None:
        payload = _synthetic_report()
        payload.update({"report_mode": "falsification_execution", "execution_status": "falsified", "decision": "falsified", "market_returns_read": False, "blockers": ["none"]})
        result = _validate(payload)
        self.assertIn("execution_requires_market_return_read", result["blockers"])
        self.assertIn("falsification_container_shape_invalid", result["blockers"])

    def test_fake_contract_hash_is_rejected(self) -> None:
        payload = _synthetic_report()
        payload["contract_sha256"] = "0" * 64
        self.assertIn("contract_sha256_not_active_contract", _validate(payload)["blockers"])

    def test_fake_producing_commit_is_rejected(self) -> None:
        payload = _synthetic_report()
        payload["producing_git_commit"] = "0" * 40
        self.assertIn("producing_git_commit_not_current_checkout", _validate(payload)["blockers"])

    def test_unexpected_field_is_rejected(self) -> None:
        payload = _synthetic_report()
        payload["unexpected_unvalidated_field"] = "validation-return-like value"
        self.assertIn("synthetic_unexpected_fields:unexpected_unvalidated_field", _validate(payload)["blockers"])
        payload = _execution_report()
        payload["falsification_container"]["unexpected_unvalidated_field"] = "validation-return-like value"
        self.assertIn("falsification_container_shape_invalid", _validate(payload)["blockers"])

    def test_missing_or_mismatched_decision_metrics_are_rejected(self) -> None:
        payload = _execution_report()
        del payload["primary_statistics"]
        self.assertIn("primary_statistics_shape_invalid", _validate(payload)["blockers"])
        payload = _execution_report()
        payload["decision_matrix_trace"]["annualized_active_sharpe_threshold"] = 0.2
        self.assertIn("decision_matrix_trace_mismatch", _validate(payload)["blockers"])

    def test_incomplete_trial_inventory_is_rejected(self) -> None:
        payload = _execution_report()
        payload["trial_inventory"] = payload["trial_inventory"][:-1]
        self.assertIn("trial_inventory_count_invalid", _validate(payload)["blockers"])

    def test_falsified_requires_mechanism_autopsy(self) -> None:
        payload = _execution_report()
        result = _validate(payload)
        self.assertIn("mechanism_autopsy_incomplete", result["blockers"])
        payload["mechanism_autopsy"] = {key: "documented" for key in ("horizon_diversification", "signal_transform", "lag", "noise", "cost")}
        self.assertEqual("pass", _validate(payload)["status"])

    def test_validation_opening_is_rejected(self) -> None:
        payload = _synthetic_report()
        payload["validation_return_seal"] = dict(SEALED, returns_opened=True)
        self.assertIn("field_mismatch:validation_return_seal", _validate(payload)["blockers"])


def _common() -> dict[str, object]:
    return {
        "schema_version": "lily_l2_falsification_report_v2",
        "order_id": "B6.1",
        "hypothesis_id": "L-2",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "producing_git_commit": git_commit(),
        "contract_sha256": file_sha256(CONTRACT),
        "v2_sha256": V2,
        "v3_sha256": V3,
        "falsification_window": WINDOW,
        "validation_return_seal": SEALED,
        "claim_limits": CLAIM_LIMITS,
    }


def _synthetic_report() -> dict[str, object]:
    return _common() | {
        "report_mode": "synthetic_fixture",
        "execution_status": "not_run",
        "market_returns_read": False,
        "decision": "not_run",
        "blockers": ["synthetic_fixture_no_market_data", "validation_remains_sealed", "edge_claim_none"],
    }


def _execution_report() -> dict[str, object]:
    per_period = 0.05 / math.sqrt(252)
    payload = _common() | {
        "report_mode": "falsification_execution",
        "execution_status": "falsified",
        "market_returns_read": True,
        "decision": "falsified",
        "blockers": ["validation_remains_sealed", "edge_claim_none", "validation_not_opened"],
        "falsification_container": {"container_id": "synthetic-test-container", "container_sha256": "a" * 64, "max_date": "2015-12-31"},
        "observation_counts": {"calendar_observations": 60000, "paired_date_count": 60000, "time_effective_observations": 55000.0, "joint_independent_bet_equivalents": 54048.0},
        "primary_statistics": {"paired_daily_active_return_sha256": "b" * 64, "annualized_active_sharpe": 0.05, "per_period_active_sharpe": per_period, "annual_to_daily_conversion": "annualized_sharpe / sqrt(252)", "minimum_useful_per_period_sharpe": 0.1 / math.sqrt(252), "primary_margin_psr": 0.05, "dsr": 0.1, "dsr_trial_count": 5},
        "costs_and_turnover": {"cost_model_attested": True, "candidate_turnover_bps": 10.0, "comparator_turnover_bps": 9.0, "candidate_cost_bps": 1.0, "comparator_cost_bps": 1.0},
        "trial_inventory": [{"trial_id": trial_id, "paired_daily_active_return_sha256": char * 64, "per_period_sharpe": per_period} for trial_id, char in zip(("primary_32_64_126_252", "leave_out_32", "leave_out_64", "leave_out_126", "leave_out_252"), "cdef0")],
        "decision_matrix_trace": {"outcome": "falsified", "minimum_required_joint_independent_bet_equivalents": 54048, "annualized_active_sharpe_threshold": 0.1, "primary_margin_psr_max_for_falsification": 0.05},
        "v3_timing_attestation": {"shared_decision_index_r_t_minus_k": True, "no_future_returns": True, "next_actual_nyse_close_t_plus_1": True, "identical_post_execution_windows": True},
    }
    return payload


def _validate(payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.json"
        write_json(path, payload)
        return validate_report(path)


if __name__ == "__main__":
    unittest.main()
