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


class B86R13V15Tests(unittest.TestCase):
    def bootstrap(self):
        return importlib.import_module("scripts.run_l_4_breadth_b86r13_committed_bootstrap_v15")

    def temporary_git(self, mutate=None):
        temporary = tempfile.TemporaryDirectory(); root = Path(temporary.name) / "repo"; root.mkdir(); boot = self.bootstrap()
        for relative in boot.DEPENDENCIES:
            target = root / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / relative, target)
        for args in (("git", "init", "-q"), ("git", "config", "user.email", "lily-test@example.invalid"), ("git", "config", "user.name", "Lily Test"), ("git", "add", "."), ("git", "commit", "-qm", "v15 gate")):
            subprocess.run(args, cwd=root, check=True)
        accepted = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True).strip(); raw = (root / boot.GATE).read_bytes(); gate = json.loads(raw); contract = importlib.import_module("lib.l4_b86r13_contract_v15"); activation = contract.activation_content(gate, raw, accepted_gate_head_sha=accepted, hermetic_ci_run_id=1)
        if mutate: mutate(activation)
        target = root / boot.ACTIVATION; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(contract.canonical(activation)); subprocess.run(("git", "add", boot.ACTIVATION), cwd=root, check=True); subprocess.run(("git", "commit", "-qm", "synthetic activation"), cwd=root, check=True)
        return temporary, root, subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True).strip()

    def synthetic_report(self):
        contract = importlib.import_module("lib.l4_b86r13_contract_v15"); return {"schema_version": contract.REPORT_SCHEMA, "order_id": "B8.6R13", "hypothesis_id": "L-4", "mode": "synthetic_fixture", "outcome": "provisioning_blocked", "evidence_tier": "E0", "edge_claim": "none", "real_provisioning_consumed": False, "dataset_reference": contract.DATASET, "expected_dataset_sha256": contract.EXPECTED_DATASET_SHA256, "dataset_artifact": contract.artifact() | {"attempted_read_count": 1}, "contract_artifacts": {}, "activation_provenance": None, "access_counters": {"return_value_decode_count": 0, "validation_access_count": 0}, "validation_seal": contract.SEAL, "producing_git_commit": "synthetic_fixture", "blocker": "dataset_missing"}

    def test_matching_temp_git_activation_reaches_actual_preflight(self):
        temporary, root, commit = self.temporary_git()
        with temporary:
            self.assertTrue(self.bootstrap().preflight(root, commit)["ready"])
            validator = importlib.import_module("scripts.validate_l_4_breadth_b86r13_provisioning_activation_v15")
            self.assertEqual("pass", validator.validate(root, commit)["status"])

    def test_schema_and_owner_mismatches_block(self):
        cases = (lambda value: value.__setitem__("schema_version", value["schema_version"] + "x"), lambda value: value.__setitem__("owner_authorization_reference", value["owner_authorization_reference"] + "x"), lambda value: value.__setitem__("owner_authorization_reference", None), lambda value: value.__setitem__("owner_authorization_reference", "arbitrary owner authorization"))
        validator = importlib.import_module("scripts.validate_l_4_breadth_b86r13_provisioning_activation_v15")
        for mutation in cases:
            temporary, root, commit = self.temporary_git(mutation)
            with temporary:
                self.assertEqual("refused_activation", self.bootstrap().preflight(root, commit)["outcome"])
                self.assertEqual("blocked", validator.validate(root, commit)["status"])

    def test_dirty_activation_and_dependency_block(self):
        temporary, root, commit = self.temporary_git()
        with temporary:
            boot = self.bootstrap(); validator = importlib.import_module("scripts.validate_l_4_breadth_b86r13_provisioning_activation_v15")
            activation = root / boot.ACTIVATION; activation.write_bytes(activation.read_bytes() + b" ")
            self.assertEqual("refused_activation", boot.preflight(root, commit)["outcome"]); self.assertEqual("blocked", validator.validate(root, commit)["status"])
        temporary, root, commit = self.temporary_git()
        with temporary:
            (root / "lib/l4_b86r13_contract_v15.py").write_bytes((root / "lib/l4_b86r13_contract_v15.py").read_bytes() + b"\n# dirty\n")
            self.assertEqual("refused_execution_provenance", self.bootstrap().preflight(root, commit)["outcome"])

    def test_gate_report_outputs_and_direct_runtime_are_closed_world(self):
        gate = importlib.import_module("scripts.validate_l_4_breadth_b86r13_provisioning_gate_v15"); report = importlib.import_module("scripts.validate_l_4_breadth_b86r13_provisioning_report_v15"); contract = importlib.import_module("lib.l4_b86r13_contract_v15")
        self.assertEqual("pass", gate.validate()["status"]); self.assertEqual("pass", report.validate(self.synthetic_report())["status"])
        unknown = self.synthetic_report(); unknown["unknown"] = True; self.assertEqual("blocked", report.validate(unknown)["status"])
        forged = self.synthetic_report(); forged.update({"mode": "real_one_shot", "outcome": "structural_provisioned", "real_provisioning_consumed": True, "producing_git_commit": "a" * 40, "activation_provenance": {}, "manifest": {}, "payload": {}, "output_artifacts": {}, "structural_summary_sha256": "a" * 64}); forged.pop("blocker"); self.assertEqual("blocked", report.validate(forged)["status"])
        bad_manifest = {"schema_version": "lily_l4_b86r13_falsification_manifest_v15", "dataset_reference": contract.DATASET, "dataset_sha256": contract.EXPECTED_DATASET_SHA256, "dataset_byte_count": 1, "u8_members_in_order": list(contract.U8), "coverage_by_symbol": {symbol: {"start": "2015-12-31", "end": "2015-12-31", "row_count": 1} for symbol in contract.U8}, "session_count": 8, "max_session_date": "2016-01-01", "validation_seal": contract.SEAL}; payload = {"schema_version": "lily_l4_b86r13_u8_session_dates_v15", "dataset_sha256": contract.EXPECTED_DATASET_SHA256, "u8_members_in_order": list(contract.U8), "session_dates_by_symbol": {symbol: ["2015-12-31"] for symbol in contract.U8}}
        self.assertFalse(contract.outputs_ok(bad_manifest, payload)); self.assertEqual(2, subprocess.run((sys.executable, str(ROOT / "scripts/run_l_4_breadth_b86r13_provisioning_v15.py"))).returncode)


if __name__ == "__main__": unittest.main()
