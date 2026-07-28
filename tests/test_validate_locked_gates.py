from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib.provenance import file_sha256
from scripts import validate_locked_gates as locked_gates
from scripts.validate_locked_gates import validate_locked_gates


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LockedGateValidatorTests(unittest.TestCase):
    def test_hash_bound_files_are_pinned_to_LF(self) -> None:
        lines = (PROJECT_ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
        for pattern in ("*.json text eol=lf", "*.jsonl text eol=lf", "*.md text eol=lf", "*.py text eol=lf"):
            self.assertIn(pattern, lines)

    def test_empty_initial_manifest_passes_without_locking_an_experiment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "locked_gates.jsonl"
            manifest.write_text("", encoding="utf-8")
            result = validate_locked_gates(manifest, committed_lines=[])
        self.assertEqual("pass", result["status"], result["blockers"])
        self.assertEqual(0, result["entry_count"])

    def test_active_gate_hashes_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            entry = _entry("gate-v1", artifact, validator)
            entry["validator_sha256"] = "0" * 64
            manifest.write_text(json.dumps(entry) + "\n", encoding="utf-8")
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[])
        self.assertIn("gate-v1:validator_hash_mismatch", result["blockers"])

    def test_prior_manifest_lines_cannot_be_edited(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            original = json.dumps(_entry("gate-v1", artifact, validator), sort_keys=True)
            changed_entry = _entry("gate-v1", artifact, validator)
            changed_entry["human_approval"] = "edited after lock"
            manifest.write_text(json.dumps(changed_entry, sort_keys=True) + "\n", encoding="utf-8")
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[original])
        self.assertIn("locked_gate_manifest_is_not_append_only", result["blockers"])

    def test_supersession_requires_reviewer_and_replacement_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            initial = _entry("gate-v1", artifact, validator)
            replacement = dict(initial)
            replacement.update(
                {
                    "gate_id": "gate-v2",
                    "supersedes_gate_id": "gate-v1",
                    "human_approval": "owner approved revision",
                }
            )
            manifest.write_text(
                "\n".join(json.dumps(item) for item in (initial, replacement)) + "\n",
                encoding="utf-8",
            )
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[])
        self.assertIn("gate-v2:supersession_requires_reviewer_identity", result["blockers"])
        self.assertIn("gate-v2:supersession_requires_replacement_hash", result["blockers"])

    def test_reviewed_supersession_with_new_hashes_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            initial = _entry("gate-v1", artifact, validator)
            artifact.write_text('{"gate":"revised"}\n', encoding="utf-8")
            replacement = _entry("gate-v2", artifact, validator)
            replacement.update(
                {
                    "supersedes_gate_id": "gate-v1",
                    "human_approval": "owner approved revision",
                    "reviewed_by": "independent-review-agent",
                }
            )
            manifest.write_text(
                "\n".join(json.dumps(item) for item in (initial, replacement)) + "\n",
                encoding="utf-8",
            )
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[])
        self.assertEqual("pass", result["status"], result["blockers"])
        self.assertEqual("superseded", result["checked"][0]["status"])

    def test_reviewed_supersession_may_preserve_predecessor_at_new_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            initial = _entry("gate-v1", artifact, validator)
            replacement_artifact = artifact.with_name("gate_v2.json")
            replacement_validator = validator.with_name("validate_gate_v2.py")
            replacement_artifact.write_text('{"gate":"v2"}\n', encoding="utf-8")
            replacement_validator.write_text("print('validate v2')\n", encoding="utf-8")
            replacement = _entry("gate-v2", replacement_artifact, replacement_validator)
            replacement.update(
                {
                    "artifact_path": "experiments/gate_v2.json",
                    "validator_path": "scripts/validate_gate_v2.py",
                    "supersedes_gate_id": "gate-v1",
                    "human_approval": "owner approved immutable revision",
                    "reviewed_by": "independent-review-agent",
                }
            )
            manifest.write_text(
                "\n".join(json.dumps(item) for item in (initial, replacement)) + "\n",
                encoding="utf-8",
            )
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[])
        self.assertEqual("pass", result["status"], result["blockers"])
        self.assertEqual("superseded", result["checked"][0]["status"])

    def test_new_path_supersession_requires_intact_predecessor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            initial = _entry("gate-v1", artifact, validator)
            replacement_artifact = artifact.with_name("gate_v2.json")
            replacement_validator = validator.with_name("validate_gate_v2.py")
            replacement_artifact.write_text('{"gate":"v2"}\n', encoding="utf-8")
            replacement_validator.write_text("print('validate v2')\n", encoding="utf-8")
            replacement = _entry("gate-v2", replacement_artifact, replacement_validator)
            replacement.update(
                {
                    "artifact_path": "experiments/gate_v2.json",
                    "validator_path": "scripts/validate_gate_v2.py",
                    "supersedes_gate_id": "gate-v1",
                    "human_approval": "owner approved immutable revision",
                    "reviewed_by": "independent-review-agent",
                }
            )
            artifact.write_text('{"gate":"tampered"}\n', encoding="utf-8")
            manifest.write_text(
                "\n".join(json.dumps(item) for item in (initial, replacement)) + "\n",
                encoding="utf-8",
            )
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[])
        self.assertIn("gate-v2:immutable_predecessor_artifact_hash_mismatch", result["blockers"])

    def test_only_missing_human_approval_may_have_one_direct_hash_bound_correction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            predecessor = _entry("gate-v1", artifact, validator)
            predecessor.pop("human_approval")
            successor = _corrective_successor(predecessor, artifact, validator)
            manifest.write_text(
                "\n".join(json.dumps(item) for item in (predecessor, successor)) + "\n",
                encoding="utf-8",
            )
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[])
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_correction_rejects_any_missing_field_besides_human_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            predecessor = _entry("gate-v1", artifact, validator)
            predecessor.pop("human_approval")
            predecessor.pop("locked_by")
            successor = _corrective_successor(predecessor, artifact, validator)
            manifest.write_text(
                "\n".join(json.dumps(item) for item in (predecessor, successor)) + "\n",
                encoding="utf-8",
            )
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[])
        self.assertIn("gate-v1:missing_required_field:locked_by", result["blockers"])

    def test_missing_human_approval_without_correction_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            predecessor = _entry("gate-v1", artifact, validator)
            predecessor.pop("human_approval")
            manifest.write_text(json.dumps(predecessor) + "\n", encoding="utf-8")
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[])
        self.assertIn("gate-v1:missing_required_field:human_approval", result["blockers"])

    def test_correction_rejects_wrong_hash_or_missing_field_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            predecessor = _entry("gate-v1", artifact, validator)
            predecessor.pop("human_approval")
            successor = _corrective_successor(predecessor, artifact, validator)
            successor["predecessor_line_sha256"] = "0" * 64
            successor["corrects_predecessor_missing_fields"] = ["locked_by"]
            manifest.write_text(
                "\n".join(json.dumps(item) for item in (predecessor, successor)) + "\n",
                encoding="utf-8",
            )
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[])
        self.assertIn("gate-v1:missing_required_field:human_approval", result["blockers"])

    def test_correction_must_be_direct_and_unique(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            predecessor = _entry("gate-v1", artifact, validator)
            predecessor.pop("human_approval")
            unrelated = _entry("gate-middle", artifact, validator)
            successor = _corrective_successor(predecessor, artifact, validator)
            duplicate = dict(successor)
            duplicate["gate_id"] = "gate-v3"
            manifest.write_text(
                "\n".join(json.dumps(item) for item in (predecessor, unrelated, successor, duplicate)) + "\n",
                encoding="utf-8",
            )
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[])
        self.assertIn("gate-v1:missing_required_field:human_approval", result["blockers"])
        self.assertIn("gate-v3:predecessor_already_superseded:gate-v1", result["blockers"])

    def test_correction_requires_its_own_human_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            predecessor = _entry("gate-v1", artifact, validator)
            predecessor.pop("human_approval")
            successor = _corrective_successor(predecessor, artifact, validator)
            successor.pop("human_approval")
            manifest.write_text(
                "\n".join(json.dumps(item) for item in (predecessor, successor)) + "\n",
                encoding="utf-8",
            )
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[])
        self.assertIn("gate-v1:missing_required_field:human_approval", result["blockers"])
        self.assertIn("gate-v2:missing_required_field:human_approval", result["blockers"])

    def test_recovery_restores_only_the_committed_human_approval_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest, artifact, validator = _gate_paths(Path(tmp))
            predecessor = _entry("gate-v1", artifact, validator)
            historical = dict(predecessor)
            predecessor.pop("human_approval")
            successor = _corrective_successor(predecessor, artifact, validator)
            manifest.write_text(
                "\n".join(json.dumps(item) for item in (predecessor, successor)) + "\n",
                encoding="utf-8",
            )
            with patch("scripts.validate_locked_gates.PROJECT_ROOT", root):
                result = validate_locked_gates(manifest, committed_lines=[json.dumps(historical)])
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_cross_platform_exception_is_only_the_two_audited_hash_mismatches(self) -> None:
        predecessor = {
            "gate_id": "l_3_b714_date_only_preflight_remediation_v6",
            "artifact_sha256": "565d7bcaa726f566b8d81e1197e41d024238286ba2783f93f341e7e019727925",
            "validator_sha256": "09b2ca768b1cb7a27a48401e91319f3c68f328cba2fd82ac764886d91d7cf793",
        }
        self.assertFalse(
            locked_gates._approved_cross_platform_predecessor(
                predecessor, "pass", "hash_mismatch"
            )
        )
        predecessor["artifact_sha256"] = "0" * 64
        self.assertFalse(
            locked_gates._approved_cross_platform_predecessor(
                predecessor, "hash_mismatch", "hash_mismatch"
            )
        )
        predecessor["gate_id"] = "unrelated_gate"
        self.assertFalse(
            locked_gates._approved_cross_platform_predecessor(
                predecessor, "hash_mismatch", "hash_mismatch"
            )
        )


