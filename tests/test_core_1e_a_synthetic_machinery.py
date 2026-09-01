from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lib.core_1e_a_lifecycle_v1 import (
    ACTIVATION_PATH,
    GATE_PATH,
    RUNTIME_PATHS,
    build_synthetic_activation,
    canonical,
    hash_file,
    preflight,
    run_synthetic_once,
    validate_activation,
)
from lib.core_1e_a_synthetic_engine import (
    CANDIDATES,
    NO_TRADE_BAND,
    PRIMARY_COMMISSION,
    PRIMARY_SELL_SURCHARGE,
    PRIMARY_SPREAD_SLIPPAGE,
    SLEEVE_WEIGHT,
    apply_no_trade_band,
    best_episode_concentration,
    build_report,
    daily_asset_attribution,
    directional_count,
    directional_count_signal,
    drifted_pre_trade_weights,
    execution_costs,
    evaluate_gates,
    fixed_sleeve_target_weights,
    inherited_l1_episodes,
    select_candidate,
    simple_moving_average_signal,
    simulate,
    summarize_path,
    weekly_next_session_schedule,
)
from lib.io import load_json, write_json
from lib.provenance import file_sha256, git_commit
from scripts.validate_core_1e_a_phase_a_execution_contract_v1 import validate_contract
from scripts.validate_core_1e_a_synthetic_report_v1 import validate_report


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "core1e_a" / "synthetic_market_v1.json"
CONTRACT = ROOT / "experiments" / "core_1e_a_phase_a_execution_contract_v1.json"
BOOTSTRAP = ROOT / "scripts" / "run_core_1e_a_committed_bootstrap_v1.py"


