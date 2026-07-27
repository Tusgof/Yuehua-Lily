from __future__ import annotations

import copy
import hashlib
import subprocess
import unittest
from pathlib import Path

from scripts.validate_l_3_corrected_rerun_report_v3 import validate

ROOT = Path(__file__).resolve().parents[1]


def digest(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def fixture(mode: str, decision: str) -> dict:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    identities = {name: {"path": path, "sha256": digest(path)} for name, path in {"gate": "experiments/l_3_corrected_rerun_activation_v3.json", "runner": "scripts/run_l_3_corrected_rerun_v3.py", "report_validator": "scripts/validate_l_3_corrected_rerun_report_v3.py", "report_schema": "schemas/l_3_corrected_rerun_report_v3.schema.json", "side_effect_library": "lib/l3_corrected_rerun_v3.py"}.items()}
    present = mode == "future_execution"
    provenance = {"producing_git_commit": head, **identities, **{name: {"present": present, "path": f"reports/experiments/{name}.json" if present else None, "sha256": "a" * 64 if present else None} for name in ("container_identity", "schedule_identity", "ledger_identity")}}
    future = mode == "future_execution"
    return {"schema_version": "lily_l3_corrected_rerun_report_v3", "order_id": "B7.8", "hypothesis_id": "L-3", "report_mode": mode, "decision": decision, "evidence_tier": "E1" if mode != "synthetic_not_run" else "E0", "edge_claim": "none", "provenance": provenance, "counts": {"paired_observations": 49 if future else 0, "effective_independent_bets": 49.0 if future else 0.0, "mintrl_falsify": 49, "asset_multiplier": 1, "day_multiplier": 1, "trade_multiplier": 1, "t20_multiplier": 1}, "primary": {"ucb": .04 if future else None, "autocorrelation_ucb_trace": [.03, .04] if future else []}, "realized": {"evaluable": future, "complete_t_plus_20": future, "observations": 49 if future else 0}, "side_effects": {"evaluable": future, "met": True, "cost_alias_turnover": False, "turnover_relative_increase": .20 if future else None, "cost_relative_increase": .20 if future else None, "cap_frequency_increase": .10 if future else None, "cash_frequency_increase": .10 if future else None, "scale_down_frequency_increase": .10 if future else None}, "regimes": {"claims": [{"name": "synthetic-only-fixture", "evaluable": True, "funded": True, "observations": 49}] if future else [], "pooled": False}, "validation_seal": {"status": "sealed_not_accessed", "accessed": False}, "autopsy": None}


class B78ReportValidatorTests(unittest.TestCase):
    def test_positive_fixture_for_each_allowed_mode(self) -> None:
        for mode, decision in (("synthetic_not_run", "not_run"), ("pre_return_failure", "scope_restricted"), ("future_execution", "not_falsified_not_validated")):
            report = fixture(mode, decision)
            self.assertEqual("pass", validate(report)["status"], validate(report))
        report = fixture("future_execution", "falsified")
        report["autopsy"] = {"volatility_scaling_concentration": "a", "common_constraints": "b", "ex_ante_vs_realized_hhi": "c", "turnover_cost": "d", "implementation_data_alternatives": "e"}
        self.assertEqual("pass", validate(report)["status"], validate(report))

    def test_forged_hash_empty_evidence_nonfinite_pooling_and_autopsy_fail(self) -> None:
        report = fixture("future_execution", "not_falsified_not_validated")
        forged = copy.deepcopy(report); forged["provenance"]["gate"]["sha256"] = "0" * 64
        self.assertEqual("blocked", validate(forged)["status"])
        empty = copy.deepcopy(report); empty["regimes"]["claims"] = []
        self.assertEqual("blocked", validate(empty)["status"])
        nonfinite = copy.deepcopy(report); nonfinite["primary"]["ucb"] = float("nan")
        self.assertEqual("blocked", validate(nonfinite)["status"])
        pooled = copy.deepcopy(report); pooled["regimes"]["pooled"] = True
        self.assertEqual("blocked", validate(pooled)["status"])
        false = fixture("future_execution", "falsified")
        false["autopsy"] = None
        self.assertEqual("blocked", validate(false)["status"])


if __name__ == "__main__":
    unittest.main()
