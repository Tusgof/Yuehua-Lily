from __future__ import annotations
import copy, tempfile, unittest
from pathlib import Path
from lib.io import load_json, write_json
from scripts.validate_l_2_falsification_capacity_gate_v2 import GATE, validate_gate
class Tests(unittest.TestCase):
    def test_gate_passes(self): self.assertEqual("pass", validate_gate()["status"])
    def test_locked_source_and_window_tampering_blocked(self):
        for mutate, expected in [
            (lambda p: p["falsification_window"].update(start="2015-12-31"), "locked_falsification_window_mismatch"),
            (lambda p: p["falsification_window"].update(end="2007-02-05"), "locked_falsification_window_mismatch"),
            (lambda p: p["locked_sources"].update(l1_baseline_path="does/not/exist.json"), "locked_source_mismatch:l1"),
            (lambda p: p["locked_sources"].update(l2_v2_sha256="0" * 64), "locked_source_mismatch:l2"),
            (lambda p: p["absolute_upper_bound"].update(fixed_research_asset_count=9), "absolute_upper_bound_mismatch"),
            (lambda p: p["absolute_upper_bound"].update(required_mintrl_falsify=1), "absolute_upper_bound_mismatch"),
            (lambda p: p.update(capacity_outcome="funded"), "field_mismatch:capacity_outcome"),
            (lambda p: p.update(execution_authorized=True), "field_mismatch:execution_authorized"),
        ]:
            payload = copy.deepcopy(load_json(GATE)); mutate(payload)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "gate.json"; write_json(path, payload); result = validate_gate(path, require_manifest=False)
            self.assertIn(expected, result["blockers"])
    def test_incomplete_hard_stops_blocked(self):
        payload = copy.deepcopy(load_json(GATE)); payload["hard_stops"] = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gate.json"; write_json(path, payload); result = validate_gate(path, require_manifest=False)
        self.assertIn("hard_stops_incomplete", result["blockers"])
if __name__ == "__main__": unittest.main()
