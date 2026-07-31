from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from lib.l4_b88r2_lifecycle_v3 import DEPENDENCIES, GATE, ACTIVATION, build_activation, canonical
from lib.l4_b88r2_scientific_engine_v3 import classify_outcome, constraints, metric_statistics, regime_funding, robustness, side_effects
from lib.l4_b88_scientific_contract_v1 import METRICS, USEFUL
from scripts.validate_l_4_breadth_b88r2_phase_a_execution_contract_v3 import validate as gate
from scripts.validate_l_4_breadth_b88r2_scientific_report_v3 import validate as report

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/l4_b88r2/synthetic_blocked_report_v3.json"


def bootstrap_module(root: Path):
    specification = importlib.util.spec_from_file_location("temporary_b88r2_bootstrap", root / "scripts/run_l_4_breadth_b88r2_committed_bootstrap_v3.py")
    module = importlib.util.module_from_spec(specification); specification.loader.exec_module(module)
    return module


def raw_week(week: int) -> dict:
    from lib.l4_b88r_scientific_engine_v2 import directional_q, ewma_covariance
    def history(width): return [[.01 if (day*(asset+1)+week) % 5 else -.01 for asset in range(width)] for day in range(60)]
    def q_history(width): return [[((week*week*13+day*(asset+2)+asset*asset*day*day) % 97-48)/100 for asset in range(width)] for day in range(52)]
    def realised(width): return [[((week*week*17+day*(asset+3)+asset*asset*7) % 97-48)/1000 for asset in range(width)] for day in range(20)]
    h4, h8 = history(4), history(8); decision_day = date(2015, 1, 2)+timedelta(days=week*5); execution_day = decision_day+timedelta(days=1); decision, execution = decision_day.isoformat(), execution_day.isoformat()
    return {"timing": {"week_sessions": [decision], "decision_date": decision, "execution_date": execution, "realized_dates": [(execution_day+timedelta(days=day)).isoformat() for day in range(20)], "u4_date": decision, "u8_date": decision}, "returns_history_u4": h4, "returns_history_u8": h8, "q_u4": [directional_q([row[index] for row in h4]) for index in range(4)], "q_u8": [directional_q([row[index] for row in h8]) for index in range(8)], "covariance_u4": ewma_covariance(h4)[0], "covariance_u8": ewma_covariance(h8)[0], "q_history_u4": q_history(4), "q_history_u8": q_history(8), "weights_u4": [.15+.001*week, .2, .25, .25], "weights_u8": [.1+.001*week, .1, .1, .1, .1, .1, .1, .1], "changes_u4": [.01]*4, "changes_u8": [.01]*8, "cash_return": .0001, "realized_returns_u4": realised(4), "realized_returns_u8": realised(8), "net_pnl_contribution_u4": {symbol: .01*(week+index+1) for index, symbol in enumerate(("VTI", "IEF", "GLD", "DBC"))}, "net_pnl_contribution_u8": {symbol: .01*(week+index+1) for index, symbol in enumerate(("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"))}, "regime": {"global_state": "trend", "volatility_tercile": "middle", "equity_synchronization": "mixed"}}


