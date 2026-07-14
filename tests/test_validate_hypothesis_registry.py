from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from lib.io import load_json
from scripts.validate_hypothesis_registry import DEFAULT_REGISTRY, DEFAULT_SCHEMA, validate_hypothesis_registry


class HypothesisRegistryValidatorTests(unittest.TestCase):
    def test_current_registry_passes_schema_contract(self) -> None:
        result = validate_hypothesis_registry()
        self.assertEqual("pass", result["status"], result["blockers"])
        self.assertEqual(5, result["hypothesis_count"])

    def test_validated_status_requires_E2_evidence(self) -> None:
        registry = copy.deepcopy(load_json(DEFAULT_REGISTRY))
        registry["hypotheses"][0]["status"] = "validated"
        registry["hypotheses"][0]["evidence"] = [
            {"path": "reports/feasibility/l_0.json", "evidence_tier": "E1"}
        ]
        result = _validate_temp_registry(registry)
        self.assertIn("L-0:validated_status_requires_E2_or_E3_evidence", result["blockers"])

    def test_missing_schema_field_is_rejected(self) -> None:
        registry = copy.deepcopy(load_json(DEFAULT_REGISTRY))
        del registry["hypotheses"][1]["mintrl_validate"]
        result = _validate_temp_registry(registry)
        self.assertIn("L-1:missing_required_field:mintrl_validate", result["blockers"])


def _validate_temp_registry(registry: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "registry.json"
        path.write_text(json.dumps(registry), encoding="utf-8")
        return validate_hypothesis_registry(path, DEFAULT_SCHEMA)


if __name__ == "__main__":
    unittest.main()
