from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACKER = PROJECT_ROOT / "experiments" / "bootstrap_tracker.json"
VALID_STATUSES = {"not_started", "in_progress", "done", "blocked"}
SUPPORTED_PYTHON_LINE = (3, 14)
TEXT_SUFFIXES = {
    "",
    ".css",
    ".env",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_PARTS = {".git", ".venv", "Backup_", "__pycache__", "venv"}
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)(?<![A-Za-z0-9])[A-Z]:[\\/]")
FILE_URI = re.compile("(?i)" + "file" + "://")
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
HIGH_RISK_VALUE_PATTERN = re.compile(
    r"(?i)\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b|\bAKIA[0-9A-Z]{16}\b"
)
SENSITIVE_ASSIGNMENT = re.compile(
    r'''(?im)^\s*["']?([A-Z0-9_]*(?:API_KEY|APP_KEY|SECRET|TOKEN|PASSWORD|ACCOUNT_ID)[A-Z0-9_]*)["']?\s*[:=]\s*["']?([^"'# ,\s]+)'''
)
PLACEHOLDER_VALUES = {"", "null", "none", "false", "true", "placeholder", "changeme", "example", "not_set"}


def validate_tracker(
    path: Path = DEFAULT_TRACKER,
    *,
    project_root: Path = PROJECT_ROOT,
    verify_runtime: bool = False,
) -> dict[str, Any]:
    blockers: list[str] = []
    checked: list[dict[str, str]] = []
    unverified: list[dict[str, str]] = []
    payload = _load_tracker(path, blockers)
    if payload is None:
        return _result("fail", path, blockers, checked, unverified)

    orders = payload.get("orders")
    if not isinstance(orders, list):
        blockers.append("orders_must_be_list")
        return _result("fail", path, blockers, checked, unverified)

    seen: set[str] = set()
    statuses: dict[str, str] = {}
    for index, order in enumerate(orders):
        if not isinstance(order, dict):
            blockers.append(f"order_{index}_must_be_object")
            continue
        order_id = order.get("id")
        if not isinstance(order_id, str) or not order_id:
            blockers.append(f"order_{index}_missing_id")
            continue
        if order_id in seen:
            blockers.append(f"duplicate_order_id:{order_id}")
        seen.add(order_id)
        status = order.get("status")
        if status not in VALID_STATUSES:
            blockers.append(f"{order_id}:invalid_status:{status}")
        else:
            statuses[order_id] = status
        required = order.get("required_artifacts")
        if not isinstance(required, list) or not required:
            blockers.append(f"{order_id}:required_artifacts_must_be_nonempty_list")
        else:
            for artifact in required:
                if not isinstance(artifact, dict):
                    blockers.append(f"{order_id}:artifact_must_be_object")
                    continue
                if not isinstance(artifact.get("path"), str) or not artifact["path"]:
                    blockers.append(f"{order_id}:artifact_missing_path")
                if not isinstance(artifact.get("must"), str) or not artifact["must"]:
                    blockers.append(f"{order_id}:artifact_missing_must")
        dependencies = order.get("depends_on")
        if not isinstance(dependencies, list) or any(not isinstance(item, str) for item in dependencies):
            blockers.append(f"{order_id}:depends_on_must_be_string_list")
        forbidden = order.get("forbidden")
        if not isinstance(forbidden, list) or not forbidden:
            blockers.append(f"{order_id}:forbidden_must_be_nonempty_list")
        evidence = order.get("evidence")
        if not isinstance(evidence, list):
            blockers.append(f"{order_id}:evidence_must_be_list")
        elif status == "done" and not evidence:
            blockers.append(f"{order_id}:done_requires_evidence")

    runtime_cache: dict[str, bool] = {}
    for order in orders:
        if not isinstance(order, dict) or not isinstance(order.get("id"), str):
            continue
        order_id = order["id"]
        dependencies = order.get("depends_on", [])
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if dependency not in seen:
                    blockers.append(f"{order_id}:unknown_dependency:{dependency}")
                elif order.get("status") == "done" and statuses.get(dependency) != "done":
                    blockers.append(f"{order_id}:done_dependency_not_done:{dependency}")
        if order.get("status") != "done":
            continue
        for artifact in order.get("required_artifacts", []):
            if not isinstance(artifact, dict):
                continue
            artifact_path = str(artifact.get("path", ""))
            must = str(artifact.get("must", ""))
            artifact_blockers, was_checked, was_unverified = _validate_done_artifact(
                order_id,
                artifact_path,
                must,
                project_root=project_root,
                verify_runtime=verify_runtime,
                runtime_cache=runtime_cache,
            )
            blockers.extend(artifact_blockers)
            entry = {"order": order_id, "path": artifact_path, "must": must}
            if was_checked:
                checked.append(entry)
            if was_unverified:
                unverified.append(entry | {"reason": "runtime_checks_disabled"})

    return _result("fail" if blockers else "pass", path, blockers, checked, unverified)


