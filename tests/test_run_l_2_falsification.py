from __future__ import annotations

import unittest

from scripts.run_l_2_falsification import ExecutionBlocked, load_execution_spec, run_falsification


class L2FalsificationRunnerTests(unittest.TestCase):
    def test_spec_uses_v2_inference_and_v3_time_index(self) -> None:
        spec = load_execution_spec()
        self.assertEqual("v2", spec["inference_source"])
        self.assertEqual("v3", spec["time_index_source"])
        self.assertIn("r[t-k]", spec["time_index_contract"]["shared_signal_information_set"])
        self.assertIn("paired daily net active-return", spec["primary_utility_and_inference"]["primary_utility"])

    def test_execution_is_blocked_before_any_data_loader_exists(self) -> None:
        with self.assertRaisesRegex(ExecutionBlocked, "b6_1_activation_gate_required"):
            run_falsification()


if __name__ == "__main__":
    unittest.main()
