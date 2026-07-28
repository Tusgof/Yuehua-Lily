from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lib.l4_b86r3_contract_v4 import REACHABLE_BLOCKERS, category
import scripts.run_l_4_breadth_b86r3_provisioning_v4 as runner
import scripts.validate_l_4_breadth_b86r3_provisioning_gate_v4 as gate_validator
from scripts.validate_l_4_breadth_b86r3_provisioning_report_v4 import validate
from tests.test_l4_b86r2_provisioning import source


def accepted():
    return runner.canonical(
        {
            "schema_version": "lily_l4_b86r3_provisioning_activation_v4",
            "gate_id": runner.GATE_ID,
            "gate_sha256": runner.identities()["phase_a_gate"]["sha256"],
            "accepted_gate_head_sha": "a" * 40,
            "hermetic_ci_head_sha": "a" * 40,
            "hermetic_ci_run_id": 1,
            "inspector_decision": "ACCEPTED",
            "owner_authorization_reference": "B8.6R3 one-shot owner authorization",
            "scope": "one_repo_relative_falsification_container_provisioning_only",
            "validation_seal": {"status": "sealed_not_accessed", "accessed": False},
        }
    )


def accepted_gate_check(accepted_head, checkpoint_head, gate_sha256):
    return accepted_head == "a" * 40 and len(checkpoint_head) == 40 and gate_sha256 == runner.identities()["phase_a_gate"]["sha256"]


def synthetic_blocked(blocker):
    row = runner.artifact()
    row["attempted_read_count"] = 1
    if category(blocker) == "over":
        row.update(
            {
                "read_count": 1,
                "observed_byte_count": 32 * 1024 * 1024 + 1,
                "hash_count": 1,
                "bounded_prefix_sha256": "0" * 64,
            }
        )
    elif category(blocker) == "scanned":
        row.update(
            {
                "read_count": 1,
                "observed_byte_count": 1,
                "complete_read": True,
                "complete_raw_sha256": "0" * 64,
                "bounded_prefix_sha256": "0" * 64,
                "hash_count": 1,
                "scan_count": 1,
            }
        )
    report = runner.base("synthetic_fixture", row, None)
    report.update({"outcome": "provisioning_blocked", "blocker": blocker})
    return report


class ProvisioningV4Tests(unittest.TestCase):
    def test_gate_rejects_semantic_drift(self):
        self.assertEqual("pass", gate_validator.validate()["status"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gate.json"
            gate = json.loads(gate_validator.GATE.read_text("ascii"))
            gate["phase_a_authorizations"]["data"] = True
            path.write_text(json.dumps(gate), encoding="ascii")
            self.assertEqual("blocked", gate_validator.validate(path)["status"])
            gate = json.loads(gate_validator.GATE.read_text("ascii"))
            gate["blocker_matrix"]["fabricated_blocker_rejected"] = False
            path.write_text(json.dumps(gate), encoding="ascii")
            self.assertEqual("blocked", gate_validator.validate(path)["status"])

    def test_every_declared_blocker_is_valid_and_fabrication_is_rejected(self):
        for blocker in REACHABLE_BLOCKERS:
            report = synthetic_blocked(blocker)
            self.assertEqual("pass", validate(report)["status"], blocker)
        report = synthetic_blocked("dataset_missing")
        report["blocker"] = "fabricated_blocker"
        self.assertEqual("blocked", validate(report)["status"])

    def test_success_summary_output_identity_and_cross_bindings(self):
        report = runner.structural(source())
        self.assertEqual("pass", validate(report)["status"])
        mutations = (
            lambda value: value.__setitem__("structural_summary_sha256", "0" * 64),
            lambda value: value["output_artifacts"]["manifest"].__setitem__("byte_count", 0),
            lambda value: value["payload"].__setitem__("dataset_sha256", "0" * 64),
            lambda value: value["manifest"]["coverage_by_symbol"]["VTI"].__setitem__("row_count", 9),
            lambda value: value["payload"].__setitem__("u8_members_in_order", []),
        )
        for mutation in mutations:
            changed = copy.deepcopy(report)
            mutation(changed)
            self.assertEqual("blocked", validate(changed)["status"])

    def test_real_run_consumes_once_and_provenance_mutations_block(self):
        raw = source()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "synthetic_input.json"
            dataset.write_bytes(raw)
            report = runner.run_one_shot(
                dataset,
                report_path=root / "report.json",
                marker_path=root / "marker.json",
                manifest_path=root / "manifest.json",
                payload_path=root / "payload.json",
                activation_raw=accepted(),
                activation_head=runner.git_commit(runner.ROOT),
                accepted_gate_check=accepted_gate_check,
            )
            self.assertEqual("dataset_hash_mismatch", report["blocker"])
            self.assertEqual(
                "pass", validate(report, accepted_gate_check=accepted_gate_check)["status"]
            )
            second = runner.run_one_shot(
                dataset,
                report_path=root / "second_report.json",
                marker_path=root / "marker.json",
                manifest_path=root / "second_manifest.json",
                payload_path=root / "second_payload.json",
                activation_raw=accepted(),
                activation_head=runner.git_commit(runner.ROOT),
                accepted_gate_check=accepted_gate_check,
            )
            self.assertEqual({"outcome": "refused_already_consumed"}, second)
            for mutate in (
                lambda value: value.__setitem__("real_provisioning_consumed", False),
                lambda value: value.__setitem__("producing_git_commit", "not_a_commit"),
                lambda value: value["activation_provenance"].__setitem__("raw_sha256", "0" * 64),
                lambda value: value["activation_provenance"].__setitem__("activation_checkpoint_head", "0" * 40),
                lambda value: value["contract_artifacts"].pop("runner"),
            ):
                changed = copy.deepcopy(report)
                mutate(changed)
                self.assertEqual(
                    "blocked", validate(changed, accepted_gate_check=accepted_gate_check)["status"]
                )

    def test_refuses_before_marker_when_activation_is_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = runner.run_one_shot(
                root / "unreadable_dataset.json",
                report_path=root / "report.json",
                marker_path=root / "marker.json",
                manifest_path=root / "manifest.json",
                payload_path=root / "payload.json",
                activation_raw=b"{}",
                activation_head="b" * 40,
                accepted_gate_check=accepted_gate_check,
            )
            self.assertEqual({"outcome": "refused_activation"}, result)
            self.assertFalse((root / "marker.json").exists())


if __name__ == "__main__":
    unittest.main()
