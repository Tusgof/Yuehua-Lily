"""Synthetic temporary-Git lifecycle and activation-binding tests for v6."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from lib.l4_b88r5_lifecycle_v6 import (
    GATE,
    PROVISIONED_IDENTITY,
    _identity_from_gate,
    build_activation,
    clean_checkout,
)

ROOT = Path(__file__).resolve().parents[1]


class B88R5V6Lifecycle(unittest.TestCase):
    def git(self, root: Path, *args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()

    def test_clean_checkout_rejects_tracked_dirty_and_untracked_temporary_git_states(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.email", "lily-e0@example.invalid")
            self.git(root, "config", "user.name", "Lily E0 fixture")
            tracked = root / "tracked.txt"
            tracked.write_text("clean\n", encoding="utf-8")
            self.git(root, "add", "tracked.txt")
            self.git(root, "commit", "-qm", "clean synthetic checkout")
            self.assertTrue(clean_checkout(root))

            tracked.write_text("dirty\n", encoding="utf-8")
            self.assertFalse(clean_checkout(root))
            tracked.write_text("clean\n", encoding="utf-8")
            self.assertTrue(clean_checkout(root))

            (root / "untracked.txt").write_text("untracked\n", encoding="utf-8")
            self.assertFalse(clean_checkout(root))
            (root / "untracked.txt").unlink()
            self.assertTrue(clean_checkout(root))

    def test_activation_builder_has_no_caller_supplied_identity_and_rejects_gate_drift(self):
        gate_raw = (ROOT / GATE).read_bytes()
        gate = json.loads(gate_raw.decode("ascii"))
        accepted = "a" * 40
        activation = build_activation(gate_raw=gate_raw, accepted_gate_head_sha=accepted, hermetic_ci_run_id=1)
        for key, value in PROVISIONED_IDENTITY.items():
            self.assertEqual(activation[key], value)

        mutated = copy.deepcopy(gate)
        mutated["provisioned_identity"]["container"]["path"] = "tests/fixtures/other.json"
        with self.assertRaises(ValueError):
            build_activation(gate_raw=json.dumps(mutated, separators=(",", ":")).encode("ascii"), accepted_gate_head_sha=accepted, hermetic_ci_run_id=1)

        mutated = copy.deepcopy(gate)
        mutated["provisioned_identity"]["u8_sessions"]["sha256"] = "0" * 64
        self.assertIsNone(_identity_from_gate(mutated))

    def test_bootstrap_and_direct_runtime_refuse_without_activation_without_outputs(self):
        bootstrap_spec = importlib.util.spec_from_file_location(
            "lily_b88r5_bootstrap", ROOT / "scripts/run_l_4_breadth_b88r5_committed_bootstrap_v6.py"
        )
        bootstrap = importlib.util.module_from_spec(bootstrap_spec)
        bootstrap_spec.loader.exec_module(bootstrap)
        checked = bootstrap.preflight(ROOT, self.git(ROOT, "rev-parse", "HEAD"))
        self.assertFalse(checked["ready"])
        self.assertIn(checked["outcome"], {"refused_execution_provenance", "dirty_checkout", "refused_activation"})
        self.assertFalse((ROOT / "experiments/activation_records/l_4_breadth_b88r5_scientific_execution_activation_v6.json").exists())
        self.assertFalse((ROOT / "reports/experiments/l_4_breadth_b88r5_one_shot_marker_v6.json").exists())

        runtime_spec = importlib.util.spec_from_file_location(
            "lily_b88r5_runtime", ROOT / "scripts/run_l_4_breadth_b88r5_scientific_execution_v6.py"
        )
        runtime = importlib.util.module_from_spec(runtime_spec)
        runtime_spec.loader.exec_module(runtime)
        with tempfile.TemporaryDirectory() as temporary:
            result = runtime.run_one_shot({}, root=Path(temporary))
            self.assertEqual(result["outcome"], "refused_preflight")
            self.assertFalse((Path(temporary) / "reports").exists())


if __name__ == "__main__":
    unittest.main()
