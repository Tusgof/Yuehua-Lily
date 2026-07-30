from __future__ import annotations

import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from lib.l4_b86r13_contract_v15 import activation_content, canonical


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/l_4_breadth_b86r13_provisioning_gate_v15.json"
ACTIVATION = ROOT / "experiments/activation_records/l_4_breadth_b86r13_provisioning_activation_v15.json"
ACCEPTED = "42bfe3da3c58103317a71edb33bcd0d280b3017c"
CI_RUN = 30591744500


class B86R13ActivationCheckpointTests(unittest.TestCase):
    def test_checkpoint_is_gate_derived_canonical_and_committed(self) -> None:
        gate_raw = GATE.read_bytes()
        expected = canonical(activation_content(json.loads(gate_raw.decode("ascii")), gate_raw, accepted_gate_head_sha=ACCEPTED, hermetic_ci_run_id=CI_RUN))
        raw = ACTIVATION.read_bytes()
        head = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=ROOT, text=True).strip()
        committed = subprocess.check_output(("git", "show", f"{head}:{ACTIVATION.relative_to(ROOT).as_posix()}"), cwd=ROOT)
        self.assertEqual(expected, raw)
        self.assertFalse(raw.endswith(b"\n"))
        self.assertEqual(raw, committed)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), hashlib.sha256(committed).hexdigest())


if __name__ == "__main__":
    unittest.main()
