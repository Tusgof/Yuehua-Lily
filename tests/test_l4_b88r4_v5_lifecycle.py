"""E0-only, temporary-Git proof for B8.8R4/v5's future lifecycle."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = "experiments/l_4_breadth_b88r4_phase_a_execution_contract_v5.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b88r4_scientific_execution_activation_v5.json"
BOOTSTRAP = "scripts/run_l_4_breadth_b88r4_committed_bootstrap_v5.py"
REPORT = "reports/experiments/l_4_breadth_b88r4_scientific_report_v5.json"
VALIDATOR = "scripts/validate_l_4_breadth_b88r4_scientific_report_v5.py"
MARKER = "reports/experiments/l_4_breadth_b88r4_one_shot_marker_v5.json"
U8 = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def synthetic_container(days: int = 430) -> dict:
    sessions: list[str] = []
    cursor = date(2013, 1, 2)
    while len(sessions) < days:
        if cursor.weekday() < 5:
            sessions.append(cursor.isoformat())
        cursor += timedelta(days=1)
    returns = {symbol: [((index * (asset + 3) + index * index * (asset + 1)) % 17 - 8) / 1000 for index in range(days)] for asset, symbol in enumerate(U8)}
    return {"schema_version": "lily_l4_normalized_container_v1", "cutoff_inclusive": "2015-12-31", "universe": list(U8), "sessions": sessions, "returns": returns, "cash_returns": [.00001] * days}


class B88R4V5Lifecycle(unittest.TestCase):
    def copy_runtime_tree(self, root: Path) -> dict:
        gate = json.loads((ROOT / GATE).read_text("ascii"))
        paths = set(gate["sources"]) | set(gate["execution_dependencies"]) | {"lib/__init__.py"}
        for relative in paths:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        return gate

    def git(self, root: Path, *args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()

    def write_gate(self, root: Path, gate: dict) -> None:
        gate["sources"] = {path: digest((root / path).read_bytes()) for path in gate["sources"]}
        gate["execution_binding"] = {path: {"path": path, "sha256": digest((root / path).read_bytes())} for path in gate["execution_dependencies"]}
        (root / GATE).write_bytes(canonical(gate))

    def make_activated_repo(self, root: Path) -> tuple[Path, dict]:
        gate = self.copy_runtime_tree(root)
        self.write_gate(root, gate)
        self.git(root, "init", "-q")
        self.git(root, "config", "user.email", "lily-e0@example.invalid")
        self.git(root, "config", "user.name", "Lily E0 fixture")
        self.git(root, "add", ".")
        self.git(root, "commit", "-qm", "temporary accepted v5 gate")
        accepted = self.git(root, "rev-parse", "HEAD")

        container = synthetic_container()
        container_path = "tests/fixtures/l4_b88r4_v5/synthetic_normalized_container.json"
        manifest_path = "tests/fixtures/l4_b88r4_v5/synthetic_structural_manifest.json"
        (root / container_path).parent.mkdir(parents=True, exist_ok=True)
        raw_container = canonical(container)
        (root / container_path).write_bytes(raw_container)
        (root / manifest_path).write_bytes(canonical({"schema_version": "lily_l4_b88r4_synthetic_manifest_v1", "dataset_reference": container_path, "dataset_sha256": digest(raw_container), "max_session_date": "2015-12-31", "u8_members_in_order": list(U8), "validation_seal": {"status": "sealed_not_accessed", "accessed": False}}))
        gate_raw = (root / GATE).read_bytes()
        activation = {"schema_version": "lily_l4_b88r4_activation_v5", "gate_id": "l_4_breadth_b88r4_phase_a_execution_contract_v5", "gate_sha256": digest(gate_raw), "owner_literal": "continue the work till we complete L4", "accepted_gate_head_sha": accepted, "hermetic_ci_head_sha": accepted, "hermetic_ci_run_id": 1, "inspector_decision": "ACCEPTED", "container_path": container_path, "container_sha256": digest(raw_container), "structural_manifest_path": manifest_path, "structural_manifest_sha256": digest((root / manifest_path).read_bytes()), "u8_sessions_sha256": digest(canonical(container["sessions"])), "cutoff_inclusive": "2015-12-31", "marker_path": MARKER, "validation_seal": {"status": "sealed_not_accessed", "accessed": False}}
        activation_path = root / ACTIVATION
        activation_path.parent.mkdir(parents=True, exist_ok=True)
        activation_path.write_bytes(canonical(activation))
        self.git(root, "add", ".")
        self.git(root, "commit", "-qm", "temporary canonical activation")
        return root, activation

    def run_cli(self, root: Path, relative: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, relative, *args], cwd=root, capture_output=True, text=True, check=False)

    def assert_rejected_after(self, root: Path, mutate) -> None:
        report_path = root / REPORT
        original = report_path.read_bytes()
        report = json.loads(original.decode("ascii"))
        mutate(report, root)
        report_path.write_bytes(canonical(report))
        checked = self.run_cli(root, VALIDATOR, REPORT, "--container", report["provenance"]["container_path"])
        self.assertNotEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        report_path.write_bytes(original)

    def test_clean_git_activation_runs_once_and_rejects_provenance_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, activation = self.make_activated_repo(Path(temporary))
            first = self.run_cli(root, BOOTSTRAP)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(json.loads(first.stdout)["status"], "complete")
            for relative in (REPORT, MARKER, "reports/experiments/l_4_breadth_b88r4_execution_ledger_v5.json", "reports/experiments/l_4_breadth_b88r4_execution_attempt_v5.json"):
                self.assertTrue((root / relative).is_file(), relative)
            checked = self.run_cli(root, VALIDATOR, REPORT, "--container", activation["container_path"])
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            second = self.run_cli(root, BOOTSTRAP)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(json.loads(second.stdout)["outcome"], "refused_prior_invocation")

            def set_value(path, value):
                def change(report, _root):
                    target = report
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = value
                return change

            checks = [
                set_value(("provenance", "producing_commit"), "0" * 40),
                set_value(("provenance", "accepted_gate_head_sha"), "0" * 40),
                set_value(("provenance", "hermetic_ci_head_sha"), "0" * 40),
                set_value(("provenance", "hermetic_ci_run_id"), 2),
                set_value(("provenance", "marker_path"), "reports/experiments/forged_marker.json"),
                set_value(("provenance", "marker_sha256"), "0" * 64),
                set_value(("provenance", "structural_manifest_sha256"), "0" * 64),
                set_value(("provenance", "u8_sessions_sha256"), "0" * 64),
                set_value(("provenance", "container_sha256"), "0" * 64),
                set_value(("provenance", "runtime_dependency_identities", "lib/l4_b88r4_scientific_engine_v5.py"), "0" * 64),
                set_value(("access_counts", "real_container_read_hash_scan_count"), 0),
            ]
            for change in checks:
                self.assert_rejected_after(root, change)
            self.assert_rejected_after(root, lambda report, _root: report.__setitem__("unexpected", True))

            activation_path = root / ACTIVATION
            original_activation = activation_path.read_bytes()
            activation_path.write_bytes(original_activation + b" ")
            self.assertNotEqual(self.run_cli(root, VALIDATOR, REPORT, "--container", activation["container_path"]).returncode, 0)
            activation_path.write_bytes(original_activation)
            marker_path = root / MARKER
            original_marker = marker_path.read_bytes()
            marker_path.write_bytes(original_marker + b" ")
            self.assertNotEqual(self.run_cli(root, VALIDATOR, REPORT, "--container", activation["container_path"]).returncode, 0)
            marker_path.write_bytes(original_marker)


if __name__ == "__main__":
    unittest.main()
