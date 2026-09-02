from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lib.core_1e_b1_lifecycle_v1 import (
    ACTIVATION_PATH,
    GATE_PATH,
    RUNTIME_PATHS,
    EXPECTED_CONTAINER_IDENTITY,
    build_synthetic_activation,
    canonical,
    hash_file,
    preflight,
    run_synthetic_once,
    validate_activation,
)
from lib.core_1e_b1_synthetic_adapter_v1 import FIXTURE_PATH
from lib.io import load_json, write_json
from scripts.validate_core_1e_b1_development_execution_contract_v1 import validate_contract
from scripts.validate_core_1e_b1_synthetic_report_v1 import validate_report


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / FIXTURE_PATH
CONTRACT = ROOT / GATE_PATH
BOOTSTRAP = ROOT / "scripts" / "run_core_1e_b1_committed_bootstrap_v1.py"


class Core1EAB1SyntheticMachineryTests(unittest.TestCase):
    def test_contract_and_project_bootstrap_are_e0_deny_only(self) -> None:
        contract_result = validate_contract()
        self.assertEqual("pass", contract_result["status"])
        completed = subprocess.run(
            [sys.executable, str(BOOTSTRAP)], cwd=ROOT, text=True, capture_output=True, check=False
        )
        self.assertEqual(1, completed.returncode)
        payload = json.loads(completed.stdout)
        self.assertEqual("canonical_activation_absent", payload["outcome"])
        self.assertFalse(payload["data_accessed"])
        self.assertFalse(payload["real_data_accessed"])
        self.assertFalse(payload["validation_accessed"])
        self.assertEqual([], payload["paths_resolved"])
        self.assertFalse(payload["project_artifacts_created"])

    def test_clean_temporary_git_proves_marker_first_closed_world_report_and_no_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            activation = self._install_activation(root)
            self.assertEqual("ready", preflight(root)["status"])
            first = run_synthetic_once(root)
            self.assertEqual("complete", first["status"])
            self.assertEqual(1, first["input_read_count"])
            report_path = root / activation["one_shot"]["report_path"]
            self.assertEqual("pass", validate_report(report_path, project_root=root)["status"])
            second = run_synthetic_once(root)
            self.assertEqual("refused_prior_invocation", second["outcome"])
            self.assertEqual(0, second["input_read_count"])
            self.assertTrue((root / activation["one_shot"]["marker_path"]).is_file())
            self.assertTrue((root / activation["one_shot"]["attempt_path"]).is_file())
            self.assertTrue(report_path.is_file())

    def test_tampered_source_gate_activation_and_container_identity_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            activation = self._install_activation(root)
            head = self._head(root)

            source_path = root / RUNTIME_PATHS[1]
            source_path.write_bytes(source_path.read_bytes() + b"\n")
            self._git(root, "add", RUNTIME_PATHS[1])
            self._git(root, "commit", "-m", "tamper adapter source")
            self.assertIn(
                f"activation_current_runtime_byte_mismatch:{RUNTIME_PATHS[1]}",
                validate_activation(root, self._head(root), activation),
            )

            gate_path = root / GATE_PATH
            gate = load_json(gate_path)
            gate["owner_authorization_ref"] = "forged-owner"
            write_json(gate_path, gate)
            self._git(root, "add", GATE_PATH)
            self._git(root, "commit", "-m", "tamper gate")
            self.assertIn("activation_current_gate_blob_mismatch", validate_activation(root, self._head(root), activation))

            forged_activation = copy.deepcopy(activation)
            forged_activation["owner_authorization_ref"] = "forged-owner"
            self.assertIn("activation_owner_authorization_mismatch", validate_activation(root, head, forged_activation))
            forged_container = copy.deepcopy(activation)
            forged_container["container_identity"] = dict(EXPECTED_CONTAINER_IDENTITY, sha256="0" * 64)
            self.assertIn("activation_container_identity_mismatch", validate_activation(root, head, forged_container))

    def test_pre_decode_cutoff_and_validation_opening_are_rejected_without_input_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            activation = self._install_activation(root)
            cutoff = copy.deepcopy(activation)
            cutoff["development_cutoff"] = "2016-01-04"
            cutoff_result = preflight_with_activation(root, cutoff)
            self.assertEqual("activation_invalid", cutoff_result["outcome"])
            self.assertEqual(0, cutoff_result["input_read_count"])
            self.assertIn("activation_development_cutoff_changed", cutoff_result["blockers"])
            opening = copy.deepcopy(activation)
            opening["validation_boundary"]["accessed"] = True
            opening_result = preflight_with_activation(root, opening)
            self.assertEqual("activation_invalid", opening_result["outcome"])
            self.assertEqual(0, opening_result["input_read_count"])
            self.assertIn("activation_validation_boundary_changed", opening_result["blockers"])

    def test_forged_report_selection_and_contract_gates_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            activation = self._install_activation(root)
            self.assertEqual("complete", run_synthetic_once(root)["status"])
            report_path = root / activation["one_shot"]["report_path"]
            report = load_json(report_path)
            report["selection"]["winner"] = "CORE1_DC60"
            forged_report_path = root / "forged_report.json"
            write_json(forged_report_path, report)
            self.assertEqual("blocked", validate_report(forged_report_path, project_root=root)["status"])
            report_with_forged_gates = load_json(report_path)
            report_with_forged_gates["calculation_report"]["candidates"][0]["gates"] = {
                key: True for key in "ABCDEFGH"
            }
            forged_gates_path = root / "forged_gates_report.json"
            write_json(forged_gates_path, report_with_forged_gates)
            self.assertEqual("blocked", validate_report(forged_gates_path, project_root=root)["status"])

            contract = load_json(CONTRACT)
            contract["execution_boundaries"]["reject_on_or_after"] = "2015-12-31"
            forged_contract_path = root / "forged_contract.json"
            write_json(forged_contract_path, contract)
            self.assertEqual("blocked", validate_contract(forged_contract_path, project_root=root, verify_static=False)["status"])

    def test_dirty_and_untracked_checkout_is_blocked_before_input_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            self._install_activation(root)
            (root / "untracked.txt").write_text("untracked\n", encoding="utf-8")
            result = preflight(root)
            self.assertEqual("dirty_checkout", result["outcome"])
            self.assertEqual(0, result["input_read_count"])

    def _seed_temp_repo(self, root: Path) -> None:
        for relative in (GATE_PATH, *RUNTIME_PATHS, FIXTURE_PATH):
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        self._git(root, "init", "-b", "main")
        self._git(root, "config", "user.email", "synthetic@example.invalid")
        self._git(root, "config", "user.name", "Synthetic Test")
        self._git(root, "add", ".")
        self._git(root, "commit", "-m", "seed CORE-1E-B1 synthetic runtime")

    def _install_activation(self, root: Path) -> dict:
        base_commit = self._head(root)
        runtime = {relative: hash_file(root / relative) for relative in RUNTIME_PATHS}
        input_path = root / FIXTURE_PATH
        activation = build_synthetic_activation(
            gate_commit=base_commit,
            gate_sha256=hash_file(root / GATE_PATH),
            runtime_bytes=runtime,
            input_ref=FIXTURE_PATH,
            input_sha256=hash_file(input_path),
            input_size_bytes=input_path.stat().st_size,
        )
        activation_path = root / ACTIVATION_PATH
        activation_path.parent.mkdir(parents=True, exist_ok=True)
        activation_path.write_bytes(canonical(activation))
        self._git(root, "add", ACTIVATION_PATH)
        self._git(root, "commit", "-m", "install temporary synthetic activation")
        return activation

    @staticmethod
    def _head(root: Path) -> str:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True
        ).stdout.strip()

    @staticmethod
    def _git(root: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def preflight_with_activation(root: Path, activation: dict) -> dict:
    """Exercise activation validation without writing an activation artifact."""

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True
    ).stdout.strip()
    blockers = validate_activation(root, head, activation)
    return {
        "status": "blocked" if blockers else "ready",
        "outcome": "activation_invalid" if blockers else "canonical_activation_ready",
        "blockers": blockers,
        "input_read_count": 0,
    }


if __name__ == "__main__":
    unittest.main()
