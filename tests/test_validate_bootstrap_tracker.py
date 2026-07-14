from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "validate_bootstrap_tracker.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_bootstrap_tracker", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load bootstrap tracker validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_bootstrap_tracker"] = module
    spec.loader.exec_module(module)
    return module


class BootstrapTrackerValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = _load_validator()

    def test_current_tracker_passes_without_recursive_runtime_checks(self) -> None:
        result = self.validator.validate_tracker(verify_runtime=False)
        self.assertEqual("pass", result["status"], result["blockers"])
        self.assertEqual([], result["blockers"])

    def test_done_claim_without_artifact_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tracker = root / "tracker.json"
            tracker.write_text(
                json.dumps(_tracker_with_artifact("missing.py", "pass")),
                encoding="utf-8",
            )
            result = self.validator.validate_tracker(
                tracker,
                project_root=root,
                verify_runtime=False,
            )
        self.assertEqual("fail", result["status"])
        self.assertIn("B0.1:missing_artifact:missing.py", result["blockers"])

    def test_done_claim_requires_evidence(self) -> None:
        payload = _tracker_with_artifact("present.py", "pass")
        payload["orders"][0]["evidence"] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "present.py").write_text("pass\n", encoding="utf-8")
            tracker = root / "tracker.json"
            tracker.write_text(json.dumps(payload), encoding="utf-8")
            result = self.validator.validate_tracker(
                tracker,
                project_root=root,
                verify_runtime=False,
            )
        self.assertIn("B0.1:done_requires_evidence", result["blockers"])

    def test_absolute_path_scan_excludes_backup_and_catches_active_file(self) -> None:
        absolute = "D" + ":" + "\\private\\dataset"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active = root / "config.json"
            active.write_text(json.dumps({"root": absolute}), encoding="utf-8")
            backup = root / "Backup_" / "2026-07-15"
            backup.mkdir(parents=True)
            (backup / "legacy.md").write_text(absolute, encoding="utf-8")
            blockers = self.validator._scan_active_artifacts(root)
        self.assertEqual(["forbidden_absolute_path:config.json"], blockers)

    def test_credential_scan_reports_name_without_echoing_value(self) -> None:
        key_name = "LILY_" + "API_KEY"
        sample_value = "sensitive" + "value123456789"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "settings.env").write_text(f'{key_name}="{sample_value}"\n', encoding="utf-8")
            blockers = self.validator._scan_active_artifacts(root)
        self.assertEqual([f"credential_like_assignment:settings.env:{key_name}"], blockers)
        self.assertNotIn(sample_value, " ".join(blockers))

    def test_placeholder_values_are_allowed(self) -> None:
        key_name = "LILY_" + "API_KEY"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "machine.example.json").write_text(
                json.dumps({key_name: None}),
                encoding="utf-8",
            )
            blockers = self.validator._scan_active_artifacts(root)
        self.assertEqual([], blockers)

    def test_b02_lib_claim_requires_every_shared_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lib_dir = root / "lib"
            lib_dir.mkdir()
            (lib_dir / "environment.py").write_text("", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B0.2",
                "lib",
                "contain_environment_io_timestamp_provenance_guardrail_report_search_modules",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B0.2:lib_module_missing:io.py", blockers)


def _tracker_with_artifact(path: str, must: str) -> dict[str, object]:
    return {
        "schema_version": "lily_bootstrap_tracker_v1",
        "done_claim_rule": "Done requires checked artifacts.",
        "orders": [
            {
                "id": "B0.1",
                "title": "test",
                "status": "done",
                "depends_on": [],
                "required_artifacts": [{"path": path, "must": must}],
                "forbidden": ["scope expansion"],
                "evidence": ["test evidence"],
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
