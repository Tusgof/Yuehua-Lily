from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_l_4_breadth_b84r_preflight_v2 import run
from scripts.validate_l_4_breadth_b84r_preflight_report_v2 import materialize_fixture, validate

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/l4_b84/synthetic_preflight_report_v2.json"


def payload() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def materialized_payload() -> dict:
    return materialize_fixture(payload())


class B84Tests(unittest.TestCase):
    def assert_blocked(self, mutate) -> None:
        item = materialized_payload()
        mutate(item)
        self.assertEqual("blocked", validate(item, committed_fixture=True)["status"])

    def test_fixture_and_runner_pass(self) -> None:
        self.assertEqual("pass", validate(materialized_payload(), committed_fixture=True)["status"])
        self.assertEqual("pass", run(FIXTURE)["status"])

    def test_v4_and_b84_provenance_forgery_fails_closed(self) -> None:
        for mutate in (
            lambda p: p["provenance"].__setitem__("v4_sha256", "0" * 64),
            lambda p: p["provenance"]["v4_manifest_identity"].__setitem__("artifact_sha256", "0" * 64),
            lambda p: p["provenance"].__setitem__("b84_gate_sha256", "0" * 64),
            lambda p: p["provenance"]["b84_manifest_identity"].__setitem__("artifact_sha256", "0" * 64),
            lambda p: p["provenance"]["b84_implementation"]["runner"].__setitem__("sha256", "0" * 64),
        ):
            self.assert_blocked(mutate)

    def test_v4_controls_and_outcome_drift_fails_closed(self) -> None:
        for mutate in (
            lambda p: p["canonical_sections"].__setitem__("mandatory_metrics", "forged"),
            lambda p: p["canonical_sections"].__setitem__("statistics", "forged"),
            lambda p: p["canonical_sections"].__setitem__("decision_contract", "forged"),
            lambda p: p["canonical_sections"].__setitem__("regime_matrix", "forged"),
            lambda p: p["canonical_sections"].__setitem__("robustness_and_side_effects", "forged"),
            lambda p: p.__setitem__("v4_controls_sha256", "forged"),
        ):
            self.assert_blocked(mutate)

    def test_date_schema_authorization_and_seal_drift_fail_closed(self) -> None:
        for mutate in (
            lambda p: p["symbol_sessions"]["VTI"].__setitem__(0, "2016-01-04"),
            lambda p: p["symbol_sessions"]["VTI"].__setitem__(0, "not-a-date"),
            lambda p: p["symbol_sessions"]["VTI"].__setitem__(0, "2015-12-31T00:00:00"),
            lambda p: p["symbol_sessions"].pop("VTI"),
            lambda p: p["authorizations"].__setitem__("container", True),
            lambda p: p["authorizations"].__setitem__("extra", False),
            lambda p: p["validation_seal"].__setitem__("accessed", True),
            lambda p: p.__setitem__("paired_weeks", 466),
            lambda p: p.__setitem__("extra", True),
            lambda p: p["provenance"].__setitem__("extra", True),
        ):
            self.assert_blocked(mutate)

    def test_e1_decision_or_edge_claim_is_blocked(self) -> None:
        for mutate in (
            lambda p: p.update({"evidence_tier": "E1"}),
            lambda p: p.update({"decision": "falsified_E1_only"}),
            lambda p: p.update({"edge_claim": "breadth"}),
        ):
            self.assert_blocked(mutate)

    def test_producing_checkout_forgery_and_context_fail_closed(self) -> None:
        self.assertEqual("blocked", validate(payload())["status"])
        old_commit = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
        self.assert_blocked(lambda p: p["producing_checkout"].__setitem__("validating_checkout_commit", old_commit))
        self.assert_blocked(lambda p: p["producing_checkout"].__setitem__("mode", "generated"))

    def test_runner_rejects_nonfixture_and_tampered_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            forged = Path(tmp) / "synthetic_preflight_report_v2.json"
            forged.write_text(json.dumps(payload()), encoding="utf-8")
            self.assertEqual("blocked", run(forged)["status"])
            tampered = payload()
            tampered["symbol_sessions"]["VTI"] = ["2016-01-04"]
            forged.write_text(json.dumps(tampered), encoding="utf-8")
            with patch("scripts.run_l_4_breadth_b84r_preflight_v2.FIXTURE", forged):
                self.assertEqual("blocked", run(forged)["status"])


if __name__ == "__main__":
    unittest.main()
