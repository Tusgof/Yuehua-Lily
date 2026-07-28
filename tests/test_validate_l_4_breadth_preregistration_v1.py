from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments" / "l_4_breadth_preregistration_v1.json"
SCRIPT = ROOT / "scripts" / "validate_l_4_breadth_preregistration_v1.py"


def _validator():
    spec = importlib.util.spec_from_file_location("validate_l4_breadth", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("validator import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class L4BreadthPreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = _validator()

    def test_current_gate_passes(self) -> None:
        self.assertEqual([], self.validator.validate_gate()["blockers"])

    def test_rejects_source_hash_and_universe_or_threshold_tampering(self) -> None:
        cases = [
            (lambda gate: gate["source_binding"]["l3_preregistration"].update(sha256="0" * 64), "source_declaration_mismatch:l3_preregistration"),
            (lambda gate: gate["universes"]["U8"].update(members=["VTI"]), "universe_order_or_nesting_mismatch"),
            (lambda gate: gate["non_tautology_gates"]["top_dependency"].update(useful_reduction_minimum=0.01), "non_tautology_gate_mismatch"),
        ]
        for mutate, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as directory:
                gate = json.loads(GATE.read_text(encoding="utf-8"))
                mutate(gate)
                path = Path(directory) / "gate.json"
                path.write_text(json.dumps(gate), encoding="utf-8")
                result = self.validator.validate_gate(path)
                self.assertIn(expected, result["blockers"])

    def test_rejects_open_authorization_and_snapshot_byte_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "project"
            for relative in (
                "experiments/l_1_baseline_preregistration.json",
                "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json",
                "research_log/010-lily-l3-corrected-rerun.md",
                "experiments/l_4_breadth_preregistration_v1.json",
            ):
                target = copied / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            shutil.copytree(ROOT / "methodology_snapshots" / "l4_breadth_v1", copied / "methodology_snapshots" / "l4_breadth_v1")
            gate_path = copied / "experiments/l_4_breadth_preregistration_v1.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            gate["authorizations"]["data"] = True
            gate_path.write_text(json.dumps(gate), encoding="utf-8")
            snapshot = copied / "methodology_snapshots/l4_breadth_v1/wiki/concepts/covariance-and-correlation.md"
            snapshot.write_bytes(b"forged snapshot bytes\n")
            blockers = self.validator.validate_gate(gate_path, project_root=copied)["blockers"]
        self.assertIn("authorizations_not_all_false", blockers)
        self.assertIn("methodology_snapshot_hash_mismatch:wiki/concepts/covariance-and-correlation.md", blockers)


if __name__ == "__main__":
    unittest.main()