class B88R2(unittest.TestCase):
    def temporary_checkout(self):
        temporary = tempfile.TemporaryDirectory(); root = Path(temporary.name) / "repo"; root.mkdir()
        for relative in DEPENDENCIES:
            target = root / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / relative, target)
        for args in (("git", "init", "-q"), ("git", "config", "user.email", "lily-test@example.invalid"), ("git", "config", "user.name", "Lily Test"), ("git", "add", "."), ("git", "commit", "-qm", "gate")):
            subprocess.run(args, cwd=root, check=True)
        return temporary, root, subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True).strip()

    def temporary_activation(self, mutate=None):
        temporary, root, accepted = self.temporary_checkout()
        raw = (root / GATE).read_bytes(); value = build_activation(gate=json.loads(raw), gate_raw=raw, accepted_gate_head_sha=accepted, hermetic_ci_run_id=1)
        if mutate: mutate(value)
        target = root / ACTIVATION; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(canonical(value)); subprocess.run(("git", "add", ACTIVATION), cwd=root, check=True); subprocess.run(("git", "commit", "-qm", "activation"), cwd=root, check=True)
        return temporary, root, subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True).strip()

    def test_gate_fixture_and_absent_activation_bootstrap(self):
        self.assertEqual("pass", gate()["status"]); self.assertEqual("pass", report(FIXTURE)["status"])
        temporary, root, commit = self.temporary_checkout()
        with temporary: self.assertEqual("canonical_activation_absent", bootstrap_module(root).preflight(root, commit)["outcome"])

    def test_gate_owned_activation_owner_schema_blob_and_dirty_dependency(self):
        temporary, root, commit = self.temporary_activation()
        with temporary: self.assertTrue(bootstrap_module(root).preflight(root, commit)["ready"])
        for mutation in (lambda value: value.__setitem__("schema_version", "forged"), lambda value: value.__setitem__("owner_reference", "forged"), lambda value: value.__setitem__("gate_sha256", "0"*64)):
            temporary, root, commit = self.temporary_activation(mutation)
            with temporary: self.assertEqual("refused_activation", bootstrap_module(root).preflight(root, commit)["outcome"])
        temporary, root, commit = self.temporary_activation()
        with temporary:
            dependency = root / "lib/statistics.py"; dependency.write_bytes(dependency.read_bytes()+b"\n# dirty\n")
            self.assertEqual("refused_execution_provenance", bootstrap_module(root).preflight(root, commit)["outcome"])

    def test_e1_golden_and_adversarial_recomputation(self):
        rows = [raw_week(index) for index in range(30)]; statistics = metric_statistics(rows); derived_constraints = constraints(rows); derived_side_effects = side_effects(rows); derived_robustness = robustness(rows, statistics); derived_regimes = regime_funding(rows, statistics)
        report_value = {"schema_version": "lily_l4_b88r2_scientific_report_v3", "order_id": "B8.8R2", "hypothesis_id": "L-4", "mode": "future_falsification_only", "evidence_tier": "E1", "edge_claim": "none", "provenance": {"gate_path": "experiments/l_4_breadth_b88r2_phase_a_execution_contract_v3.json", "gate_sha256": (ROOT / GATE).read_bytes() and __import__("hashlib").sha256((ROOT / GATE).read_bytes()).hexdigest(), "activation_schema": "lily_l4_b88r2_activation_v3"}, "validation_seal": {"status": "sealed_not_accessed", "accessed": False}, "authorizations": {key: False for key in ("data", "container", "market", "return", "signal", "position", "covariance", "regime", "cost", "pnl", "validation", "provider", "network", "credentials", "broker", "paid", "paper_trade", "real_money", "activation", "execution", "report", "research_decision", "ledger")}, "access_counts": {"activation_count": 0, "production_execution_count": 0, "production_report_count": 0, "ledger_count": 0, "real_container_read_hash_scan_count": 0, "market_return_signal_position_covariance_regime_cost_pnl_count": 0, "validation_access_count": 0, "provider_network_credentials_broker_paid_paper_real_money_count": 0}, "weekly_observations": rows, "metric_statistics": statistics, "constraints": derived_constraints, "robustness": derived_robustness, "side_effects": derived_side_effects, "regimes": derived_regimes, "outcome": "scope_restricted", "autopsy": None}
        constraints_pass = derived_constraints["pass"] and derived_side_effects["pass"] and all(value["pass"] for value in derived_robustness.values())
        report_value["outcome"] = classify_outcome(statistics, constraints_evaluable=derived_constraints["evaluable"], constraints_pass=constraints_pass)
        report_value["autopsy"] = {"classification": "falsified_E1_only", "metric_breaches": [metric for metric in METRICS if statistics[metric]["falsify_ucb"] < USEFUL[metric]], "constraint_breach": not constraints_pass} if report_value["outcome"] == "falsified_E1_only" else None
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "golden.json"; path.write_text(json.dumps(report_value), encoding="ascii"); self.assertEqual("pass", report(path)["status"], report(path))
            report_value["metric_statistics"]["n_eff_delta"]["mean"] += .1; path.write_text(json.dumps(report_value), encoding="ascii"); self.assertIn("metric_statistics", report(path)["blockers"])


if __name__ == "__main__": unittest.main()
