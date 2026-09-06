from __future__ import annotations

import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from lib.core_1e_b2_empirical_adapter_v2 import EXPENSE_INPUT_PATH, FIXTURE_PATH
from lib.core_1e_b2_lifecycle_v2 import (
    ACTIVATION_PATH,
    ADAPTER_PATH,
    EXPECTED_CONTAINER_IDENTITY,
    GATE_PATH,
    RUNTIME_PATHS,
    build_synthetic_activation,
    canonical,
    hash_file,
    preflight,
    run_synthetic_once,
    validate_activation,
)
from lib.io import load_json
from scripts.validate_core_1e_b2_empirical_report_v2 import (
    _expected,
    _validate_report_against_expected,
    validate_report,
)


ROOT = Path(__file__).resolve().parents[1]


class Core1EB2R1LifecycleTests(unittest.TestCase):
    def test_temporary_git_path_is_marker_first_one_shot_and_refuses_second_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            activation = self._install_activation(root)
            self.assertEqual("ready", preflight(root)["status"])

            first = run_synthetic_once(root)
            self.assertEqual("complete", first["status"])
            self.assertEqual(1, first["input_read_count"])
            self.assertEqual(1, first["expense_input_read_count"])
            self.assertGreater(first["return_values_decoded"], 0)
            report_path = root / activation["one_shot"]["report_path"]
            attempt_path = root / activation["one_shot"]["attempt_path"]
            marker_path = root / activation["one_shot"]["marker_path"]
            report_before = report_path.read_bytes()
            report = load_json(report_path)
            self.assertEqual("pass", validate_report(report_path, project_root=root)["status"])
            self.assertEqual("E0", report["evidence_tier"])
            self.assertEqual("none", report["edge_claim"])
            self.assertFalse(report["empirical_result_created"])
            self.assertEqual(1, load_json(marker_path)["completion_count"])
            self.assertEqual("completed", load_json(attempt_path)["status"])

            second = run_synthetic_once(root)
            self.assertEqual("refused_prior_invocation", second["outcome"])
            self.assertEqual(0, second["input_read_count"])
            self.assertEqual(report_before, report_path.read_bytes())

    def test_marker_is_written_before_first_input_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            activation = self._install_activation(root)
            marker_path = root / activation["one_shot"]["marker_path"]

            def reader(path: Path) -> bytes:
                self.assertTrue(marker_path.is_file())
                self.assertEqual(0, load_json(marker_path)["input_read_count"])
                return path.read_bytes()

            result = run_synthetic_once(
                root,
                input_reader=reader,
                report_builder=lambda _normalized, _activation: {"synthetic_test_report": True},
            )
            self.assertEqual("complete", result["status"])

    def test_dirty_checkout_is_blocked_before_input_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            self._install_activation(root)
            (root / "untracked.txt").write_text("synthetic only\n", encoding="utf-8")
            result = preflight(root)
            self.assertEqual("dirty_checkout", result["outcome"])
            self.assertEqual(0, result["input_read_count"])

    def test_activation_rejects_owner_ci_container_cutoff_and_runtime_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            activation = self._install_activation(root)
            head = self._head(root)
            cases = [
                ("owner_authorization_ref", "wrong-owner", "activation_owner_authorization_mismatch"),
                ("development_cutoff", "2016-01-04", "activation_development_cutoff_changed"),
                ("exact_ci_head_sha", "0" * 40, "activation_gate_ci_identity_mismatch"),
            ]
            for key, value, blocker in cases:
                changed = copy.deepcopy(activation)
                changed[key] = value
                self.assertIn(blocker, validate_activation(root, head, changed))

            forged_container = copy.deepcopy(activation)
            forged_container["container_identity"] = dict(EXPECTED_CONTAINER_IDENTITY, sha256="0" * 64)
            self.assertIn("activation_container_identity_mismatch", validate_activation(root, head, forged_container))

            forged_runtime = copy.deepcopy(activation)
            forged_runtime["runtime_bytes"][ADAPTER_PATH] = "0" * 64
            self.assertIn(
                f"activation_runtime_byte_mismatch:{ADAPTER_PATH}",
                validate_activation(root, head, forged_runtime),
            )

    def test_gate_and_runtime_drift_are_rejected_before_input_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            self._install_activation(root)
            gate_path = root / GATE_PATH
            gate_path.write_bytes(gate_path.read_bytes() + b"\n")
            self._git(root, "add", GATE_PATH)
            self._git(root, "commit", "-m", "drift gate")
            gate_result = preflight(root)
            self.assertEqual("activation_invalid", gate_result["outcome"])
            self.assertEqual(0, gate_result["input_read_count"])
            self.assertIn("activation_current_gate_blob_mismatch", gate_result["blockers"])

            with tempfile.TemporaryDirectory() as tmp2:
                root2 = Path(tmp2)
                self._seed_temp_repo(root2)
                self._install_activation(root2)
                runtime_path = root2 / ADAPTER_PATH
                runtime_path.write_bytes(runtime_path.read_bytes() + b"\n")
                self._git(root2, "add", ADAPTER_PATH)
                self._git(root2, "commit", "-m", "drift adapter")
                runtime_result = preflight(root2)
                self.assertEqual("activation_invalid", runtime_result["outcome"])
                self.assertEqual(0, runtime_result["input_read_count"])
                self.assertIn(
                    f"activation_current_runtime_byte_mismatch:{ADAPTER_PATH}",
                    runtime_result["blockers"],
                )

    def test_report_validator_rejects_unknown_forged_decisions_costs_turnover_and_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_temp_repo(root)
            activation = self._install_activation(root)
            self.assertEqual("complete", run_synthetic_once(root)["status"])
            report = load_json(root / activation["one_shot"]["report_path"])
            expected, schema = _expected(root)
            mutations: list[dict[str, object]] = []

            unknown = copy.deepcopy(report)
            unknown["unexpected"] = True
            mutations.append(unknown)

            forged_gates = copy.deepcopy(report)
            forged_gates["candidates"][0]["gates"] = {key: True for key in "ABCDEFGH"}
            forged_gates["candidates"][0]["all_gates_pass"] = True
            mutations.append(forged_gates)

            forged_cost = copy.deepcopy(report)
            forged_cost["candidates"][0]["costs"]["execution_cost_primary"] = 99.0
            mutations.append(forged_cost)

            forged_turnover = copy.deepcopy(report)
            forged_turnover["candidates"][0]["metrics"]["primary_net"]["one_way_turnover"] = 99.0
            mutations.append(forged_turnover)

            forged_selection = copy.deepcopy(report)
            forged_selection["selection"]["winner"] = "CORE1_DC60"
            mutations.append(forged_selection)

            for candidate in mutations:
                result = _validate_report_against_expected(candidate, expected, schema)
                self.assertEqual("blocked", result["status"])

    def _seed_temp_repo(self, root: Path) -> None:
        for relative in (GATE_PATH, *RUNTIME_PATHS, FIXTURE_PATH, EXPENSE_INPUT_PATH):
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        self._git(root, "init", "-b", "main")
        self._git(root, "config", "user.email", "synthetic@example.invalid")
        self._git(root, "config", "user.name", "Synthetic Test")
        self._git(root, "add", ".")
        self._git(root, "commit", "-m", "seed CORE-1E-B2-R1 synthetic runtime")

    def _install_activation(self, root: Path) -> dict[str, object]:
        base_commit = self._head(root)
        runtime = {relative: hash_file(root / relative) for relative in RUNTIME_PATHS}
        input_path = root / FIXTURE_PATH
        expense_path = root / EXPENSE_INPUT_PATH
        activation = build_synthetic_activation(
            gate_commit=base_commit,
            gate_sha256=hash_file(root / GATE_PATH),
            runtime_bytes=runtime,
            input_ref=FIXTURE_PATH,
            input_sha256=hash_file(input_path),
            input_size_bytes=input_path.stat().st_size,
            expense_input_sha256=hash_file(expense_path),
            expense_input_size_bytes=expense_path.stat().st_size,
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


if __name__ == "__main__":
    unittest.main()
