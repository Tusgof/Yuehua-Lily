"""Tracker done-claim coverage for the B8.8R5AR replacement namespace."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_bootstrap_tracker.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("lily_b88r5ar_tracker_validator", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load tracker validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class B88R5ARTrackerValidatorTests(unittest.TestCase):
    def test_false_done_activation_claim_fails_runtime_validation(self) -> None:
        validator = _load_validator()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = root / "scripts/validate_l_4_breadth_b88r5ar_activation_v6.py"
            script.parent.mkdir(parents=True)
            script.write_text(
                "import json\n"
                "print(json.dumps({'status': 'blocked', 'preflight_outcome': 'refused_activation', 'real_accessed': False}))\n"
                "raise SystemExit(1)\n",
                encoding="utf-8",
            )
            tracker = root / "tracker.json"
            tracker.write_text(
                json.dumps(
                    {
                        "schema_version": "lily_bootstrap_tracker_v1",
                        "done_claim_rule": "Done requires checked artifacts.",
                        "orders": [
                            {
                                "id": "B8.8R5AR",
                                "title": "replacement activation checkpoint",
                                "status": "done",
                                "depends_on": [],
                                "required_artifacts": [
                                    {
                                        "path": "scripts/validate_l_4_breadth_b88r5ar_activation_v6.py",
                                        "must": "validate_l4_b88r5ar_activation",
                                    }
                                ],
                                "forbidden": ["execution"],
                                "evidence": ["synthetic test"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = validator.validate_tracker(
                tracker,
                project_root=root,
                verify_runtime=True,
            )
        self.assertEqual("fail", result["status"])
        self.assertIn(
            "B8.8R5AR:l4_b88r5ar_activation_validation_failed",
            result["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
