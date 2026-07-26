from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from lib.io import load_json, write_json
from scripts.validate_l_3_falsification_activation_preflight_v1 import (
    GATE,
    L1_GATE,
    L3_V1_GATE,
    L3_V2_GATE,
    L3_V2_VALIDATOR,
    MANIFEST,
    validate_gate,
)


class L3FalsificationActivationPreflightTests(unittest.TestCase):
    def test_gate_passes_without_data_access(self) -> None:
        self.assertEqual("pass", validate_gate()["status"])

    def test_rejects_forged_source_hashes_and_manifest_identity(self) -> None:
        for parameter, source, blocker in (
            ("l3_v2_gate_path", L3_V2_GATE, "active_l3_v2_artifact_hash_mismatch"),
            ("l3_v2_validator_path", L3_V2_VALIDATOR, "active_l3_v2_validator_hash_mismatch"),
            ("l3_v1_gate_path", L3_V1_GATE, "immutable_l3_v1_artifact_hash_mismatch"),
            ("l1_gate_path", L1_GATE, "l1_baseline_artifact_hash_mismatch"),
        ):
            with self.subTest(parameter=parameter):
                with tempfile.TemporaryDirectory() as directory:
                    forged = Path(directory) / source.name
                    forged.write_text("{}\n", encoding="utf-8")
                    result = validate_gate(**{parameter: forged})
                self.assertIn(blocker, result["blockers"])
        rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines()]
        row = next(row for row in rows if row["gate_id"] == "l_3_inverse_volatility_sizing_v2")
        row["artifact_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "locked_gates.jsonl"
            manifest.write_text("\n".join(json.dumps(item, sort_keys=True) for item in rows) + "\n", encoding="utf-8")
            result = validate_gate(manifest_path=manifest)
        self.assertIn("active_l3_v2_manifest_identity_mismatch", result["blockers"])

    def test_rejects_whole_manifest_or_circular_binding_and_unknown_fields(self) -> None:
        payload = load_json(GATE)
        cases = [
            (lambda gate: gate["source_binding"].update(whole_manifest_sha256="0" * 64), "unknown_source_binding_field:whole_manifest_sha256"),
            (lambda gate: gate["source_binding"].update(self_artifact_sha256="0" * 64), "unknown_source_binding_field:self_artifact_sha256"),
            (lambda gate: gate.update(unapproved_field=True), "unknown_top_level_field:unapproved_field"),
            (lambda gate: gate.pop("hard_stops"), "missing_top_level_field:hard_stops"),
        ]
        for mutate, blocker in cases:
            with self.subTest(blocker=blocker):
                candidate = copy.deepcopy(payload)
                mutate(candidate)
                self.assertIn(blocker, self._validate_temporary_gate(candidate)["blockers"])

    def test_rejects_research_semantic_capacity_boundary_and_unit_drift(self) -> None:
        payload = load_json(GATE)
        cases = [
            (lambda gate: gate["locked_research_facts"]["research_universe_tickers_in_order"].reverse(), "research_fact_mismatch:research_universe_tickers_in_order"),
            (lambda gate: gate["locked_research_facts"].update(candidate_raw_score="q[i,t]"), "research_fact_mismatch:candidate_raw_score"),
            (lambda gate: gate["locked_research_facts"].update(comparator_raw_score="equal_weight"), "research_fact_mismatch:comparator_raw_score"),
            (lambda gate: gate["locked_research_facts"].update(decision_index_and_timing="same close"), "research_fact_mismatch:decision_index_and_timing"),
            (lambda gate: gate["locked_research_facts"]["falsification_window"].update(end="2016-01-04"), "research_fact_mismatch:falsification_window"),
            (lambda gate: gate["locked_research_facts"]["falsification_window"].update(validation_pooling="allowed"), "research_fact_mismatch:falsification_window"),
            (lambda gate: gate["locked_research_facts"].update(observation_unit="one trade"), "research_fact_mismatch:observation_unit"),
            (lambda gate: gate["locked_research_facts"].update(mintrl_falsify_weekly_paired_observations=48), "research_fact_mismatch:mintrl_falsify_weekly_paired_observations"),
            (lambda gate: gate["locked_research_facts"].update(optimistic_weekly_capacity_ceiling=466), "research_fact_mismatch:optimistic_weekly_capacity_ceiling"),
            (lambda gate: gate["locked_research_facts"].update(optimistic_regime_eligible_weekly_capacity_ceiling=367), "research_fact_mismatch:optimistic_regime_eligible_weekly_capacity_ceiling"),
            (lambda gate: gate["validation_seal"].update(opened=True), "governance_mismatch:validation_seal"),
        ]
        for mutate, blocker in cases:
            with self.subTest(blocker=blocker):
                candidate = copy.deepcopy(payload)
                mutate(candidate)
                self.assertIn(blocker, self._validate_temporary_gate(candidate)["blockers"])

    def test_rejects_all_authorization_and_preflight_hard_stop_openings(self) -> None:
        payload = load_json(GATE)
        for field in payload["authorizations"]:
            with self.subTest(field=field):
                candidate = copy.deepcopy(payload)
                candidate["authorizations"][field] = True
                self.assertIn(f"authorization_mismatch:{field}", self._validate_temporary_gate(candidate)["blockers"])
        cases = [
            (lambda gate: gate["future_preflight_sequence"].__setitem__(4, "filter mixed container in memory"), "future_preflight_sequence_mismatch"),
            (lambda gate: gate["future_preflight_sequence"].__setitem__(1, "provider fallback allowed"), "future_preflight_sequence_mismatch"),
            (lambda gate: gate["future_preflight_sequence"].pop(5), "future_preflight_sequence_mismatch"),
            (lambda gate: gate.update(hard_stops=[]), "hard_stops_incomplete_or_open"),
        ]
        for mutate, blocker in cases:
            with self.subTest(blocker=blocker):
                candidate = copy.deepcopy(payload)
                mutate(candidate)
                self.assertIn(blocker, self._validate_temporary_gate(candidate)["blockers"])

    def _validate_temporary_gate(self, payload: dict[str, Any]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "l3_b71_gate.json"
            write_json(path, payload)
            return validate_gate(path)


if __name__ == "__main__":
    unittest.main()
