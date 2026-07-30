from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.run_l_4_breadth_b86r7_provisioning_v9 as runner
import scripts.validate_l_4_breadth_b86r7_provisioning_report_v9 as report_validator
from scripts.validate_l_4_breadth_b86r7_provisioning_gate_v9 import validate as validate_gate


class B86R7Tests(unittest.TestCase):
    def activation(self, gate_sha):
        return {
            "schema_version": runner.ACTIVATION_SCHEMA, "gate_id": runner.GATE_ID, "gate_sha256": gate_sha,
            "accepted_gate_head_sha": "a" * 40, "hermetic_ci_head_sha": "a" * 40, "hermetic_ci_run_id": 1,
            "inspector_decision": "ACCEPTED", "owner_authorization_reference": "B8.6R7 one-shot owner authorization",
            "scope": "one_repo_relative_falsification_container_provisioning_only", "validation_seal": runner.SEAL,
        }

    def test_gate_is_hash_bound(self):
        self.assertEqual("pass", validate_gate()["status"])

    def test_invalid_activation_has_zero_marker_and_zero_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); activation = root / runner.ACTIVATION
            activation.parent.mkdir(parents=True); activation.write_bytes(b"{}")
            result = runner.run_one_shot(root=root, head="b" * 40, blob_loader=lambda *_: b"{}", gate_check=lambda *_: True)
            self.assertEqual({"outcome": "refused_activation", "dataset_read_count": 0}, result)
            self.assertFalse((root / runner.MARKER).exists())

    def test_temp_root_missing_dataset_claims_once_and_preserves_first_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); gate = root / runner.GATE
            gate.parent.mkdir(parents=True); gate.write_bytes(b"{}")
            raw = runner.canonical(self.activation(hashlib.sha256(gate.read_bytes()).hexdigest()))
            activation = root / runner.ACTIVATION; activation.parent.mkdir(parents=True); activation.write_bytes(raw)
            check = lambda accepted, checkpoint, digest: accepted == "a" * 40 and checkpoint == "b" * 40 and digest == hashlib.sha256(b"{}").hexdigest()
            first = runner.run_one_shot(root=root, head="b" * 40, blob_loader=lambda *_: raw, gate_check=check)
            self.assertEqual("dataset_missing", first["blocker"])
            self.assertTrue((root / runner.MARKER).exists())
            self.assertEqual("refused_already_consumed", runner.run_one_shot(root=root, head="b" * 40, blob_loader=lambda *_: raw, gate_check=check)["outcome"])

    def blocked_synthetic(self):
        row = runner.artifact(); row["attempted_read_count"] = 1
        return {
            "schema_version": runner.REPORT_SCHEMA, "order_id": "B8.6R7", "hypothesis_id": "L-4",
            "mode": "synthetic_fixture", "outcome": "provisioning_blocked", "blocker": "dataset_missing",
            "evidence_tier": "E0", "edge_claim": "none", "real_provisioning_consumed": False,
            "dataset_reference": runner.DATASET, "expected_dataset_sha256": runner.EXPECTED_DATASET_SHA256,
            "dataset_artifact": row, "contract_artifacts": runner.identities(), "activation_provenance": None,
            "access_counters": {"return_value_decode_count": 0, "validation_access_count": 0},
            "validation_seal": runner.SEAL, "producing_git_commit": "synthetic_fixture",
        }

    def success_report(self, root):
        dates = {symbol: ["2015-12-30", "2015-12-31"] for symbol in runner.U8}
        digest = runner.EXPECTED_DATASET_SHA256
        manifest = {"schema_version": runner.MANIFEST_SCHEMA, "dataset_reference": runner.DATASET, "dataset_sha256": digest, "dataset_byte_count": 17, "u8_members_in_order": list(runner.U8), "coverage_by_symbol": {symbol: {"start": values[0], "end": values[-1], "row_count": len(values)} for symbol, values in dates.items()}, "session_count": 16, "max_session_date": "2015-12-31", "validation_seal": runner.SEAL}
        payload = {"schema_version": runner.PAYLOAD_SCHEMA, "dataset_sha256": digest, "u8_members_in_order": list(runner.U8), "session_dates_by_symbol": dates}
        for path, value in ((runner.MANIFEST, manifest), (runner.PAYLOAD, payload)):
            target = root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(runner.canonical(value))
        row = runner.artifact(); row.update({"attempted_read_count": 1, "read_count": 1, "observed_byte_count": 17, "complete_read": True, "complete_raw_sha256": digest, "bounded_prefix_sha256": digest, "hash_count": 1, "scan_count": 1})
        activation = self.activation("b" * 64); raw = runner.canonical(activation)
        provenance = {"path": runner.ACTIVATION, "raw_sha256": hashlib.sha256(raw).hexdigest(), "content": activation, "activation_checkpoint_head": "c" * 40, "accepted_gate_blob_sha256": "b" * 64}
        return {"schema_version": runner.REPORT_SCHEMA, "order_id": "B8.6R7", "hypothesis_id": "L-4", "mode": "real_one_shot", "outcome": "structural_provisioned", "evidence_tier": "E0", "edge_claim": "none", "real_provisioning_consumed": True, "dataset_reference": runner.DATASET, "expected_dataset_sha256": runner.EXPECTED_DATASET_SHA256, "dataset_artifact": row, "contract_artifacts": runner.identities(), "activation_provenance": provenance, "access_counters": {"return_value_decode_count": 0, "validation_access_count": 0}, "validation_seal": runner.SEAL, "producing_git_commit": "c" * 40, "manifest": manifest, "payload": payload, "output_artifacts": {"manifest": {"path": runner.MANIFEST, "raw_sha256": hashlib.sha256(runner.canonical(manifest)).hexdigest(), "byte_count": len(runner.canonical(manifest))}, "payload": {"path": runner.PAYLOAD, "raw_sha256": hashlib.sha256(runner.canonical(payload)).hexdigest(), "byte_count": len(runner.canonical(payload))}}, "structural_summary_sha256": hashlib.sha256(runner.canonical({"manifest": manifest, "payload": payload})).hexdigest()}

    def validate_success(self, report, root):
        activation_raw = runner.canonical(report["activation_provenance"]["content"])
        with patch.object(report_validator, "identities", return_value=report["contract_artifacts"]):
            return report_validator.validate(report, root=root, blob_loader=lambda *_: activation_raw, gate_check=lambda *_: True)

    def refresh_forged_outputs(self, report, root):
        for name, path, value in (("manifest", runner.MANIFEST, report["manifest"]), ("payload", runner.PAYLOAD, report["payload"])):
            raw = runner.canonical(value); target = root / path; target.write_bytes(raw)
            report["output_artifacts"][name] = {"path": path, "raw_sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}
        report["structural_summary_sha256"] = hashlib.sha256(runner.canonical({"manifest": report["manifest"], "payload": report["payload"]})).hexdigest()

    def test_valid_synthetic_blocked_report_passes_but_synthetic_success_is_rejected(self):
        self.assertEqual("pass", report_validator.validate(self.blocked_synthetic())["status"])
        forged = self.blocked_synthetic(); forged["outcome"] = "structural_provisioned"
        self.assertEqual("blocked", report_validator.validate(forged)["status"])

    def test_exact_output_and_row_contract_rejects_inspector_forgery_and_mutations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); good = self.success_report(root)
            self.assertEqual("pass", self.validate_success(good, root)["status"])
            forged = json.loads(json.dumps(good)); forged["manifest"]["dataset_sha256"] = "x"; forged["payload"]["dataset_sha256"] = "x"; forged["dataset_artifact"]["complete_raw_sha256"] = "x"; forged["dataset_artifact"]["bounded_prefix_sha256"] = "x"; forged["dataset_artifact"]["observed_byte_count"] = -1
            for symbol in runner.U8:
                forged["manifest"]["coverage_by_symbol"][symbol] = {"start": "9999-99-99", "end": "9999-99-99", "row_count": 1}; forged["payload"]["session_dates_by_symbol"][symbol] = ["9999-99-99"]
            forged["manifest"]["session_count"] = 8; forged["manifest"]["max_session_date"] = "9999-99-99"; forged["structural_summary_sha256"] = hashlib.sha256(runner.canonical({"manifest": forged["manifest"], "payload": forged["payload"]})).hexdigest()
            self.refresh_forged_outputs(forged, root)
            self.assertEqual("blocked", self.validate_success(forged, root)["status"])
            for mutator in (
                lambda r: r["dataset_artifact"].update({"complete_raw_sha256": "z" * 64}),
                lambda r: r["dataset_artifact"].update({"observed_byte_count": -1}),
                lambda r: r["payload"]["session_dates_by_symbol"]["VTI"].append("2016-01-01"),
                lambda r: r["payload"]["session_dates_by_symbol"]["VTI"].append("not-a-date"),
                lambda r: r["activation_provenance"].update({"accepted_gate_blob_sha256": "x" * 64}),
                lambda r: r["activation_provenance"]["content"].update({"scope": "wrong-scope"}),
                lambda r: r["dataset_artifact"].update({"scan_count": 0}),
            ):
                self.refresh_forged_outputs(good, root)
                altered = json.loads(json.dumps(good)); mutator(altered)
                self.assertEqual("blocked", self.validate_success(altered, root)["status"])

    def test_cli_requires_exact_flag(self):
        self.assertEqual(2, runner.main([]))


if __name__ == "__main__":
    unittest.main()
