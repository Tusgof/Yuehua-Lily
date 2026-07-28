from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_l_4_breadth_b85_phase_a_activation_order_v1 import GATE, validate


class B85PhaseATests(unittest.TestCase):
    def payload(self) -> dict:
        return json.loads(GATE.read_text(encoding="utf-8"))

    def assert_blocked(self, mutate) -> None:
        payload = self.payload()
        mutate(payload)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gate.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual("blocked", validate(path)["status"])

    def test_phase_a_gate_passes(self) -> None:
        self.assertEqual({"status": "pass", "blockers": []}, validate())

    def test_source_and_manifest_identity_tamper_fails_closed(self) -> None:
        for mutate in (
            lambda p: p["source_binding"]["accepted_b84r2_gate"].__setitem__("artifact_sha256", "0" * 64),
            lambda p: p["source_binding"]["accepted_v4_science"]["manifest_identity"].__setitem__("gate_id", "forged"),
            lambda p: p["source_binding"]["b84r2_preflight_implementation"].__setitem__("runner_sha256", "0" * 64),
            lambda p: p["source_binding"]["sealed_validation_boundary"].__setitem__("validation_opened", True),
        ):
            self.assert_blocked(mutate)

    def test_phase_b_cannot_expand_or_decode(self) -> None:
        for mutate in (
            lambda p: p["phase_b_contract"].__setitem__("status", "executed"),
            lambda p: p["phase_b_contract"]["real_preflight_limit"].__setitem__("maximum", 2),
            lambda p: p["phase_b_contract"]["exact_environment"].__setitem__("container_id_environment_variable", "OTHER"),
            lambda p: p["phase_b_contract"]["structural_metadata_only"].__setitem__("latest_permitted_session_date", "2016-01-01"),
            lambda p: p["phase_b_contract"]["structural_metadata_only"]["payload_allowed_fields"].append("return"),
            lambda p: p["phase_b_contract"]["structural_metadata_only"]["rejection_conditions"].pop(),
        ):
            self.assert_blocked(mutate)

    def test_phase_a_access_is_all_false_and_zero(self) -> None:
        for mutate in (
            lambda p: p["phase_a_authorizations"].__setitem__("container", True),
            lambda p: p["phase_a_authorizations"].__setitem__("extra", False),
            lambda p: p["phase_a_access_counts"].__setitem__("environment_read", 1),
            lambda p: p["validation_seal"].__setitem__("accessed", True),
        ):
            self.assert_blocked(mutate)


if __name__ == "__main__":
    unittest.main()
