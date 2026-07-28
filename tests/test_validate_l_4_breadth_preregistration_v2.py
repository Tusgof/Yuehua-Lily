from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import validate_l_4_breadth_preregistration_v2 as validator


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/l_4_breadth_preregistration_v2.json"


class L4BreadthPreregistrationV2Tests(unittest.TestCase):
    def _copy_root(self) -> tuple[Path, Path, tempfile.TemporaryDirectory[str]]:
        temp = tempfile.TemporaryDirectory()
        copied = Path(temp.name)
        for relative in (
            "experiments/l_4_breadth_preregistration_v2.json", "experiments/l_4_breadth_preregistration_v1.json",
            "experiments/l_1_baseline_preregistration.json", "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json",
            "experiments/locked_gates.jsonl", "scripts/validate_l_4_breadth_preregistration_v1.py",
            "research_log/010-lily-l3-corrected-rerun.md",
        ):
            target = copied / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        shutil.copytree(ROOT / "methodology_snapshots/l4_breadth_v1", copied / "methodology_snapshots/l4_breadth_v1")
        return copied, copied / "experiments/l_4_breadth_preregistration_v2.json", temp

    def _mutated_result(self, mutate) -> dict[str, object]:
        copied, gate_path, temp = self._copy_root()
        with temp:
            payload = json.loads(gate_path.read_text(encoding="utf-8"))
            mutate(payload)
            gate_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return validator.validate_gate(gate_path, project_root=copied)

    def test_current_gate_passes(self) -> None:
        self.assertEqual("pass", validator.validate_gate()["status"])

    def test_inspector_mutations_and_closed_world_are_blocked(self) -> None:
        mutations = [
            lambda p: p["primary_metrics"]["n_eff_delta"].__setitem__("formula", "breadth always passes"),
            lambda p: p["primary_metrics"]["n_eff_delta"].__setitem__("formula", "Pearson labels without a window"),
            lambda p: p["statistics"].__setitem__("unexpected", "statistics field"),
            lambda p: p["timing_and_decisions"].__setitem__("validation_opened", True),
            lambda p: p["authorizations"].__setitem__("data", True),
            lambda p: p["universes"]["U1"].__setitem__("role", "primary_comparator"),
            lambda p: p["sizing"].__setitem__("primary_raw_score", "q / volatility"),
            lambda p: p["universes"].__setitem__("common_dates", "pairwise dates"),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.assertEqual("blocked", self._mutated_result(mutate)["status"])

    def test_component_independence_robustness_mintrl_and_regime_tampering_is_blocked(self) -> None:
        mutations = [
            lambda p: p["component_risk"].__setitem__("formula", "HHI = equal-weight asset count"),
            lambda p: p["primary_metrics"]["n_eff_delta"].__setitem__("useful_threshold", 0.0),
            lambda p: p["primary_metrics"]["n_eff_delta"].__setitem__("formula", "trailing 51 dates"),
            lambda p: p["robustness"]["best_market"].__setitem__("recalculation", "rerun strategy and choose removal"),
            lambda p: p["robustness"]["best_trend_episode"].__setitem__("selection", "search all alternatives"),
            lambda p: p["statistics"]["planning_mintrl"].__setitem__("n_eff_delta", 48),
            lambda p: p["regime_matrix"].__setitem__("no_pooling", "pool underfunded buckets"),
            lambda p: p["source_binding"]["b715_closure"].__setitem__("commit", "a30fb4425a3abac5ecb03051c8677618f34c03c8"),
            lambda p: p["source_binding"]["methodology_snapshot_hashes"].__setitem__(0, "0" * 64),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.assertEqual("blocked", self._mutated_result(mutate)["status"])


if __name__ == "__main__":
    unittest.main()
