from __future__ import annotations

import copy
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class B86R12V14ContractTests(unittest.TestCase):
    def bootstrap(self):
        return importlib.import_module("scripts.run_l_4_breadth_b86r12_committed_bootstrap_v14")

    def temporary_git(self, *, schema_mutation=False):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "repo"
        root.mkdir()
        bootstrap = self.bootstrap()
        for relative in bootstrap.DEPENDENCIES:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "lily-test@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Lily Test"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "v14 gate"], cwd=root, check=True)
        accepted = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        gate_raw = (root / bootstrap.GATE).read_bytes()
        gate = json.loads(gate_raw.decode("ascii"))
        contract = importlib.import_module("lib.l4_b86r12_contract_v14")
        activation = contract.activation_content(gate, gate_raw, accepted_gate_head_sha=accepted, hermetic_ci_run_id=1, owner_authorization_reference="synthetic activation")
        if schema_mutation:
            activation["schema_version"] = activation["schema_version"][:-1] + "X"
        target = root / bootstrap.ACTIVATION
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contract.canonical(activation))
        subprocess.run(["git", "add", bootstrap.ACTIVATION], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "synthetic activation"], cwd=root, check=True)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        return temporary, root, commit

    def synthetic_report(self):
        contract = importlib.import_module("lib.l4_b86r12_contract_v14")
        row = contract.artifact() | {"attempted_read_count": 1}
        return {"schema_version": contract.REPORT_SCHEMA, "order_id": "B8.6R12", "hypothesis_id": "L-4", "mode": "synthetic_fixture", "outcome": "provisioning_blocked", "evidence_tier": "E0", "edge_claim": "none", "real_provisioning_consumed": False, "dataset_reference": contract.DATASET, "expected_dataset_sha256": contract.EXPECTED_DATASET_SHA256, "dataset_artifact": row, "contract_artifacts": {}, "activation_provenance": None, "access_counters": {"return_value_decode_count": 0, "validation_access_count": 0}, "validation_seal": contract.SEAL, "producing_git_commit": "synthetic_fixture", "blocker": "dataset_missing"}

    def test_gate_and_synthetic_report_pass_and_forged_success_blocks(self):
        gate = importlib.import_module("scripts.validate_l_4_breadth_b86r12_provisioning_gate_v14")
        report = importlib.import_module("scripts.validate_l_4_breadth_b86r12_provisioning_report_v14")
        self.assertEqual("pass", gate.validate()["status"])
        self.assertEqual("pass", report.validate(self.synthetic_report())["status"])
        forged = self.synthetic_report()
        forged.update({"mode": "real_one_shot", "outcome": "structural_provisioned", "real_provisioning_consumed": True, "producing_git_commit": "a" * 40, "activation_provenance": {}, "manifest": {}, "payload": {}, "output_artifacts": {}, "structural_summary_sha256": "a" * 64})
        forged.pop("blocker")
        self.assertEqual("blocked", report.validate(forged)["status"])

    def test_matching_gate_derived_activation_reaches_preflight_ready_and_validator_agrees(self):
        temporary, root, commit = self.temporary_git()
        with temporary:
            checked = self.bootstrap().preflight(root, commit)
            self.assertTrue(checked["ready"])
            validator = importlib.import_module("scripts.validate_l_4_breadth_b86r12_provisioning_activation_v14")
            self.assertEqual("pass", validator.validate(root, commit)["status"])

    def test_one_character_schema_mismatch_blocks_preflight_and_validator(self):
        temporary, root, commit = self.temporary_git(schema_mutation=True)
        with temporary:
            self.assertEqual("refused_activation", self.bootstrap().preflight(root, commit)["outcome"])
            validator = importlib.import_module("scripts.validate_l_4_breadth_b86r12_provisioning_activation_v14")
            self.assertEqual("blocked", validator.validate(root, commit)["status"])

    def test_dirty_dependency_blocks_before_runtime_import_and_direct_runtime_refuses(self):
        temporary, root, commit = self.temporary_git()
        with temporary:
            runtime = root / "scripts/run_l_4_breadth_b86r12_provisioning_v14.py"
            self.assertEqual(2, subprocess.run([sys.executable, str(runtime)], cwd=root).returncode)
            dirty = root / "lib/l4_b86r12_contract_v14.py"
            dirty.write_bytes(dirty.read_bytes() + b"\n# dirty\n")
            checked = self.bootstrap().preflight(root, commit)
            self.assertEqual({"ready": False, "outcome": "refused_execution_provenance", "dataset_read_count": 0}, checked)


if __name__ == "__main__":
    unittest.main()