def _load_tracker(path: Path, blockers: list[str]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        blockers.append(f"tracker_missing:{path}")
        return None
    except json.JSONDecodeError as exc:
        blockers.append(f"tracker_invalid_json:{exc}")
        return None
    if not isinstance(payload, dict):
        blockers.append("tracker_must_be_object")
        return None
    if payload.get("schema_version") != "lily_bootstrap_tracker_v1":
        blockers.append(f"invalid_schema_version:{payload.get('schema_version')}")
    if not isinstance(payload.get("done_claim_rule"), str) or not payload["done_claim_rule"].strip():
        blockers.append("done_claim_rule_missing")
    return payload


def _validate_done_artifact(
    order_id: str,
    artifact_path: str,
    must: str,
    *,
    project_root: Path,
    verify_runtime: bool,
    runtime_cache: dict[str, bool],
) -> tuple[list[str], bool, bool]:
    target = (project_root / artifact_path).resolve()
    if must == "exist":
        exists = target.exists()
        return ([] if exists else [f"{order_id}:missing_artifact:{artifact_path}"], exists, False)
    if must == "pass":
        if not target.is_file():
            return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
        if target == Path(__file__).resolve():
            return [], True, False
        if not verify_runtime:
            return [], False, True
        completed = subprocess.run(
            [sys.executable, str(target)],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        return (
            [] if completed.returncode == 0 else [f"{order_id}:artifact_command_failed:{artifact_path}"],
            completed.returncode == 0,
            False,
        )
    if must in {"pass_in_hermetic_tier", "pass_hermetic_tier"}:
        if not target.exists():
            return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
        if not verify_runtime:
            return [], False, True
        passed = _run_hermetic_once(project_root, runtime_cache)
        return ([] if passed else [f"{order_id}:hermetic_tier_failed"], passed, False)
    if must == "pass_all_available_tiers":
        if not target.is_file():
            return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
        if not verify_runtime:
            return [], False, True
        passed = _run_all_tiers_once(project_root, runtime_cache)
        return ([] if passed else [f"{order_id}:all_test_tiers_failed"], passed, False)
    if must == "run_hermetic_on_push":
        return _validate_ci(target, order_id, artifact_path)
    if must == "use_checkout_v5_and_run_hermetic_on_push":
        return _validate_ci_checkout_v5(target, order_id, artifact_path)
    if must == "match_webull_th_uat_scope_decision":
        return _validate_webull_th_uat_scope_decision(target, order_id, artifact_path)
    if must == "match_uat_scope_project_memory":
        return _validate_uat_scope_project_memory(target, order_id, artifact_path)
    if must == "match_uat_scope_implementation_plan":
        return _validate_uat_scope_implementation_plan(target, order_id, artifact_path)
    if must == "pin_supported_python":
        return _validate_python_pin(target, order_id, artifact_path)
    if must == "declare_python_and_dependencies":
        return _validate_pyproject(target, project_root, order_id, artifact_path)
    if must == "contain_placeholders_only":
        return _validate_machine_example(target, order_id, artifact_path)
    if must == "contain_environment_io_timestamp_provenance_guardrail_report_search_modules":
        return _validate_lib_skeleton(target, order_id, artifact_path)
    if must == "contain_hermetic_lib_unit_tests":
        return _validate_lib_tests(target, order_id, artifact_path)
    if must == "document_conventions_and_exist":
        return _validate_statistics_kernel(target, order_id, artifact_path)
    if must == "cite_published_anchors_and_independent_bets":
        return _validate_statistics_conventions(target, order_id, artifact_path)
    if must == "pin_lf_for_hash_bound_artifacts":
        return _validate_lf_attributes(target, order_id, artifact_path)
    if must == "contain_registry_tier_and_locked_gate_tests":
        return _validate_governance_tests(target, order_id, artifact_path)
    if must == "require_adversarial_review_for_E2":
        return _validate_evidence_policy(target, order_id, artifact_path)
    if must == "record_successful_committed_artifact_restore":
        return _validate_restore_rehearsal(target, order_id, artifact_path)
    if must == "cover_etf_and_futures_traps":
        return _validate_data_integrity_policy(target, order_id, artifact_path)
    if must == "contain_provider_boundary_schemas":
        return _validate_provider_boundary_schemas(target, order_id, artifact_path)
    if must == "contain_synthetic_data_fixtures":
        return _validate_synthetic_data_fixtures(target, order_id, artifact_path)
    if must == "superseded_by_l_1_shadow_accounting_activation_v2":
        return _validate_shadow_accounting_gate_supersession(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
        )
    if must == "locked_and_valid":
        if artifact_path == "experiments/l_0_webull_th_fractional_preview_activation_v2.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_0_webull_th_fractional_preview_activation_v2",
                label="l0_webull_th_fractional_preview_activation_v2",
                expected_status="locked_execution_authorized",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_0_webull_th_fractional_preview_activation.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_0_webull_th_fractional_preview_activation_v1",
                label="l0_webull_th_fractional_preview_activation",
                expected_status="locked_execution_authorized",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_0_webull_th_fractional_preview_probe.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_0_webull_th_fractional_preview_probe_v1",
                label="l0_webull_th_fractional_preview_probe",
                expected_status="locked_machinery_ready_execution_not_authorized",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_1_shadow_accounting_activation_contract.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id=(
                    "l_1_shadow_accounting_activation_v2"
                    if order_id == "B4.9"
                    else "l_1_shadow_accounting_activation_v1"
                ),
                label="l1_shadow_accounting_activation",
                expected_status=(
                    "locked_scope_decision_and_preview_probe"
                    if order_id == "B4.9"
                    else "locked_activation_blocked"
                ),
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_1_prospective_shadow_accounting_preregistration.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_1_prospective_shadow_accounting_v1",
                label="l1_prospective_shadow_accounting",
                expected_status="locked_before_observation",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_0_webull_th_read_only_capability_probe.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_0_webull_th_read_only_capability_probe_v1",
                label="l0_webull_th_read_only_capability",
                expected_status="locked_before_probe",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_1_alpha_vantage_corporate_actions_acquisition.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_1_alpha_vantage_corporate_actions_acquisition_v1",
                label="l1_alpha_vantage_corporate_actions",
                expected_status="locked_before_acquisition",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_1_data_quality_remediation.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_1_data_quality_remediation_v1",
                label="l1_data_quality",
                expected_status="locked_before_remediation_measurement",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_1_baseline_preregistration.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_1_baseline_v1",
                label="l1",
                expected_status="locked_before_execution",
                edge_claim_field="edge_claim_before_execution",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_2_multi_lookback_tstat_preregistration.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_2_multi_lookback_tstat_v1",
                label="l2_multi_lookback_tstat",
                expected_status="locked_before_execution",
                edge_claim_field="edge_claim_before_execution",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_2_multi_lookback_tstat_preregistration_v2.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_2_multi_lookback_tstat_v2",
                label="l2_multi_lookback_tstat_v2",
                expected_status="locked_before_execution",
                edge_claim_field="edge_claim_before_execution",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_2_multi_lookback_tstat_preregistration_v3.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_2_multi_lookback_tstat_v3",
                label="l2_multi_lookback_tstat_v3",
                expected_status="locked_before_execution",
                edge_claim_field="edge_claim_before_execution",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        return _validate_l0_locked_gate(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
        )
    if must == "contain_active_l_1_hashes":
        return _validate_l1_manifest(target, order_id, artifact_path, project_root=project_root)
    if must == "define_human_readable_research_log_contract":
        return _validate_research_log_format(target, order_id, artifact_path)
    if must == "contain_l0_and_l1_research_log_requirements":
        return _validate_research_log_requirements(target, order_id, artifact_path)
    if must == "pass_research_log_audit":
        return _validate_research_log(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
            runtime_cache=runtime_cache,
        )
    if must == "pass_data_quality_remediation_validator":
        return _validate_l1_data_quality_runtime(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
            runtime_cache=runtime_cache,
        )
    if must == "match_data_quality_machine_report":
        return _validate_l1_data_quality_markdown(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
        )
    if must == "pass_validation_capacity_validator":
        return _validate_l1_validation_capacity_runtime(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
            runtime_cache=runtime_cache,
        )
    if must == "match_validation_capacity_machine_report":
        return _validate_l1_validation_capacity_markdown(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
        )
    if must == "record_zero_spend_metadata_probe":
        return _validate_zero_spend_metadata_probe(target, order_id, artifact_path)
    if must == "pass_alpha_vantage_corporate_actions_report_validator":
        return _validate_alpha_vantage_report_runtime(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
            runtime_cache=runtime_cache,
        )
    if must == "match_alpha_vantage_corporate_actions_machine_report":
        return _validate_alpha_vantage_markdown(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
        )
    if must == "contain_alpha_vantage_corporate_action_datasets":
        return _validate_alpha_vantage_registry(target, order_id, artifact_path)
    if must == "record_zero_spend_alpha_vantage_acquisition":
        return _validate_alpha_vantage_cost_ledger(target, order_id, artifact_path)
    if must == "pass_corporate_action_scope_decision_validator":
        return _validate_corporate_action_scope_decision_runtime(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
            runtime_cache=runtime_cache,
        )
    if must == "match_corporate_action_scope_decision":
        return _validate_corporate_action_scope_decision_markdown(target, order_id, artifact_path)
    if must == "pass_webull_th_read_only_capability_report_validator":
        return _validate_webull_th_read_only_capability_report_runtime(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
            runtime_cache=runtime_cache,
        )
    if must == "match_webull_th_read_only_capability_report":
        return _validate_webull_th_read_only_capability_markdown(target, order_id, artifact_path)
    if must == "pass_fractional_preview_report_validator":
        return _validate_fractional_preview_report_runtime(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
            runtime_cache=runtime_cache,
        )
    if must == "pass_fractional_preview_report_validator_v2":
        return _validate_fractional_preview_report_v2_runtime(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
            runtime_cache=runtime_cache,
        )
    if must == "pass_summary_validator":
        return _validate_l1_summary_runtime(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
            runtime_cache=runtime_cache,
        )
    if must == "exist_before_E2":
        return _validate_l1_adversarial_status(target, order_id, artifact_path, project_root=project_root)
    if must == "not_exist":
        absent = not target.exists()
        return ([] if absent else [f"{order_id}:forbidden_legacy_artifact_present:{artifact_path}"], absent, False)
    if must == "classify_current_and_minimum_capital":
        return _validate_l0_machine_report(target, order_id, artifact_path)
    if must == "match_machine_report":
        if order_id == "B4":
            return _validate_l1_markdown_report(target, order_id, artifact_path, project_root=project_root)
        return _validate_l0_markdown_report(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
        )
    if must == "no_active_absolute_paths_or_credentials_excluding_immutable_backup_history":
        blockers = _scan_active_artifacts(project_root)
        return ([f"{order_id}:{item}" for item in blockers], not blockers, False)
    return [f"{order_id}:unsupported_done_rule:{must}"], False, False


def _validate_l1_data_quality_runtime(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
    runtime_cache: dict[str, bool],
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    if not verify_runtime:
        return [], False, True
    if "l1_data_quality" not in runtime_cache:
        completed = subprocess.run(
            [sys.executable, "scripts/validate_l_1_data_quality_report.py"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        runtime_cache["l1_data_quality"] = completed.returncode == 0
    passed = runtime_cache["l1_data_quality"]
    return ([] if passed else [f"{order_id}:l1_data_quality_validator_failed"], passed, False)


def _validate_l1_validation_capacity_runtime(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
    runtime_cache: dict[str, bool],
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    if not verify_runtime:
        return [], False, True
    if "l1_validation_capacity" not in runtime_cache:
        completed = subprocess.run(
            [sys.executable, "scripts/validate_l_1_validation_capacity.py"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        runtime_cache["l1_validation_capacity"] = completed.returncode == 0
    passed = runtime_cache["l1_validation_capacity"]
    return ([] if passed else [f"{order_id}:l1_validation_capacity_validator_failed"], passed, False)


def _validate_alpha_vantage_report_runtime(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
    runtime_cache: dict[str, bool],
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    if not verify_runtime:
        return [], False, True
    if "alpha_vantage_corporate_actions" not in runtime_cache:
        completed = subprocess.run(
            [sys.executable, "scripts/validate_l_1_alpha_vantage_corporate_actions_report.py"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        runtime_cache["alpha_vantage_corporate_actions"] = completed.returncode == 0
    passed = runtime_cache["alpha_vantage_corporate_actions"]
    return ([] if passed else [f"{order_id}:alpha_vantage_report_validator_failed"], passed, False)


def _validate_alpha_vantage_markdown(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        report = json.loads(
            (project_root / "reports" / "data_quality" / "l_1_alpha_vantage_corporate_actions.json")
            .read_text(encoding="utf-8")
        )
        markdown = target.read_text(encoding="utf-8")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"{order_id}:alpha_vantage_report_pair_unreadable:{exc.__class__.__name__}"], False, False
    required = (
        str(report.get("producing_git_commit", "")),
        str(report.get("report_digest_sha256", "")),
        "E1",
        "scope_restricted_no_point_in_time_revision_archive",
        "sealed_not_accessed",
        "USD 0",
    )
    missing = [value for value in required if not value or value not in markdown]
    blockers = [f"{order_id}:alpha_vantage_markdown_missing_machine_value:{value}" for value in missing]
    return blockers, not blockers, False


def _validate_alpha_vantage_registry(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:dataset_registry_invalid_json"], False, False
    rows = {row.get("dataset_id"): row for row in payload.get("datasets", []) if isinstance(row, dict)}
    raw = rows.get("l1.alpha_vantage.corporate_actions.raw.v1", {})
    normalized = rows.get("l1.alpha_vantage.corporate_actions.normalized.v1", {})
    blockers: list[str] = []
    if raw.get("status") != "scope_restricted" or normalized.get("status") != "scope_restricted":
        blockers.append(f"{order_id}:alpha_vantage_registry_status_mismatch")
    if normalized.get("parent_dataset_ids") != ["l1.alpha_vantage.corporate_actions.raw.v1"]:
        blockers.append(f"{order_id}:alpha_vantage_registry_parent_mismatch")
    if raw.get("acquisition", {}).get("paid_amount_usd") != 0 or normalized.get("acquisition", {}).get("paid_amount_usd") != 0:
        blockers.append(f"{order_id}:alpha_vantage_registry_paid_spend_mismatch")
    return blockers, not blockers, False


def _validate_alpha_vantage_cost_ledger(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:cost_ledger_invalid_json"], False, False
    blockers: list[str] = []
    if payload.get("actual_cumulative_paid_spend_usd") != 0:
        blockers.append(f"{order_id}:cost_ledger_nonzero_spend")
    rows = [row for row in payload.get("entries", []) if isinstance(row, dict) and row.get("order_id") == "B4.4"]
    if len(rows) != 1:
        blockers.append(f"{order_id}:cost_ledger_B4_4_entry_mismatch")
    else:
        row = rows[0]
        if row.get("key_environment_name") != "ALPHAVANTAGE_API_FREE":
            blockers.append(f"{order_id}:cost_ledger_alpha_key_provenance_mismatch")
        if row.get("actual_paid_amount_usd") != 0 or row.get("network_attempt_count") != 16:
            blockers.append(f"{order_id}:cost_ledger_alpha_acquisition_mismatch")
        if row.get("market_price_or_return_data_downloaded") is not False or row.get("validation_returns_opened") is not False:
            blockers.append(f"{order_id}:cost_ledger_alpha_boundary_mismatch")
    return blockers, not blockers, False


def _validate_corporate_action_scope_decision_runtime(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
    runtime_cache: dict[str, bool],
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    if not verify_runtime:
        return [], False, True
    if "corporate_action_scope_decision" not in runtime_cache:
        completed = subprocess.run(
            [sys.executable, "scripts/validate_l_1_corporate_action_scope_decision.py"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        runtime_cache["corporate_action_scope_decision"] = completed.returncode == 0
    passed = runtime_cache["corporate_action_scope_decision"]
    return ([] if passed else [f"{order_id}:corporate_action_scope_decision_validator_failed"], passed, False)


def _validate_corporate_action_scope_decision_markdown(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = (
        "accepted by the owner",
        "E1 scope_restricted",
        "sealed_not_accessed",
        "E0 operational dry run",
        "edge_claim: none",
        "ไม่อนุญาตให้เริ่ม paper trade ทันที",
        "Webull Thailand capability probe",
    )
    missing = [value for value in required if value not in text]
    blockers = [f"{order_id}:corporate_action_scope_decision_markdown_missing:{value}" for value in missing]
    return blockers, not blockers, False


def _validate_webull_th_read_only_capability_report_runtime(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
    runtime_cache: dict[str, bool],
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    if not verify_runtime:
        return [], False, True
    if "webull_th_read_only_capability_report" not in runtime_cache:
        completed = subprocess.run(
            [sys.executable, "scripts/validate_l_0_webull_th_read_only_capability_report.py"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        runtime_cache["webull_th_read_only_capability_report"] = completed.returncode == 0
    passed = runtime_cache["webull_th_read_only_capability_report"]
    return ([] if passed else [f"{order_id}:webull_th_read_only_capability_report_validator_failed"], passed, False)


def _validate_webull_th_read_only_capability_markdown(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = (
        "verified_read_only_and_fractional_candidate_set",
        "validation returns: `sealed_not_accessed`",
        "| VTI | OC | true |",
        "| VNQI | OC | true |",
        "ไม่มีการเรียก preview/place/replace/cancel order",
        "E0 prospective shadow accounting dry run",
    )
    missing = [value for value in required if value not in text]
    blockers = [f"{order_id}:webull_th_read_only_capability_markdown_missing:{value}" for value in missing]
    return blockers, not blockers, False


def _validate_fractional_preview_report_runtime(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
    runtime_cache: dict[str, bool],
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    if not verify_runtime:
        return [], False, True
    if "fractional_preview_report" not in runtime_cache:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/validate_l_0_webull_th_fractional_preview_report.py",
                "--report",
                artifact_path,
            ],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        runtime_cache["fractional_preview_report"] = completed.returncode == 0
    passed = runtime_cache["fractional_preview_report"]
    return ([] if passed else [f"{order_id}:fractional_preview_report_validator_failed"], passed, False)


def _validate_fractional_preview_report_v2_runtime(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
    runtime_cache: dict[str, bool],
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    if not verify_runtime:
        return [], False, True
    if "fractional_preview_report_v2" not in runtime_cache:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/validate_l_0_webull_th_fractional_preview_report_v2.py",
                "--report",
                artifact_path,
            ],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        runtime_cache["fractional_preview_report_v2"] = completed.returncode == 0
    passed = runtime_cache["fractional_preview_report_v2"]
    return ([] if passed else [f"{order_id}:fractional_preview_report_v2_validator_failed"], passed, False)


def _validate_l1_validation_capacity_markdown(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(
            (project_root / "reports" / "diagnostics" / "l_1_validation_capacity.json").read_text(
                encoding="utf-8"
            )
        )
        markdown = target.read_text(encoding="utf-8")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"{order_id}:l1_validation_capacity_pair_unreadable:{exc.__class__.__name__}"], False, False
    required = (
        str(payload.get("producing_git_commit", "")),
        str(payload.get("report_digest_sha256", "")),
        "E1",
        "8,673",
        "Databento",
    )
    missing = [value for value in required if not value or value not in markdown]
    blockers = [f"{order_id}:l1_validation_capacity_markdown_missing_machine_value:{value}" for value in missing]
    return blockers, not blockers, False


def _validate_zero_spend_metadata_probe(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:cost_ledger_invalid_json"], False, False
    blockers: list[str] = []
    if payload.get("schema_version") != "lily_data_cost_ledger_v1":
        blockers.append(f"{order_id}:cost_ledger_schema_mismatch")
    if payload.get("actual_cumulative_paid_spend_usd") != 0:
        blockers.append(f"{order_id}:cost_ledger_nonzero_spend")
    entries = payload.get("entries", [])
    matching = [row for row in entries if isinstance(row, dict) and row.get("order_id") == "B4.2"]
    if len(matching) != 1:
        blockers.append(f"{order_id}:cost_ledger_B4_2_entry_mismatch")
    else:
        entry = matching[0]
        if entry.get("key_environment_name") != "DATABENTO_API_02":
            blockers.append(f"{order_id}:cost_ledger_key_provenance_mismatch")
        if entry.get("actual_paid_amount_usd") != 0 or entry.get("market_data_downloaded") is not False:
            blockers.append(f"{order_id}:cost_ledger_probe_boundary_mismatch")
        if entry.get("credit_real_payment_status") != "unverified":
            blockers.append(f"{order_id}:cost_ledger_real_payment_status_mismatch")
    return blockers, not blockers, False


def _validate_l1_data_quality_markdown(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(
            (project_root / "reports" / "data_quality" / "l_1_data_quality_remediation.json").read_text(
                encoding="utf-8"
            )
        )
        markdown = target.read_text(encoding="utf-8")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"{order_id}:l1_data_quality_report_pair_unreadable:{exc.__class__.__name__}"], False, False
    required = (
        str(payload.get("producing_git_commit", "")),
        str(payload.get("report_digest_sha256", "")),
        "E1",
        "requires_account_observation",
        "not_documented",
    )
    missing = [value for value in required if not value or value not in markdown]
    blockers = [f"{order_id}:l1_data_quality_markdown_missing_machine_value:{value}" for value in missing]
    return blockers, not blockers, False


def _validate_l1_summary_runtime(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
    runtime_cache: dict[str, bool],
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    if not verify_runtime:
        return [], False, True
    if "l1_summary" not in runtime_cache:
        completed = subprocess.run(
            [sys.executable, "scripts/validate_l_1_baseline_summary.py"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        runtime_cache["l1_summary"] = completed.returncode == 0
    passed = runtime_cache["l1_summary"]
    return ([] if passed else [f"{order_id}:l1_summary_validator_failed"], passed, False)


def _validate_l1_markdown_report(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads((project_root / "reports" / "experiments" / "l_1_baseline_summary.json").read_text(encoding="utf-8"))
        markdown = target.read_text(encoding="utf-8")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"{order_id}:l1_report_pair_unreadable:{exc.__class__.__name__}"], False, False
    required = (
        str(payload.get("producing_git_commit", "")),
        str(payload.get("report_digest_sha256", "")),
        "E1",
        "sealed_not_accessed",
        "ไม่ยืนยันว่ามี edge",
    )
    missing = [value for value in required if not value or value not in markdown]
    blockers = [f"{order_id}:l1_markdown_missing_machine_value:{value}" for value in missing]
    return blockers, not blockers, False


def _validate_l1_adversarial_status(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        review = json.loads(target.read_text(encoding="utf-8"))
        summary = json.loads((project_root / "reports" / "experiments" / "l_1_baseline_summary.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"{order_id}:l1_adversarial_pair_unreadable:{exc.__class__.__name__}"], False, False
    blockers: list[str] = []
    if summary.get("evidence_tier") == "E1":
        if review.get("status") != "not_started_E1_no_promotion" or review.get("promotion_requested") is not False:
            blockers.append(f"{order_id}:l1_E1_review_status_invalid")
    elif summary.get("evidence_tier") == "E2":
        if review.get("status") != "completed" or review.get("reviewer_is_independent") is not True:
            blockers.append(f"{order_id}:l1_E2_requires_independent_review")
        if review.get("unresolved_critical_issues"):
            blockers.append(f"{order_id}:l1_E2_review_has_critical_issues")
    else:
        blockers.append(f"{order_id}:l1_evidence_tier_invalid")
    return blockers, not blockers, False


def _validate_l0_locked_gate(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
) -> tuple[list[str], bool, bool]:
    return _validate_locked_preregistration_gate(
        target,
        order_id,
        artifact_path,
        gate_id="l_0_sizing_feasibility_v1",
        label="l0",
        expected_status="locked_before_measurement",
        edge_claim_field="edge_claim",
        project_root=project_root,
        verify_runtime=verify_runtime,
    )


def _validate_locked_preregistration_gate(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    gate_id: str,
    label: str,
    expected_status: str,
    edge_claim_field: str,
    project_root: Path,
    verify_runtime: bool,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    blockers: list[str] = []
    try:
        preregistration = json.loads(target.read_text(encoding="utf-8"))
        rows = [
            json.loads(line)
            for line in (project_root / "experiments" / "locked_gates.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"{order_id}:{label}_locked_gate_unreadable:{exc.__class__.__name__}"], False, False
    matching = [row for row in rows if row.get("gate_id") == gate_id]
    if len(matching) != 1:
        blockers.append(f"{order_id}:{label}_locked_gate_entry_count:{len(matching)}")
    else:
        row = matching[0]
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if row.get("artifact_path") != artifact_path or row.get("artifact_sha256") != digest:
            blockers.append(f"{order_id}:{label}_preregistration_hash_mismatch")
        validator_path = project_root / str(row.get("validator_path", ""))
        if not validator_path.is_file():
            blockers.append(f"{order_id}:{label}_preregistration_validator_missing")
        elif row.get("validator_sha256") != hashlib.sha256(validator_path.read_bytes()).hexdigest():
            blockers.append(f"{order_id}:{label}_preregistration_validator_hash_mismatch")
        elif verify_runtime:
            completed = subprocess.run(
                [sys.executable, str(validator_path)],
                cwd=project_root,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                blockers.append(f"{order_id}:{label}_preregistration_validator_failed")
    if preregistration.get("status") != expected_status:
        blockers.append(f"{order_id}:{label}_preregistration_not_locked")
    if preregistration.get(edge_claim_field) != "none":
        blockers.append(f"{order_id}:{label}_preregistration_edge_claim_not_none")
    return blockers, not blockers, False


def _validate_shadow_accounting_gate_supersession(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        contract = json.loads(target.read_text(encoding="utf-8"))
        rows = [
            json.loads(line)
            for line in (project_root / "experiments" / "locked_gates.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"{order_id}:shadow_accounting_supersession_unreadable:{exc.__class__.__name__}"], False, False

    blockers: list[str] = []
    predecessor = [row for row in rows if row.get("gate_id") == "l_1_shadow_accounting_activation_v1"]
    successor = [row for row in rows if row.get("gate_id") == "l_1_shadow_accounting_activation_v2"]
    if len(predecessor) != 1:
        blockers.append(f"{order_id}:shadow_accounting_predecessor_entry_count:{len(predecessor)}")
    elif (
        predecessor[0].get("artifact_sha256")
        != "62d23376a83823b6b710afb2dc74fdaf2f04d008c79a88a71a2b6dc06bff4d79"
        or predecessor[0].get("validator_sha256")
        != "8f0bce4261ad6bc26976eae4904152578de2e0b810a8103b2ec718526af67e55"
    ):
        blockers.append(f"{order_id}:shadow_accounting_predecessor_hash_history_mismatch")
    if len(successor) != 1:
        blockers.append(f"{order_id}:shadow_accounting_successor_entry_count:{len(successor)}")
    else:
        row = successor[0]
        if row.get("supersedes_gate_id") != "l_1_shadow_accounting_activation_v1":
            blockers.append(f"{order_id}:shadow_accounting_supersession_link_mismatch")
        if row.get("artifact_path") != artifact_path or row.get("artifact_sha256") != hashlib.sha256(target.read_bytes()).hexdigest():
            blockers.append(f"{order_id}:shadow_accounting_successor_artifact_mismatch")
        validator_path = project_root / str(row.get("validator_path", ""))
        if not validator_path.is_file() or row.get("validator_sha256") != hashlib.sha256(validator_path.read_bytes()).hexdigest():
            blockers.append(f"{order_id}:shadow_accounting_successor_validator_mismatch")
        elif verify_runtime:
            completed = subprocess.run(
                [sys.executable, str(validator_path)],
                cwd=project_root,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                blockers.append(f"{order_id}:shadow_accounting_successor_validator_failed")
    if contract.get("order_id") != "B4.9" or contract.get("status") != "locked_scope_decision_and_preview_probe":
        blockers.append(f"{order_id}:shadow_accounting_successor_contract_state_mismatch")
    return blockers, not blockers, False


def _validate_l1_manifest(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    except json.JSONDecodeError:
        return [f"{order_id}:l1_locked_gate_manifest_invalid_jsonl"], False, False
    matching = [row for row in rows if row.get("gate_id") == "l_1_baseline_v1"]
    blockers: list[str] = []
    if len(matching) != 1:
        blockers.append(f"{order_id}:l1_locked_gate_entry_count:{len(matching)}")
    else:
        row = matching[0]
        artifact = project_root / "experiments" / "l_1_baseline_preregistration.json"
        validator = project_root / "scripts" / "validate_l_1_baseline_preregistration.py"
        if row.get("artifact_path") != "experiments/l_1_baseline_preregistration.json":
            blockers.append(f"{order_id}:l1_manifest_artifact_path_mismatch")
        elif not artifact.is_file() or row.get("artifact_sha256") != hashlib.sha256(artifact.read_bytes()).hexdigest():
            blockers.append(f"{order_id}:l1_manifest_artifact_hash_mismatch")
        if row.get("validator_path") != "scripts/validate_l_1_baseline_preregistration.py":
            blockers.append(f"{order_id}:l1_manifest_validator_path_mismatch")
        elif not validator.is_file() or row.get("validator_sha256") != hashlib.sha256(validator.read_bytes()).hexdigest():
            blockers.append(f"{order_id}:l1_manifest_validator_hash_mismatch")
        if any(other.get("supersedes_gate_id") == "l_1_baseline_v1" for other in rows):
            blockers.append(f"{order_id}:l1_gate_is_not_active")
    return blockers, not blockers, False


def _validate_research_log_format(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = (
        "## 1. ข้อมูลพื้นฐาน",
        "## 2. ปัญหา (คำถาม) และสมมติฐาน",
        "## 3. ขั้นตอนการทดลอง",
        "## 4. ผลลัพธ์",
        "## 5. อภิปรายผล ปัญหา และข้อจำกัด",
        "## 6. สรุปผลการทดลองและแนวทางพัฒนาต่อ",
        "- คำถามวิจัย:",
        "- ขอบเขต:",
        "- สมมติฐาน:",
        "- เกณฑ์ตัดสิน:",
        "ไม่เกิน 240 ตัวอักษร",
        "mojibake",
        "config/research_log_requirements.json",
    )
    missing = [item for item in required if item not in text]
    blockers = [f"{order_id}:research_log_format_missing:{item}" for item in missing]
    return blockers, not blockers, False


def _validate_research_log_requirements(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:research_log_requirements_invalid_json"], False, False
    blockers: list[str] = []
    if payload.get("schema_version") != "lily_research_log_requirements_v1":
        blockers.append(f"{order_id}:research_log_requirements_schema_mismatch")
    expected = {
        (
            "L0-SIZING-FEASIBILITY",
            "reports/feasibility/l_0_sizing_feasibility.json",
            "research_log/001-lily-l0-sizing-feasibility.md",
            True,
        ),
        (
            "L1-BASELINE",
            "reports/experiments/l_1_baseline_summary.json",
            "research_log/002-lily-l1-baseline.md",
            True,
        ),
    }
    entries = payload.get("entries", [])
    actual = {
        (
            row.get("experiment_id"),
            row.get("summary_path"),
            row.get("research_log_path"),
            row.get("required_when_summary_exists"),
        )
        for row in entries
        if isinstance(row, dict)
    }
    experiment_ids = [row.get("experiment_id") for row in entries if isinstance(row, dict)]
    if not expected.issubset(actual) or len(experiment_ids) != len(set(experiment_ids)):
        blockers.append(f"{order_id}:research_log_requirement_inventory_mismatch")
    return blockers, not blockers, False


def _validate_research_log(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
    runtime_cache: dict[str, bool],
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    static_required = (
        "# บันทึกการวิจัย ",
        "## 2. ปัญหา (คำถาม) และสมมติฐาน",
        "- คำถามวิจัย:",
        "- ขอบเขต:",
        "- เกณฑ์ตัดสิน:",
        "สิ่งที่ห้ามสรุปจากการทดลองนี้:",
    )
    blockers = [
        f"{order_id}:research_log_missing:{item}"
        for item in static_required
        if item not in text
    ]
    if blockers:
        return blockers, False, False
    if not verify_runtime:
        return [], False, True
    if "research_logs" not in runtime_cache:
        completed = subprocess.run(
            [sys.executable, "scripts/audit_research_logs.py"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        runtime_cache["research_logs"] = completed.returncode == 0
    passed = runtime_cache["research_logs"]
    return ([] if passed else [f"{order_id}:research_log_audit_failed"]), passed, False


def _validate_l0_machine_report(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l0_machine_report_invalid_json"], False, False
    blockers: list[str] = []
    expected_root = {
        "schema_version": "lily_l0_sizing_feasibility_report_v1",
        "hypothesis_id": "L-0",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "decision": "scope_restricted",
    }
    for field, expected in expected_root.items():
        if payload.get(field) != expected:
            blockers.append(f"{order_id}:l0_report_{field}_mismatch")
    if any(payload.get("guardrails", {}).values()):
        blockers.append(f"{order_id}:l0_report_forbidden_activity")
    broker_rows = payload.get("etf", {}).get("broker_results", [])
    expected_pairs = {
        (capital, broker)
        for capital in (1000, 2000)
        for broker in (
            "Webull_Thailand_manual_fractional",
            "Webull_Thailand_OpenAPI_fractional",
            "IBKR_fractional_reference",
        )
    }
    actual_pairs = {(row.get("capital_usd"), row.get("broker_path")) for row in broker_rows}
    if actual_pairs != expected_pairs:
        blockers.append(f"{order_id}:l0_report_broker_scenarios_incomplete")
    if any(row.get("classification") != "scope_restricted" for row in broker_rows):
        blockers.append(f"{order_id}:l0_report_broker_classification_mismatch")
    micro = payload.get("futures", {}).get("micro", [])
    full = payload.get("futures", {}).get("full_size_comparator", [])
    if [row.get("minimum_capital_usd") for row in micro] != [40600, 54200, 95400]:
        blockers.append(f"{order_id}:l0_report_micro_capital_mismatch")
    if [row.get("minimum_capital_usd") for row in full] != [405900, 541200, 1614600]:
        blockers.append(f"{order_id}:l0_report_full_capital_mismatch")
    if not payload.get("source_inventory") or not payload.get("tier_blockers"):
        blockers.append(f"{order_id}:l0_report_sources_or_blockers_missing")
    return blockers, not blockers, False


def _validate_l0_markdown_report(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    json_path = project_root / "reports" / "feasibility" / "l_0_sizing_feasibility.json"
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        markdown = target.read_text(encoding="utf-8")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"{order_id}:l0_report_pair_unreadable:{exc.__class__.__name__}"], False, False
    required = (
        str(payload.get("producing_git_commit", "")),
        str(payload.get("report_digest_sha256", "")),
        "$40,600",
        "$54,200",
        "$95,400",
        "scope_restricted",
        "No edge or deployment claim",
    )
    missing = [value for value in required if not value or value not in markdown]
    blockers = [f"{order_id}:l0_markdown_missing_machine_value:{value}" for value in missing]
    return blockers, not blockers, False


def _run_hermetic_once(project_root: Path, cache: dict[str, bool]) -> bool:
    if "hermetic" not in cache:
        completed = subprocess.run(
            [sys.executable, "scripts/run_test_tier.py", "hermetic", "--verbosity", "0"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        cache["hermetic"] = completed.returncode == 0
    return cache["hermetic"]


def _run_all_tiers_once(project_root: Path, cache: dict[str, bool]) -> bool:
    if "all" not in cache:
        completed = subprocess.run(
            [sys.executable, "scripts/run_test_tier.py", "all", "--verbosity", "0"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        cache["all"] = completed.returncode == 0
    return cache["all"]


def _validate_ci(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = ("push:", "pull_request:", "actions/checkout@", "actions/setup-python@", "python scripts/run_test_tier.py hermetic")
    missing = [item for item in required if item not in text]
    return ([f"{order_id}:ci_missing:{item}" for item in missing], not missing, False)


def _validate_ci_checkout_v5(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    blockers, _, _ = _validate_ci(target, order_id, artifact_path)
    if target.is_file() and "uses: actions/checkout@v5" not in target.read_text(encoding="utf-8"):
        blockers.append(f"{order_id}:ci_missing:uses: actions/checkout@v5")
    return blockers, not blockers, False


def _validate_webull_th_uat_scope_decision(
    target: Path, order_id: str, artifact_path: str
) -> tuple[list[str], bool, bool]:
    required = (
        "https://developer.webull.co.th/apis/docs/sdk.md",
        "https://developer.webull.co.th/apis/docs/trade-api/getting-started/",
        "https://developer.webull.co.th/apis/docs/market-data-api/getting-started/",
        "unverified_reference",
        "ไม่ใช่หลักฐานว่า Webull เปิด UAT เป็นบริการสาธารณะ",
        "UAT ที่เจ้าของควบคุมได้",
    )
    return _validate_required_text(target, order_id, artifact_path, "uat_scope_decision", required)


def _validate_uat_scope_project_memory(
    target: Path, order_id: str, artifact_path: str
) -> tuple[list[str], bool, bool]:
    required = ("B4.13 confirms", "No UAT work is planned", "new locked gate")
    return _validate_required_text(target, order_id, artifact_path, "uat_scope_project_memory", required)


def _validate_uat_scope_implementation_plan(
    target: Path, order_id: str, artifact_path: str
) -> tuple[list[str], bool, bool]:
    required = ("### B4.13", "### B4.14", "No UAT work planned")
    return _validate_required_text(target, order_id, artifact_path, "uat_scope_implementation_plan", required)


def _validate_required_text(
    target: Path,
    order_id: str,
    artifact_path: str,
    rule_name: str,
    required: tuple[str, ...],
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    missing = [item for item in required if item not in text]
    return ([f"{order_id}:{rule_name}_missing:{item}" for item in missing], not missing, False)


def _validate_python_pin(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    value = target.read_text(encoding="utf-8").strip()
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        return [f"{order_id}:python_version_not_exact:{value}"], False, False
    if tuple(map(int, match.groups()[:2])) != SUPPORTED_PYTHON_LINE:
        return [f"{order_id}:unsupported_python_line:{value}"], False, False
    return [], True, False


def _validate_pyproject(
    target: Path,
    project_root: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = tomllib.loads(target.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return [f"{order_id}:invalid_pyproject:{exc}"], False, False
    project = payload.get("project", {})
    lily = payload.get("tool", {}).get("lily", {})
    blockers: list[str] = []
    if project.get("requires-python") != ">=3.14,<3.15":
        blockers.append(f"{order_id}:pyproject_python_range_not_pinned")
    if project.get("dependencies") != []:
        blockers.append(f"{order_id}:dependencies_must_be_explicit_list")
    pin_path = project_root / ".python-version"
    pin = pin_path.read_text(encoding="utf-8").strip() if pin_path.exists() else None
    if lily.get("python-version") != pin:
        blockers.append(f"{order_id}:pyproject_python_pin_mismatch")
    return blockers, not blockers, False


def _validate_machine_example(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{order_id}:invalid_machine_example:{exc}"], False, False
    expected = {"LILY_DATA_ROOT", "LILY_WIKI_ROOT", "LILY_IBKR_PYTHON", "LILY_WEBULL_PYTHON"}
    variables = payload.get("environment_variables")
    blockers: list[str] = []
    if not isinstance(variables, dict) or set(variables) != expected:
        blockers.append(f"{order_id}:machine_example_variable_set_mismatch")
    elif any(value is not None for value in variables.values()):
        blockers.append(f"{order_id}:machine_example_contains_non_placeholder_value")
    if set(payload) != {"schema_version", "environment_variables"}:
        blockers.append(f"{order_id}:machine_example_contains_extra_fields")
    return blockers, not blockers, False


def _validate_lib_skeleton(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    required = {
        "__init__.py",
        "environment.py",
        "guardrails.py",
        "io.py",
        "provenance.py",
        "report.py",
        "search_log.py",
        "timestamps.py",
    }
    if not target.is_dir():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    missing = sorted(name for name in required if not (target / name).is_file())
    blockers = [f"{order_id}:lib_module_missing:{name}" for name in missing]
    return blockers, not blockers, False


def _validate_lib_tests(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    required = {"test_lib_foundation.py", "test_audit_new_script_lib_usage.py"}
    if not target.is_dir():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    missing = sorted(name for name in required if not (target / name).is_file())
    blockers = [f"{order_id}:lib_test_missing:{name}" for name in missing]
    return blockers, not blockers, False


def _validate_statistics_kernel(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = (
        "raw Pearson kurtosis",
        "finite-sample Bartlett",
        "def probabilistic_sharpe_ratio",
        "def minimum_track_record_length_falsify",
        "def minimum_track_record_length_validate",
        "def deflated_sharpe_ratio",
        "def newey_west_variance_of_mean",
        "def independent_bet_equivalent_count",
    )
    missing = [item for item in required if item not in text]
    blockers = [f"{order_id}:statistics_kernel_missing:{item}" for item in missing]
    return blockers, not blockers, False


def _validate_statistics_conventions(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = (
        "Published-method anchor",
        "Offline library cross-check",
        "independent-bet",
        "Wiki-relative source",
        "SHA-256",
        "probabilistic-sharpe-ratio.md",
        "deflated-sharpe-ratio.md",
        "newey-west-validation.md",
    )
    blockers = [
        f"{order_id}:statistics_conventions_missing:{item}"
        for item in required
        if item not in text
    ]
    if len(re.findall(r"\b[0-9a-f]{64}\b", text)) < 3:
        blockers.append(f"{order_id}:statistics_conventions_require_source_hashes")
    return blockers, not blockers, False


def _validate_lf_attributes(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    lines = set(target.read_text(encoding="utf-8").splitlines())
    required = {"*.json text eol=lf", "*.jsonl text eol=lf", "*.md text eol=lf", "*.py text eol=lf"}
    missing = sorted(required - lines)
    blockers = [f"{order_id}:gitattributes_missing:{line}" for line in missing]
    return blockers, not blockers, False


def _validate_governance_tests(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_dir():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    required = {
        "test_validate_hypothesis_registry.py",
        "test_validate_evidence_tiers.py",
        "test_validate_locked_gates.py",
    }
    missing = sorted(name for name in required if not (target / name).is_file())
    blockers = [f"{order_id}:governance_test_missing:{name}" for name in missing]
    return blockers, not blockers, False


def _validate_evidence_policy(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = (
        "Adversarial Review Before E2",
        "reviewer_is_independent: true",
        "unresolved_critical_issues",
        "append-only",
        "supersedes_gate_id",
    )
    blockers = [f"{order_id}:evidence_policy_missing:{item}" for item in required if item not in text]
    return blockers, not blockers, False


def _validate_restore_rehearsal(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{order_id}:invalid_restore_rehearsal:{exc}"], False, False
    blockers: list[str] = []
    if payload.get("schema_version") != "lily_restore_rehearsal_v1":
        blockers.append(f"{order_id}:restore_rehearsal_schema_invalid")
    if payload.get("outcome") != "successful_committed_artifact_restore":
        blockers.append(f"{order_id}:committed_artifact_restore_not_successful")
    if not re.fullmatch(r"[0-9a-f]{40}", str(payload.get("producing_git_commit", ""))):
        blockers.append(f"{order_id}:restore_rehearsal_missing_commit")
    checks = payload.get("checks")
    required_checks = {
        "remote_clone",
        "commit_hash_match",
        "hermetic_tier",
        "bootstrap_tracker",
        "restored_worktree_clean",
        "machine_manifest_expected_absent",
        "repository_data_expected_absent",
        "wiki_relative_source_hashes",
    }
    if not isinstance(checks, dict):
        blockers.append(f"{order_id}:restore_rehearsal_checks_missing")
    else:
        for check in sorted(required_checks):
            if not isinstance(checks.get(check), dict) or checks[check].get("status") != "pass":
                blockers.append(f"{order_id}:restore_check_not_pass:{check}")
    external = payload.get("external_state")
    if not isinstance(external, dict):
        external = {}
        blockers.append(f"{order_id}:external_state_missing")
    local_data = external.get("local_data") if isinstance(external.get("local_data"), dict) else {}
    machine_manifest = (
        external.get("machine_manifest") if isinstance(external.get("machine_manifest"), dict) else {}
    )
    local_wiki = external.get("local_llm_wiki") if isinstance(external.get("local_llm_wiki"), dict) else {}
    if local_data.get("restore_status") != "pending_no_data":
        blockers.append(f"{order_id}:external_data_restore_status_must_be_pending_no_data")
    if machine_manifest.get("expected_in_clone") is not False:
        blockers.append(f"{order_id}:machine_manifest_absence_not_recorded")
    if local_wiki.get("hash_verification") != "pass":
        blockers.append(f"{order_id}:wiki_hash_verification_not_passed")
    if payload.get("temporary_clone_removed") is not True:
        blockers.append(f"{order_id}:temporary_clone_cleanup_not_recorded")
    return blockers, not blockers, False


def _validate_data_integrity_policy(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8").lower()
    required = (
        "inception",
        "delisting",
        "backfill",
        "corporate action",
        "point-in-time universe membership",
        "currency",
        "individual contracts",
        "continuous futures",
        "first-notice",
        "roll selection and timing",
        "adjusted price differences cannot be booked as pnl",
        "dual integrity",
        "scope_restricted",
    )
    blockers = [f"{order_id}:data_integrity_policy_missing:{item}" for item in required if item not in text]
    return blockers, not blockers, False


def _validate_provider_boundary_schemas(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_dir():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    required = {
        "dataset_registry.schema.json",
        "provider_continuous_futures.schema.json",
        "provider_daily_bars.schema.json",
        "provider_futures_contracts.schema.json",
        "provider_instrument_master.schema.json",
        "provider_universe_membership.schema.json",
    }
    missing = sorted(name for name in required if not (target / name).is_file())
    blockers = [f"{order_id}:provider_boundary_schema_missing:{name}" for name in missing]
    return blockers, not blockers, False


def _validate_synthetic_data_fixtures(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    data_root = target / "data"
    required = {
        "provider_continuous_futures.json",
        "provider_daily_bars.json",
        "provider_futures_contracts.json",
        "provider_instrument_master.json",
        "provider_universe_membership.json",
    }
    if not data_root.is_dir():
        return [f"{order_id}:synthetic_data_fixture_directory_missing"], False, False
    missing = sorted(name for name in required if not (data_root / name).is_file())
    blockers = [f"{order_id}:synthetic_data_fixture_missing:{name}" for name in missing]
    return blockers, not blockers, False


def _scan_active_artifacts(project_root: Path) -> list[str]:
    blockers: list[str] = []
    for path in _candidate_files(project_root):
        relative = path.relative_to(project_root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if WINDOWS_ABSOLUTE_PATH.search(text) or FILE_URI.search(text):
            blockers.append(f"forbidden_absolute_path:{relative}")
        if PRIVATE_KEY.search(text) or HIGH_RISK_VALUE_PATTERN.search(text):
            blockers.append(f"credential_like_value:{relative}")
            continue
        for match in SENSITIVE_ASSIGNMENT.finditer(text):
            value = match.group(2).strip().lower()
            if value not in PLACEHOLDER_VALUES and not value.startswith("${"):
                blockers.append(f"credential_like_assignment:{relative}:{match.group(1)}")
                break
    return sorted(set(blockers))


def _candidate_files(project_root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        paths = [project_root / line for line in completed.stdout.splitlines() if line.strip()]
    else:
        paths = [path for path in project_root.rglob("*") if path.is_file()]
    result: list[Path] = []
    for path in paths:
        try:
            relative_parts = path.relative_to(project_root).parts
        except ValueError:
            continue
        if any(part in EXCLUDED_PARTS for part in relative_parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {".gitignore", ".python-version"}:
            result.append(path)
    return sorted(set(result))


def _result(
    status: str,
    path: Path,
    blockers: list[str],
    checked: list[dict[str, str]],
    unverified: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "status": status,
        "tracker_path": str(path),
        "blockers": blockers,
        "done_artifacts_checked": checked,
        "unverified": unverified,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Lily's bootstrap tracker and all done claims.")
    parser.add_argument("--tracker", type=Path, default=DEFAULT_TRACKER)
    parser.add_argument(
        "--no-runtime-checks",
        action="store_true",
        help="Validate structure and static artifacts without running artifact commands.",
    )
    args = parser.parse_args()
    result = validate_tracker(args.tracker, verify_runtime=not args.no_runtime_checks)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
