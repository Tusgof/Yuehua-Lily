from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_4_breadth_b89_execution_contract_v1 import (
    DEFAULT_CONTRACT,
    PROJECT_ROOT,
    validate,
)


class B89DExecutionContractTests(unittest.TestCase):
    def _load(self) -> dict:
        return json.loads(DEFAULT_CONTRACT.read_text(encoding="utf-8"))

    def _validate_mutation(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mutated-contract.json"
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return validate(path, project_root=PROJECT_ROOT)

    def test_locked_static_contract_passes(self) -> None:
        result = validate()
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["evidence_ceiling"], "E0")
        self.assertEqual(result["edge_claim"], "none")
        self.assertFalse(result["real_access"])

    def test_contract_is_not_bound_to_consumed_legacy_marker(self) -> None:
        raw = DEFAULT_CONTRACT.read_text(encoding="utf-8")
        self.assertNotIn("l_4_breadth_b88r5_one_shot_marker_v6.json", raw)
        self.assertNotIn("l_4_breadth_b88r5_scientific_execution_activation_v6.json", raw)

    def test_rejects_authorization_drift(self) -> None:
        payload = self._load()
        payload["authorizations"]["execution"] = True
        result = self._validate_mutation(payload)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("authorization_not_false:execution", result["blockers"])

    def test_rejects_science_threshold_drift(self) -> None:
        payload = self._load()
        payload["preserved_science"]["mandatory_metrics"]["ex_ante_hhi_delta"]["useful_threshold"] = 0.04
        result = self._validate_mutation(payload)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("science_semantics_drift:mandatory_metrics", result["blockers"])

    def test_rejects_source_hash_drift(self) -> None:
        payload = self._load()
        payload["source_binding"]["capacity"]["gate"]["sha256"] = "0" * 64
        result = self._validate_mutation(payload)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("capacity.gate:source_hash_mismatch:experiments/l_4_breadth_b87_phase_a_capacity_gate_v1.json", result["blockers"])

    def test_rejects_legacy_path_in_source_binding(self) -> None:
        payload = self._load()
        payload["source_binding"]["incident"]["legacy"] = {
            "path": "reports/experiments/l_4_breadth_b88r5_one_shot_marker_v6.json",
            "sha256": "0" * 64,
        }
        result = self._validate_mutation(payload)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("legacy_consumed_marker_bound", result["blockers"])

    def test_rejects_future_stage_authorization(self) -> None:
        payload = self._load()
        payload["future_lifecycle"]["activation_authorized"] = True
        result = self._validate_mutation(payload)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("future_activation_authorized_must_be_false", result["blockers"])

    def test_rejects_closure_provenance_drift(self) -> None:
        payload = self._load()
        payload["closure_provenance"]["closure_commit"] = "0" * 40
        result = self._validate_mutation(payload)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("closure_commit_mismatch", result["blockers"])

    def test_rejects_unknown_top_level_field(self) -> None:
        payload = self._load()
        payload["unexpected"] = True
        result = self._validate_mutation(payload)
        self.assertEqual(result["status"], "blocked")
        self.assertIn("contract_top_level_is_not_closed_world", result["blockers"])


if __name__ == "__main__":
    unittest.main()
