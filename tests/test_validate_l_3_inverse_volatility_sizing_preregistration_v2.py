from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from lib.io import load_json, write_json
from scripts.validate_l_3_inverse_volatility_sizing_preregistration_v2 import (
    GATE,
    MANIFEST,
    PROJECT_ROOT,
    V1_GATE,
    V1_VALIDATOR,
    validate_gate,
)


class L3InverseVolatilityPreregistrationV2Tests(unittest.TestCase):
    def test_gate_passes_hermetically(self) -> None:
        self.assertEqual("pass", validate_gate()["status"])

    def test_rejects_snapshot_byte_hash_and_path_changes(self) -> None:
        payload = load_json(GATE)
        cases = [
            (lambda gate: gate["source_binding"]["methodology_snapshots"][0].update(sha256="0" * 64), "methodology_snapshot_declarations_mismatch"),
            (lambda gate: gate["source_binding"]["methodology_snapshots"][0].update(snapshot_path="methodology_snapshots/forged.md"), "methodology_snapshot_declarations_mismatch"),
        ]
        for mutate, blocker in cases:
            with self.subTest(blocker=blocker):
                candidate = copy.deepcopy(payload)
                mutate(candidate)
                result = self._validate_temporary_gate(candidate)
                self.assertIn(blocker, result["blockers"])
        with tempfile.TemporaryDirectory() as directory:
            copied_root = Path(directory) / "project"
            snapshot = copied_root / "methodology_snapshots/l3_inverse_volatility_sizing_v1/wiki/concepts/inverse-volatility-weighting.md"
            snapshot.parent.mkdir(parents=True)
            snapshot.write_bytes(b"forged snapshot bytes\n")
            result = validate_gate(GATE, project_root=copied_root)
        self.assertIn("methodology_snapshot_hash_mismatch:wiki/concepts/inverse-volatility-weighting.md", result["blockers"])

    def test_rejects_forged_v1_artifact_validator_and_manifest_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            forged_v1 = temporary / "v1.json"
            forged_v1.write_text("{}\n", encoding="utf-8")
            result = validate_gate(GATE, v1_gate_path=forged_v1)
        self.assertIn("v1_preregistration_hash_mismatch", result["blockers"])
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            forged_validator = temporary / "validator.py"
            forged_validator.write_text("pass\n", encoding="utf-8")
            result = validate_gate(GATE, v1_validator_path=forged_validator)
        self.assertIn("v1_validator_hash_mismatch", result["blockers"])
        rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines()]
        v1_row = next(row for row in rows if row["gate_id"] == "l_3_inverse_volatility_sizing_v1")
        v1_row["validator_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "locked_gates.jsonl"
            manifest.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
            result = validate_gate(GATE, manifest_path=manifest)
        self.assertIn("v1_manifest_row_identity_mismatch", result["blockers"])

    def test_rejects_research_semantic_drift_and_unknown_fields(self) -> None:
        payload = load_json(GATE)
        cases = [
            (lambda gate: gate["research_semantics"].update(v1_artifact_sha256="0" * 64), "research_semantics_inheritance_mismatch"),
            (lambda gate: gate.update(research_question="open B7.1"), "unknown_top_level_field:research_question"),
            (lambda gate: gate["hermeticity_remediation"].update(scope="replace threshold"), "hermeticity_remediation_contract_mismatch"),
        ]
        for mutate, blocker in cases:
            with self.subTest(blocker=blocker):
                candidate = copy.deepcopy(payload)
                mutate(candidate)
                result = self._validate_temporary_gate(candidate)
                self.assertIn(blocker, result["blockers"])

    def test_rejects_b7_1_data_and_validation_opening(self) -> None:
        payload = load_json(GATE)
        cases = [
            (lambda gate: gate["b7_1"].update(authorized=True), "governance_mismatch:b7_1"),
            (lambda gate: gate["b7_1"].update(data_access_authorized=True), "governance_mismatch:b7_1"),
            (lambda gate: gate["b7_1"].update(execution_authorized=True), "governance_mismatch:b7_1"),
            (lambda gate: gate["validation_seal"].update(opened=True), "governance_mismatch:validation_seal"),
            (lambda gate: gate.update(hard_stops=[]), "hard_stops_incomplete_or_open"),
        ]
        for mutate, blocker in cases:
            with self.subTest(blocker=blocker):
                candidate = copy.deepcopy(payload)
                mutate(candidate)
                result = self._validate_temporary_gate(candidate)
                self.assertIn(blocker, result["blockers"])

    def _validate_temporary_gate(self, payload: dict[str, Any]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "l3_v2_gate.json"
            write_json(path, payload)
            return validate_gate(path)


if __name__ == "__main__":
    unittest.main()
