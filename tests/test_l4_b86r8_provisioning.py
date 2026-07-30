from __future__ import annotations
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import scripts.run_l_4_breadth_b86r8_provisioning_v10 as runner
import scripts.validate_l_4_breadth_b86r8_provisioning_report_v10 as report_validator
from scripts.validate_l_4_breadth_b86r8_provisioning_gate_v10 import validate as validate_gate


class B86R8Tests(unittest.TestCase):
    def prepare(self):
        temporary = tempfile.TemporaryDirectory(); root = Path(temporary.name); head = "b" * 40
        raws = {name: (name + "-bytes").encode("ascii") for name in runner.DEPENDENCY_PATHS}
        sources = {name: {"path": runner.DEPENDENCY_PATHS[name], "sha256": hashlib.sha256(raws[name]).hexdigest()} for name in runner.DEPENDENCY_PATHS if name != "gate"}
        raws["gate"] = json.dumps({"source_binding": sources}, sort_keys=True, separators=(",", ":")).encode("ascii")
        for name, path in runner.DEPENDENCY_PATHS.items():
            target = root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raws[name])
        activation = {"schema_version": runner.ACTIVATION_SCHEMA, "gate_id": runner.GATE_ID, "gate_sha256": hashlib.sha256(raws["gate"]).hexdigest(), "accepted_gate_head_sha": "a" * 40, "hermetic_ci_head_sha": "a" * 40, "hermetic_ci_run_id": 1, "inspector_decision": "ACCEPTED", "owner_authorization_reference": "B8.6R8 one-shot owner authorization", "scope": "one_repo_relative_falsification_container_provisioning_only", "validation_seal": runner.SEAL}
        activation_raw = runner.canonical(activation); target = root / runner.ACTIVATION; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(activation_raw)
        blobs = {path: raws[name] for name, path in runner.DEPENDENCY_PATHS.items()} | {runner.ACTIVATION: activation_raw}
        return temporary, root, head, raws, blobs

    def loader(self, blobs): return lambda commit, path: blobs.get(path) if commit == "b" * 40 else None

    def test_gate_is_strict_and_hash_bound(self): self.assertEqual("pass", validate_gate()["status"])

    def test_valid_temp_root_lifecycle_and_report_provenance_pass(self):
        temporary, root, _, _, blobs = self.prepare()
        with temporary:
            report = runner.run_one_shot(root=root, head="b" * 40, blob_loader=self.loader(blobs), gate_check=lambda *_: True)
            self.assertEqual("dataset_missing", report["blocker"]); self.assertTrue((root / runner.MARKER).exists())
            self.assertEqual("pass", report_validator.validate(report, root=root, blob_loader=self.loader(blobs), gate_check=lambda *_: True)["status"])
            self.assertEqual("refused_already_consumed", runner.run_one_shot(root=root, head="b" * 40, blob_loader=self.loader(blobs), gate_check=lambda *_: True)["outcome"])

    def test_dirty_execution_dependencies_fail_before_marker_or_read(self):
        for name in ("scanner", "runner", "contract"):
            temporary, root, _, raws, blobs = self.prepare()
            with temporary:
                (root / runner.DEPENDENCY_PATHS[name]).write_bytes(raws[name] + b"-dirty")
                result = runner.run_one_shot(root=root, head="b" * 40, blob_loader=self.loader(blobs), gate_check=lambda *_: True)
                self.assertEqual({"outcome": "refused_execution_provenance", "dataset_read_count": 0}, result)
                self.assertFalse((root / runner.MARKER).exists())

    def test_missing_blob_and_wrong_head_fail_before_marker_or_read(self):
        temporary, root, _, _, blobs = self.prepare()
        with temporary:
            missing = dict(blobs); missing.pop(runner.DEPENDENCY_PATHS["scanner"])
            self.assertEqual("refused_execution_provenance", runner.run_one_shot(root=root, head="b" * 40, blob_loader=self.loader(missing), gate_check=lambda *_: True)["outcome"])
            self.assertFalse((root / runner.MARKER).exists())
            self.assertEqual("refused_execution_provenance", runner.run_one_shot(root=root, head="c" * 40, blob_loader=self.loader(blobs), gate_check=lambda *_: True)["outcome"])

    def test_report_rejects_wrong_commit_and_contract_artifact_substitution(self):
        temporary, root, _, _, blobs = self.prepare()
        with temporary:
            report = runner.run_one_shot(root=root, head="b" * 40, blob_loader=self.loader(blobs), gate_check=lambda *_: True)
            forged = json.loads(json.dumps(report)); forged["producing_git_commit"] = "c" * 40
            self.assertEqual("blocked", report_validator.validate(forged, root=root, blob_loader=self.loader(blobs), gate_check=lambda *_: True)["status"])
            forged = json.loads(json.dumps(report)); forged["contract_artifacts"]["scanner"]["sha256"] = "a" * 64
            self.assertEqual("blocked", report_validator.validate(forged, root=root, blob_loader=self.loader(blobs), gate_check=lambda *_: True)["status"])

    def test_valid_synthetic_blocked_only_and_output_guards_hold(self):
        temporary, root, _, _, _ = self.prepare()
        with temporary:
            row = runner.artifact(); row["attempted_read_count"] = 1
            report = {"schema_version": runner.REPORT_SCHEMA, "order_id": "B8.6R8", "hypothesis_id": "L-4", "mode": "synthetic_fixture", "outcome": "provisioning_blocked", "blocker": "dataset_missing", "evidence_tier": "E0", "edge_claim": "none", "real_provisioning_consumed": False, "dataset_reference": runner.DATASET, "expected_dataset_sha256": runner.EXPECTED_DATASET_SHA256, "dataset_artifact": row, "contract_artifacts": runner.dependency_identities(root), "activation_provenance": None, "access_counters": {"return_value_decode_count": 0, "validation_access_count": 0}, "validation_seal": runner.SEAL, "producing_git_commit": "synthetic_fixture"}
            self.assertEqual("pass", report_validator.validate(report, root=root)["status"])
            report["outcome"] = "structural_provisioned"; self.assertEqual("blocked", report_validator.validate(report, root=root)["status"])
            manifest = {"schema_version": runner.MANIFEST_SCHEMA, "dataset_reference": runner.DATASET, "dataset_sha256": runner.EXPECTED_DATASET_SHA256, "dataset_byte_count": 1, "u8_members_in_order": list(runner.U8), "coverage_by_symbol": {symbol: {"start": "2015-12-31", "end": "2015-12-31", "row_count": 1} for symbol in runner.U8}, "session_count": 8, "max_session_date": "2015-12-31", "validation_seal": runner.SEAL}; payload = {"schema_version": runner.PAYLOAD_SCHEMA, "dataset_sha256": runner.EXPECTED_DATASET_SHA256, "u8_members_in_order": list(runner.U8), "session_dates_by_symbol": {symbol: ["2015-12-31"] for symbol in runner.U8}}
            self.assertTrue(runner.outputs_ok(manifest, payload)); payload["session_dates_by_symbol"]["VTI"] = ["2016-01-01"]; self.assertFalse(runner.outputs_ok(manifest, payload))

if __name__ == "__main__": unittest.main()