def _gate_paths(root: Path) -> tuple[Path, Path, Path, Path]:
    experiments = root / "experiments"
    scripts = root / "scripts"
    experiments.mkdir()
    scripts.mkdir()
    artifact = experiments / "gate.json"
    validator = scripts / "validate_gate.py"
    artifact.write_text('{"gate":"locked"}\n', encoding="utf-8")
    validator.write_text("print('validate')\n", encoding="utf-8")
    return root, experiments / "locked_gates.jsonl", artifact, validator


def _entry(gate_id: str, artifact: Path, validator: Path) -> dict[str, str]:
    return {
        "gate_id": gate_id,
        "gate_type": "preregistration",
        "artifact_path": "experiments/gate.json",
        "artifact_sha256": file_sha256(artifact),
        "validator_path": "scripts/validate_gate.py",
        "validator_sha256": file_sha256(validator),
        "locked_at": "2026-07-15T00:00:00Z",
        "locked_by": "owner",
        "human_approval": "owner approved initial lock",
    }


def _corrective_successor(
    predecessor: dict[str, str], artifact: Path, validator: Path
) -> dict[str, str | list[str]]:
    replacement_artifact = artifact.with_name("gate_v2.json")
    replacement_validator = validator.with_name("validate_gate_v2.py")
    replacement_artifact.write_text('{"gate":"corrected"}\n', encoding="utf-8")
    replacement_validator.write_text("print('validate corrected')\n", encoding="utf-8")
    predecessor_line = json.dumps(predecessor)
    return {
        **_entry("gate-v2", replacement_artifact, replacement_validator),
        "artifact_path": "experiments/gate_v2.json",
        "validator_path": "scripts/validate_gate_v2.py",
        "supersedes_gate_id": predecessor["gate_id"],
        "human_approval": "owner approved correction",
        "reviewed_by": "independent-review-agent",
        "corrects_predecessor_missing_fields": ["human_approval"],
        "predecessor_line_sha256": hashlib.sha256(predecessor_line.encode("utf-8")).hexdigest(),
    }


if __name__ == "__main__":
    unittest.main()
