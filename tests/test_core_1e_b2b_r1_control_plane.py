import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from lib.core_1e_b2b_r1_control_plane import (
    ActivationRefused,
    AdmissionRefused,
    ControlSpec,
    DirtyCheckoutRefused,
    SecondInvocationRefused,
    execute_once,
)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", "-C", str(root), *args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        text=True,
    )
    return result.stdout.strip()


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


@contextmanager
def _synthetic_repo(
    allowed: tuple[str, ...] = (),
    closed_world: dict | None = None,
    *,
    gitignore: bytes | None = None,
    activation_path: str = "activation.json",
):
    with tempfile.TemporaryDirectory(prefix="core-1e-b2b-r1-") as directory:
        root = Path(directory)
        _git(root, "init", "--quiet")
        _git(root, "config", "user.email", "cp1@example.invalid")
        _git(root, "config", "user.name", "CP1 synthetic test")
        gate = b'{"control_gate":"synthetic-v1"}\n'
        runtime = b"synthetic runtime bytes\n"
        _write(root / "gate.json", gate)
        _write(root / "runtime.bin", runtime)
        if gitignore is not None:
            _write(root / ".gitignore", gitignore)
        _git(root, "add", "gate.json", "runtime.bin")
        if gitignore is not None:
            _git(root, "add", ".gitignore")
        _git(root, "commit", "--quiet", "-m", "synthetic provenance")
        source_commit = _git(root, "rev-parse", "HEAD")
        gate_hash = hashlib.sha256(gate).hexdigest()
        runtime_hash = hashlib.sha256(runtime).hexdigest()
        control = closed_world or {"scope": "control-only", "fixture": "synthetic"}
        activation = {
            "schema": "lily_core_1e_b2b_r1_activation_v1",
            "activation_id": "synthetic-cp1",
            "source_commit": source_commit,
            "gate": {"path": "gate.json", "sha256": gate_hash},
            "runtime": [{"path": "runtime.bin", "sha256": runtime_hash}],
            "control_spec": control,
        }
        activation_bytes = json.dumps(
            activation, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        activation_file = root.joinpath(*activation_path.split("/"))
        _write(activation_file, activation_bytes)
        _git(root, "add", activation_path)
        _git(root, "commit", "--quiet", "-m", "synthetic activation")
        spec = ControlSpec(
            repo_root=root,
            activation_path=activation_path,
            expected_activation_sha256=hashlib.sha256(activation_bytes).hexdigest(),
            source_commit=source_commit,
            gate_path="gate.json",
            expected_gate_sha256=gate_hash,
            runtime_paths=("runtime.bin",),
            expected_runtime_sha256=(runtime_hash,),
            marker_path="marker.json",
            allowed_untracked_paths=allowed,
            closed_world=control,
        )
        yield root, spec


def _marker(root: Path) -> dict:
    return json.loads((root / "marker.json").read_text(encoding="utf-8"))


class ControlPlaneTests(unittest.TestCase):
    def test_valid_run_claims_before_callbacks_and_completes_once(self) -> None:
        with _synthetic_repo() as (root, spec):
            observations: list[tuple[str, str, int]] = []

            def resolver(admission):
                state = _marker(root)
                observations.append(("resolver", state["state"], state["completion_count"]))
                return admission

            def operation(admission):
                state = _marker(root)
                observations.append(("operation", state["state"], state["completion_count"]))
                return "synthetic-success"

            self.assertEqual(execute_once(spec, resolver, operation), "synthetic-success")
            self.assertEqual(
                observations,
                [("resolver", "claimed", 0), ("operation", "claimed", 0)],
            )
            self.assertEqual(_marker(root)["state"], "completed")
            self.assertEqual(_marker(root)["completion_count"], 1)

    def test_failure_is_terminal_and_consumes_one_shot(self) -> None:
        with _synthetic_repo() as (root, spec):
            calls = 0

            def resolver(admission):
                return admission

            def failing_operation(_):
                nonlocal calls
                calls += 1
                raise ValueError("synthetic callback failure")

            with self.assertRaises(ValueError):
                execute_once(spec, resolver, failing_operation)
            failed = _marker(root)
            self.assertEqual(failed["state"], "failed")
            self.assertEqual(failed["completion_count"], 1)
            self.assertEqual(failed["error_type"], "ValueError")

            with self.assertRaises(SecondInvocationRefused):
                execute_once(spec, resolver, failing_operation)
            self.assertEqual(calls, 1)

    def test_missing_activation_refuses_before_injected_callbacks(self) -> None:
        with _synthetic_repo() as (root, spec):
            root.joinpath("activation.json").unlink()
            calls = []

            def resolver(_):
                calls.append("resolver")
                return None

            def operation(_):
                calls.append("operation")
                return None

            with self.assertRaises(AdmissionRefused):
                execute_once(spec, resolver, operation)
            self.assertEqual(calls, [])
            self.assertFalse(root.joinpath("marker.json").exists())

    def test_exact_allowlisted_untracked_path_passes(self) -> None:
        with _synthetic_repo(
            allowed=("data/allowed.bin",), gitignore=b"data/\n"
        ) as (root, spec):
            _write(root / "data/allowed.bin", b"synthetic opaque input\n")
            self.assertEqual(execute_once(spec, lambda _: None, lambda _: "ok"), "ok")

    def test_ignored_sibling_is_not_allowed_by_ignored_directory(self) -> None:
        with _synthetic_repo(
            allowed=("data/allowed.bin",), gitignore=b"data/\n"
        ) as (root, spec):
            _write(root / "data/allowed.bin", b"synthetic opaque input\n")
            _write(root / "data/sibling.bin", b"not allowlisted\n")
            with self.assertRaises(DirtyCheckoutRefused):
                execute_once(spec, lambda _: None, lambda _: None)

    def test_other_untracked_path_fails_even_with_allowed_data(self) -> None:
        with _synthetic_repo(allowed=("data/allowed.bin",)) as (root, spec):
            _write(root / "data/allowed.bin", b"synthetic opaque input\n")
            _write(root / "other.bin", b"not allowlisted\n")
            with self.assertRaises(DirtyCheckoutRefused):
                execute_once(spec, lambda _: None, lambda _: None)

    def test_tracked_modification_fails_clean_checkout_guard(self) -> None:
        with _synthetic_repo() as (root, spec):
            _write(root / "gate.json", b"changed synthetic gate\n")
            with self.assertRaises(DirtyCheckoutRefused):
                execute_once(spec, lambda _: None, lambda _: None)

    def test_activation_gate_and_runtime_drift_refuse_before_operation(self) -> None:
        cases = {
            "activation": ("activation.json", b"tampered activation\n"),
            "gate": ("gate.json", b"tampered gate\n"),
            "runtime": ("runtime.bin", b"tampered runtime\n"),
        }
        for name, (path, content) in cases.items():
            with self.subTest(name=name), _synthetic_repo() as (root, spec):
                _write(root / path, content)
                _git(root, "add", path)
                _git(root, "commit", "--quiet", "-m", f"drift {name}")
                calls = []
                with self.assertRaises(ActivationRefused):
                    execute_once(
                        spec,
                        lambda _: calls.append("resolver"),
                        lambda _: calls.append("operation"),
                    )
                self.assertEqual(calls, [])
                self.assertFalse(root.joinpath("marker.json").exists())

    def test_closed_world_spec_is_caller_bound(self) -> None:
        with _synthetic_repo(closed_world={"scope": "caller-a"}) as (root, spec):
            altered = ControlSpec(
                repo_root=spec.repo_root,
                activation_path=spec.activation_path,
                expected_activation_sha256=spec.expected_activation_sha256,
                source_commit=spec.source_commit,
                gate_path=spec.gate_path,
                expected_gate_sha256=spec.expected_gate_sha256,
                runtime_paths=spec.runtime_paths,
                expected_runtime_sha256=spec.expected_runtime_sha256,
                marker_path=spec.marker_path,
                closed_world={"scope": "caller-b"},
            )
            with self.assertRaises(ActivationRefused):
                execute_once(altered, lambda _: None, lambda _: None)
            self.assertFalse(root.joinpath("marker.json").exists())

    def test_second_invocation_refuses_before_callbacks(self) -> None:
        with _synthetic_repo() as (root, spec):
            execute_once(spec, lambda _: None, lambda _: None)
            calls = []
            with self.assertRaises(SecondInvocationRefused):
                execute_once(
                    spec,
                    lambda _: calls.append("resolver"),
                    lambda _: calls.append("operation"),
                )
            self.assertEqual(calls, [])
            self.assertEqual(_marker(root)["completion_count"], 1)

    def test_initial_marker_directory_sync_precedes_callbacks(self) -> None:
        with _synthetic_repo() as (root, spec):
            events: list[tuple[str, str]] = []

            def sync(directory: str) -> None:
                events.append(("sync", _marker(root)["state"]))
                self.assertEqual(Path(directory), root)

            def resolver(admission):
                events.append(("resolver", _marker(root)["state"]))
                return admission

            def operation(admission):
                events.append(("operation", _marker(root)["state"]))
                return admission

            with patch(
                "lib.core_1e_b2b_r1_control_plane._fsync_directory",
                side_effect=sync,
            ):
                execute_once(spec, resolver, operation)
            self.assertEqual(
                events,
                [
                    ("sync", "claimed"),
                    ("resolver", "claimed"),
                    ("operation", "claimed"),
                    ("sync", "completed"),
                ],
            )

    def test_symlinked_activation_parent_refuses_before_activation_read(self) -> None:
        with _synthetic_repo(activation_path="nested/activation.json") as (root, spec):
            parent = root / "nested"
            redirected = root / "redirected"
            redirected.mkdir()
            _write(redirected / "activation.json", (parent / "activation.json").read_bytes())
            (parent / "activation.json").unlink()
            parent.rmdir()
            try:
                os.symlink(redirected, parent, target_is_directory=True)
            except OSError as error:
                if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                    self.skipTest("Windows symlink privilege is unavailable")
                raise
            calls: list[str] = []
            with self.assertRaises(ActivationRefused):
                execute_once(
                    spec,
                    lambda _: calls.append("resolver"),
                    lambda _: calls.append("operation"),
                )
            self.assertEqual(calls, [])
            self.assertFalse(root.joinpath("marker.json").exists())


if __name__ == "__main__":
    unittest.main()
