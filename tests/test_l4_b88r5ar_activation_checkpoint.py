"""Canonical B8.8R5AR activation checkpoint tests."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib.draft202012_subset import ValidationError, validate as draft_validate
from lib.l4_b88r5_lifecycle_v6 import ACTIVATION, GATE, blob, build_activation, canonical
from scripts import run_l_4_breadth_b88r5_committed_bootstrap_v6 as bootstrap
from scripts import run_l_4_breadth_b88r5_scientific_execution_v6 as runtime
from scripts.validate_l_4_breadth_b88r5ar_activation_v6 import (
    ACCEPTED_GATE_HEAD_SHA,
    EXPECTED_ACTIVATION_SHA256,
    HERMETIC_CI_RUN_ID,
    SCHEMA,
    _static_blockers,
    validate,
)


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_COMMIT = "8f080d39dca04714f7a245e13e8a4d782875c7d9"


class B88R5ARActivationCheckpointTests(unittest.TestCase):
    def test_record_is_exact_gate_derived_ascii_no_lf_and_committed(self) -> None:
        gate_raw = (ROOT / GATE).read_bytes()
        expected = canonical(
            build_activation(
                gate_raw=gate_raw,
                accepted_gate_head_sha=ACCEPTED_GATE_HEAD_SHA,
                hermetic_ci_run_id=HERMETIC_CI_RUN_ID,
            )
        )
        raw = (ROOT / ACTIVATION).read_bytes()
        head = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=ROOT, text=True).strip()
        committed = subprocess.check_output(("git", "show", f"{head}:{ACTIVATION}"), cwd=ROOT)
        self.assertEqual(expected, raw)
        self.assertFalse(raw.endswith(b"\n"))
        self.assertEqual(EXPECTED_ACTIVATION_SHA256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(raw, committed)
        self.assertIsNone(blob(ROOT, CHECKPOINT_COMMIT, bootstrap.MARKER))

    def test_validator_runs_preflight_only_and_never_bootstrap_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkout = Path(temporary) / "checkpoint-checkout"
            subprocess.run(
                ["git", "worktree", "add", "--detach", str(checkout), CHECKPOINT_COMMIT],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            try:
                gate_resolution = bootstrap._gate_and_dependencies(checkout, CHECKPOINT_COMMIT)
                self.assertIsNotNone(gate_resolution)
                _, _, dependency_identities = gate_resolution
                activation = json.loads(blob(checkout, CHECKPOINT_COMMIT, ACTIVATION).decode("ascii"))
                historical_ready = {
                    "ready": True,
                    "status": "ready",
                    "outcome": "preflight_ready",
                    "activation": activation,
                    "producing_commit": CHECKPOINT_COMMIT,
                    "runtime_dependency_identities": dependency_identities,
                    "real_accessed": False,
                }
                with (
                    patch.object(bootstrap, "preflight", return_value=historical_ready) as preflight,
                    patch.object(bootstrap, "run", side_effect=AssertionError("bootstrap run must not be called")) as bootstrap_run,
                    patch.object(runtime, "run_one_shot", side_effect=AssertionError("runtime must not be called")) as runtime_run,
                ):
                    result = validate(checkout, producing_commit=CHECKPOINT_COMMIT)
            finally:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", str(checkout)],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
        self.assertEqual("pass", result["status"], result)
        self.assertEqual("preflight_ready", result["preflight_outcome"])
        self.assertFalse(result["real_accessed"])
        preflight.assert_called_once_with(checkout, CHECKPOINT_COMMIT)
        bootstrap_run.assert_not_called()
        runtime_run.assert_not_called()

    def test_schema_rejects_unknown_field_and_static_check_rejects_noncanonical_equivalent(self) -> None:
        schema = json.loads((ROOT / SCHEMA).read_text(encoding="ascii"))
        value = json.loads((ROOT / ACTIVATION).read_text(encoding="ascii"))
        forged = dict(value)
        forged["unexpected"] = True
        with self.assertRaises(ValidationError):
            draft_validate(schema, forged)
        gate_raw = (ROOT / GATE).read_bytes()
        self.assertIn(
            "schema_mismatch",
            _static_blockers(canonical(forged), schema, gate_raw),
        )
        self.assertIn(
            "noncanonical_activation_bytes",
            _static_blockers(canonical(value) + b"\n", schema, gate_raw),
        )


if __name__ == "__main__":
    unittest.main()
