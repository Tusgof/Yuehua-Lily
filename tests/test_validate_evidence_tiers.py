from __future__ import annotations

import unittest

from scripts.validate_evidence_tiers import validate_evidence_tiers, validate_report_payload


class EvidenceTierValidatorTests(unittest.TestCase):
    def test_current_research_report_set_passes(self) -> None:
        result = validate_evidence_tiers()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_E1_pass_or_edge_claim_is_rejected(self) -> None:
        payload = {
            "hypothesis_id": "L-1",
            "evidence_tier": "E1",
            "tier_blockers": ["MinTRL_validate not funded"],
            "conclusion": "positive edge",
        }
        blockers = validate_report_payload(payload, known_ids={"L-1"})
        self.assertIn(
            "acceptance_or_edge_claim_below_E2:conclusion:positive edge",
            blockers,
        )

    def test_E2_without_adversarial_review_is_rejected(self) -> None:
        payload = {
            "hypothesis_id": "L-1",
            "evidence_tier": "E2",
            "tier_blockers": [],
            "conclusion": "pass",
        }
        blockers = validate_report_payload(payload, known_ids={"L-1"})
        self.assertIn("E2_requires_adversarial_review", blockers)

    def test_E0_machinery_pass_is_not_mistaken_for_research_acceptance(self) -> None:
        payload = {
            "hypothesis_id": "L-1",
            "evidence_tier": "E0",
            "tier_blockers": ["real data not evaluated"],
            "edge_claim": "none",
            "validation": {"status": "pass"},
        }
        self.assertEqual([], validate_report_payload(payload, known_ids={"L-1"}))

    def test_fractional_preview_claim_limits_supply_E0_tier_boundary(self) -> None:
        for version in ("v1", "v2"):
            with self.subTest(version=version):
                payload = {
                    "schema_version": f"lily_l0_webull_th_fractional_preview_report_{version}",
                    "hypothesis_id": "L-0",
                    "evidence_tier": "E0",
                    "edge_claim": "none",
                    "claim_limits": ["UAT preview is not production or edge evidence"],
                    "decision": "blocked_before_preview",
                }
                self.assertEqual([], validate_report_payload(payload, known_ids={"L-0"}))

    def test_E2_with_independent_completed_review_passes(self) -> None:
        payload = {
            "hypothesis_id": "L-1",
            "evidence_tier": "E2",
            "tier_blockers": [],
            "conclusion": "pass",
            "adversarial_review": {
                "status": "completed",
                "reviewed_by": "independent-review-agent",
                "reviewer_is_independent": True,
                "refutation_attempts": ["leakage", "alternative null", "cost stress"],
                "unresolved_critical_issues": [],
            },
        }
        self.assertEqual([], validate_report_payload(payload, known_ids={"L-1"}))


if __name__ == "__main__":
    unittest.main()
