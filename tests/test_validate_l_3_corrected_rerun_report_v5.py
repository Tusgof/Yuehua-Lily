from __future__ import annotations

import copy
import hashlib
import itertools
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_3_corrected_rerun_report_v5 import IDENTITIES, IMPLEMENTATION, validate

ROOT = Path(__file__).resolve().parents[1]


def digest(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def fixture(mode: str, decision: str) -> dict:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    present = mode == "future_execution"
    provenance = {"producing_git_commit": head}
    provenance.update({name: {"path": path, "sha256": digest(path)} for name, path in IMPLEMENTATION.items()})
    provenance.update({name: {"present": present, "path": path if present else None, "sha256": digest(path) if present else None} for name, path in IDENTITIES.items()})
    blank = mode != "future_execution"
    return {"schema_version": "lily_l3_corrected_rerun_report_v5", "order_id": "B7.9", "hypothesis_id": "L-3", "report_mode": mode, "decision": decision, "evidence_tier": "E0" if mode == "synthetic_not_run" else "E1", "edge_claim": "none", "provenance": provenance,
        "counts": {"paired_observations": 0 if blank else 49, "effective_independent_bets": 0.0 if blank else 49.0, "mintrl_falsify": 49, "asset_multiplier": 1, "day_multiplier": 1, "trade_multiplier": 1, "t20_multiplier": 1},
        "primary": {"candidate_mean_hhi": None if blank else .40, "comparator_mean_hhi": None if blank else .50, "mean_delta": None if blank else .10, "threshold": None if blank else .05, "autocorrelation_ucb_trace": [] if blank else [.01, .02, .03, .04, .04], "ucb": None if blank else .04},
        "realized": {"candidate_mean_hhi": None if blank else .40, "comparator_mean_hhi": None if blank else .50, "mean_delta": None if blank else .10, "threshold": None if blank else .05, "complete_t_plus_20_observations": 0 if blank else 49},
        "side_effects": {"paired_observations": 0 if blank else 49, "candidate": None if blank else {"turnover": 12.0, "commission": .36, "spread_slippage": .36, "sell_surcharge": .48, "cap_events": 9, "cash_events": 9, "scale_down_events": 9}, "comparator": None if blank else {"turnover": 10.0, "commission": .30, "spread_slippage": .30, "sell_surcharge": .40, "cap_events": 5, "cash_events": 5, "scale_down_events": 5}},
        "regimes": {"claims": [] if blank else [{"name": name, "paired_observations": 49, "effective_independent_bets": 49.0, "mintrl_falsify": 49, "asset_multiplier": 1, "day_multiplier": 1, "trade_multiplier": 1, "t20_multiplier": 1} for name in ("low", "middle", "high")], "pooled": False},
        "validation_seal": {"status": "sealed_not_accessed", "accessed": False}, "autopsy": None}


class B79ReportValidatorTests(unittest.TestCase):
    def test_positive_fixture_for_every_allowed_mode_and_direct_cli(self) -> None:
        for mode, decision in (("synthetic_not_run", "not_run"), ("pre_return_failure", "scope_restricted"), ("future_execution", "not_falsified_not_validated")):
            report = fixture(mode, decision)
            self.assertEqual("pass", validate(report)["status"], validate(report))
        report = fixture("future_execution", "falsified")
        report["autopsy"] = {key: "mechanism evidence" for key in ("volatility_scaling_concentration", "common_constraints", "ex_ante_vs_realized_hhi", "turnover_cost", "implementation_data_alternatives")}
        self.assertEqual("pass", validate(report)["status"], validate(report))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"; path.write_text(json.dumps(fixture("future_execution", "not_falsified_not_validated")), encoding="utf-8")
            self.assertEqual(0, subprocess.run(["python", "scripts/validate_l_3_corrected_rerun_report_v5.py", str(path)], cwd=ROOT, check=False).returncode)

    def test_every_unsupported_mode_decision_tier_pair_and_autopsy_is_blocked(self) -> None:
        allowed = {("synthetic_not_run", "not_run", "E0"), ("pre_return_failure", "scope_restricted", "E1"), ("future_execution", "falsified", "E1"), ("future_execution", "not_falsified_not_validated", "E1")}
        for mode, decision, tier in itertools.product(("synthetic_not_run", "pre_return_failure", "future_execution"), ("not_run", "scope_restricted", "falsified", "not_falsified_not_validated"), ("E0", "E1")):
            if (mode, decision, tier) in allowed:
                continue
            report = fixture(mode, "not_run" if mode == "synthetic_not_run" else "scope_restricted" if mode == "pre_return_failure" else "not_falsified_not_validated")
            report["decision"], report["evidence_tier"] = decision, tier
            self.assertEqual("blocked", validate(report)["status"], (mode, decision, tier, validate(report)))
        report = fixture("future_execution", "not_falsified_not_validated"); report["autopsy"] = {"volatility_scaling_concentration": "wrong"}
        self.assertEqual("blocked", validate(report)["status"])

    def test_inspector_arithmetic_and_provenance_probes_fail(self) -> None:
        report = fixture("future_execution", "not_falsified_not_validated")
        cases = []
        side_breach = copy.deepcopy(report); side_breach["side_effects"]["candidate"]["turnover"] = 12.1; cases.append(side_breach)
        trace_forge = copy.deepcopy(report); trace_forge["primary"]["ucb"] = .01; cases.append(trace_forge)
        realized_forge = copy.deepcopy(report); realized_forge["realized"]["mean_delta"] = .09; cases.append(realized_forge)
        regime_missing = copy.deepcopy(report); regime_missing["regimes"]["claims"].pop(); cases.append(regime_missing)
        for name in IDENTITIES:
            missing = copy.deepcopy(report); missing["provenance"][name]["path"] = "tests/fixtures/l3_corrected_rerun_v5/identities/missing.json"; cases.append(missing)
            forged = copy.deepcopy(report); forged["provenance"][name]["sha256"] = "z" * 64; cases.append(forged)
            wrong_path = copy.deepcopy(report); wrong_path["provenance"][name]["path"] = "experiments/does_not_exist.json"; cases.append(wrong_path)
        for candidate in cases:
            self.assertEqual("blocked", validate(candidate)["status"], validate(candidate))


if __name__ == "__main__":
    unittest.main()