class Core1EASyntheticMachineryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = load_json(FIXTURE)
        cls.report = build_report(
            cls.fixture,
            contract_sha256=file_sha256(CONTRACT),
            fixture_sha256=file_sha256(FIXTURE),
            producing_commit=git_commit(ROOT),
            engine_sha256=file_sha256(ROOT / "lib" / "core_1e_a_synthetic_engine.py"),
            stop_rule=load_json(CONTRACT)["locked_science"]["stop_rule"],
        )

    def test_directional_count_zero_returns_and_sma_strictness(self) -> None:
        values = [0.01, 0.0, -0.02, 0.0, 0.03]
        self.assertEqual(1, directional_count(values, 5))
        self.assertTrue(directional_count_signal(values, 5))
        self.assertEqual(0, directional_count([0.0, 0.0, 0.0], 3))
        self.assertFalse(directional_count_signal([0.0, 0.0, 0.0], 3))
        self.assertIsNone(directional_count(values, 6))
        equal = [100.0] * 200
        self.assertFalse(simple_moving_average_signal(equal))
        self.assertTrue(simple_moving_average_signal(equal[:-1] + [100.000001]))
        self.assertFalse(simple_moving_average_signal(equal[:-1] + [99.999999]))

    def test_weekly_schedule_uses_next_supplied_session(self) -> None:
        dates = ["2007-02-08", "2007-02-09", "2007-02-12", "2007-02-13", "2007-02-16", "2007-02-20"]
        schedule = weekly_next_session_schedule(dates)
        self.assertEqual(
            [("2007-02-09", "2007-02-12"), ("2007-02-16", "2007-02-20")],
            [(item["decision_date"], item["execution_date"]) for item in schedule],
        )
        self.assertTrue(all(item["execution_index"] > item["decision_index"] for item in schedule))

    def test_warmup_end_decision_executes_on_first_development_session(self) -> None:
        dates = ["2007-02-02", "2007-02-05", "2007-02-06", "2007-02-09", "2007-02-12"]
        schedule = weekly_next_session_schedule(dates)
        self.assertEqual(
            [("2007-02-02", "2007-02-05"), ("2007-02-09", "2007-02-12")],
            [(item["decision_date"], item["execution_date"]) for item in schedule],
        )
        self.assertTrue(all(item["decision_index"] < item["execution_index"] for item in schedule))

    def test_fixed_sleeves_drift_and_inclusive_no_trade_band(self) -> None:
        target = fixed_sleeve_target_weights({"VTI"})
        self.assertEqual(SLEEVE_WEIGHT, target["VTI"])
        self.assertEqual(1.0 - SLEEVE_WEIGHT, target["cash"])
        self.assertEqual(0.0, fixed_sleeve_target_weights(set())["VTI"])
        previous = fixed_sleeve_target_weights({"VTI"})
        drifted = drifted_pre_trade_weights(previous, {symbol: 0.0 for symbol in target if symbol != "cash"} | {"VTI": 0.08})
        self.assertAlmostEqual(0.135 / 1.01, drifted["VTI"], places=12)
        exact = fixed_sleeve_target_weights({"VTI"})
        exact_drift = dict(exact)
        exact_drift["VTI"] = 0.105
        exact_drift["cash"] = 0.895
        self.assertEqual(SLEEVE_WEIGHT, apply_no_trade_band(exact_drift, exact)["VTI"])
        below = dict(exact_drift)
        below["VTI"] = 0.1051
        below["cash"] = 0.8949
        self.assertEqual(0.1051, apply_no_trade_band(below, exact)["VTI"])

    def test_cost_paths_and_expenses_are_separate(self) -> None:
        drifted = fixed_sleeve_target_weights(set())
        target = fixed_sleeve_target_weights({"VTI"})
        costs = execution_costs(drifted, target, nav=1.0)
        traded = SLEEVE_WEIGHT
        self.assertAlmostEqual(traded, costs["traded_notional"], places=12)
        self.assertAlmostEqual(PRIMARY_COMMISSION * traded, costs["commission"], places=12)
        self.assertAlmostEqual(PRIMARY_SPREAD_SLIPPAGE * traded, costs["spread_slippage"], places=12)
        self.assertEqual(0.0, costs["sell_surcharge"])
        stress = execution_costs(drifted, target, nav=1.0, multiplier=2.0)
        self.assertAlmostEqual(2.0 * costs["execution_cost"], stress["execution_cost"], places=12)
        sell = execution_costs(target, drifted, nav=1.0)
        self.assertAlmostEqual(PRIMARY_SELL_SURCHARGE * traded, sell["sell_surcharge"], places=12)
        simulated = simulate(self.fixture, lambda _decision_index: fixed_sleeve_target_weights(set(self.fixture["closes"])))
        funded_row = next(row for row in simulated["rows"] if row["expense_accrual"] > 0.0)
        self.assertGreater(funded_row["expense_accrual"], 0.0)
        execution_row = next(row for row in simulated["rows"] if row["primary_execution_cost"] > 0.0)
        self.assertAlmostEqual(2.0 * execution_row["primary_execution_cost"], execution_row["two_x_execution_cost"], places=12)
        self.assertAlmostEqual(2.0 * simulated["cost_totals"]["execution_cost_primary"], simulated["cost_totals"]["execution_cost_two_x"], places=12)
        self.assertEqual({"gross", "primary_net", "two_x_execution_cost_net"}, set(self.report["benchmark"]["metrics"]))
        self.assertEqual(1.0, self.report["calculation_attestation"]["two_x_expense_multiplier"])
        for candidate in self.report["candidates"]:
            self.assertLessEqual(
                candidate["metrics"]["two_x_execution_cost_net"]["annual_geometric_return"] or 0.0,
                candidate["metrics"]["primary_net"]["annual_geometric_return"] or 0.0,
            )

    def test_hand_checkable_daily_net_attribution_reconciles_components(self) -> None:
        start_weights = fixed_sleeve_target_weights({"VTI"})
        executed_weights = fixed_sleeve_target_weights(set())
        returns = {symbol: 0.0 for symbol in start_weights if symbol != "cash"}
        returns["VTI"] = 0.10
        expenses = {symbol: 0.0 for symbol in returns}
        expenses["VTI"] = 0.252
        attribution = daily_asset_attribution(
            start_nav=1.0,
            start_weights=start_weights,
            asset_returns=returns,
            executed_weights=executed_weights,
            expense_ratios=expenses,
        )
        vti = attribution["VTI"]
        expected_commission = -PRIMARY_COMMISSION * SLEEVE_WEIGHT
        expected_spread = -PRIMARY_SPREAD_SLIPPAGE * SLEEVE_WEIGHT
        expected_surcharge = -PRIMARY_SELL_SURCHARGE * SLEEVE_WEIGHT
        expected_expense = -SLEEVE_WEIGHT * expenses["VTI"] / 252.0
        self.assertAlmostEqual(0.10 * SLEEVE_WEIGHT, vti["return"], places=14)
        self.assertAlmostEqual(expected_expense, vti["etf_expense"], places=14)
        self.assertAlmostEqual(expected_commission, vti["commission"], places=14)
        self.assertAlmostEqual(expected_spread, vti["spread_slippage"], places=14)
        self.assertAlmostEqual(expected_surcharge, vti["sell_surcharge"], places=14)
        self.assertAlmostEqual(
            sum(vti[key] for key in ("return", "etf_expense", "commission", "spread_slippage", "sell_surcharge")),
            vti["primary_net"],
            places=14,
        )

    def test_simulation_exposes_daily_and_full_window_primary_attribution(self) -> None:
        result = simulate(self.fixture, lambda _decision_index: fixed_sleeve_target_weights({"VTI"}))
        self.assertTrue(result["daily_attribution"])
        for row in result["daily_attribution"]:
            total = sum(item["primary_net"] for item in row["asset_components"].values())
            self.assertAlmostEqual(row["primary_net_return"], total, places=12)
        full = result["full_window_attribution"]
        self.assertAlmostEqual(
            sum(item["primary_net"] for item in full.values()),
            sum(row["primary_net_return"] for row in result["daily_attribution"]),
            places=12,
        )
        self.assertEqual(
            {symbol: full[symbol]["primary_net"] for symbol in full},
            result["asset_contributions"],
        )

    def test_inherited_l1_episode_rule_allows_one_neutral_and_closes_on_two(self) -> None:
        dates = [f"2007-02-{day:02d}" for day in (5, 6, 7, 8, 9, 12, 13)]
        q_by_asset = {symbol: [0.0] * len(dates) for symbol in ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")}
        q_by_asset["VTI"] = [1.0, 1.0, 0.0, 1.0, 0.0, 0.0, -1.0]
        episodes = inherited_l1_episodes(dates, q_by_asset)
        vti = [item for item in episodes if item["symbol"] == "VTI"]
        self.assertEqual(
            [(1, "2007-02-05", "2007-02-12"), (-1, "2007-02-13", "2007-02-13")],
            [(item["sign"], item["start_date"], item["end_date"]) for item in vti],
        )
        contributions = {symbol: [0.0] * len(dates) for symbol in q_by_asset}
        contributions["VTI"] = [0.10, 0.10, 0.01, 0.20, 0.02, 0.03, 0.40]
        concentration, selected = best_episode_concentration(
            dates,
            q_by_asset,
            dates,
            contributions,
        )
        self.assertAlmostEqual(0.46 / (0.46 + 0.40), concentration, places=12)
        self.assertEqual(2, len(selected))

        open_dates = ["2007-02-05", "2007-02-09"]
        open_q = {symbol: [0.0, 0.0] for symbol in q_by_asset}
        open_q["VTI"] = [1.0, 1.0]
        open_contributions = {symbol: [0.0, 0.0, 0.0] for symbol in q_by_asset}
        open_contributions["VTI"] = [0.10, 0.20, 0.30]
        open_concentration, open_episodes = best_episode_concentration(
            open_dates,
            open_q,
            ["2007-02-05", "2007-02-09", "2007-02-12"],
            open_contributions,
        )
        self.assertEqual(1.0, open_concentration)
        self.assertEqual("2007-02-12", open_episodes[0]["end_date"])

    def test_cross_sectional_effective_dimension_uses_correlation_eigenvalues(self) -> None:
        values = [float(index) for index in range(10)]
        series = {symbol: list(values) for symbol in ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")}
        rows = [{"turnover": 0.0, "trades": 0, "exposure": 0.0} for _ in values]
        metrics = summarize_path([0.01, -0.005, 0.02, -0.012, 0.008, 0.003, -0.017, 0.011, -0.004, 0.009], rows, asset_net_contribution_series=series)
        equivalents = metrics["independent_bet_equivalents"]
        self.assertIsNotNone(equivalents["cross_section_eigenvalues"])
        self.assertLess(equivalents["cross_section_count"], 8.0)
        self.assertLess(equivalents["cross_section_count"], 2.0)
        constant = dict(series)
        constant["DBC"] = [1.0] * len(values)
        non_evaluable = summarize_path([0.01, -0.005, 0.02, -0.012, 0.008, 0.003, -0.017, 0.011, -0.004, 0.009], rows, asset_net_contribution_series=constant)
        self.assertIsNone(non_evaluable["independent_bet_equivalents"]["cross_section_count"])
        self.assertIsNone(non_evaluable["independent_bet_equivalents"]["joint_count"])

    def test_undefined_trial_sharpe_preserves_non_evaluable_dsr_and_fails_gate_b(self) -> None:
        returns = [0.01, -0.005, 0.02, -0.01, 0.015, -0.002]
        rows = [{"turnover": 0.0, "trades": 0, "exposure": 0.0} for _ in returns]
        primary = summarize_path(returns, rows, trial_sharpes_daily=[None, 0.1, 0.2])
        self.assertIsNone(primary["dsr"])
        self.assertIsNone(primary["independent_bet_equivalents"]["joint_count"])
        candidate = {
            "metrics": {"primary_net": primary, "two_x_execution_cost_net": primary},
            "subperiods": {
                "2007_2009": {"observations": 1, "annual_geometric_return": 0.01, "annualized_sharpe": 0.1},
                "2010_2012": {"observations": 1, "annual_geometric_return": 0.01, "annualized_sharpe": 0.1},
                "2013_2015": {"observations": 1, "annual_geometric_return": 0.01, "annualized_sharpe": 0.1},
            },
            "leave_one_out": {"annual_geometric_return": 0.01},
            "largest_positive_contribution_share": 0.1,
            "positive_contribution_hhi": 0.1,
            "best_episode_concentration": 0.1,
            "critical_blockers": [],
        }
        benchmark = {"metrics": {"primary_net": primary}}
        trial_statistics = [{"dsr": None}, {"dsr": 0.9}, {"dsr": 0.9}]
        self.assertFalse(evaluate_gates(candidate, benchmark, trial_statistics)["B"])

    def test_report_contains_required_statistics_and_locked_decisions(self) -> None:
        self.assertEqual(list(CANDIDATES), self.report["trial_inventory"]["candidate_ids"])
        self.assertEqual(3, self.report["trial_inventory"]["count"])
        self.assertEqual(3, len(self.report["candidates"]))
        required_metrics = {
            "calendar_count", "annual_arithmetic_return", "annual_geometric_return", "annualized_volatility",
            "annualized_sharpe", "maximum_drawdown", "one_way_turnover", "trade_count", "average_exposure",
            "psr", "dsr", "autocorrelation_adjusted_sharpe_variance", "hac_newey_west",
            "independent_bet_equivalents",
        }
        for candidate in self.report["candidates"]:
            self.assertTrue(required_metrics.issubset(candidate["metrics"]["primary_net"]))
            self.assertEqual(
                {"commission", "spread_slippage", "sell_surcharge", "execution_cost_primary", "execution_cost_two_x", "etf_expense_accrual", "primary_total_cost_drag", "two_x_total_cost_drag"},
                set(candidate["costs"]),
            )
            self.assertEqual(set("ABCDEFGH"), set(candidate["gates"]))
            self.assertEqual(candidate["all_gates_pass"], all(candidate["gates"].values()))
        self.assertFalse(self.report["timing_attestation"]["same_close_execution"])
        self.assertFalse(self.report["timing_attestation"]["lookahead_detected"])
        self.assertEqual("no_winner_stop", self.report["selection"]["outcome"])
        self.assertIsNone(self.report["selection"]["winner"])
        self.assertEqual([], self.report["selection"]["eligible_candidates"])

    def test_selection_discards_first_and_applies_locked_ties(self) -> None:
        def evaluation(candidate_id: str, score: float, turnover: float, eligible: bool = True) -> dict:
            return {
                "id": candidate_id,
                "all_gates_pass": eligible,
                "subperiods": {
                    "2007_2009": {"annualized_sharpe": score},
                    "2010_2012": {"annualized_sharpe": score + 0.01},
                    "2013_2015": {"annualized_sharpe": score + 0.02},
                },
                "metrics": {"primary_net": {"one_way_turnover": turnover}},
            }

        tied = [
            evaluation("CORE1_DC60", 0.50, 0.30),
            evaluation("CORE1_DC120", 0.49, 0.10),
            evaluation("CORE1_SMA200", 0.20, 0.05),
        ]
        selected = select_candidate(tied, "stop")
        self.assertEqual("single_winner", selected["outcome"])
        self.assertEqual("CORE1_DC120", selected["winner"])
        tied[1]["metrics"]["primary_net"]["one_way_turnover"] = 0.30
        self.assertEqual("CORE1_DC60", select_candidate(tied, "stop")["winner"])
        discarded = [evaluation(item, 0.90, 0.01, eligible=item != "CORE1_DC60") for item in CANDIDATES]
        result = select_candidate(discarded, "stop")
        self.assertEqual(["CORE1_DC60"], result["discarded_candidates"])
        none = [evaluation(item, 0.90, 0.01, eligible=False) for item in CANDIDATES]
        self.assertEqual("no_winner_stop", select_candidate(none, "stop")["outcome"])

    def test_contract_and_report_validators_reject_drift_and_forgery(self) -> None:
        self.assertEqual("pass", validate_contract()["status"])
        self.assertEqual("pass", validate_report()["status"])
        mutations = []
        unknown = copy.deepcopy(self.report)
        unknown["unexpected"] = True
        mutations.append(unknown)
        missing = copy.deepcopy(self.report)
        del missing["candidates"][0]["metrics"]["primary_net"]["psr"]
        mutations.append(missing)
        forged = copy.deepcopy(self.report)
        forged["candidates"][0]["gates"] = {key: True for key in "ABCDEFGH"}
        forged["candidates"][0]["all_gates_pass"] = True
        mutations.append(forged)
        validation = copy.deepcopy(self.report)
        validation["validation_seal"]["accessed"] = True
        validation["access_counts"]["validation_access"] = 1
        mutations.append(validation)
        provenance = copy.deepcopy(self.report)
        provenance["provenance"]["engine_sha256"] = "0" * 64
        mutations.append(provenance)
        fixture_path = copy.deepcopy(self.report)
        fixture_path["fixture"]["path"] = "tests/fixtures/unknown.json"
        mutations.append(fixture_path)
        with tempfile.TemporaryDirectory() as tmp:
            for index, payload in enumerate(mutations):
                path = Path(tmp) / f"report_{index}.json"
                write_json(path, payload)
                self.assertEqual("blocked", validate_report(path)["status"])
            contract = load_json(CONTRACT)
            contract_mutations = [
                lambda payload: payload["locked_science"]["universe"]["symbols_in_order"].reverse(),
                lambda payload: payload["locked_science"]["development_candidates_in_locked_order"].pop(),
                lambda payload: payload["locked_science"]["costs"]["primary"].__setitem__("spread_slippage_one_way", 0.01),
                lambda payload: payload["locked_science"]["windows"]["opened_development_falsification"].__setitem__("start", "2008-01-01"),
            ]
            for index, mutate in enumerate(contract_mutations):
                changed = copy.deepcopy(contract)
                mutate(changed)
                contract_path = Path(tmp) / f"contract_{index}.json"
                write_json(contract_path, changed)
                self.assertEqual("blocked", validate_contract(contract_path)["status"])

    def test_bootstrap_denies_without_activation(self) -> None:
        completed = subprocess.run(
            ["python", str(BOOTSTRAP)], cwd=ROOT, text=True, capture_output=True, check=False
        )
        self.assertEqual(1, completed.returncode)
        payload = json.loads(completed.stdout)
        self.assertEqual("canonical_activation_absent", payload["outcome"])
        self.assertFalse(payload["data_accessed"])
        self.assertFalse(payload["validation_accessed"])
        self.assertEqual([], payload["paths_resolved"])

    def test_clean_temporary_git_proves_activation_marker_and_no_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            activation = self._install_synthetic_activation(root)
            self.assertEqual("ready", preflight(root)["status"])
            first = run_synthetic_once(root)
            self.assertEqual("complete", first["status"])
            self.assertEqual(1, first["input_read_count"])
            second = run_synthetic_once(root)
            self.assertEqual("refused_prior_invocation", second["outcome"])
            self.assertEqual(0, second["input_read_count"])
            for relative in (activation["one_shot"]["marker_path"], activation["one_shot"]["attempt_path"], activation["one_shot"]["report_path"]):
                self.assertTrue((root / relative).is_file())

    def test_activation_rejects_runtime_blob_drift_at_current_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            activation = self._install_synthetic_activation(root)
            runtime_path = root / RUNTIME_PATHS[0]
            runtime_path.write_bytes(runtime_path.read_bytes() + b"\n")
            self._git(root, "add", RUNTIME_PATHS[0])
            self._git(root, "commit", "-m", "drift bound runtime")
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
            blockers = validate_activation(root, head, activation)
            self.assertIn(f"activation_current_runtime_byte_mismatch:{RUNTIME_PATHS[0]}", blockers)

    def test_activation_rejects_arbitrary_protected_and_duplicate_lifecycle_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            activation = self._install_synthetic_activation(root)
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
            for field, value in (("marker_path", "AGENTS.md"), ("attempt_path", "reports/experiments/arbitrary.json")):
                changed = copy.deepcopy(activation)
                changed["one_shot"][field] = value
                blockers = validate_activation(root, head, changed)
                self.assertIn(f"activation_one_shot_path_changed:{field}", blockers)
            duplicate = copy.deepcopy(activation)
            duplicate["one_shot"]["attempt_path"] = duplicate["one_shot"]["marker_path"]
            self.assertIn("activation_one_shot_paths_not_distinct", validate_activation(root, head, duplicate))

    def _seed_temp_repo(self, root: Path) -> None:
        for relative in (GATE_PATH, *RUNTIME_PATHS, "tests/fixtures/core1e_a/synthetic_market_v1.json"):
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        self._git(root, "init", "-b", "main")
        self._git(root, "config", "user.email", "synthetic@example.invalid")
        self._git(root, "config", "user.name", "Synthetic Test")
        self._git(root, "add", ".")
        self._git(root, "commit", "-m", "seed synthetic runtime")

    def _install_synthetic_activation(self, root: Path) -> dict:
        base_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
        runtime = {relative: hash_file(root / relative) for relative in RUNTIME_PATHS}
        input_ref = "tests/fixtures/core1e_a/synthetic_market_v1.json"
        activation = build_synthetic_activation(
            gate_commit=base_commit,
            gate_sha256=hash_file(root / GATE_PATH),
            runtime_bytes=runtime,
            owner_authorization_ref="owner-order:CORE-1E-A-synthetic-proof",
            input_ref=input_ref,
            input_sha256=hash_file(root / input_ref),
        )
        activation_path = root / ACTIVATION_PATH
        activation_path.parent.mkdir(parents=True, exist_ok=True)
        activation_path.write_bytes(canonical(activation))
        self._git(root, "add", ".")
        self._git(root, "commit", "-m", "add synthetic activation")
        return activation

    @staticmethod
    def _git(root: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
