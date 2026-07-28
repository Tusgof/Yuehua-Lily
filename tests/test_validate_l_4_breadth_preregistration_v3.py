from __future__ import annotations
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from scripts import validate_l_4_breadth_preregistration_v3 as validator

ROOT = Path(__file__).resolve().parents[1]

class L4BreadthV3Tests(unittest.TestCase):
    def _mutate(self, mutate):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in ("experiments/l_4_breadth_preregistration_v3.json", "experiments/l_4_breadth_preregistration_v2.json", "experiments/l_1_baseline_preregistration.json", "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json", "experiments/locked_gates.jsonl", "scripts/validate_l_4_breadth_preregistration_v2.py", "research_log/010-lily-l3-corrected-rerun.md"):
                target = root / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / relative, target)
            gate_path = root / "experiments/l_4_breadth_preregistration_v3.json"; payload = json.loads(gate_path.read_text(encoding="utf-8")); mutate(payload); gate_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return validator.validate_gate(gate_path, project_root=root)
    def test_current_gate_passes(self): self.assertEqual("pass", validator.validate_gate()["status"])
    def test_truth_table_is_exhaustive_and_precedence_is_fixed(self):
        self.assertEqual("scope_restricted", validator.classify_e1(non_evaluable=False, underfunded=True, ucb_breach=True, constraint_breach=False))
        self.assertEqual("falsified_E1_only", validator.classify_e1(non_evaluable=False, underfunded=False, ucb_breach=False, constraint_breach=True))
        self.assertEqual("not_falsified_not_validated_E1", validator.classify_e1(non_evaluable=False, underfunded=False, ucb_breach=False, constraint_breach=False))
        self.assertEqual("scope_restricted", validator.classify_validation(non_evaluable_or_underfunded=True, all_lcb_strictly_above=True, constraints_pass=True, integrity_pass=True))
    def test_adversarial_contract_drift_is_blocked(self):
        mutations = [lambda p: p["primary_sizing"].__setitem__("step_1", "u=q/volatility"), lambda p: p.pop("research_question"), lambda p: p.pop("inherited_controls"), lambda p: p["statistics"].__setitem__("extra", 1), lambda p: p["decision_contract"].__setitem__("e1_precedence", ["falsified_E1_only", "scope_restricted"]), lambda p: p["mandatory_metrics"]["n_eff_delta"]["falsify"].__setitem__("expected_mintrl", 48), lambda p: p["authorizations"].__setitem__("data", True), lambda p: p["source_binding"]["v2_predecessor"].__setitem__("gate_sha256", "0" * 64)]
        for mutate in mutations:
            with self.subTest(mutate=mutate): self.assertEqual("blocked", self._mutate(mutate)["status"])

if __name__ == "__main__": unittest.main()
