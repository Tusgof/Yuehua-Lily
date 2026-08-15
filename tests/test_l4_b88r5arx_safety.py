"""Adversarial safety tests for the B8.8R5AR-X tracker remediation."""
from __future__ import annotations

import ast
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_l_4_breadth_b88r5_committed_bootstrap_v6 as bootstrap
from scripts import validate_l_4_breadth_b88r5_historical_pre_activation_v6 as historical


ROOT = Path(__file__).resolve().parents[1]


def _load_tracker_validator():
    path = ROOT / "scripts/validate_bootstrap_tracker.py"
    spec = importlib.util.spec_from_file_location("lily_tracker_safety_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load tracker validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class B88R5ARXSafetyTests(unittest.TestCase):
    def test_dangerous_handler_and_requirement_are_absent(self) -> None:
        source = (ROOT / "scripts/validate_bootstrap_tracker.py").read_text(encoding="utf-8")
        self.assertNotIn("exist_and_deny_without_activation", source)
        tracker = json.loads((ROOT / "experiments/bootstrap_tracker.json").read_text(encoding="utf-8"))
        b88r5 = next(item for item in tracker["orders"] if item["id"] == "B8.8R5")
        bootstrap_artifact = next(item for item in b88r5["required_artifacts"] if "committed_bootstrap_v6.py" in item["path"])
        self.assertEqual("exist", bootstrap_artifact["must"])
        self.assertEqual("B8.8R5AR-X", tracker["orders"][-1]["id"])

    def test_safe_validator_calls_only_preflight_when_runtime_is_poisoned(self) -> None:
        expected = {"status": "blocked", "outcome": "refused_activation", "ready": False, "real_accessed": False}
        with patch.object(bootstrap, "preflight", return_value=expected), patch.object(bootstrap, "run", side_effect=AssertionError("run called"), create=True), patch.object(bootstrap, "run_one_shot", side_effect=AssertionError("run_one_shot called"), create=True):
            result = historical.validate(ROOT)
        self.assertEqual("pass", result["status"], result)
        self.assertEqual("refused_activation", result["outcome"])

    def test_safe_validator_has_no_runtime_entrypoint_call(self) -> None:
        tree = ast.parse((ROOT / "scripts/validate_l_4_breadth_b88r5_historical_pre_activation_v6.py").read_text(encoding="utf-8"))
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "bootstrap":
                calls.append(node.func.attr)
        self.assertEqual(["preflight"], calls)

    def test_removed_tracker_rule_cannot_execute_a_subprocess(self) -> None:
        validator = _load_tracker_validator()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "bootstrap.py"
            target.write_text("raise AssertionError('executed')", encoding="utf-8")
            tracker = root / "tracker.json"
            tracker.write_text(json.dumps({
                "schema_version": "lily_bootstrap_tracker_v1",
                "done_claim_rule": "Done requires checked artifacts.",
                "orders": [{
                    "id": "B8.8R5", "title": "historical", "status": "done", "depends_on": [],
                    "required_artifacts": [{"path": "bootstrap.py", "must": "exist_and_deny_without_activation"}],
                    "forbidden": ["execution"], "evidence": ["historical"],
                }],
            }), encoding="utf-8")
            original_run = validator.subprocess.run

            def guarded_run(command, *args, **kwargs):
                if list(command[:2]) == ["git", "ls-files"]:
                    return original_run(command, *args, **kwargs)
                raise AssertionError(f"unexpected subprocess execution: {command}")

            with patch.object(validator.subprocess, "run", side_effect=guarded_run):
                result = validator.validate_tracker(tracker, project_root=root, verify_runtime=True)
        self.assertEqual("fail", result["status"])
        self.assertIn("B8.8R5:unsupported_done_rule:exist_and_deny_without_activation", result["blockers"])


if __name__ == "__main__":
    unittest.main()
