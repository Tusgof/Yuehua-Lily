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


def _reviewed_v1_exception_root(root: Path) -> tuple[Path, Path, Path]:
    source = root / "lib" / "l3_b714_date_only_scanner_v1.py"
    exception = root / "experiments" / "l_3_b714_v1_noncredential_structural_byte_local_exception_v1.json"
    manifest = root / "experiments" / "locked_gates.jsonl"
    source.parent.mkdir(parents=True)
    exception.parent.mkdir(parents=True)
    source.write_bytes((PROJECT_ROOT / "lib" / "l3_b714_date_only_scanner_v1.py").read_bytes())
    exception.write_bytes((PROJECT_ROOT / "experiments" / "l_3_b714_v1_noncredential_structural_byte_local_exception_v1.json").read_bytes())
    manifest.write_text(json.dumps({"gate_id": "l_3_b714_date_only_preflight_activation_v2", "supersedes_gate_id": "l_3_b714_date_only_preflight_activation_v1"}) + "\n", encoding="utf-8")
    return source, exception, manifest


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

    def test_B7_manifest_done_claim_rejects_forged_artifact_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiments = root / "experiments"
            scripts = root / "scripts"
            experiments.mkdir()
            scripts.mkdir()
            gate = experiments / "l_3_inverse_volatility_sizing_preregistration_v1.json"
            validator = scripts / "validate_l_3_inverse_volatility_sizing_preregistration.py"
            gate.write_text("{}\n", encoding="utf-8")
            validator.write_text("pass\n", encoding="utf-8")
            row = {
                "gate_id": "l_3_inverse_volatility_sizing_v1",
                "gate_type": "preregistration",
                "artifact_path": "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json",
                "artifact_sha256": "0" * 64,
                "validator_path": "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py",
                "validator_sha256": hashlib.sha256(validator.read_bytes()).hexdigest(),
                "human_approval": "B7 planning only",
                "notes": "E0 edge none validation sealed B7.1 forbidden",
            }
            manifest = experiments / "locked_gates.jsonl"
            manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B7",
                "experiments/locked_gates.jsonl",
                "contain_l3_manifest_identity",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7:l3_manifest_artifact_hash_mismatch", blockers)

    def test_B7_registry_done_claim_rejects_incomplete_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "experiments" / "hypothesis_registry.json"
            registry.parent.mkdir()
            registry.write_text(json.dumps({"hypotheses": [{"id": "L-3", "status": "proposed"}]}), encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B7",
                "experiments/hypothesis_registry.json",
                "match_l3_registry_mirror",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7:l3_registry_status_or_edge_claim_mismatch", blockers)

    def test_B7_2_manifest_done_claim_rejects_forged_artifact_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiments = root / "experiments"
            scripts = root / "scripts"
            experiments.mkdir()
            scripts.mkdir()
            gate = experiments / "l_3_inverse_volatility_sizing_preregistration_v2.json"
            validator = scripts / "validate_l_3_inverse_volatility_sizing_preregistration_v2.py"
            gate.write_text("{}\n", encoding="utf-8")
            validator.write_text("pass\n", encoding="utf-8")
            row = {
                "gate_id": "l_3_inverse_volatility_sizing_v2",
                "gate_type": "preregistration",
                "artifact_path": "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json",
                "artifact_sha256": "0" * 64,
                "validator_path": "scripts/validate_l_3_inverse_volatility_sizing_preregistration_v2.py",
                "validator_sha256": hashlib.sha256(validator.read_bytes()).hexdigest(),
                "supersedes_gate_id": "l_3_inverse_volatility_sizing_v1",
                "notes": "hermetic source-provenance remediation",
            }
            manifest = experiments / "locked_gates.jsonl"
            manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B7.2",
                "experiments/locked_gates.jsonl",
                "contain_l3_v2_manifest_identity",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7.2:l3_v2_manifest_artifact_hash_mismatch", blockers)

    def test_B7_2_done_claim_rejects_incomplete_snapshot_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate = root / "experiments" / "l_3_inverse_volatility_sizing_preregistration_v2.json"
            gate.parent.mkdir()
            gate.write_text(json.dumps({"source_binding": {"methodology_snapshots": []}}), encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B7.2",
                "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json",
                "match_l3_v2_source_binding",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7.2:l3_v2_snapshot_declarations_mismatch", blockers)

    def test_B7_1_manifest_done_claim_rejects_forged_artifact_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiments = root / "experiments"
            scripts = root / "scripts"
            experiments.mkdir()
            scripts.mkdir()
            gate = experiments / "l_3_falsification_activation_preflight_v1.json"
            validator = scripts / "validate_l_3_falsification_activation_preflight_v1.py"
            gate.write_text("{}\n", encoding="utf-8")
            validator.write_text("from lib.io import load_json\n", encoding="utf-8")
            row = {
                "gate_id": "l_3_falsification_activation_preflight_v1",
                "gate_type": "activation_preflight_contract",
                "artifact_path": "experiments/l_3_falsification_activation_preflight_v1.json",
                "artifact_sha256": "0" * 64,
                "validator_path": "scripts/validate_l_3_falsification_activation_preflight_v1.py",
                "validator_sha256": hashlib.sha256(validator.read_bytes()).hexdigest(),
                "human_approval": "Owner explicitly authorized B7.1 gate only",
                "notes": "E0 edge_claim none sealed; neither data/container inspection nor execution",
            }
            manifest = experiments / "locked_gates.jsonl"
            manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B7.1",
                "experiments/locked_gates.jsonl",
                "contain_l3_b71_manifest_identity",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7.1:l3_b71_manifest_artifact_hash_mismatch", blockers)

    def test_B7_1_registry_done_claim_rejects_authorization_mirror_omission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "experiments" / "hypothesis_registry.json"
            registry.parent.mkdir()
            registry.write_text(
                json.dumps({"hypotheses": [{"id": "L-3", "status": "active", "edge_claim": "none", "evidence": []}]}),
                encoding="utf-8",
            )
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B7.1",
                "experiments/hypothesis_registry.json",
                "match_l3_b71_registry_mirror",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7.1:l3_b71_registry_E0_evidence_mismatch", blockers)
        self.assertIn("B7.1:l3_b71_registry_decision_log_missing", blockers)

    def test_B7_3_done_claim_rejects_fake_run_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "reports" / "experiments" / "l_3_falsification_report.json"
            ledger_path = root / "reports" / "experiments" / "l_3_falsification_execution_ledger.jsonl"
            authorization_path = root / "experiments" / "l_3_one_run_falsification_authorization_v1.json"
            report_path.parent.mkdir(parents=True)
            authorization_path.parent.mkdir(exist_ok=True)
            source_report = json.loads((PROJECT_ROOT / "reports/experiments/l_3_falsification_report.json").read_text(encoding="utf-8"))
            source_authorization = (PROJECT_ROOT / "experiments/l_3_one_run_falsification_authorization_v1.json").read_text(encoding="utf-8")
            source_ledger = (PROJECT_ROOT / "reports/experiments/l_3_falsification_execution_ledger.jsonl").read_text(encoding="utf-8")
            authorization_path.write_text(source_authorization, encoding="utf-8")
            source_report["authorization_sha256"] = hashlib.sha256(authorization_path.read_bytes()).hexdigest()
            report_path.write_text(json.dumps(source_report), encoding="utf-8")
            ledger_path.write_text(source_ledger + source_ledger, encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B7.3", "reports/experiments/l_3_falsification_report.json", "match_l3_b73_report_and_ledger",
                project_root=root, verify_runtime=False, runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7.3:l3_b73_exactly_one_run_ledger_mismatch", blockers)

    def test_B7_4_done_claim_rejects_original_ledger_row_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "reports" / "experiments" / "l_3_falsification_execution_ledger.jsonl"
            ledger.parent.mkdir(parents=True)
            lines = (PROJECT_ROOT / "reports/experiments/l_3_falsification_execution_ledger.jsonl").read_text(encoding="utf-8").splitlines()
            ledger.write_text(lines[0] + " " + "\n" + lines[1] + "\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B7.4", "reports/experiments/l_3_falsification_execution_ledger.jsonl", "match_l3_b74_ledger_state",
                project_root=root, verify_runtime=False, runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7.4:l3_b74_original_row_hash_mismatch", blockers)

    def test_B7_5_done_claim_rejects_forged_manifest_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "experiments" / "locked_gates.jsonl"
            manifest.parent.mkdir(parents=True)
            rows = [json.loads(line) for line in (PROJECT_ROOT / "experiments/locked_gates.jsonl").read_text(encoding="utf-8").splitlines() if line]
            row = next(item for item in rows if item.get("gate_id") == "l_3_corrected_rerun_pre_return_schedule_v1")
            row["artifact_sha256"] = "0" * 64
            manifest.write_text("\n".join(json.dumps(item, sort_keys=True) for item in rows) + "\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B7.5", "experiments/locked_gates.jsonl", "contain_l3_b75_manifest_identity",
                project_root=root, verify_runtime=False, runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7.5:l3_b75_manifest_artifact_hash_mismatch", blockers)

    def test_B7_historical_validator_claim_requires_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            validator = root / "scripts" / "validate_l_3_inverse_volatility_sizing_preregistration.py"
            historical_test = (
                root / "tests" / "test_validate_l_3_inverse_volatility_sizing_preregistration.py"
            )
            validator.parent.mkdir()
            historical_test.parent.mkdir()
            validator.write_text("pass\n", encoding="utf-8")
            historical_test.write_text("SNAPSHOT_WIKI_ROOT = None\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B7",
                "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py",
                "pass_with_l3_snapshots",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertTrue(unverified)
        self.assertIn(
            "B7:l3_v1_snapshot_hash_mismatch:"
            "methodology_snapshots/l3_inverse_volatility_sizing_v1/wiki/concepts/"
            "inverse-volatility-weighting.md",
            blockers,
        )

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

    def test_reviewed_v1_structural_byte_local_is_reported_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _reviewed_v1_exception_root(root)
            blockers, reviewed = self.validator._scan_active_artifacts(root, include_reviewed=True)
        self.assertEqual([], blockers)
        self.assertEqual(["noncredential_structural_byte_local"], [item["classification"] for item in reviewed])

    def test_reviewed_v1_exception_rejects_other_path_second_assignment_byte_mutation_and_missing_supersession(self) -> None:
        cases = (
            ("other_path", lambda source, exception, manifest: (source.rename(source.with_name("other.py")), None)),
            ("second_assignment", lambda source, exception, manifest: source.write_text(source.read_text(encoding="utf-8") + "\ntoken = self.raw[self.pos]\n", encoding="utf-8")),
            ("byte_mutation", lambda source, exception, manifest: source.write_text(source.read_text(encoding="utf-8") + "\n# byte mutation\n", encoding="utf-8")),
            ("missing_supersession", lambda source, exception, manifest: manifest.write_text("", encoding="utf-8")),
        )
        for name, mutate in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                source, exception, manifest = _reviewed_v1_exception_root(Path(tmp))
                mutate(source, exception, manifest)
                blockers = self.validator._scan_active_artifacts(Path(tmp))
                self.assertTrue(any("credential_like_assignment" in blocker for blocker in blockers), blockers)

    def test_reviewed_v1_exception_rejects_tamper_and_nonstructural_rhs(self) -> None:
        cases = (
            ("exception_tamper", lambda source, exception: exception.write_text(exception.read_text(encoding="utf-8").replace("Lily Inspector", "Other Reviewer"), encoding="utf-8")),
            ("string_rhs", lambda source, exception: source.write_text(source.read_text(encoding="utf-8").replace("self.raw[self.pos]", '"not-a-byte"', 1), encoding="utf-8")),
            ("environment_rhs", lambda source, exception: source.write_text(source.read_text(encoding="utf-8").replace("self.raw[self.pos]", "os.environ['TOKEN']", 1), encoding="utf-8")),
        )
        for name, mutate in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                source, exception, _ = _reviewed_v1_exception_root(Path(tmp))
                mutate(source, exception)
                blockers = self.validator._scan_active_artifacts(Path(tmp))
                self.assertTrue(any("credential_like_assignment" in blocker for blocker in blockers), blockers)

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

    def test_B48_supersession_rule_preserves_predecessor_and_checks_active_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiments = root / "experiments"
            scripts = root / "scripts"
            experiments.mkdir()
            scripts.mkdir()
            artifact = experiments / "l_1_shadow_accounting_activation_contract.json"
            validator = scripts / "validate_l_1_shadow_accounting_activation_contract.py"
            artifact.write_text(
                json.dumps({"order_id": "B4.9", "status": "locked_scope_decision_and_preview_probe"}),
                encoding="utf-8",
            )
            validator.write_text("print('pass')\n", encoding="utf-8")
            predecessor = {
                "gate_id": "l_1_shadow_accounting_activation_v1",
                "artifact_sha256": "62d23376a83823b6b710afb2dc74fdaf2f04d008c79a88a71a2b6dc06bff4d79",
                "validator_sha256": "8f0bce4261ad6bc26976eae4904152578de2e0b810a8103b2ec718526af67e55",
            }
            successor = {
                "gate_id": "l_1_shadow_accounting_activation_v2",
                "supersedes_gate_id": "l_1_shadow_accounting_activation_v1",
                "artifact_path": "experiments/l_1_shadow_accounting_activation_contract.json",
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "validator_path": "scripts/validate_l_1_shadow_accounting_activation_contract.py",
                "validator_sha256": hashlib.sha256(validator.read_bytes()).hexdigest(),
            }
            manifest = experiments / "locked_gates.jsonl"
            manifest.write_text(
                "\n".join(json.dumps(row) for row in (predecessor, successor)) + "\n",
                encoding="utf-8",
            )
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B4.8",
                "experiments/l_1_shadow_accounting_activation_contract.json",
                "superseded_by_l_1_shadow_accounting_activation_v2",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
            successor["supersedes_gate_id"] = "wrong_gate"
            manifest.write_text(
                "\n".join(json.dumps(row) for row in (predecessor, successor)) + "\n",
                encoding="utf-8",
            )
            broken, _, _ = self.validator._validate_done_artifact(
                "B4.8",
                "experiments/l_1_shadow_accounting_activation_contract.json",
                "superseded_by_l_1_shadow_accounting_activation_v2",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertEqual([], blockers)
        self.assertTrue(checked)
        self.assertFalse(unverified)
        self.assertIn("B4.8:shadow_accounting_supersession_link_mismatch", broken)

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

    def test_B413_scope_decision_requires_all_inspected_sources_and_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = root / "decision.md"
            record.write_text("unverified_reference\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B4.13",
                "decision.md",
                "match_webull_th_uat_scope_decision",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn(
            "B4.13:uat_scope_decision_missing:https://developer.webull.co.th/apis/docs/sdk.md",
            blockers,
        )

    def test_B414_project_memory_requires_closed_uat_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory = root / "brain.md"
            memory.write_text("B4.13 confirms\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B4.14",
                "brain.md",
                "match_uat_scope_project_memory",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B4.14:uat_scope_project_memory_missing:No UAT work is planned", blockers)

    def test_B415_ci_rule_requires_checkout_v5(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = root / "ci.yml"
            workflow.write_text(
                "push:\npull_request:\nactions/checkout@v4\nactions/setup-python@v6\npython scripts/run_test_tier.py hermetic\n",
                encoding="utf-8",
            )
            blockers, checked, unverified = self.validator._validate_done_artifact(
                "B4.15",
                "ci.yml",
                "use_checkout_v5_and_run_hermetic_on_push",
                project_root=root,
                verify_runtime=False,
                runtime_cache={},
            )
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B4.15:ci_missing:uses: actions/checkout@v5", blockers)

    def test_B714R8_done_claim_rejects_missing_gate_validator_snapshot_and_manifest(self) -> None:
        checks = (
            ("experiments/l_3_b714_date_only_preflight_remediation_v10.json", "validate_l3_b714r8_gate"),
            ("scripts/validate_l_3_b714_date_only_preflight_remediation_v10.py", "validate_l3_b714r8_validator"),
            ("experiments/l_3_b714r8_snapshot_index_v1.json", "validate_l3_b714r8_snapshots"),
            ("experiments/locked_gates.jsonl", "contain_l3_b714r8_manifest_identity"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path, must in checks:
                blockers, checked, unverified = self.validator._validate_done_artifact(
                    "B7.14R8", path, must, project_root=root, verify_runtime=False, runtime_cache={}
                )
                self.assertFalse(checked)
                self.assertFalse(unverified)
                self.assertTrue(blockers)

    def test_B715_registry_closure_rejects_missing_no_rerun_statement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "experiments" / "hypothesis_registry.json"
            registry.parent.mkdir()
            registry.write_text(
                json.dumps({"hypotheses": [{"id": "L-3", "status": "scope_restricted", "edge_claim": "none", "decision_log": [{"date": "2026-07-28", "decision": "B7_15_current_preregistration_closure_synchronized", "notes": "L-3 remains E1 scope_restricted and unresolved, not falsified or validated; validation is sealed; edge_claim none; no L-3 result may be carried forward as proof that inverse-volatility sizing passed."}]}]}),
                encoding="utf-8",
            )
            blockers, checked, unverified = self.validator._validate_done_artifact("B7.15", "experiments/hypothesis_registry.json", "match_l3_b715_closure", project_root=root, verify_runtime=False, runtime_cache={})
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7.15:l3_b715_registry_closure_missing:no rerun is planned under the current preregistration;", blockers)

    def test_B715_human_closure_rejects_validated_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "docs" / "HYPOTHESIS_REGISTRY.md"
            registry.parent.mkdir()
            registry.write_text("B7.15 current-preregistration closure: L-3 remains E1 scope_restricted and unresolved, validated; no rerun is planned under the current preregistration; validation is sealed; edge_claim none; no L-3 result may be carried forward as proof that inverse-volatility sizing passed.", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact("B7.15", "docs/HYPOTHESIS_REGISTRY.md", "match_l3_b715_closure", project_root=root, verify_runtime=False, runtime_cache={})
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7.15:l3_b715_closure_missing:and unresolved, not falsified or validated;", blockers)

    def test_B715_project_brain_rejects_missing_l4_only_next_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brain = root / "PROJECT_BRAIN.md"
            brain.write_text("B7.15 current-preregistration closure: L-3 remains E1 scope_restricted and unresolved, not falsified or validated; no rerun is planned under the current preregistration; validation is sealed; edge_claim none; no L-3 result may be carried forward as proof that inverse-volatility sizing passed.", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact("B7.15", "PROJECT_BRAIN.md", "match_l3_b715_closure", project_root=root, verify_runtime=False, runtime_cache={})
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7.15:l3_b715_project_brain_next_action_missing", blockers)

    def test_B715_implementation_plan_rejects_missing_l4_next_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "IMPLEMENT_PLAN.md"
            plan.write_text("B7.15 current-preregistration closure: L-3 remains E1 scope_restricted and unresolved, not falsified or validated; no rerun is planned under the current preregistration; validation is sealed; edge_claim none; no L-3 result may be carried forward as proof that inverse-volatility sizing passed.", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact("B7.15", "IMPLEMENT_PLAN.md", "match_l3_b715_closure", project_root=root, verify_runtime=False, runtime_cache={})
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B7.15:l3_b715_implementation_plan_next_gate_missing", blockers)

    def test_B8_registry_mirror_rejects_missing_e0_planning_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "experiments" / "hypothesis_registry.json"
            registry.parent.mkdir()
            registry.write_text(json.dumps({"hypotheses": [{"id": "L-4", "status": "active", "edge_claim": "none", "evidence": [], "decision_log": []}]}), encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact("B8", "experiments/hypothesis_registry.json", "match_l4_b8_mirror", project_root=root, verify_runtime=False, runtime_cache={})
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B8:l4_b8_registry_mirror_mismatch", blockers)

    def test_B8_manifest_claim_rejects_forged_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiments = root / "experiments"
            scripts = root / "scripts"
            experiments.mkdir()
            scripts.mkdir()
            (experiments / "l_4_breadth_preregistration_v1.json").write_text("{}", encoding="utf-8")
            (scripts / "validate_l_4_breadth_preregistration_v1.py").write_text("pass\n", encoding="utf-8")
            manifest = experiments / "locked_gates.jsonl"
            manifest.write_text(json.dumps({"gate_id": "l_4_breadth_v1", "gate_type": "E0_no_data_preregistration", "artifact_path": "experiments/l_4_breadth_preregistration_v1.json", "artifact_sha256": "0" * 64, "validator_path": "scripts/validate_l_4_breadth_preregistration_v1.py", "validator_sha256": "0" * 64, "human_approval": "L-4 planning only"}) + "\n", encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact("B8", "experiments/locked_gates.jsonl", "contain_l4_b8_manifest_identity", project_root=root, verify_runtime=False, runtime_cache={})
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B8:l4_b8_manifest_identity_mismatch", blockers)

    def test_B8_snapshot_claim_rejects_missing_or_forged_snapshot_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshots = root / "methodology_snapshots" / "l4_breadth_v1"
            snapshots.mkdir(parents=True)
            gate = root / "experiments" / "l_4_breadth_preregistration_v1.json"
            gate.parent.mkdir()
            gate.write_text(json.dumps({"source_binding": {"methodology_snapshots": []}}), encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact("B8", "methodology_snapshots/l4_breadth_v1", "match_l4_b8_snapshots", project_root=root, verify_runtime=False, runtime_cache={})
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B8:l4_b8_snapshot_declaration_mismatch", blockers)

    def test_B81_registry_mirror_requires_v2_remediation_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "experiments" / "hypothesis_registry.json"
            registry.parent.mkdir()
            registry.write_text(json.dumps({"hypotheses": [{"id": "L-4", "status": "active", "edge_claim": "none", "decision_log": []}]}), encoding="utf-8")
            blockers, checked, unverified = self.validator._validate_done_artifact("B8.1", "experiments/hypothesis_registry.json", "match_l4_b81_mirror", project_root=root, verify_runtime=False, runtime_cache={})
        self.assertFalse(checked)
        self.assertFalse(unverified)
        self.assertIn("B8.1:l4_b81_registry_mirror_mismatch", blockers)

    def test_B83_gate_drift_blocks_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate = root / "experiments/l_4_breadth_preregistration_v4.json"
            gate.parent.mkdir()
            payload = json.loads((PROJECT_ROOT / "experiments/l_4_breadth_preregistration_v4.json").read_text(encoding="utf-8"))
            payload["authorizations"]["data"] = True
            gate.write_text(json.dumps(payload), encoding="utf-8")
            blockers, checked, _ = self.validator._validate_l4_b83_gate(gate, "B8.3", "experiments/l_4_breadth_preregistration_v4.json", project_root=PROJECT_ROOT)
            self.assertFalse(checked)
            self.assertIn("B8.3:l4_b83_gate_validator_failed", blockers)

    def test_B83_manifest_drift_blocks_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "experiments").mkdir(); (root / "scripts").mkdir()
            (root / "experiments/l_4_breadth_preregistration_v4.json").write_text("{}", encoding="utf-8")
            (root / "scripts/validate_l_4_breadth_preregistration_v4.py").write_text("pass\n", encoding="utf-8")
            (root / "experiments/locked_gates.jsonl").write_text(json.dumps({"gate_id": "l_4_breadth_v4", "artifact_sha256": "0" * 64}) + "\n", encoding="utf-8")
            blockers, checked, _ = self.validator._validate_done_artifact("B8.3", "experiments/locked_gates.jsonl", "contain_l4_b83_manifest_identity", project_root=root, verify_runtime=False, runtime_cache={})
            self.assertFalse(checked)
            self.assertIn("B8.3:l4_b83_manifest_identity_mismatch", blockers)

    def test_B83_registry_drift_blocks_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root / "experiments/hypothesis_registry.json"; target.parent.mkdir()
            target.write_text(json.dumps({"hypotheses": [{"id": "L-4", "status": "active", "edge_claim": "none", "evidence": [], "decision_log": []}]}), encoding="utf-8")
            blockers, checked, _ = self.validator._validate_done_artifact("B8.3", "experiments/hypothesis_registry.json", "match_l4_b83_registry_mirror", project_root=root, verify_runtime=False, runtime_cache={})
            self.assertFalse(checked)
            self.assertIn("B8.3:l4_b83_registry_mirror_mismatch", blockers)

    def test_B83_human_registry_brain_and_plan_drift_block_done(self) -> None:
        cases = (("docs/HYPOTHESIS_REGISTRY.md", "match_l4_b83_human_registry_mirror", "human_registry"), ("PROJECT_BRAIN.md", "match_l4_b83_project_brain", "project_brain"), ("IMPLEMENT_PLAN.md", "match_l4_b83_implement_plan", "implement_plan"))
        for path, must, label in cases:
            with self.subTest(path=path), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); target = root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_text("B8.3 v4", encoding="utf-8")
                blockers, checked, _ = self.validator._validate_done_artifact("B8.3", path, must, project_root=root, verify_runtime=False, runtime_cache={})
                self.assertFalse(checked)
                self.assertTrue(any(f"B8.3:l4_b83_{label}_missing:" in blocker for blocker in blockers))

    def test_B83_script_registration_drift_blocks_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root / "config/new_code_scripts.json"; target.parent.mkdir()
            target.write_text(json.dumps({"scripts": []}), encoding="utf-8")
            blockers, checked, _ = self.validator._validate_done_artifact("B8.3", "config/new_code_scripts.json", "register_l4_b83_validator", project_root=root, verify_runtime=False, runtime_cache={})
            self.assertFalse(checked)
            self.assertIn("B8.3:l4_b83_script_registration_mismatch", blockers)

    def test_B84_manifest_drift_blocks_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "experiments").mkdir(); (root / "scripts").mkdir()
            (root / "experiments/l_4_breadth_b84_activation_contract_v1.json").write_text("{}", encoding="utf-8")
            (root / "scripts/validate_l_4_breadth_b84_activation_contract_v1.py").write_text("pass\n", encoding="utf-8")
            (root / "experiments/locked_gates.jsonl").write_text(json.dumps({"gate_id": "l_4_breadth_b84_activation_contract_v1", "activation_for_gate_id": "l_4_breadth_v4", "artifact_sha256": "0" * 64, "validator_sha256": "0" * 64}) + "\n", encoding="utf-8")
            blockers, checked, _ = self.validator._validate_done_artifact("B8.4", "experiments/locked_gates.jsonl", "contain_l4_b84_manifest", project_root=root, verify_runtime=False, runtime_cache={})
            self.assertFalse(checked)
            self.assertIn("B8.4:l4_b84_manifest_mismatch", blockers)

    def test_B84_script_registration_drift_blocks_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root / "config/new_code_scripts.json"; target.parent.mkdir()
            target.write_text(json.dumps({"scripts": []}), encoding="utf-8")
            blockers, checked, _ = self.validator._validate_done_artifact("B8.4", "config/new_code_scripts.json", "register_l4_b84_scripts", project_root=root, verify_runtime=False, runtime_cache={})
            self.assertFalse(checked)
            self.assertIn("B8.4:l4_b84_script_registration_mismatch", blockers)

    def test_B84R2_registration_and_mirror_drift_block_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); target = root / "config/new_code_scripts.json"; target.parent.mkdir()
            target.write_text(json.dumps({"scripts": []}), encoding="utf-8")
            blockers, checked, _ = self.validator._validate_done_artifact("B8.4R2", "config/new_code_scripts.json", "register_l4_b84r2_scripts", project_root=root, verify_runtime=False, runtime_cache={})
            self.assertFalse(checked); self.assertIn("B8.4R2:l4_b84r2_script_registration_mismatch", blockers)
            mirror = root / "PROJECT_BRAIN.md"; mirror.write_text("B8.4R2", encoding="utf-8")
            blockers, checked, _ = self.validator._validate_done_artifact("B8.4R2", "PROJECT_BRAIN.md", "match_l4_b84r2_mirror", project_root=root, verify_runtime=False, runtime_cache={})
            self.assertFalse(checked); self.assertIn("B8.4R2:l4_b84r2_mirror_mismatch", blockers)


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
