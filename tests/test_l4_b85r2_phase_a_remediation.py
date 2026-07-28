from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_4_breadth_b85r2_phase_a_activation_order_v3 import GATE, validate


class B85R2PhaseARemediationTests(unittest.TestCase):
    def test_gate_passes(self) -> None:
        self.assertEqual("pass", validate()["status"])

    def test_gate_blocks_open_resolution_or_unbound_implementation(self) -> None:
        mutations = (
            lambda payload: payload["future_phase_b_contract"].__setitem__("storage_root_variable", "OTHER"),
            lambda payload: payload["future_phase_b_contract"].__setitem__("one_shot_real_preflight_maximum", 2),
            lambda payload: payload["implementation"]["scanner"].__setitem__("sha256", "0" * 64),
            lambda payload: payload["phase_a_authorizations"].__setitem__("environment", True),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                payload = json.loads(GATE.read_text(encoding="utf-8"))
                mutate(payload)
                with tempfile.TemporaryDirectory() as temporary:
                    path = Path(temporary) / "gate.json"
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    self.assertEqual("blocked", validate(path)["status"])


if __name__ == "__main__":
    unittest.main()
