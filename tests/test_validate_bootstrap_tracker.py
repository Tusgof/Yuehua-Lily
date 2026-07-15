from __future__ import annotations

import importlib.util
import hashlib
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

    def test_b03_statistics_kernel_claim_requires_documented_primitives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "statistics.py").write_text(
                '"""raw Pearson kurtosis and finite-sample Bartlett conventions."""\n'
                "def probabilistic_sharpe_ratio(): pass\n",
                encoding="utf-8",
            )
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B0.3",
                "statistics.py",
                "document_conventions_and_exist",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn(
            "B0.3:statistics_kernel_missing:def independent_bet_equivalent_count",
            blockers,
        )

    def test_b03_conventions_claim_requires_source_hashes(self) -> None:
        required_text = "\n".join(
            (
                "Published-method anchor",
                "Offline library cross-check",
                "independent-bet",
                "Wiki-relative source",
                "SHA-256",
                "probabilistic-sharpe-ratio.md",
                "deflated-sharpe-ratio.md",
                "newey-west-validation.md",
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "conventions.md").write_text(required_text, encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B0.3",
                "conventions.md",
                "cite_published_anchors_and_independent_bets",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertEqual(
            ["B0.3:statistics_conventions_require_source_hashes"],
            blockers,
        )

    def test_b04_LF_claim_requires_all_hash_bound_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitattributes").write_text("*.json text eol=lf\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B0.4",
                ".gitattributes",
                "pin_lf_for_hash_bound_artifacts",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B0.4:gitattributes_missing:*.jsonl text eol=lf", blockers)

    def test_b05_restore_claim_requires_successful_checks(self) -> None:
        payload = {
            "schema_version": "lily_restore_rehearsal_v1",
            "outcome": "successful_committed_artifact_restore",
            "producing_git_commit": "a" * 40,
            "checks": {},
            "external_state": {
                "local_data": {"restore_status": "pending_no_data"},
                "machine_manifest": {"expected_in_clone": False},
                "local_llm_wiki": {"hash_verification": "pass"},
            },
            "temporary_clone_removed": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "restore.json").write_text(json.dumps(payload), encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B0.5",
                "restore.json",
                "record_successful_committed_artifact_restore",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B0.5:restore_check_not_pass:remote_clone", blockers)

    def test_B1_policy_claim_requires_ETF_and_futures_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "policy.md").write_text("inception and delisting", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B1",
                "policy.md",
                "cover_etf_and_futures_traps",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B1:data_integrity_policy_missing:continuous futures", blockers)

    def test_B1_fixture_claim_requires_roll_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "fixtures" / "data"
            data.mkdir(parents=True)
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B1",
                "fixtures",
                "contain_synthetic_data_fixtures",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn(
            "B1:synthetic_data_fixture_missing:provider_continuous_futures.json",
            blockers,
        )

    def test_B2_machine_report_rejects_wrong_minimum_capital(self) -> None:
        payload = {
            "schema_version": "lily_l0_sizing_feasibility_report_v1",
            "hypothesis_id": "L-0",
            "evidence_tier": "E0",
            "edge_claim": "none",
            "decision": "scope_restricted",
            "guardrails": {},
            "etf": {"broker_results": []},
            "futures": {"micro": [], "full_size_comparator": []},
            "source_inventory": [{}],
            "tier_blockers": ["test"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "report.json").write_text(json.dumps(payload), encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B2",
                "report.json",
                "classify_current_and_minimum_capital",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B2:l0_report_micro_capital_mismatch", blockers)
        self.assertIn("B2:l0_report_broker_scenarios_incomplete", blockers)

    def test_B2_markdown_claim_requires_machine_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_dir = root / "reports" / "feasibility"
            report_dir.mkdir(parents=True)
            (report_dir / "l_0_sizing_feasibility.json").write_text(
                json.dumps({"producing_git_commit": "a" * 40, "report_digest_sha256": "b" * 64}),
                encoding="utf-8",
            )
            (root / "report.md").write_text("scope_restricted\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B2",
                "report.md",
                "match_machine_report",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn(
            f"B2:l0_markdown_missing_machine_value:{'b' * 64}",
            blockers,
        )

    def test_B3_locked_rule_uses_L1_gate_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiments = root / "experiments"
            scripts = root / "scripts"
            experiments.mkdir()
            scripts.mkdir()
            artifact = experiments / "l_1_baseline_preregistration.json"
            validator = scripts / "validate_l_1_baseline_preregistration.py"
            artifact.write_text(
                json.dumps({"status": "locked_before_execution", "edge_claim_before_execution": "none"}),
                encoding="utf-8",
            )
            validator.write_text("print('pass')\n", encoding="utf-8")
            entry = {
                "gate_id": "l_1_baseline_v1",
                "artifact_path": "experiments/l_1_baseline_preregistration.json",
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "validator_path": "scripts/validate_l_1_baseline_preregistration.py",
                "validator_sha256": hashlib.sha256(validator.read_bytes()).hexdigest(),
            }
            manifest = experiments / "locked_gates.jsonl"
            manifest.write_text(json.dumps(entry) + "\n", encoding="utf-8")
            locked_blockers, locked_checked, locked_unverified = self.validator._validate_done_artifact(
                "B3",
                "experiments/l_1_baseline_preregistration.json",
                "locked_and_valid",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
            manifest_blockers, manifest_checked, manifest_unverified = self.validator._validate_done_artifact(
                "B3",
                "experiments/locked_gates.jsonl",
                "contain_active_l_1_hashes",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertEqual([], locked_blockers)
        self.assertTrue(locked_checked)
        self.assertFalse(locked_unverified)
        self.assertEqual([], manifest_blockers)
        self.assertTrue(manifest_checked)
        self.assertFalse(manifest_unverified)

    def test_B43_locked_rule_uses_alpha_vantage_gate_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiments = root / "experiments"
            scripts = root / "scripts"
            experiments.mkdir()
            scripts.mkdir()
            artifact = experiments / "l_1_alpha_vantage_corporate_actions_acquisition.json"
            validator = scripts / "validate_l_1_alpha_vantage_corporate_actions_acquisition.py"
            artifact.write_text(
                json.dumps({"status": "locked_before_acquisition", "edge_claim": "none"}),
                encoding="utf-8",
            )
            validator.write_text("print('pass')\n", encoding="utf-8")
            entry = {
                "gate_id": "l_1_alpha_vantage_corporate_actions_acquisition_v1",
                "artifact_path": "experiments/l_1_alpha_vantage_corporate_actions_acquisition.json",
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "validator_path": "scripts/validate_l_1_alpha_vantage_corporate_actions_acquisition.py",
                "validator_sha256": hashlib.sha256(validator.read_bytes()).hexdigest(),
            }
            manifest = experiments / "locked_gates.jsonl"
            manifest.write_text(json.dumps(entry) + "\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B4.3",
                "experiments/l_1_alpha_vantage_corporate_actions_acquisition.json",
                "locked_and_valid",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertEqual([], blockers)
        self.assertTrue(checked)
        self.assertFalse(unverified)

    def test_B31_format_requires_scoped_question_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "format.md").write_text("## 1. ข้อมูลพื้นฐาน\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B3.1",
                "format.md",
                "define_human_readable_research_log_contract",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn(
            "B3.1:research_log_format_missing:- คำถามวิจัย:",
            blockers,
        )

    def test_B31_legacy_note_must_be_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Note").mkdir()
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B3.1",
                "Note",
                "not_exist",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertEqual(["B3.1:forbidden_legacy_artifact_present:Note"], blockers)

    def test_B31_requirements_must_cover_L0_and_L1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements.json").write_text(
                json.dumps({"schema_version": "lily_research_log_requirements_v1", "entries": []}),
                encoding="utf-8",
            )
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B3.1",
                "requirements.json",
                "contain_l0_and_l1_research_log_requirements",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B3.1:research_log_requirement_inventory_mismatch", blockers)

    def test_B4_adversarial_status_does_not_fabricate_review_at_E1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review = root / "reports" / "adversarial" / "review.json"
            summary = root / "reports" / "experiments" / "l_1_baseline_summary.json"
            review.parent.mkdir(parents=True)
            summary.parent.mkdir(parents=True)
            review.write_text(json.dumps({"status": "not_started_E1_no_promotion", "promotion_requested": False, "reviewer_is_independent": False}), encoding="utf-8")
            summary.write_text(json.dumps({"evidence_tier": "E1"}), encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_l1_adversarial_status(
                review, "B4", "reports/adversarial/review.json", project_root=root
            )
        self.assertEqual([], blockers)
        self.assertTrue(checked)
        self.assertFalse(unverified)

    def test_B41_data_quality_markdown_requires_machine_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_dir = root / "reports" / "data_quality"
            report_dir.mkdir(parents=True)
            (report_dir / "l_1_data_quality_remediation.json").write_text(
                json.dumps({"producing_git_commit": "a" * 40, "report_digest_sha256": "b" * 64}),
                encoding="utf-8",
            )
            markdown = report_dir / "l_1_data_quality_remediation.md"
            markdown.write_text("E1 requires_account_observation not_documented\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B4.1",
                "reports/data_quality/l_1_data_quality_remediation.md",
                "match_data_quality_machine_report",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn(
            f"B4.1:l1_data_quality_markdown_missing_machine_value:{'b' * 64}",
            blockers,
        )

    def test_B42_validation_capacity_markdown_requires_machine_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_dir = root / "reports" / "diagnostics"
            report_dir.mkdir(parents=True)
            (report_dir / "l_1_validation_capacity.json").write_text(
                json.dumps({"producing_git_commit": "a" * 40, "report_digest_sha256": "b" * 64}),
                encoding="utf-8",
            )
            markdown = report_dir / "l_1_validation_capacity.md"
            markdown.write_text("E1 8,673 Databento\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B4.2",
                "reports/diagnostics/l_1_validation_capacity.md",
                "match_validation_capacity_machine_report",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn(
            f"B4.2:l1_validation_capacity_markdown_missing_machine_value:{'b' * 64}",
            blockers,
        )

    def test_B42_cost_ledger_rejects_paid_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ledger.json"
            ledger.write_text(
                json.dumps(
                    {
                        "schema_version": "lily_data_cost_ledger_v1",
                        "actual_cumulative_paid_spend_usd": 1,
                        "entries": [],
                    }
                ),
                encoding="utf-8",
            )
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B4.2",
                "ledger.json",
                "record_zero_spend_metadata_probe",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B4.2:cost_ledger_nonzero_spend", blockers)


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
