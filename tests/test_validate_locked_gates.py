from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib.provenance import file_sha256
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


if __name__ == "__main__":
    unittest.main()
