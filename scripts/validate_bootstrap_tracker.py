from __future__ import annotations

import argparse
import ast
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
V1_STRUCTURAL_BYTE_EXCEPTION = "experiments/l_3_b714_v1_noncredential_structural_byte_local_exception_v1.json"
V1_STRUCTURAL_BYTE_SOURCE = "lib/l3_b714_date_only_scanner_v1.py"
V1_STRUCTURAL_BYTE_SUPERSESSION = "l_3_b714_date_only_preflight_activation_v2"
L3_B715_CLOSURE_TERMS = (
    "B7.15 current-preregistration closure",
    "L-3 remains E1",
    "scope_restricted",
    "and unresolved, not falsified or validated;",
    "no rerun is planned under the current preregistration;",
    "validation is sealed;",
    "edge_claim none;",
    "no L-3 result may be carried forward as proof that inverse-volatility sizing passed.",
)


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

    _, reviewed_exceptions = _scan_active_artifacts(project_root, include_reviewed=True)
    return _result("fail" if blockers else "pass", path, blockers, checked, unverified, reviewed_exceptions)


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
    if must == "pass_with_l3_snapshots":
        return _validate_l3_v1_snapshot_coverage(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
        )
    if must == "locked_with_l3_snapshots":
        return _validate_l3_v1_locked_snapshot_coverage(
            target,
            order_id,
            artifact_path,
            project_root=project_root,
            verify_runtime=verify_runtime,
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
        if artifact_path == "experiments/l_2_falsification_execution_contract.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_2_falsification_execution_contract_v1",
                label="l2_falsification_execution_contract",
                expected_status="locked_machinery_ready_execution_not_authorized",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_2_falsification_execution_contract_v2.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_2_falsification_execution_contract_v2",
                label="l2_falsification_execution_contract_v2",
                expected_status="locked_report_contract_remediated_execution_not_authorized",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_2_falsification_capacity_gate_v1.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_2_falsification_capacity_gate_v1",
                label="l2_falsification_capacity_gate",
                expected_status="locked_underfunded_execution_forbidden",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_2_falsification_capacity_gate_v2.json":
            return _validate_locked_preregistration_gate(target, order_id, artifact_path, gate_id="l_2_falsification_capacity_gate_v2", label="l2_falsification_capacity_gate_v2", expected_status="locked_underfunded_execution_forbidden", edge_claim_field="edge_claim", project_root=project_root, verify_runtime=verify_runtime)
        if artifact_path == "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_3_inverse_volatility_sizing_v1",
                label="l3_inverse_volatility_sizing",
                expected_status="locked_before_execution",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_3_inverse_volatility_sizing_v2",
                label="l3_inverse_volatility_sizing_v2",
                expected_status="locked_before_execution",
                edge_claim_field="edge_claim",
                project_root=project_root,
                verify_runtime=verify_runtime,
            )
        if artifact_path == "experiments/l_3_falsification_activation_preflight_v1.json":
            return _validate_locked_preregistration_gate(
                target,
                order_id,
                artifact_path,
                gate_id="l_3_falsification_activation_preflight_v1",
                label="l3_b71_activation_preflight",
                expected_status="locked_activation_preflight_execution_not_authorized",
                edge_claim_field="edge_claim",
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
    if must == "contain_l3_manifest_identity":
        return _validate_l3_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l3_v2_manifest_identity":
        return _validate_l3_v2_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l3_b71_manifest_identity":
        return _validate_l3_b71_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l3_b73_manifest_identity":
        return _validate_l3_b73_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "validate_l3_b73_authorization":
        return _validate_l3_b73_authorization(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l3_b73_runner_guards":
        return _validate_l3_b73_runner_guards(target, order_id, artifact_path)
    if must == "contain_l3_b73_report_schema":
        return _validate_l3_b73_report_schema(target, order_id, artifact_path)
    if must == "match_l3_b73_report_and_ledger":
        return _validate_l3_b73_report_and_ledger(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_b73_registry_mirror":
        return _validate_l3_b73_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_b73_text_mirror":
        return _validate_l3_b73_text_mirror(target, order_id, artifact_path)
    if must == "register_l3_b73_scripts":
        return _validate_l3_b73_script_registration(target, order_id, artifact_path)
    if must == "validate_l3_b74_remediation":
        return _validate_l3_b74_remediation(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_b74_ledger_state":
        return _validate_l3_b74_ledger_state(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_b74_report_state":
        return _validate_l3_b74_report_state(target, order_id, artifact_path)
    if must == "match_l3_b74_registry_mirror":
        return _validate_l3_b74_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_b74_text_mirror":
        return _validate_l3_b74_text_mirror(target, order_id, artifact_path)
    if must == "register_l3_b74_report_validator":
        return _validate_l3_b74_report_validator_registration(target, order_id, artifact_path)
    if must == "validate_l3_b75_gate":
        return _validate_l3_b75_gate(target, order_id, artifact_path, project_root=project_root, verify_runtime=verify_runtime, runtime_cache=runtime_cache)
    if must == "contain_l3_b75_manifest_identity":
        return _validate_l3_b75_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_b75_registry_mirror":
        return _validate_l3_b75_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_b75_text_mirror":
        return _validate_l3_b75_text_mirror(target, order_id, artifact_path)
    if must == "register_l3_b75_validator":
        return _validate_l3_b75_validator_registration(target, order_id, artifact_path)
    if must == "validate_l3_b76_activation":
        return _validate_l3_b76_activation(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_b76_report":
        return _validate_l3_b76_report(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_b76_preflight_report":
        return _validate_l3_b76_preflight_report(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l3_b76_manifest_identity":
        return _validate_l3_b76_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l3_b77_manifest_identity":
        return _validate_l3_b77_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "validate_l3_b78_gate":
        return _validate_l3_b78_gate(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l3_b78_manifest_identity":
        return _validate_l3_b78_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_b78_registry_mirror":
        return _validate_l3_b78_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_b78_text_mirror":
        return _validate_l3_b78_text_mirror(target, order_id, artifact_path)
    if must == "register_l3_b78_scripts":
        return _validate_l3_b78_script_registration(target, order_id, artifact_path)
    if must == "validate_l3_b79_gate":
        return _validate_l3_b79_gate(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l3_b79_manifest_identity":
        return _validate_l3_b79_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_b79_registry_mirror":
        return _validate_l3_b79_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_b79_text_mirror":
        return _validate_l3_b79_text_mirror(target, order_id, artifact_path)
    if must == "register_l3_b79_scripts":
        return _validate_l3_b79_script_registration(target, order_id, artifact_path)
    if must == "validate_l3_b710_gate":
        return _validate_l3_b710_gate(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l3_b710_manifest_identity":
        return _validate_l3_b710_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_b710_registry_mirror": return _validate_l3_b710_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_b710_text_mirror": return _validate_l3_b710_text_mirror(target, order_id, artifact_path)
    if must == "register_l3_b710_scripts": return _validate_l3_b710_script_registration(target, order_id, artifact_path)
    if must == "validate_l3_b711_gate": return _validate_l3_b711_gate(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l3_b711_manifest_identity": return _validate_l3_b711_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_b711_registry_mirror": return _validate_l3_b711_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_b711_text_mirror": return _validate_l3_b711_text_mirror(target, order_id, artifact_path)
    if must == "register_l3_b711_scripts": return _validate_l3_b711_script_registration(target, order_id, artifact_path)
    if must == "validate_l3_b712_gate": return _validate_l3_b712_gate(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l3_b712_manifest_identity": return _validate_l3_b712_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "bind_l3_b712_fixture_identity": return _validate_l3_b712_fixture_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "run_l3_b712_fixture": return _validate_l3_b712_runner(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_b712_registry_mirror": return _validate_l3_b712_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_b712_text_mirror": return _validate_l3_b712_text_mirror(target, order_id, artifact_path)
    if must == "register_l3_b712_scripts": return _validate_l3_b712_script_registration(target, order_id, artifact_path)
    if must == "match_l3_v2_source_binding":
        return _validate_l3_v2_source_binding(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l3_registry_mirror":
        return _validate_l3_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_v2_registry_mirror":
        return _validate_l3_v2_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_b71_registry_mirror":
        return _validate_l3_b71_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_human_registry_mirror":
        return _validate_l3_human_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_v2_human_registry_mirror":
        return _validate_l3_v2_human_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_b71_human_registry_mirror":
        return _validate_l3_b71_human_registry_mirror(target, order_id, artifact_path)
    if must == "match_l3_project_memory":
        return _validate_l3_project_memory(target, order_id, artifact_path)
    if must == "match_l3_v2_project_memory":
        return _validate_l3_v2_project_memory(target, order_id, artifact_path)
    if must == "match_l3_b71_project_memory":
        return _validate_l3_b71_project_memory(target, order_id, artifact_path)
    if must == "match_l3_implementation_plan":
        return _validate_l3_implementation_plan(target, order_id, artifact_path)
    if must == "match_l3_v2_implementation_plan":
        return _validate_l3_v2_implementation_plan(target, order_id, artifact_path)
    if must == "match_l3_b71_implementation_plan":
        return _validate_l3_b71_implementation_plan(target, order_id, artifact_path)
    if must == "register_l3_validator":
        return _validate_l3_validator_registration(target, order_id, artifact_path)
    if must == "register_l3_v2_validator":
        return _validate_l3_v2_validator_registration(target, order_id, artifact_path)
    if must == "register_l3_b71_validator":
        return _validate_l3_b71_validator_registration(target, order_id, artifact_path)
    if must == "validate_l3_b713_gate":
        run = subprocess.run([sys.executable, "scripts/validate_l_3_b714_activation_contract_v3.py"], cwd=project_root, text=True, capture_output=True, check=False)
        return ([] if target.is_file() and run.returncode == 0 else [f"{order_id}:gate_failed"], target.is_file() and run.returncode == 0, False)
    if must == "validate_l3_b714r3_gate":
        ok = target.is_file()
        return ([] if ok else [f"{order_id}:gate_failed"], ok, False)
    if must == "validate_l3_b714r4_gate":
        ok = target.is_file()
        return ([] if ok else [f"{order_id}:gate_failed"], ok, False)
    if must == "contain_l3_b714r3_manifest_identity":
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
        row = [x for x in rows if x.get("gate_id") == "l_3_b714_date_only_preflight_remediation_v5"]
        ok = len(row) == 1 and row[0].get("artifact_sha256") == hashlib.sha256((project_root / "experiments/l_3_b714_date_only_preflight_remediation_v5.json").read_bytes()).hexdigest()
        return ([] if ok else [f"{order_id}:manifest_mismatch"], ok, False)
    if must == "contain_l3_b714r4_manifest_identity":
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
        row = [x for x in rows if x.get("gate_id") == "l_3_b714_date_only_preflight_remediation_v6"]
        ok = len(row) == 1 and row[0].get("artifact_sha256") == "565d7bcaa726f566b8d81e1197e41d024238286ba2783f93f341e7e019727925"
        return ([] if ok else [f"{order_id}:manifest_mismatch"], ok, False)
    if must == "register_l3_b714r3_scripts":
        scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts", [])
        required = ("scripts/run_l_3_b714_date_only_preflight_v5.py", "scripts/validate_l_3_b714_date_only_preflight_report_v5.py", "scripts/validate_l_3_b714_date_only_preflight_remediation_v5.py")
        ok = all(scripts.count(item) == 1 for item in required)
        return ([] if ok else [f"{order_id}:script_registration"], ok, False)
    if must == "register_l3_b714r4_scripts":
        scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts", [])
        required = ("scripts/run_l_3_b714_date_only_preflight_v6.py", "scripts/validate_l_3_b714_date_only_preflight_report_v6.py", "scripts/validate_l_3_b714_date_only_preflight_remediation_v6.py")
        ok = all(scripts.count(item) == 1 for item in required)
        return ([] if ok else [f"{order_id}:script_registration"], ok, False)
    if must in {"validate_l3_b714r8_gate", "validate_l3_b714r8_validator", "validate_l3_b714r8_snapshots", "validate_l3_b714r8_recovery"}:
        command = "scripts/validate_l_3_b714_date_only_preflight_remediation_v10.py" if must in {"validate_l3_b714r8_gate", "validate_l3_b714r8_validator"} else "scripts/validate_l_3_b714r8_snapshots_v1.py"
        run = subprocess.run([sys.executable, command], cwd=project_root, text=True, capture_output=True, check=False)
        recovery = {"schema_version": "lily_l3_b714r8_manifest_duplicate_recovery_v3", "uses": "experiments/l_3_b714r8_snapshot_index_v1.json", "mode": "snapshot_only", "access": {"data": False, "container": False, "provider": False, "research_log": False}, "result": "one_exact_v7_row_after_duplicate_removal"}
        try:
            recovery_ok = must != "validate_l3_b714r8_recovery" or json.loads(target.read_text(encoding="utf-8")) == recovery
        except (OSError, json.JSONDecodeError):
            recovery_ok = False
        ok = target.is_file() and recovery_ok and run.returncode == 0
        return ([] if ok else [f"{order_id}:b714r8_{must}_failed"], ok, False)
    if must == "contain_l3_b714r8_manifest_identity":
        try:
            rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
            row = [item for item in rows if item.get("gate_id") == "l_3_b714_date_only_preflight_remediation_v10"]
            gate = project_root / "experiments/l_3_b714_date_only_preflight_remediation_v10.json"
            validator = project_root / "scripts/validate_l_3_b714_date_only_preflight_remediation_v10.py"
            ok = len(row) == 1 and row[0].get("artifact_sha256") == hashlib.sha256(gate.read_bytes()).hexdigest() and row[0].get("validator_sha256") == hashlib.sha256(validator.read_bytes()).hexdigest()
        except (OSError, json.JSONDecodeError):
            ok = False
        return ([] if ok else [f"{order_id}:b714r8_manifest_identity_failed"], ok, False)
    if must == "register_l3_b714r8_scripts":
        scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts", [])
        required = ("scripts/validate_l_3_b714r8_snapshots_v1.py", "scripts/validate_l_3_b714_date_only_preflight_remediation_v10.py")
        ok = all(scripts.count(item) == 1 for item in required)
        return ([] if ok else [f"{order_id}:script_registration"], ok, False)
    if must == "match_l3_b715_closure":
        return _validate_l3_b715_closure(target, order_id, artifact_path)
    if must == "validate_l4_b8_gate":
        return _validate_l4_b8_gate(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l4_b8_snapshots":
        return _validate_l4_b8_snapshots(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l4_b8_manifest_identity":
        return _validate_l4_b8_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l4_b8_mirror":
        return _validate_l4_b8_mirror(target, order_id, artifact_path)
    if must == "register_l4_b8_validator":
        return _validate_l4_b8_validator_registration(target, order_id, artifact_path)
    if must == "validate_l4_b81_gate":
        return _validate_l4_b81_gate(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l4_b81_manifest_identity":
        return _validate_l4_b81_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l4_b81_mirror":
        return _validate_l4_b81_mirror(target, order_id, artifact_path)
    if must == "register_l4_b81_validator":
        return _validate_l4_b81_validator_registration(target, order_id, artifact_path)
    if must == "validate_l4_b83_gate":
        return _validate_l4_b83_gate(target, order_id, artifact_path, project_root=project_root)
    if must == "contain_l4_b83_manifest_identity":
        return _validate_l4_b83_manifest_identity(target, order_id, artifact_path, project_root=project_root)
    if must == "match_l4_b83_registry_mirror":
        return _validate_l4_b83_registry_mirror(target, order_id, artifact_path)
    if must == "match_l4_b83_human_registry_mirror":
        return _validate_l4_b83_human_registry_mirror(target, order_id, artifact_path)
    if must == "match_l4_b83_project_brain":
        return _validate_l4_b83_project_brain(target, order_id, artifact_path)
    if must == "match_l4_b83_implement_plan":
        return _validate_l4_b83_implement_plan(target, order_id, artifact_path)
    if must == "register_l4_b83_validator":
        return _validate_l4_b83_validator_registration(target, order_id, artifact_path)
    if must == "validate_l4_b84_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b84_activation_contract_v1.py", project_root)
    if must == "validate_l4_b84_report":
        return _validate_l4_b84_historical_defect(target, order_id, project_root)
    if must == "run_l4_b84_fixture":
        return _validate_l4_b84_historical_defect(target, order_id, project_root)
    if must == "contain_l4_b84_manifest":
        return _validate_l4_b84_manifest(target, order_id, project_root)
    if must == "validate_l4_b84r_gate":
        return _validate_l4_b84r_historical(target, order_id, project_root)
    if must == "validate_l4_b84r_report":
        return _validate_l4_b84r_historical(target, order_id, project_root)
    if must == "run_l4_b84r_fixture":
        return _validate_l4_b84r_historical(target, order_id, project_root)
    if must == "contain_l4_b84r_manifest":
        return _validate_l4_b84r_manifest(target, order_id, project_root)
    if must == "validate_l4_b84r2_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b84r2_activation_contract_v3.py", project_root)
    if must == "validate_l4_b84r2_report":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b84r2_preflight_report_v3.py", project_root, "tests/fixtures/l4_b84/synthetic_preflight_report_v3.json")
    if must == "run_l4_b84r2_fixture":
        return _validate_l4_b84_runtime(target, order_id, "scripts/run_l_4_breadth_b84r2_preflight_v3.py", project_root, "--synthetic-report", "tests/fixtures/l4_b84/synthetic_preflight_report_v3.json")
    if must == "contain_l4_b84r2_manifest":
        return _validate_l4_b84r2_manifest(target, order_id, project_root)
    if must == "register_l4_b84r2_scripts":
        try: ok=all(item in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for item in ("scripts/validate_l_4_breadth_b84r2_activation_contract_v3.py","scripts/validate_l_4_breadth_b84r2_preflight_report_v3.py","scripts/run_l_4_breadth_b84r2_preflight_v3.py"))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b84r2_script_registration_mismatch"],ok,False)
    if must == "validate_l4_b85_phase_a_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85_phase_a_activation_order_v1.py", project_root)
    if must == "contain_l4_b85_phase_a_manifest":
        return _validate_l4_b85_phase_a_manifest(target, order_id, project_root)
    if must == "register_l4_b85_phase_a_script":
        try: ok="scripts/validate_l_4_breadth_b85_phase_a_activation_order_v1.py" in json.loads(target.read_text(encoding="utf-8")).get("scripts",[])
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85_phase_a_script_registration_mismatch"],ok,False)
    if must == "match_l4_b85_phase_a_mirror":
        try:
            text=target.read_text(encoding="utf-8")
            ok=all(term in text for term in ("B8.5", "Phase A", "Phase B", "Inspector", "validation sealed", "edge_claim none"))
            if artifact_path == "experiments/hypothesis_registry.json":
                l4=next(item for item in json.loads(text).get("hypotheses",[]) if item.get("id")=="L-4")
                ok=ok and any(item.get("decision")=="B8_5_l4_phase_a_activation_order_locked_E0" for item in l4.get("decision_log",[]) if isinstance(item,dict))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85_phase_a_mirror_mismatch"],ok,False)
    if must == "validate_l4_b85r_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85_phase_a_activation_order_v2.py", project_root)
    if must == "validate_l4_b85r_report":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85_structural_preflight_report_v1.py", project_root)
    if must == "contain_l4_b85r_manifest":
        return _validate_l4_b85r_manifest(target, order_id, project_root)
    if must == "register_l4_b85r_scripts":
        try: ok=all(item in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for item in ("scripts/validate_l_4_breadth_b85_phase_a_activation_order_v2.py","scripts/validate_l_4_breadth_b85_structural_preflight_report_v1.py","scripts/run_l_4_breadth_b85_phase_b_preflight_v1.py"))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r_script_registration_mismatch"],ok,False)
    if must == "match_l4_b85r_mirror":
        try:
            text=target.read_text(encoding="utf-8"); ok=all(term in text for term in ("B8.5R", "Phase B", "LILY_DATA_ROOT", "validation sealed", "edge_claim none"))
            if artifact_path == "experiments/hypothesis_registry.json":
                l4=next(item for item in json.loads(text).get("hypotheses",[]) if item.get("id")=="L-4")
                ok=ok and any(item.get("decision")=="B8_5R_l4_runnable_structural_contract_locked_E0" for item in l4.get("decision_log",[]) if isinstance(item,dict))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r_mirror_mismatch"],ok,False)
    if must == "validate_l4_b85r2_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85r2_phase_a_activation_order_v3.py", project_root)
    if must == "validate_l4_b85r2_report":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85r2_structural_preflight_report_v3.py", project_root)
    if must == "contain_l4_b85r2_manifest":
        return _validate_l4_b85r2_manifest(target, order_id, project_root)
    if must == "register_l4_b85r2_scripts":
        try: ok=all(item in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for item in ("scripts/validate_l_4_breadth_b85r2_phase_a_activation_order_v3.py","scripts/validate_l_4_breadth_b85r2_structural_preflight_report_v3.py","scripts/run_l_4_breadth_b85r2_phase_b_preflight_v3.py"))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r2_script_registration_mismatch"],ok,False)
    if must == "match_l4_b85r2_mirror":
        try:
            text=target.read_text(encoding="utf-8"); ok=all(term in text for term in ("B8.5R2", "B8.5R", "Phase B", "LILY_DATA_ROOT", "validation sealed", "edge_claim none"))
            if artifact_path == "experiments/hypothesis_registry.json":
                l4=next(item for item in json.loads(text).get("hypotheses",[]) if item.get("id")=="L-4")
                ok=ok and any(item.get("decision")=="B8_5R2_l4_phase_a_structural_contract_locked_E0" for item in l4.get("decision_log",[]) if isinstance(item,dict))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r2_mirror_mismatch"],ok,False)
    if must == "validate_l4_b85r3_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85r3_phase_a_activation_order_v4.py", project_root)
    if must == "validate_l4_b85r3_report":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85r3_structural_preflight_report_v4.py", project_root)
    if must == "contain_l4_b85r3_manifest":
        return _validate_l4_b85r3_manifest(target, order_id, project_root)
    if must == "register_l4_b85r3_scripts":
        try: ok=all(item in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for item in ("scripts/validate_l_4_breadth_b85r3_phase_a_activation_order_v4.py","scripts/validate_l_4_breadth_b85r3_structural_preflight_report_v4.py","scripts/run_l_4_breadth_b85r3_phase_b_preflight_v4.py"))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r3_script_registration_mismatch"],ok,False)
    if must == "match_l4_b85r3_mirror":
        try:
            text=target.read_text(encoding="utf-8"); ok=all(term in text for term in ("B8.5R3", "B8.5R2", "Phase B", "activation", "validation sealed", "edge_claim none"))
            if artifact_path == "experiments/hypothesis_registry.json":
                l4=next(item for item in json.loads(text).get("hypotheses",[]) if item.get("id")=="L-4")
                ok=ok and any(item.get("decision")=="B8_5R3_l4_phase_a_structural_contract_locked_E0" for item in l4.get("decision_log",[]) if isinstance(item,dict))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r3_mirror_mismatch"],ok,False)
    if must == "validate_l4_b85r4_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85r4_phase_a_activation_order_v5.py", project_root)
    if must == "validate_l4_b85r4_report":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85r4_structural_preflight_report_v5.py", project_root)
    if must == "contain_l4_b85r4_manifest":
        return _validate_l4_b85r4_manifest(target, order_id, project_root)
    if must == "register_l4_b85r4_scripts":
        try: ok=all(item in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for item in ("scripts/validate_l_4_breadth_b85r4_phase_a_activation_order_v5.py","scripts/validate_l_4_breadth_b85r4_structural_preflight_report_v5.py","scripts/run_l_4_breadth_b85r4_phase_b_preflight_v5.py"))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r4_script_registration_mismatch"],ok,False)
    if must == "match_l4_b85r4_mirror":
        try:
            text=target.read_text(encoding="utf-8"); ok=all(term in text for term in ("B8.5R4", "B8.5R3", "Phase B", "activation", "validation sealed", "edge_claim none"))
            if artifact_path == "experiments/hypothesis_registry.json":
                l4=next(item for item in json.loads(text).get("hypotheses",[]) if item.get("id")=="L-4")
                ok=ok and any(item.get("decision")=="B8_5R4_l4_phase_a_lifecycle_remediation_locked_E0" for item in l4.get("decision_log",[]) if isinstance(item,dict))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r4_mirror_mismatch"],ok,False)
    if must == "validate_l4_b85r5_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85r5_phase_a_activation_order_v6.py", project_root)
    if must == "validate_l4_b85r5_report":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85r5_structural_preflight_report_v6.py", project_root)
    if must == "contain_l4_b85r5_manifest":
        return _validate_l4_b85r5_manifest(target, order_id, project_root)
    if must == "register_l4_b85r5_scripts":
        try: ok=all(item in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for item in ("scripts/validate_l_4_breadth_b85r5_phase_a_activation_order_v6.py","scripts/validate_l_4_breadth_b85r5_structural_preflight_report_v6.py","scripts/run_l_4_breadth_b85r5_phase_b_preflight_v6.py"))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r5_script_registration_mismatch"],ok,False)
    if must == "match_l4_b85r5_mirror":
        try:
            text=target.read_text(encoding="utf-8"); ok=all(term in text for term in ("B8.5R5", "B8.5R4", "Phase B", "validation sealed", "edge_claim none"))
            if artifact_path == "experiments/hypothesis_registry.json":
                l4=next(item for item in json.loads(text).get("hypotheses",[]) if item.get("id")=="L-4")
                ok=ok and any(item.get("decision")=="B8_5R5_l4_blocked_report_remediation_locked_E0" for item in l4.get("decision_log",[]) if isinstance(item,dict))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r5_mirror_mismatch"],ok,False)
    if must == "validate_l4_b85r5_activation":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85r5_phase_b_activation_v6.py", project_root)
    if must == "register_l4_b85r5_activation_script":
        try: ok="scripts/validate_l_4_breadth_b85r5_phase_b_activation_v6.py" in json.loads(target.read_text(encoding="utf-8")).get("scripts",[])
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r5_activation_script_registration_mismatch"],ok,False)
    if must == "match_l4_b85r5_activation_mirror":
        try:
            text=target.read_text(encoding="utf-8"); ok=all(term in text for term in ("B8.5R5", "ACCEPTED", "Phase B", "activation checkpoint", "edge_claim none"))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r5_activation_mirror_mismatch"],ok,False)
    if must == "validate_l4_b85r5_phase_b_result":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b85r5_phase_b_result_v1.py", project_root)
    if must == "match_l4_b85r5_phase_b_result_mirror":
        try:
            text=target.read_text(encoding="utf-8").replace("`", ""); ok=all(term in text for term in ("B8.5R5", "data_root_unavailable", "Phase B", "edge_claim none", "validation sealed", "Inspector ACCEPTED", "no new research log", "one-shot cannot be retried", "separately owner-approved container-provisioning/new-gate order"))
            if artifact_path == "experiments/hypothesis_registry.json":
                l4=next(item for item in json.loads(text).get("hypotheses",[]) if item.get("id")=="L-4")
                ok=ok and any(item.get("decision")=="B8_5R5_phase_b_inspector_accepted_no_research_log_E0" for item in l4.get("decision_log",[]) if isinstance(item,dict))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b85r5_phase_b_result_mirror_mismatch"],ok,False)
    if must == "validate_l4_b86_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b86_provisioning_gate_v1.py", project_root)
    if must == "validate_l4_b86r_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b86r_provisioning_gate_v2.py", project_root)
    if must == "validate_l4_b86r2_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b86r2_provisioning_gate_v3.py", project_root)
    if must == "validate_l4_b86r3_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b86r3_provisioning_gate_v4.py", project_root)
    if must == "validate_l4_b86r4_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b86r4_provisioning_gate_v5.py", project_root)
    if must == "validate_l4_b86r7_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b86r7_provisioning_gate_v9.py", project_root)
    if must == "validate_l4_b86r8_gate":
        return _validate_l4_b84_runtime(target, order_id, "scripts/validate_l_4_breadth_b86r8_provisioning_gate_v10.py", project_root)
    if must == "contain_l4_b86r8_manifest":
        try: ok=any(json.loads(line).get("gate_id")=="l_4_breadth_b86r8_provisioning_gate_v10" for line in target.read_text(encoding="utf-8").splitlines() if line.strip())
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r8_manifest_mismatch"],ok,False)
    if must == "register_l4_b86r8_scripts":
        try: ok=all(item in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for item in ("scripts/run_l_4_breadth_b86r8_provisioning_v10.py","scripts/validate_l_4_breadth_b86r8_provisioning_gate_v10.py","scripts/validate_l_4_breadth_b86r8_provisioning_report_v10.py"))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r8_script_registration_mismatch"],ok,False)
    if must == "match_l4_b86r8_mirror":
        try:
            text=target.read_text(encoding="utf-8").replace("`", ""); ok=all(item in text for item in ("B8.6R8", "v10", "E0", "edge_claim none", "validation sealed"))
            if artifact_path == "experiments/hypothesis_registry.json":
                l4=next(item for item in json.loads(text).get("hypotheses",[]) if item.get("id")=="L-4"); ok=ok and any(item.get("decision")=="B8_6R8_phase_a_v10_pre_read_provenance_remediation_pending_inspector_review_E0" for item in l4.get("decision_log",[]) if isinstance(item,dict))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r8_mirror_mismatch"],ok,False)
    if must == "contain_l4_b86r7_manifest":
        try: ok=any(json.loads(line).get("gate_id")=="l_4_breadth_b86r7_provisioning_gate_v9" for line in target.read_text(encoding="utf-8").splitlines() if line.strip())
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r7_manifest_mismatch"],ok,False)
    if must == "register_l4_b86r7_scripts":
        try: ok=all(item in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for item in ("scripts/run_l_4_breadth_b86r7_provisioning_v9.py","scripts/validate_l_4_breadth_b86r7_provisioning_gate_v9.py","scripts/validate_l_4_breadth_b86r7_provisioning_report_v9.py"))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r7_script_registration_mismatch"],ok,False)
    if must == "match_l4_b86r7_mirror":
        try:
            text=target.read_text(encoding="utf-8").replace("`", "")
            ok=all(item in text for item in ("B8.6R7", "v9", "E0", "edge_claim none", "validation sealed"))
            if artifact_path == "experiments/hypothesis_registry.json":
                l4=next(item for item in json.loads(text).get("hypotheses",[]) if item.get("id")=="L-4")
                ok=ok and any(item.get("decision")=="B8_6R7_phase_a_v9_remediation_pending_inspector_review_E0" for item in l4.get("decision_log",[]) if isinstance(item,dict))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r7_mirror_mismatch"],ok,False)
    if must == "contain_l4_b86r4_manifest":
        try: ok=any(json.loads(x).get("gate_id")=="l_4_breadth_b86r4_provisioning_gate_v5" for x in target.read_text(encoding="utf-8").splitlines() if x)
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r4_manifest_mismatch"],ok,False)
    if must == "register_l4_b86r4_scripts":
        try: ok=all(x in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for x in ("scripts/run_l_4_breadth_b86r4_provisioning_v5.py","scripts/validate_l_4_breadth_b86r4_provisioning_gate_v5.py","scripts/validate_l_4_breadth_b86r4_provisioning_report_v5.py","scripts/validate_l_4_breadth_b86r4_falsification_outputs_v5.py"))
        except Exception:ok=False
        return ([] if ok else [f"{order_id}:l4_b86r4_registration_mismatch"],ok,False)
    if must == "match_l4_b86r4_mirror":
        try:
            text=target.read_text(encoding="utf-8").replace("`", "");ok=all(x in text for x in ("B8.6R4","E0","edge_claim none","validation sealed"))
            if artifact_path=="experiments/hypothesis_registry.json":
                l4=next(x for x in json.loads(text)["hypotheses"] if x.get("id")=="L-4");ok=ok and any(x.get("decision")=="B8_6R4_phase_a_v5_remediation_locked_E0" for x in l4["decision_log"])
        except Exception:ok=False
        return ([] if ok else [f"{order_id}:l4_b86r4_mirror_mismatch"],ok,False)
    if must == "contain_l4_b86r3_manifest":
        try: ok=any(json.loads(x).get("gate_id")=="l_4_breadth_b86r3_provisioning_gate_v4" for x in target.read_text(encoding="utf-8").splitlines() if x)
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r3_manifest_mismatch"],ok,False)
    if must == "register_l4_b86r3_scripts":
        try: ok=all(x in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for x in ("scripts/validate_l_4_breadth_b86r3_provisioning_gate_v4.py","scripts/run_l_4_breadth_b86r3_provisioning_v4.py","scripts/validate_l_4_breadth_b86r3_provisioning_report_v4.py"))
        except Exception:ok=False
        return ([] if ok else [f"{order_id}:l4_b86r3_registration_mismatch"],ok,False)
    if must == "match_l4_b86r3_mirror":
        try:
            text=target.read_text(encoding="utf-8").replace("`", "");ok=all(x in text for x in ("B8.6R3","E0","edge_claim none","validation sealed"))
            if artifact_path=="experiments/hypothesis_registry.json":
                l4=next(x for x in json.loads(text)["hypotheses"] if x.get("id")=="L-4");ok=ok and any(x.get("decision")=="B8_6R3_phase_a_v4_remediation_locked_E0" for x in l4["decision_log"])
        except Exception:ok=False
        return ([] if ok else [f"{order_id}:l4_b86r3_mirror_mismatch"],ok,False)
    if must == "contain_l4_b86r2_manifest":
        try: ok=any(json.loads(x).get("gate_id")=="l_4_breadth_b86r2_provisioning_gate_v3" for x in target.read_text(encoding="utf-8").splitlines() if x)
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r2_manifest_mismatch"],ok,False)
    if must == "register_l4_b86r2_scripts":
        try: ok=all(x in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for x in ("scripts/validate_l_4_breadth_b86r2_provisioning_gate_v3.py","scripts/run_l_4_breadth_b86r2_provisioning_v3.py","scripts/validate_l_4_breadth_b86r2_provisioning_report_v3.py","scripts/validate_l_4_breadth_b86r2_falsification_manifest_v3.py","scripts/validate_l_4_breadth_b86r2_u8_session_dates_v3.py"))
        except Exception:ok=False
        return ([] if ok else [f"{order_id}:l4_b86r2_registration_mismatch"],ok,False)
    if must == "contain_l4_b86r_manifest":
        try: ok=any(item.get("gate_id")=="l_4_breadth_b86r_provisioning_gate_v2" for item in (json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r_manifest_mismatch"],ok,False)
    if must == "register_l4_b86r_scripts":
        try: ok=all(item in json.loads(target.read_text(encoding="utf-8")).get("scripts",[]) for item in ("scripts/validate_l_4_breadth_b86r_provisioning_gate_v2.py","scripts/run_l_4_breadth_b86r_provisioning_v2.py","scripts/validate_l_4_breadth_b86r_provisioning_report_v2.py","scripts/validate_l_4_breadth_b86r_falsification_manifest_v2.py","scripts/validate_l_4_breadth_b86r_u8_session_dates_v2.py"))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r_script_registration_mismatch"],ok,False)
    if must == "match_l4_b86_mirror":
        try:
            text=target.read_text(encoding="utf-8").replace("`", ""); ok=all(term in text for term in ("B8.6", "provisioning", "edge_claim none", "hash-only"))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86_mirror_mismatch"],ok,False)
    if must == "match_l4_b86r_mirror":
        try:
            text=target.read_text(encoding="utf-8").replace("`", ""); ok=all(term in text for term in ("B8.6R", "repo-relative", "edge_claim none", "activation"))
            if artifact_path == "experiments/hypothesis_registry.json":
                l4=next(item for item in json.loads(text).get("hypotheses",[]) if item.get("id")=="L-4")
                ok=ok and any(item.get("decision")=="B8_6R_phase_a_v2_remediation_locked_E0" for item in l4.get("decision_log",[]) if isinstance(item,dict))
        except Exception: ok=False
        return ([] if ok else [f"{order_id}:l4_b86r_mirror_mismatch"],ok,False)
    if must == "match_l4_b86r2_mirror":
        try:
            text=target.read_text(encoding="utf-8").replace("`", "");ok=all(x in text for x in ("B8.6R2","E0","edge_claim none","validation sealed"))
            if artifact_path=="experiments/hypothesis_registry.json":
                l4=next(x for x in json.loads(text)["hypotheses"] if x.get("id")=="L-4");ok=ok and any(x.get("decision")=="B8_6R2_phase_a_v3_remediation_locked_E0" for x in l4["decision_log"])
        except Exception:ok=False
        return ([] if ok else [f"{order_id}:l4_b86r2_mirror_mismatch"],ok,False)
    if must == "match_l4_b84r2_mirror":
        try: ok="B8.4R2" in target.read_text(encoding="utf-8") and "B8.5" in target.read_text(encoding="utf-8")
        except OSError: ok=False
        return ([] if ok else [f"{order_id}:l4_b84r2_mirror_mismatch"],ok,False)
    if must == "match_l4_b84_mirror":
        return _validate_l4_b84_mirror(target, order_id, artifact_path)
    if must == "register_l4_b84_scripts":
        return _validate_l4_b84_scripts(target, order_id)
    if must == "contain_l3_b713_manifest_identity":
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
        row = [x for x in rows if x.get("gate_id") == "l_3_b714_activation_contract_v3"]
        predecessor = [x for x in rows if x.get("gate_id") == "l_3_b714_activation_contract_v2"]
        predecessor_line = next((line for line in target.read_text(encoding="utf-8").splitlines() if '"gate_id":"l_3_b714_activation_contract_v2"' in line), "")
        ok = len(row) == 1 and len(predecessor) == 1 and row[0].get("artifact_sha256") == hashlib.sha256((project_root / "experiments/l_3_b714_activation_contract_v3.json").read_bytes()).hexdigest() and row[0].get("corrects_predecessor_missing_fields") == ["human_approval"] and row[0].get("predecessor_line_sha256") == hashlib.sha256(predecessor_line.encode("utf-8")).hexdigest()
        return ([] if ok else [f"{order_id}:manifest_mismatch"], ok, False)
    if must == "register_l3_b713_scripts":
        scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts", [])
        required = ("scripts/validate_l_3_b714_activation_contract_v1.py", "scripts/validate_l_3_b714_preflight_report_v1.py", "scripts/validate_l_3_b714_activation_contract_v3.py")
        ok = all(scripts.count(item) == 1 for item in required)
        return ([] if ok else [f"{order_id}:script_registration"], ok, False)
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


def _validate_l3_v1_snapshot_coverage(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    snapshots = (
        (
            "methodology_snapshots/l3_inverse_volatility_sizing_v1/wiki/concepts/inverse-volatility-weighting.md",
            "c59b512d3df9499a738b1ee256d388376f04edee1c59727f2f79ddcc905e7f72",
        ),
        (
            "methodology_snapshots/l3_inverse_volatility_sizing_v1/wiki/concepts/position-sizing.md",
            "6d24c4ffc6770590baaeb90402af4e413040ff6856b0585773657da85dc68343",
        ),
        (
            "methodology_snapshots/l3_inverse_volatility_sizing_v1/wiki/concepts/minimum-track-record-length.md",
            "ca65225740673bd363be7461b8022281da08ae32e6ff42f8887f1072eb51ad81",
        ),
    )
    blockers: list[str] = []
    for path, digest in snapshots:
        source = project_root / path
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            blockers.append(f"{order_id}:l3_v1_snapshot_hash_mismatch:{path}")
    test_path = project_root / "tests/test_validate_l_3_inverse_volatility_sizing_preregistration.py"
    if not test_path.is_file() or "SNAPSHOT_WIKI_ROOT" not in test_path.read_text(encoding="utf-8"):
        blockers.append(f"{order_id}:l3_v1_snapshot_test_coverage_missing")
    if blockers or not verify_runtime:
        return blockers, not blockers, not verify_runtime
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "tests.test_validate_l_3_inverse_volatility_sizing_preregistration",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        blockers.append(f"{order_id}:l3_v1_snapshot_test_failed")
    return blockers, not blockers, False


def _validate_l3_v1_locked_snapshot_coverage(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
    verify_runtime: bool,
) -> tuple[list[str], bool, bool]:
    locked_blockers, _, _ = _validate_locked_preregistration_gate(
        target,
        order_id,
        artifact_path,
        gate_id="l_3_inverse_volatility_sizing_v1",
        label="l3_inverse_volatility_sizing",
        expected_status="locked_before_execution",
        edge_claim_field="edge_claim",
        project_root=project_root,
        verify_runtime=False,
    )
    snapshot_blockers, snapshot_checked, snapshot_unverified = _validate_l3_v1_snapshot_coverage(
        project_root / "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py",
        order_id,
        "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py",
        project_root=project_root,
        verify_runtime=verify_runtime,
    )
    blockers = locked_blockers + snapshot_blockers
    return blockers, not blockers and snapshot_checked, snapshot_unverified


def _validate_l3_manifest_identity(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    gate_path = project_root / "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json"
    validator_path = project_root / "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py"
    try:
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    except json.JSONDecodeError:
        return [f"{order_id}:l3_locked_gate_manifest_invalid_jsonl"], False, False
    matching = [row for row in rows if row.get("gate_id") == "l_3_inverse_volatility_sizing_v1"]
    blockers: list[str] = []
    if len(matching) != 1:
        blockers.append(f"{order_id}:l3_locked_gate_entry_count:{len(matching)}")
        return blockers, False, False
    row = matching[0]
    expected = {
        "gate_type": "preregistration",
        "artifact_path": "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json",
        "validator_path": "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py",
    }
    for key, value in expected.items():
        if row.get(key) != value:
            blockers.append(f"{order_id}:l3_manifest_{key}_mismatch")
    if not gate_path.is_file() or row.get("artifact_sha256") != hashlib.sha256(gate_path.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_manifest_artifact_hash_mismatch")
    if not validator_path.is_file() or row.get("validator_sha256") != hashlib.sha256(validator_path.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_manifest_validator_hash_mismatch")
    notes = str(row.get("notes", ""))
    approval = str(row.get("human_approval", ""))
    if "E0" not in notes or "edge" not in notes or "validation" not in notes or "B7.1" not in notes:
        blockers.append(f"{order_id}:l3_manifest_claim_limit_or_seal_missing")
    if "B7" not in approval or "planning only" not in approval:
        blockers.append(f"{order_id}:l3_manifest_owner_approval_missing")
    return blockers, not blockers, False


def _validate_l3_v2_manifest_identity(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    gate_path = project_root / "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json"
    validator_path = project_root / "scripts/validate_l_3_inverse_volatility_sizing_preregistration_v2.py"
    try:
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    except json.JSONDecodeError:
        return [f"{order_id}:l3_v2_locked_gate_manifest_invalid_jsonl"], False, False
    matching = [row for row in rows if row.get("gate_id") == "l_3_inverse_volatility_sizing_v2"]
    blockers: list[str] = []
    if len(matching) != 1:
        return [f"{order_id}:l3_v2_locked_gate_entry_count:{len(matching)}"], False, False
    row = matching[0]
    expected = {
        "gate_type": "preregistration",
        "artifact_path": "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json",
        "validator_path": "scripts/validate_l_3_inverse_volatility_sizing_preregistration_v2.py",
        "supersedes_gate_id": "l_3_inverse_volatility_sizing_v1",
    }
    for key, value in expected.items():
        if row.get(key) != value:
            blockers.append(f"{order_id}:l3_v2_manifest_{key}_mismatch")
    if not gate_path.is_file() or row.get("artifact_sha256") != hashlib.sha256(gate_path.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_v2_manifest_artifact_hash_mismatch")
    if not validator_path.is_file() or row.get("validator_sha256") != hashlib.sha256(validator_path.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_v2_manifest_validator_hash_mismatch")
    if "hermetic source-provenance remediation" not in str(row.get("notes", "")).lower():
        blockers.append(f"{order_id}:l3_v2_manifest_remediation_note_missing")
    return blockers, not blockers, False


def _validate_l3_b71_manifest_identity(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    gate_path = project_root / "experiments/l_3_falsification_activation_preflight_v1.json"
    validator_path = project_root / "scripts/validate_l_3_falsification_activation_preflight_v1.py"
    try:
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b71_locked_gate_manifest_invalid_jsonl"], False, False
    matching = [row for row in rows if row.get("gate_id") == "l_3_falsification_activation_preflight_v1"]
    if len(matching) != 1:
        return [f"{order_id}:l3_b71_locked_gate_entry_count:{len(matching)}"], False, False
    row = matching[0]
    expected = {
        "gate_type": "activation_preflight_contract",
        "artifact_path": "experiments/l_3_falsification_activation_preflight_v1.json",
        "validator_path": "scripts/validate_l_3_falsification_activation_preflight_v1.py",
    }
    blockers: list[str] = []
    for key, value in expected.items():
        if row.get(key) != value:
            blockers.append(f"{order_id}:l3_b71_manifest_{key}_mismatch")
    if not gate_path.is_file() or row.get("artifact_sha256") != hashlib.sha256(gate_path.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_b71_manifest_artifact_hash_mismatch")
    if not validator_path.is_file() or row.get("validator_sha256") != hashlib.sha256(validator_path.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_b71_manifest_validator_hash_mismatch")
    note = str(row.get("notes", "")).lower()
    approval = str(row.get("human_approval", "")).lower()
    if not all(item in note for item in ("e0", "edge_claim none", "sealed", "neither data/container inspection nor execution")):
        blockers.append(f"{order_id}:l3_b71_manifest_claim_limit_or_seal_missing")
    if "owner explicitly authorized b7.1" not in approval:
        blockers.append(f"{order_id}:l3_b71_manifest_owner_authorization_missing")
    return blockers, not blockers, False


def _validate_l3_v2_source_binding(
    target: Path,
    order_id: str,
    artifact_path: str,
    *,
    project_root: Path,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        gate = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l3_v2_gate_invalid_json"], False, False
    expected = [
        ("methodology_snapshots/l3_inverse_volatility_sizing_v1/wiki/concepts/inverse-volatility-weighting.md", "c59b512d3df9499a738b1ee256d388376f04edee1c59727f2f79ddcc905e7f72"),
        ("methodology_snapshots/l3_inverse_volatility_sizing_v1/wiki/concepts/position-sizing.md", "6d24c4ffc6770590baaeb90402af4e413040ff6856b0585773657da85dc68343"),
        ("methodology_snapshots/l3_inverse_volatility_sizing_v1/wiki/concepts/minimum-track-record-length.md", "ca65225740673bd363be7461b8022281da08ae32e6ff42f8887f1072eb51ad81"),
    ]
    source_binding = gate.get("source_binding") if isinstance(gate, dict) else None
    snapshots = source_binding.get("methodology_snapshots") if isinstance(source_binding, dict) else None
    blockers: list[str] = []
    if not isinstance(snapshots, list) or len(snapshots) != len(expected):
        blockers.append(f"{order_id}:l3_v2_snapshot_declarations_mismatch")
        return blockers, False, False
    for snapshot, (path, digest) in zip(snapshots, expected, strict=True):
        if not isinstance(snapshot, dict) or snapshot.get("snapshot_path") != path or snapshot.get("sha256") != digest:
            blockers.append(f"{order_id}:l3_v2_snapshot_declarations_mismatch")
            continue
        source = project_root / path
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            blockers.append(f"{order_id}:l3_v2_snapshot_hash_mismatch:{path}")
    return blockers, not blockers, False


def _l3_historical_or_b73_terminal_state(l3: dict[str, Any], *, allowed_evidence: tuple[list[dict[str, str]], ...]) -> bool:
    if l3.get("edge_claim") not in (None, "none"):
        return False
    if l3.get("status") == "active" and l3.get("evidence") in allowed_evidence:
        return True
    terminal_evidence = [{"evidence_tier": "E1", "path": "reports/experiments/l_3_falsification_report.json"}]
    decision_log = l3.get("decision_log")
    return (
        l3.get("status") == "scope_restricted"
        and l3.get("evidence") == terminal_evidence
        and isinstance(decision_log, list)
        and any(
            entry.get("decision") == "B7_3_one_run_invalidated_scope_restricted_E1"
            for entry in decision_log
            if isinstance(entry, dict)
        )
    )


def _validate_l3_b73_manifest_identity(
    target: Path, order_id: str, artifact_path: str, *, project_root: Path
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b73_locked_gate_manifest_invalid_jsonl"], False, False
    matching = [row for row in rows if row.get("gate_id") == "l_3_one_run_falsification_authorization_v1"]
    if len(matching) != 1:
        return [f"{order_id}:l3_b73_manifest_entry_count:{len(matching)}"], False, False
    row = matching[0]
    artifact = project_root / "experiments/l_3_one_run_falsification_authorization_v1.json"
    validator = project_root / "scripts/validate_l_3_one_run_falsification_authorization_v1.py"
    expected = {
        "gate_type": "one_run_execution_authorization",
        "artifact_path": "experiments/l_3_one_run_falsification_authorization_v1.json",
        "validator_path": "scripts/validate_l_3_one_run_falsification_authorization_v1.py",
    }
    blockers = [f"{order_id}:l3_b73_manifest_{key}_mismatch" for key, value in expected.items() if row.get(key) != value]
    if not artifact.is_file() or row.get("artifact_sha256") != hashlib.sha256(artifact.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_b73_manifest_artifact_hash_mismatch")
    if not validator.is_file() or row.get("validator_sha256") != hashlib.sha256(validator.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_b73_manifest_validator_hash_mismatch")
    note = str(row.get("notes", "")).lower()
    approval = str(row.get("human_approval", "")).lower()
    if not all(item in note for item in ("b7.3", "one falsification-window", "validation", "forbidden")):
        blockers.append(f"{order_id}:l3_b73_manifest_claim_limit_missing")
    if "owner explicitly authorized" not in approval or "2026-07-26" not in approval:
        blockers.append(f"{order_id}:l3_b73_manifest_owner_authorization_missing")
    return blockers, not blockers, False


def _validate_l3_b73_authorization(
    target: Path, order_id: str, artifact_path: str, *, project_root: Path
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b73_authorization_invalid_json"], False, False
    expected = {
        "order_id": "B7.3",
        "gate_id": "l_3_one_run_falsification_authorization_v1",
        "hypothesis_id": "L-3",
        "status": "locked_one_run_falsification_authorized",
        "evidence_ceiling": "E1",
        "edge_claim": "none",
        "approved_container": {"path": "data/normalized/l1_yahoo_daily_v1.json", "falsification_end": "2015-12-31", "validation_start": "2016-01-04"},
        "one_run": {"maximum_real_return_decision_runs": 1, "ledger_path": "reports/experiments/l_3_falsification_execution_ledger.jsonl", "report_path": "reports/experiments/l_3_falsification_report.json"},
    }
    blockers = [f"{order_id}:l3_b73_authorization_{key}_mismatch" for key, value in expected.items() if payload.get(key) != value]
    authorizations = payload.get("authorizations")
    if not isinstance(authorizations, dict) or any(authorizations.get(key) is not value for key, value in {
        "data_access_authorized": True, "container_inspection_authorized": True, "return_parsing_authorized": True,
        "execution_authorized": True, "report_decision_authorized": True, "validation_access_authorized": False,
        "provider_network_acquisition_authorized": False, "credentials_authorized": False, "paid_action_authorized": False,
        "broker_authorized": False, "paper_trade_authorized": False, "real_money_authorized": False,
    }.items()):
        blockers.append(f"{order_id}:l3_b73_authorization_drift")
    if not isinstance(payload.get("hard_stops"), list) or len(payload["hard_stops"]) != 4:
        blockers.append(f"{order_id}:l3_b73_hard_stops_incomplete")
    return blockers, not blockers, False


def _validate_l3_b73_runner_guards(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = ("validate_authorization", "_preflight", "mixed_or_validation_container_hard_stop", "second_real_return_decision_run_forbidden", "2007-02-05", "asset_multiplier':1", "trade_multiplier':1")
    blockers = [f"{order_id}:l3_b73_runner_guard_missing:{item}" for item in required if item not in text]
    return blockers, not blockers, False


def _validate_l3_b73_report_schema(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        schema = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b73_report_schema_invalid_json"], False, False
    required = set(schema.get("required", []))
    blockers: list[str] = []
    if schema.get("additionalProperties") is not False:
        blockers.append(f"{order_id}:l3_b73_report_schema_not_closed_world")
    for field in ("post_parse_hard_stop", "producing_git_commit", "authorization_sha256", "validation_seal", "observation_counts"):
        if field not in required:
            blockers.append(f"{order_id}:l3_b73_report_schema_missing:{field}")
    return blockers, not blockers, False


def _validate_l3_b73_report_and_ledger(
    target: Path, order_id: str, artifact_path: str, *, project_root: Path
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    ledger_path = project_root / "reports/experiments/l_3_falsification_execution_ledger.jsonl"
    authorization_path = project_root / "experiments/l_3_one_run_falsification_authorization_v1.json"
    try:
        report = json.loads(target.read_text(encoding="utf-8"))
        ledger = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError):
        return [f"{order_id}:l3_b73_report_or_ledger_invalid"], False, False
    runs = [row for row in ledger if row.get("event") == "real_return_decision_run"]
    blockers: list[str] = []
    if len(runs) != 1:
        blockers.append(f"{order_id}:l3_b73_exactly_one_run_ledger_mismatch")
    expected = {
        "report_mode": "execution_invalidated_post_parse", "execution_status": "scope_restricted", "decision": "scope_restricted",
        "evidence_tier": "E1", "edge_claim": "none", "market_returns_read": True,
    }
    blockers.extend(f"{order_id}:l3_b73_report_{key}_mismatch" for key, value in expected.items() if report.get(key) != value)
    if report.get("authorization_sha256") != hashlib.sha256(authorization_path.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_b73_report_authorization_provenance_mismatch")
    if report.get("validation_seal") != {"start": "2016-01-04", "end": "2026-06-30", "status": "sealed_not_accessed", "validation_access_authorized": False}:
        blockers.append(f"{order_id}:l3_b73_validation_seal_mismatch")
    counts = report.get("observation_counts")
    if not isinstance(counts, dict) or counts.get("weekly_paired_observations") != 500 or counts.get("asset_multiplier") != 1 or counts.get("trade_multiplier") != 1:
        blockers.append(f"{order_id}:l3_b73_observation_accounting_mismatch")
    hard_stop = str(report.get("post_parse_hard_stop", ""))
    if "500" not in hard_stop or "465" not in hard_stop or "no rerun" not in hard_stop.lower():
        blockers.append(f"{order_id}:l3_b73_post_parse_hard_stop_missing")
    if runs and (runs[0].get("producing_git_commit") != report.get("producing_git_commit") or runs[0].get("run_id") != "B7.3-L3-ONE"):
        blockers.append(f"{order_id}:l3_b73_commit_provenance_mismatch")
    return blockers, not blockers, False


def _validate_l3_b73_registry_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        hypotheses = json.loads(target.read_text(encoding="utf-8")).get("hypotheses", [])
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b73_registry_invalid_json"], False, False
    matching = [item for item in hypotheses if isinstance(item, dict) and item.get("id") == "L-3"]
    if len(matching) != 1:
        return [f"{order_id}:l3_b73_registry_entry_count:{len(matching)}"], False, False
    l3 = matching[0]
    return ([] if _l3_historical_or_b73_terminal_state(l3, allowed_evidence=()) else [f"{order_id}:l3_b73_registry_terminal_state_mismatch"], _l3_historical_or_b73_terminal_state(l3, allowed_evidence=()), False)


def _validate_l3_b73_text_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    normalized = text.lower().replace("_", " ").replace("-", " ")
    required = ("l 3", "e1 scope restricted", "500", "465", "no rerun")
    blockers = [f"{order_id}:l3_b73_text_mirror_missing:{item}" for item in required if item not in normalized]
    if not re.search(r"validation.{0,24}sealed", text, flags=re.IGNORECASE):
        blockers.append(f"{order_id}:l3_b73_text_mirror_missing:validation_sealed")
    return blockers, not blockers, False


def _validate_l3_b73_script_registration(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts")
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b73_script_registry_invalid_json"], False, False
    required = ("scripts/validate_l_3_one_run_falsification_authorization_v1.py", "scripts/run_l_3_falsification.py", "scripts/validate_l_3_falsification_report.py")
    blockers = [f"{order_id}:l3_b73_script_registration_missing:{path}" for path in required if not isinstance(scripts, list) or scripts.count(path) != 1]
    return blockers, not blockers, False


def _validate_l3_b74_remediation(
    target: Path, order_id: str, artifact_path: str, *, project_root: Path
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        remediation = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b74_remediation_invalid_json"], False, False
    expected = {
        "schema_version": "lily_l3_invalid_run_ledger_remediation_v1", "order_id": "B7.4", "hypothesis_id": "L-3",
        "status": "locked_invalid_run_ledger_remediation", "authoritative_outcome": "scope_restricted", "edge_claim": "none",
        "b7_4_attestation": {"market_returns_read_count": 0, "real_return_decision_run_count": 1, "invalidation_count": 1, "validation_access_authorized": False, "validation_status": "sealed_not_accessed", "second_run_authorized": False},
    }
    blockers = [f"{order_id}:l3_b74_remediation_{key}_mismatch" for key, value in expected.items() if remediation.get(key) != value]
    report = project_root / "reports/experiments/l_3_falsification_report.json"
    source_binding = remediation.get("source_binding")
    if not isinstance(source_binding, dict) or source_binding.get("final_report", {}).get("sha256") != hashlib.sha256(report.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_b74_report_hash_binding_mismatch")
    invalidation = remediation.get("invalidation")
    if not isinstance(invalidation, dict) or invalidation.get("reason") != "observation_window_started_before_2007-02-05" or invalidation.get("observed_weekly_paired_observations") != 500 or invalidation.get("locked_weekly_observation_ceiling") != 465 or invalidation.get("provisional_metrics_inference_status") != "invalid_unusable":
        blockers.append(f"{order_id}:l3_b74_invalidation_facts_mismatch")
    return blockers, not blockers, False


def _validate_l3_b74_ledger_state(
    target: Path, order_id: str, artifact_path: str, *, project_root: Path
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        rows = [line for line in target.read_bytes().splitlines() if line]
        parsed = [json.loads(line) for line in rows]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return [f"{order_id}:l3_b74_ledger_invalid"], False, False
    blockers: list[str] = []
    runs = [row for row in parsed if row.get("event") == "real_return_decision_run"]
    invalidations = [row for row in parsed if row.get("event") == "real_return_decision_run_invalidated"]
    if len(parsed) != 2 or len(runs) != 1 or len(invalidations) != 1:
        blockers.append(f"{order_id}:l3_b74_ledger_event_count_mismatch")
    if not rows or hashlib.sha256(rows[0]).hexdigest() != "594b8cbbdf7c27769191ab9495275803478481121372cd3bfc6f7e6d3a8a556a":
        blockers.append(f"{order_id}:l3_b74_original_row_hash_mismatch")
    if invalidations:
        event = invalidations[0]
        expected = {"run_id": "B7.3-L3-ONE", "producing_git_commit": "3e3cfc773b8e327dca63bfdd8f2a1b103376173d", "reason": "observation_window_started_before_2007-02-05", "observed_weekly_paired_observations": 500, "locked_weekly_observation_ceiling": 465, "authoritative_outcome": "scope_restricted", "market_returns_read_count": 0, "authorizes_real_return_decision_run": False, "validation_access_authorized": False}
        blockers.extend(f"{order_id}:l3_b74_invalidation_{key}_mismatch" for key, value in expected.items() if event.get(key) != value)
    return blockers, not blockers, False


def _validate_l3_b74_report_state(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        report = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b74_report_invalid_json"], False, False
    expected = {"decision": "scope_restricted", "execution_status": "scope_restricted", "evidence_tier": "E1", "edge_claim": "none", "report_mode": "execution_invalidated_post_parse"}
    blockers = [f"{order_id}:l3_b74_report_{key}_mismatch" for key, value in expected.items() if report.get(key) != value]
    return blockers, not blockers, False


def _validate_l3_b74_registry_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        hypotheses = json.loads(target.read_text(encoding="utf-8")).get("hypotheses", [])
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b74_registry_invalid_json"], False, False
    l3 = next((item for item in hypotheses if isinstance(item, dict) and item.get("id") == "L-3"), None)
    if not isinstance(l3, dict):
        return [f"{order_id}:l3_b74_registry_entry_missing"], False, False
    decision_log = l3.get("decision_log")
    valid = l3.get("status") == "scope_restricted" and l3.get("edge_claim") in (None, "none") and isinstance(decision_log, list) and any(entry.get("decision") == "B7_4_invalid_run_ledger_remediated_E1" for entry in decision_log if isinstance(entry, dict))
    return ([] if valid else [f"{order_id}:l3_b74_registry_terminal_state_mismatch"], valid, False)


def _validate_l3_b74_text_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = ("B7.4", "scope_restricted", "original ledger", "invalid", "validation")
    blockers = [f"{order_id}:l3_b74_text_mirror_missing:{item}" for item in required if item not in text]
    return blockers, not blockers, False


def _validate_l3_b74_report_validator_registration(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts")
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b74_script_registry_invalid_json"], False, False
    valid = isinstance(scripts, list) and scripts.count("scripts/validate_l_3_falsification_report.py") == 1
    return ([] if valid else [f"{order_id}:l3_b74_report_validator_registration_mismatch"], valid, False)


def _validate_l3_b75_gate(
    target: Path, order_id: str, artifact_path: str, *, project_root: Path, verify_runtime: bool, runtime_cache: dict[str, bool]
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    validator = project_root / "scripts/validate_l_3_corrected_rerun_pre_return_schedule_v1.py"
    if not validator.is_file():
        return [f"{order_id}:l3_b75_validator_missing"], False, False
    completed = subprocess.run([sys.executable, str(validator)], cwd=project_root, text=True, capture_output=True, check=False)
    passed = completed.returncode == 0
    return ([] if passed else [f"{order_id}:l3_b75_gate_validator_failed"], passed, False)


def _validate_l3_b75_manifest_identity(
    target: Path, order_id: str, artifact_path: str, *, project_root: Path
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b75_locked_gate_manifest_invalid_jsonl"], False, False
    matching = [row for row in rows if row.get("gate_id") == "l_3_corrected_rerun_pre_return_schedule_v1"]
    if len(matching) != 1:
        return [f"{order_id}:l3_b75_manifest_entry_count:{len(matching)}"], False, False
    row = matching[0]
    artifact = project_root / "experiments/l_3_corrected_rerun_pre_return_schedule_v1.json"
    validator = project_root / "scripts/validate_l_3_corrected_rerun_pre_return_schedule_v1.py"
    expected = {
        "gate_type": "corrected_rerun_pre_return_schedule_contract",
        "artifact_path": "experiments/l_3_corrected_rerun_pre_return_schedule_v1.json",
        "validator_path": "scripts/validate_l_3_corrected_rerun_pre_return_schedule_v1.py",
    }
    blockers = [f"{order_id}:l3_b75_manifest_{key}_mismatch" for key, value in expected.items() if row.get(key) != value]
    if not artifact.is_file() or row.get("artifact_sha256") != hashlib.sha256(artifact.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_b75_manifest_artifact_hash_mismatch")
    if not validator.is_file() or row.get("validator_sha256") != hashlib.sha256(validator.read_bytes()).hexdigest():
        blockers.append(f"{order_id}:l3_b75_manifest_validator_hash_mismatch")
    note, approval = str(row.get("notes", "")).lower(), str(row.get("human_approval", "")).lower()
    if not all(value in note for value in ("e0", "no-data", "465", "validation", "fresh")):
        blockers.append(f"{order_id}:l3_b75_manifest_claim_limit_missing")
    if "owner explicitly authorized" not in approval or "2026-07-27" not in approval:
        blockers.append(f"{order_id}:l3_b75_manifest_owner_authorization_missing")
    return blockers, not blockers, False


def _validate_l3_b75_registry_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        hypotheses = json.loads(target.read_text(encoding="utf-8")).get("hypotheses", [])
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b75_registry_invalid_json"], False, False
    l3 = next((item for item in hypotheses if isinstance(item, dict) and item.get("id") == "L-3"), None)
    if not isinstance(l3, dict):
        return [f"{order_id}:l3_b75_registry_entry_missing"], False, False
    decisions = l3.get("decision_log")
    valid = (
        l3.get("status") == "scope_restricted" and l3.get("edge_claim") in (None, "none")
        and isinstance(decisions, list)
        and any(isinstance(entry, dict) and entry.get("decision") == "B7_5_corrected_rerun_schedule_gate_locked_E0" for entry in decisions)
    )
    return ([] if valid else [f"{order_id}:l3_b75_registry_mirror_mismatch"], valid, False)


def _validate_l3_b75_text_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    normalized = text.lower().replace("_", " ").replace("-", " ")
    required = ("b7.5", "e0", "465", "scope restricted", "validation", "owner authorization")
    blockers = [f"{order_id}:l3_b75_text_mirror_missing:{item}" for item in required if item not in normalized]
    return blockers, not blockers, False


def _validate_l3_b75_validator_registration(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts")
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b75_script_registry_invalid_json"], False, False
    registered = "scripts/validate_l_3_corrected_rerun_pre_return_schedule_v1.py"
    valid = isinstance(scripts, list) and scripts.count(registered) == 1
    return ([] if valid else [f"{order_id}:l3_b75_validator_registration_mismatch"], valid, False)


def _validate_l3_b76_activation(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    run = subprocess.run([sys.executable, "scripts/validate_l_3_corrected_rerun_activation_v1.py"], cwd=project_root, text=True, capture_output=True, check=False)
    return ([] if run.returncode == 0 else [f"{order_id}:l3_b76_activation_validator_failed"], run.returncode == 0, False)


def _validate_l3_b76_report(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    run = subprocess.run([sys.executable, "scripts/validate_l_3_corrected_rerun_report.py"], cwd=project_root, text=True, capture_output=True, check=False)
    return ([] if run.returncode == 0 else [f"{order_id}:l3_b76_report_validator_failed"], run.returncode == 0, False)


def _validate_l3_b76_preflight_report(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    run = subprocess.run([sys.executable, "scripts/validate_l_3_corrected_rerun_preflight_report.py"], cwd=project_root, text=True, capture_output=True, check=False)
    return ([] if run.returncode == 0 else [f"{order_id}:l3_b76_preflight_report_validator_failed"], run.returncode == 0, False)


def _validate_l3_b76_manifest_identity(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try: rows=[json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line]
    except json.JSONDecodeError: return [f"{order_id}:l3_b76_manifest_invalid"], False, False
    matches=[row for row in rows if row.get("gate_id")=="l_3_corrected_rerun_activation_v1"]
    if len(matches)!=1:return [f"{order_id}:l3_b76_manifest_entry_count:{len(matches)}"],False,False
    row=matches[0]; artifact=project_root/'experiments/l_3_corrected_rerun_activation_v1.json'; validator=project_root/'scripts/validate_l_3_corrected_rerun_activation_v1.py'
    bad=[]
    if row.get('artifact_sha256')!=hashlib.sha256(artifact.read_bytes()).hexdigest():bad.append(f"{order_id}:l3_b76_manifest_artifact_hash_mismatch")
    if row.get('validator_sha256')!=hashlib.sha256(validator.read_bytes()).hexdigest():bad.append(f"{order_id}:l3_b76_manifest_validator_hash_mismatch")
    return bad,not bad,False


def _validate_l3_b77_manifest_identity(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try: rows=[json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line]
    except json.JSONDecodeError: return [f"{order_id}:l3_b77_manifest_invalid"], False, False
    matches=[row for row in rows if row.get("gate_id")=="l_3_corrected_rerun_activation_v2"]
    artifact=project_root/'experiments/l_3_corrected_rerun_activation_v2.json'; validator=project_root/'scripts/validate_l_3_corrected_rerun_activation_v2.py'
    if len(matches)!=1:return [f"{order_id}:l3_b77_manifest_entry_count:{len(matches)}"],False,False
    row=matches[0];bad=[]
    if row.get('supersedes_gate_id')!='l_3_corrected_rerun_activation_v1':bad.append(f"{order_id}:l3_b77_supersession_mismatch")
    if row.get('artifact_sha256')!=hashlib.sha256(artifact.read_bytes()).hexdigest():bad.append(f"{order_id}:l3_b77_manifest_artifact_hash_mismatch")
    if row.get('validator_sha256')!=hashlib.sha256(validator.read_bytes()).hexdigest():bad.append(f"{order_id}:l3_b77_manifest_validator_hash_mismatch")
    return bad,not bad,False


def _validate_l3_b78_gate(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    run = subprocess.run([sys.executable, "scripts/validate_l_3_corrected_rerun_activation_v4.py"], cwd=project_root, text=True, capture_output=True, check=False)
    return ([] if run.returncode == 0 else [f"{order_id}:l3_b78_gate_validator_failed"], run.returncode == 0, False)


def _validate_l3_b78_manifest_identity(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try: rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line]
    except json.JSONDecodeError: return [f"{order_id}:l3_b78_manifest_invalid"], False, False
    matches = [row for row in rows if row.get("gate_id") == "l_3_corrected_rerun_activation_v4"]
    if len(matches) != 1: return [f"{order_id}:l3_b78_manifest_entry_count:{len(matches)}"], False, False
    row = matches[0]; artifact = project_root / "experiments/l_3_corrected_rerun_activation_v4.json"; validator = project_root / "scripts/validate_l_3_corrected_rerun_activation_v4.py"
    bad = []
    if row.get("supersedes_gate_id") != "l_3_corrected_rerun_activation_v3": bad.append(f"{order_id}:l3_b78_supersession_mismatch")
    if row.get("artifact_path") != "experiments/l_3_corrected_rerun_activation_v4.json" or row.get("artifact_sha256") != hashlib.sha256(artifact.read_bytes()).hexdigest(): bad.append(f"{order_id}:l3_b78_manifest_artifact_hash_mismatch")
    if row.get("validator_path") != "scripts/validate_l_3_corrected_rerun_activation_v4.py" or row.get("validator_sha256") != hashlib.sha256(validator.read_bytes()).hexdigest(): bad.append(f"{order_id}:l3_b78_manifest_validator_hash_mismatch")
    if not isinstance(row.get("reviewed_by"), str) or not row["reviewed_by"].strip(): bad.append(f"{order_id}:l3_b78_reviewer_missing")
    return bad, not bad, False


def _validate_l3_b78_registry_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try: registry = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError: return [f"{order_id}:l3_b78_registry_invalid_json"], False, False
    l3 = next((item for item in registry.get("hypotheses", []) if item.get("id") == "L-3"), {})
    notes = " ".join(str(item.get("notes", "")) for item in l3.get("decision_log", []) if isinstance(item, dict))
    ok = "B7.8" in notes and "E0" in notes and "validation sealed" in notes and "edge_claim none" in notes
    return ([] if ok else [f"{order_id}:l3_b78_registry_mirror_missing"], ok, False)


def _validate_l3_b78_text_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(target, order_id, artifact_path, "l3_b78_text_mirror", ("B7.8", "synthetic-only", "E0", "validation sealed", "edge_claim none"))


def _validate_l3_b78_script_registration(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try: scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts")
    except json.JSONDecodeError: return [f"{order_id}:l3_b78_script_registry_invalid_json"], False, False
    required = ("scripts/run_l_3_corrected_rerun_v3.py", "scripts/validate_l_3_corrected_rerun_activation_v3.py", "scripts/validate_l_3_corrected_rerun_report_v3.py")
    ok = isinstance(scripts, list) and all(scripts.count(item) == 1 for item in required)
    return ([] if ok else [f"{order_id}:l3_b78_script_registration_mismatch"], ok, False)


def _validate_l3_b79_gate(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    run = subprocess.run([sys.executable, "scripts/validate_l_3_corrected_rerun_activation_v5.py"], cwd=project_root, text=True, capture_output=True, check=False)
    return ([] if run.returncode == 0 else [f"{order_id}:l3_b79_gate_validator_failed"], run.returncode == 0, False)


def _validate_l3_b79_manifest_identity(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try: rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line]
    except json.JSONDecodeError: return [f"{order_id}:l3_b79_manifest_invalid"], False, False
    matches = [row for row in rows if row.get("gate_id") == "l_3_corrected_rerun_activation_v5"]
    if len(matches) != 1: return [f"{order_id}:l3_b79_manifest_entry_count:{len(matches)}"], False, False
    row = matches[0]; artifact = project_root / "experiments/l_3_corrected_rerun_activation_v5.json"; validator = project_root / "scripts/validate_l_3_corrected_rerun_activation_v5.py"
    bad = []
    if row.get("supersedes_gate_id") != "l_3_corrected_rerun_activation_v4": bad.append(f"{order_id}:l3_b79_supersession_mismatch")
    if row.get("artifact_path") != "experiments/l_3_corrected_rerun_activation_v5.json" or row.get("artifact_sha256") != hashlib.sha256(artifact.read_bytes()).hexdigest(): bad.append(f"{order_id}:l3_b79_manifest_artifact_hash_mismatch")
    if row.get("validator_path") != "scripts/validate_l_3_corrected_rerun_activation_v5.py" or row.get("validator_sha256") != hashlib.sha256(validator.read_bytes()).hexdigest(): bad.append(f"{order_id}:l3_b79_manifest_validator_hash_mismatch")
    if not isinstance(row.get("reviewed_by"), str) or not row["reviewed_by"].strip(): bad.append(f"{order_id}:l3_b79_reviewer_missing")
    return bad, not bad, False


def _validate_l3_b79_registry_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try: registry = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError: return [f"{order_id}:l3_b79_registry_invalid_json"], False, False
    l3 = next((item for item in registry.get("hypotheses", []) if item.get("id") == "L-3"), {})
    notes = " ".join(str(item.get("notes", "")) for item in l3.get("decision_log", []) if isinstance(item, dict))
    ok = "B7.9" in notes and "E0" in notes and "validation sealed" in notes and "edge_claim none" in notes
    return ([] if ok else [f"{order_id}:l3_b79_registry_mirror_missing"], ok, False)


def _validate_l3_b79_text_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(target, order_id, artifact_path, "l3_b79_text_mirror", ("B7.9", "synthetic-only", "E0", "validation sealed", "edge_claim none"))


def _validate_l3_b79_script_registration(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file(): return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try: scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts")
    except json.JSONDecodeError: return [f"{order_id}:l3_b79_script_registry_invalid_json"], False, False
    required = ("scripts/run_l_3_corrected_rerun_v5.py", "scripts/validate_l_3_corrected_rerun_activation_v5.py", "scripts/validate_l_3_corrected_rerun_report_v5.py")
    ok = isinstance(scripts, list) and all(scripts.count(item) == 1 for item in required)
    return ([] if ok else [f"{order_id}:l3_b79_script_registration_mismatch"], ok, False)

def _validate_l3_b710_gate(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    run=subprocess.run([sys.executable,"scripts/validate_l_3_corrected_rerun_activation_v6.py"],cwd=project_root,text=True,capture_output=True,check=False)
    return ([] if target.is_file() and run.returncode==0 else [f"{order_id}:gate_failed"],target.is_file() and run.returncode==0,False)
def _validate_l3_b710_manifest_identity(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    try: rows=[json.loads(x) for x in target.read_text(encoding="utf-8").splitlines() if x]
    except Exception:return [f"{order_id}:manifest_invalid"],False,False
    rows=[x for x in rows if x.get("gate_id")=="l_3_corrected_rerun_activation_v6"];a=project_root/'experiments/l_3_corrected_rerun_activation_v6.json';v=project_root/'scripts/validate_l_3_corrected_rerun_activation_v6.py'
    ok=len(rows)==1 and rows[0].get('supersedes_gate_id')=='l_3_corrected_rerun_activation_v5' and rows[0].get('artifact_sha256')==hashlib.sha256(a.read_bytes()).hexdigest() and rows[0].get('validator_sha256')==hashlib.sha256(v.read_bytes()).hexdigest() and bool(rows[0].get('reviewed_by'))
    return ([] if ok else [f"{order_id}:manifest_mismatch"],ok,False)
def _validate_l3_b710_registry_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    try:l3=next(x for x in json.loads(target.read_text(encoding='utf-8')).get('hypotheses',[]) if x.get('id')=='L-3');text=' '.join(str(x.get('notes','')) for x in l3.get('decision_log',[]))
    except Exception:text=''
    ok=all(x in text for x in ('B7.10','E0','validation sealed','edge_claim none'));return ([] if ok else [f"{order_id}:registry_mirror"],ok,False)
def _validate_l3_b710_text_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(target,order_id,artifact_path,'l3_b710_text_mirror',('B7.10','synthetic-only','E0','validation sealed','edge_claim none'))
def _validate_l3_b710_script_registration(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    try:s=json.loads(target.read_text(encoding='utf-8')).get('scripts')
    except Exception:s=[]
    req=('scripts/run_l_3_corrected_rerun_v6.py','scripts/validate_l_3_corrected_rerun_activation_v6.py','scripts/validate_l_3_corrected_rerun_report_v6.py');ok=isinstance(s,list) and all(s.count(x)==1 for x in req)
    return ([] if ok else [f"{order_id}:script_registration"],ok,False)

def _validate_l3_b711_gate(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    run=subprocess.run([sys.executable,"scripts/validate_l_3_corrected_rerun_activation_v7.py"],cwd=project_root,text=True,capture_output=True,check=False)
    return ([] if target.is_file() and run.returncode==0 else [f"{order_id}:gate_failed"],target.is_file() and run.returncode==0,False)
def _validate_l3_b711_manifest_identity(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    try: rows=[json.loads(x) for x in target.read_text(encoding="utf-8").splitlines() if x]
    except Exception:return [f"{order_id}:manifest_invalid"],False,False
    rows=[x for x in rows if x.get("gate_id")=="l_3_corrected_rerun_activation_v7"];a=project_root/'experiments/l_3_corrected_rerun_activation_v7.json';v=project_root/'scripts/validate_l_3_corrected_rerun_activation_v7.py'
    ok=len(rows)==1 and rows[0].get('supersedes_gate_id')=='l_3_corrected_rerun_activation_v6' and rows[0].get('artifact_sha256')==hashlib.sha256(a.read_bytes()).hexdigest() and rows[0].get('validator_sha256')==hashlib.sha256(v.read_bytes()).hexdigest() and bool(rows[0].get('reviewed_by'))
    return ([] if ok else [f"{order_id}:manifest_mismatch"],ok,False)
def _validate_l3_b711_registry_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    try:l3=next(x for x in json.loads(target.read_text(encoding='utf-8')).get('hypotheses',[]) if x.get('id')=='L-3');text=' '.join(str(x.get('notes','')) for x in l3.get('decision_log',[]))
    except Exception:text=''
    ok=all(x in text for x in ('B7.10 Inspector rejection','B7.11','E0','validation sealed','edge_claim none'));return ([] if ok else [f"{order_id}:registry_mirror"],ok,False)
def _validate_l3_b711_text_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(target,order_id,artifact_path,'l3_b711_text_mirror',('B7.10 Inspector rejection','B7.11','synthetic-only','E0','validation sealed','edge_claim none'))
def _validate_l3_b711_script_registration(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    try:s=json.loads(target.read_text(encoding='utf-8')).get('scripts')
    except Exception:s=[]
    req=('scripts/run_l_3_corrected_rerun_v7.py','scripts/validate_l_3_corrected_rerun_activation_v7.py','scripts/validate_l_3_corrected_rerun_report_v7.py');ok=isinstance(s,list) and all(s.count(x)==1 for x in req)
    return ([] if ok else [f"{order_id}:script_registration"],ok,False)

def _validate_l3_b712_gate(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    run=subprocess.run([sys.executable,"scripts/validate_l_3_corrected_rerun_activation_v8.py"],cwd=project_root,text=True,capture_output=True,check=False)
    return ([] if target.is_file() and run.returncode==0 else [f"{order_id}:gate_failed"],target.is_file() and run.returncode==0,False)
def _validate_l3_b712_manifest_identity(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    try: rows=[json.loads(x) for x in target.read_text(encoding="utf-8").splitlines() if x]
    except Exception:return [f"{order_id}:manifest_invalid"],False,False
    rows=[x for x in rows if x.get("gate_id")=="l_3_corrected_rerun_activation_v8"];a=project_root/'experiments/l_3_corrected_rerun_activation_v8.json';v=project_root/'scripts/validate_l_3_corrected_rerun_activation_v8.py'
    ok=len(rows)==1 and rows[0].get('supersedes_gate_id')=='l_3_corrected_rerun_activation_v7' and rows[0].get('artifact_sha256')==hashlib.sha256(a.read_bytes()).hexdigest() and rows[0].get('validator_sha256')==hashlib.sha256(v.read_bytes()).hexdigest() and bool(rows[0].get('reviewed_by'))
    return ([] if ok else [f"{order_id}:manifest_mismatch"],ok,False)
def _validate_l3_b712_fixture_identity(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    gate=project_root/'experiments/l_3_corrected_rerun_activation_v8.json'
    try:identity=json.loads(gate.read_text(encoding='utf-8')).get('synthetic_fixture');payload=json.loads(target.read_text(encoding='utf-8'))
    except Exception:return [f"{order_id}:fixture_invalid"],False,False
    ok=identity=={'path':'tests/fixtures/l3_corrected_rerun_v8/synthetic_evaluation.json','sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'observations_sha256':payload.get('closed_world_observations_sha256')}
    return ([] if ok else [f"{order_id}:fixture_identity_mismatch"],ok,False)
def _validate_l3_b712_runner(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    run=subprocess.run([sys.executable,'scripts/run_l_3_corrected_rerun_v8.py','--synthetic-report','tests/fixtures/l3_corrected_rerun_v8/synthetic_evaluation.json'],cwd=project_root,text=True,capture_output=True,check=False)
    return ([] if target.is_file() and run.returncode==0 else [f"{order_id}:runner_failed"],target.is_file() and run.returncode==0,False)
def _validate_l3_b712_registry_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    try:l3=next(x for x in json.loads(target.read_text(encoding='utf-8')).get('hypotheses',[]) if x.get('id')=='L-3');text=' '.join(str(x.get('notes','')) for x in l3.get('decision_log',[]))
    except Exception:text=''
    ok=all(x in text for x in ('B7.12','E0','validation sealed','edge_claim none'));return ([] if ok else [f"{order_id}:registry_mirror"],ok,False)
def _validate_l3_b712_text_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(target,order_id,artifact_path,'l3_b712_text_mirror',('B7.12','synthetic-only','E0','validation sealed','edge_claim none'))
def _validate_l3_b712_script_registration(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    try:s=json.loads(target.read_text(encoding='utf-8')).get('scripts')
    except Exception:s=[]
    req=('scripts/run_l_3_corrected_rerun_v8.py','scripts/validate_l_3_corrected_rerun_activation_v8.py','scripts/validate_l_3_corrected_rerun_report_v8.py');ok=isinstance(s,list) and all(s.count(x)==1 for x in req)
    return ([] if ok else [f"{order_id}:script_registration"],ok,False)


def _validate_l3_registry_mirror(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        registry = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l3_registry_invalid_json"], False, False
    hypotheses = registry.get("hypotheses") if isinstance(registry, dict) else None
    matching = [item for item in hypotheses or [] if isinstance(item, dict) and item.get("id") == "L-3"]
    if len(matching) != 1:
        return [f"{order_id}:l3_registry_entry_count:{len(matching)}"], False, False
    l3 = matching[0]
    blockers: list[str] = []
    if not _l3_historical_or_b73_terminal_state(l3, allowed_evidence=(
        [{"evidence_tier": "E0", "path": "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json"}],
        [{"evidence_tier": "E0", "path": "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json"}],
        [{"evidence_tier": "E0", "path": "experiments/l_3_falsification_activation_preflight_v1.json"}],
    )):
        blockers.append(f"{order_id}:l3_registry_status_or_edge_claim_mismatch")
    if l3.get("evidence") not in (
        [{"evidence_tier": "E0", "path": "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json"}],
        [{"evidence_tier": "E0", "path": "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json"}],
        [{"evidence_tier": "E0", "path": "experiments/l_3_falsification_activation_preflight_v1.json"}],
        [{"evidence_tier": "E1", "path": "reports/experiments/l_3_falsification_report.json"}],
    ):
        blockers.append(f"{order_id}:l3_registry_E0_evidence_mismatch")
    falsify = l3.get("mintrl_falsify")
    validate = l3.get("mintrl_validate")
    if not isinstance(falsify, dict) or falsify.get("required_weekly_paired_observations") != 49:
        blockers.append(f"{order_id}:l3_registry_falsify_mintrl_mismatch")
    if not isinstance(validate, dict) or validate.get("binding_required_weekly_paired_observations") != 49:
        blockers.append(f"{order_id}:l3_registry_validate_mintrl_mismatch")
    text = json.dumps(l3, ensure_ascii=False)
    required = (
        "research_signed",
        "q/volatility",
        "weekly paired portfolio HHI delta",
        "0.05",
        "t+1 through t+20",
        "366",
        "B7.1",
        "No market evidence was read.",
    )
    blockers.extend(f"{order_id}:l3_registry_missing:{item}" for item in required if item not in text)
    return blockers, not blockers, False


def _validate_l3_v2_registry_mirror(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        registry = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l3_v2_registry_invalid_json"], False, False
    hypotheses = registry.get("hypotheses") if isinstance(registry, dict) else None
    matching = [item for item in hypotheses or [] if isinstance(item, dict) and item.get("id") == "L-3"]
    if len(matching) != 1:
        return [f"{order_id}:l3_v2_registry_entry_count:{len(matching)}"], False, False
    l3 = matching[0]
    blockers: list[str] = []
    if not _l3_historical_or_b73_terminal_state(l3, allowed_evidence=(
        [{"evidence_tier": "E0", "path": "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json"}],
        [{"evidence_tier": "E0", "path": "experiments/l_3_falsification_activation_preflight_v1.json"}],
    )):
        blockers.append(f"{order_id}:l3_v2_registry_status_or_edge_claim_mismatch")
    if l3.get("evidence") not in (
        [{"evidence_tier": "E0", "path": "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json"}],
        [{"evidence_tier": "E0", "path": "experiments/l_3_falsification_activation_preflight_v1.json"}],
        [{"evidence_tier": "E1", "path": "reports/experiments/l_3_falsification_report.json"}],
    ):
        blockers.append(f"{order_id}:l3_v2_registry_active_evidence_mismatch")
    falsify = l3.get("mintrl_falsify")
    validate = l3.get("mintrl_validate")
    if not isinstance(falsify, dict) or falsify.get("required_weekly_paired_observations") != 49:
        blockers.append(f"{order_id}:l3_v2_registry_falsify_mintrl_mismatch")
    if not isinstance(validate, dict) or validate.get("binding_required_weekly_paired_observations") != 49:
        blockers.append(f"{order_id}:l3_v2_registry_validate_mintrl_mismatch")
    decision_log = l3.get("decision_log")
    if not isinstance(decision_log, list) or not any(entry.get("decision") == "B7_2_hermetic_source_provenance_remediated_E0" for entry in decision_log if isinstance(entry, dict)):
        blockers.append(f"{order_id}:l3_v2_registry_decision_log_missing")
    return blockers, not blockers, False


def _validate_l3_b71_registry_mirror(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        registry = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b71_registry_invalid_json"], False, False
    hypotheses = registry.get("hypotheses") if isinstance(registry, dict) else None
    matching = [item for item in hypotheses or [] if isinstance(item, dict) and item.get("id") == "L-3"]
    if len(matching) != 1:
        return [f"{order_id}:l3_b71_registry_entry_count:{len(matching)}"], False, False
    l3 = matching[0]
    blockers: list[str] = []
    if not _l3_historical_or_b73_terminal_state(l3, allowed_evidence=(
        [{"evidence_tier": "E0", "path": "experiments/l_3_falsification_activation_preflight_v1.json"}],
    )):
        blockers.append(f"{order_id}:l3_b71_registry_status_or_edge_claim_mismatch")
    if l3.get("evidence") not in (
        [{"evidence_tier": "E0", "path": "experiments/l_3_falsification_activation_preflight_v1.json"}],
        [{"evidence_tier": "E1", "path": "reports/experiments/l_3_falsification_report.json"}],
    ):
        blockers.append(f"{order_id}:l3_b71_registry_E0_evidence_mismatch")
    decision_log = l3.get("decision_log")
    if not isinstance(decision_log, list) or not any(
        entry.get("decision") == "B7_1_activation_preflight_gate_locked_E0" for entry in decision_log if isinstance(entry, dict)
    ):
        blockers.append(f"{order_id}:l3_b71_registry_decision_log_missing")
    text = json.dumps(l3, ensure_ascii=False)
    required = ("49", "465", "366", "validation sealed", "edge_claim none", "Inspector", "one-run", "No market evidence was read.")
    blockers.extend(f"{order_id}:l3_b71_registry_missing:{item}" for item in required if item not in text)
    return blockers, not blockers, False


def _validate_l3_human_registry_mirror(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(
        target,
        order_id,
        artifact_path,
        "l3_human_registry",
        ("E1 scope-restricted", "research_signed", "q / max(annualized_volatility, 0.05)", "comparator `q`", "MinTRL_falsify = 49", "MinTRL_validate = 49", "366", "B7.1 locked E0 gate-only preflight", "500 weekly observations", "no rerun"),
    )


def _validate_l3_v2_human_registry_mirror(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(
        target, order_id, artifact_path, "l3_v2_human_registry", ("B7.2", "v2", "hermetic source-provenance", "v1 research semantics remain unchanged", "B7.1 locked E0 gate-only preflight")
    )


def _validate_l3_b71_human_registry_mirror(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(
        target, order_id, artifact_path, "l3_b71_human_registry",
        ("B7.1 locked E0 gate-only preflight", "all six authorization flags false", "validation remains sealed", "Inspector review", "separate owner-authorized one-run execution order"),
    )


def _validate_l3_project_memory(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(
        target,
        order_id,
        artifact_path,
        "l3_project_memory",
        ("L-2 E1 underfunded_scope_restricted", "L-3 is E1 scope_restricted", "MinTRL_falsify` 49", "366-slot", "B7.1 locked E0 gate-only preflight", "500 weekly observations", "no rerun"),
    )


def _validate_l3_v2_project_memory(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(
        target, order_id, artifact_path, "l3_v2_project_memory", ("B7.2", "v2", "hermetic source-provenance", "B7.1 locked E0 gate-only preflight")
    )


def _validate_l3_b71_project_memory(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(
        target, order_id, artifact_path, "l3_b71_project_memory",
        ("B7.1 locked E0 gate-only preflight", "all six authorization flags false", "validation sealed", "B7.3", "no rerun"),
    )


def _validate_l3_implementation_plan(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(
        target,
        order_id,
        artifact_path,
        "l3_implementation_plan",
        ("B7 is complete as E0 governance only", "research_signed", "MinTRL_falsify` is 49", "MinTRL_validate` 49", "366 weekly slots", "B7.1 locked E0 gate-only preflight", "500 weekly observations", "no rerun"),
    )


def _validate_l3_v2_implementation_plan(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(
        target, order_id, artifact_path, "l3_v2_implementation_plan", ("B7.2", "v2", "hermetic source-provenance", "B7.1 locked E0 gate-only preflight")
    )


def _validate_l3_b71_implementation_plan(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    return _validate_l3_text_mirror(
        target, order_id, artifact_path, "l3_b71_implementation_plan",
        ("B7.1 locked E0 gate-only preflight", "all six authorization flags false", "validation sealed", "B7.3", "no rerun"),
    )


def _validate_l3_text_mirror(
    target: Path,
    order_id: str,
    artifact_path: str,
    label: str,
    required: tuple[str, ...],
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    blockers = [f"{order_id}:{label}_missing:{item}" for item in required if item not in text]
    return blockers, not blockers, False


def _validate_l3_b715_closure(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    if artifact_path == "experiments/hypothesis_registry.json":
        try:
            registry = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [f"{order_id}:l3_b715_registry_invalid_json"], False, False
        l3_entries = [
            item
            for item in registry.get("hypotheses", [])
            if isinstance(item, dict) and item.get("id") == "L-3"
        ]
        if len(l3_entries) != 1:
            return [f"{order_id}:l3_b715_registry_entry_count:{len(l3_entries)}"], False, False
        l3 = l3_entries[0]
        blockers: list[str] = []
        if l3.get("status") != "scope_restricted" or l3.get("edge_claim") != "none":
            blockers.append(f"{order_id}:l3_b715_registry_status_or_edge_claim_mismatch")
        closure_entries = [
            entry
            for entry in l3.get("decision_log", [])
            if isinstance(entry, dict)
            and entry.get("date") == "2026-07-28"
            and entry.get("decision") == "B7_15_current_preregistration_closure_synchronized"
        ]
        if len(closure_entries) != 1:
            blockers.append(f"{order_id}:l3_b715_registry_closure_entry_count:{len(closure_entries)}")
        else:
            notes = str(closure_entries[0].get("notes", ""))
            blockers.extend(
                f"{order_id}:l3_b715_registry_closure_missing:{term}"
                for term in L3_B715_CLOSURE_TERMS[1:]
                if term not in notes
            )
        return blockers, not blockers, False

    text = target.read_text(encoding="utf-8")
    blockers = [
        f"{order_id}:l3_b715_closure_missing:{term}"
        for term in L3_B715_CLOSURE_TERMS
        if term not in text
    ]
    if artifact_path == "PROJECT_BRAIN.md":
        required_next_action = "The next safe action, for a later order, is L-4 preregistration/planning only; B7.15 authorizes no L-4 work."
        if required_next_action not in text:
            blockers.append(f"{order_id}:l3_b715_project_brain_next_action_missing")
    if artifact_path == "IMPLEMENT_PLAN.md":
        required_next_gate = "Validation sealed; no rerun is planned; next gate is L-4 preregistration/planning only"
        if required_next_gate not in text:
            blockers.append(f"{order_id}:l3_b715_implementation_plan_next_gate_missing")
    return blockers, not blockers, False


def _validate_l4_b8_gate(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    completed = subprocess.run([sys.executable, "scripts/validate_l_4_breadth_preregistration_v1.py"], cwd=project_root, text=True, capture_output=True, check=False)
    ok = completed.returncode == 0
    return ([] if ok else [f"{order_id}:l4_b8_gate_validator_failed"], ok, False)


def _validate_l4_b8_snapshots(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_dir():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        gate = json.loads((project_root / "experiments/l_4_breadth_preregistration_v1.json").read_text(encoding="utf-8"))
        declared = gate["source_binding"]["methodology_snapshots"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return [f"{order_id}:l4_b8_snapshot_declaration_unreadable"], False, False
    expected = [
        {"wiki_relative_path": path, "snapshot_path": f"methodology_snapshots/l4_breadth_v1/{path}", "sha256": digest}
        for path, digest in (
            ("wiki/concepts/global-trend-regime-diversification.md", "6f1bf76c6730f1dfdde19809608f6533e7bf371830f58c132c3f47870ab4f0fb"),
            ("wiki/concepts/covariance-and-correlation.md", "27e28cb04ac1939acc6f4a1fc59e0a8208d365ee3e59872ffea9e4bb934c8828"),
            ("wiki/concepts/minimum-track-record-length.md", "ca65225740673bd363be7461b8022281da08ae32e6ff42f8887f1072eb51ad81"),
            ("wiki/concepts/newey-west-validation.md", "355b37f5f64d938d254337663b5df635ce008e47f8197eac041c03790643fcc5"),
            ("wiki/concepts/deflated-sharpe-ratio.md", "90663b67e49dcec90bd641e801f9464e593ff8fe9091b2d70e9f4645381af556"),
            ("wiki/concepts/backtest-validation-protocol.md", "c7f843310706d902120651e677429e66cbde9ce96ee526544de5419ee99aefa0"),
        )
    ]
    if declared != expected:
        return [f"{order_id}:l4_b8_snapshot_declaration_mismatch"], False, False
    bad = [item["wiki_relative_path"] for item in expected if not (project_root / item["snapshot_path"]).is_file() or hashlib.sha256((project_root / item["snapshot_path"]).read_bytes()).hexdigest() != item["sha256"]]
    return ([] if not bad else [f"{order_id}:l4_b8_snapshot_hash_mismatch:{path}" for path in bad], not bad, False)


def _validate_l4_b8_manifest_identity(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    try:
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
        gate = project_root / "experiments/l_4_breadth_preregistration_v1.json"
        validator = project_root / "scripts/validate_l_4_breadth_preregistration_v1.py"
    except (OSError, json.JSONDecodeError):
        return [f"{order_id}:l4_b8_manifest_unreadable"], False, False
    matches = [row for row in rows if row.get("gate_id") == "l_4_breadth_v1"]
    expected = {"gate_type": "E0_no_data_preregistration", "artifact_path": "experiments/l_4_breadth_preregistration_v1.json", "artifact_sha256": hashlib.sha256(gate.read_bytes()).hexdigest(), "validator_path": "scripts/validate_l_4_breadth_preregistration_v1.py", "validator_sha256": hashlib.sha256(validator.read_bytes()).hexdigest()}
    ok = len(matches) == 1 and all(matches[0].get(key) == value for key, value in expected.items()) and "L-4 planning only" in str(matches[0].get("human_approval", ""))
    return ([] if ok else [f"{order_id}:l4_b8_manifest_identity_mismatch"], ok, False)


def _validate_l4_b8_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    if artifact_path == "experiments/hypothesis_registry.json":
        try:
            l4 = next(item for item in json.loads(target.read_text(encoding="utf-8")).get("hypotheses", []) if item.get("id") == "L-4")
        except (StopIteration, json.JSONDecodeError, OSError):
            return [f"{order_id}:l4_b8_registry_unreadable"], False, False
        evidence = l4.get("evidence")
        ok = l4.get("status") == "active" and l4.get("edge_claim") == "none" and isinstance(evidence, list) and {item.get("path") for item in evidence if isinstance(item, dict)} >= {"experiments/l_4_breadth_preregistration_v1.json", "experiments/l_4_breadth_preregistration_v2.json"} and any(entry.get("decision") == "B8_breadth_preregistration_locked_E0" for entry in l4.get("decision_log", []) if isinstance(entry, dict))
        return ([] if ok else [f"{order_id}:l4_b8_registry_mirror_mismatch"], ok, False)
    text = target.read_text(encoding="utf-8")
    required = ("B8", "E0", "edge_claim none", "U1", "U4", "U8", "validation")
    missing = [item for item in required if item not in text]
    return ([f"{order_id}:l4_b8_mirror_missing:{item}" for item in missing], not missing, False)


def _validate_l4_b8_validator_registration(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    try:
        scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts", [])
    except (OSError, json.JSONDecodeError):
        return [f"{order_id}:l4_b8_script_registry_unreadable"], False, False
    ok = isinstance(scripts, list) and scripts.count("scripts/validate_l_4_breadth_preregistration_v1.py") == 1
    return ([] if ok else [f"{order_id}:l4_b8_script_registration_mismatch"], ok, False)


def _validate_l4_b81_gate(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    completed = subprocess.run([sys.executable, "scripts/validate_l_4_breadth_preregistration_v2.py"], cwd=project_root, text=True, capture_output=True, check=False)
    ok = completed.returncode == 0
    return ([] if ok else [f"{order_id}:l4_b81_gate_validator_failed"], ok, False)


def _validate_l4_b81_manifest_identity(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    try:
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
        gate = project_root / "experiments/l_4_breadth_preregistration_v2.json"
        validator = project_root / "scripts/validate_l_4_breadth_preregistration_v2.py"
    except (OSError, json.JSONDecodeError):
        return [f"{order_id}:l4_b81_manifest_unreadable"], False, False
    matches = [row for row in rows if row.get("gate_id") == "l_4_breadth_v2"]
    expected = {"supersedes_gate_id": "l_4_breadth_v1", "gate_type": "E0_no_data_scientific_contract_remediation", "artifact_path": "experiments/l_4_breadth_preregistration_v2.json", "artifact_sha256": hashlib.sha256(gate.read_bytes()).hexdigest(), "validator_path": "scripts/validate_l_4_breadth_preregistration_v2.py", "validator_sha256": hashlib.sha256(validator.read_bytes()).hexdigest()}
    ok = len(matches) == 1 and all(matches[0].get(key) == value for key, value in expected.items()) and "E0/no-data" in str(matches[0].get("human_approval", ""))
    return ([] if ok else [f"{order_id}:l4_b81_manifest_identity_mismatch"], ok, False)


def _validate_l4_b81_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    if artifact_path == "experiments/hypothesis_registry.json":
        try:
            l4 = next(item for item in json.loads(target.read_text(encoding="utf-8")).get("hypotheses", []) if item.get("id") == "L-4")
        except (StopIteration, json.JSONDecodeError, OSError):
            return [f"{order_id}:l4_b81_registry_unreadable"], False, False
        ok = l4.get("status") == "active" and l4.get("edge_claim") == "none" and any(entry.get("decision") == "B8_1_l4_breadth_v2_locked_E0" for entry in l4.get("decision_log", []) if isinstance(entry, dict))
        return ([] if ok else [f"{order_id}:l4_b81_registry_mirror_mismatch"], ok, False)
    text = target.read_text(encoding="utf-8")
    required = ("B8.1", "v2", "E0", "N_eff", "edge_claim none", "validation")
    missing = [item for item in required if item not in text]
    return ([f"{order_id}:l4_b81_mirror_missing:{item}" for item in missing], not missing, False)


def _validate_l4_b81_validator_registration(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    try:
        scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts", [])
    except (OSError, json.JSONDecodeError):
        return [f"{order_id}:l4_b81_script_registry_unreadable"], False, False
    ok = isinstance(scripts, list) and scripts.count("scripts/validate_l_4_breadth_preregistration_v2.py") == 1
    return ([] if ok else [f"{order_id}:l4_b81_script_registration_mismatch"], ok, False)


def _validate_l4_b83_gate(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    completed = subprocess.run([sys.executable, "scripts/validate_l_4_breadth_preregistration_v4.py", "--gate", str(target)], cwd=project_root, text=True, capture_output=True, check=False)
    ok = target.is_file() and completed.returncode == 0
    return ([] if ok else [f"{order_id}:l4_b83_gate_validator_failed"], ok, False)


def _validate_l4_b83_manifest_identity(target: Path, order_id: str, artifact_path: str, *, project_root: Path) -> tuple[list[str], bool, bool]:
    try:
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line]
        gate = project_root / "experiments/l_4_breadth_preregistration_v4.json"
        validator = project_root / "scripts/validate_l_4_breadth_preregistration_v4.py"
    except (OSError, json.JSONDecodeError):
        return [f"{order_id}:l4_b83_manifest_unreadable"], False, False
    matches = [row for row in rows if row.get("gate_id") == "l_4_breadth_v4"]
    expected = {"supersedes_gate_id": "l_4_breadth_v3", "gate_type": "E0_no_data_exact_preservation_remediation", "artifact_path": "experiments/l_4_breadth_preregistration_v4.json", "artifact_sha256": hashlib.sha256(gate.read_bytes()).hexdigest(), "validator_path": "scripts/validate_l_4_breadth_preregistration_v4.py", "validator_sha256": hashlib.sha256(validator.read_bytes()).hexdigest()}
    ok = len(matches) == 1 and all(matches[0].get(key) == value for key, value in expected.items()) and "B8.3 E0/no-data" in str(matches[0].get("human_approval", ""))
    return ([] if ok else [f"{order_id}:l4_b83_manifest_identity_mismatch"], ok, False)


def _validate_l4_b83_registry_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    try:
        entries = [item for item in json.loads(target.read_text(encoding="utf-8")).get("hypotheses", []) if isinstance(item, dict) and item.get("id") == "L-4"]
    except (OSError, json.JSONDecodeError):
        entries = []
    if len(entries) != 1:
        return [f"{order_id}:l4_b83_registry_entry_count:{len(entries)}"], False, False
    l4 = entries[0]
    decisions = [item for item in l4.get("decision_log", []) if isinstance(item, dict) and item.get("decision") == "B8_3_l4_breadth_v4_locked_E0"]
    notes = str(decisions[0].get("notes", "")) if len(decisions) == 1 else ""
    paths = {item.get("path") for item in l4.get("evidence", []) if isinstance(item, dict)}
    ok = l4.get("status") == "active" and l4.get("edge_claim") == "none" and "experiments/l_4_breadth_preregistration_v4.json" in paths and len(decisions) == 1 and all(term in notes for term in ("465", "macro sleeves", "Validation remains sealed", "every authorization is false", "Inspector review only"))
    return ([] if ok else [f"{order_id}:l4_b83_registry_mirror_mismatch"], ok, False)


def _validate_l4_b83_human_registry_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    return _validate_l4_b83_text(target, order_id, ("B8.3 v4", "465 weekly-paired", "macro sleeves", "four-outcome", "edge_claim none", "validation sealed", "all authorizations false", "Inspector review"), "human_registry")


def _validate_l4_b83_project_brain(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    return _validate_l4_b83_text(target, order_id, ("B8.3 v4", "465 weekly-paired", "macro sleeves", "four-outcome", "edge_claim none", "validation sealed", "all authorizations are false", "Inspector review of B8.3 only"), "project_brain")


def _validate_l4_b83_implement_plan(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    return _validate_l4_b83_text(target, order_id, ("B8.3 v4", "465 weekly-paired", "macro sleeves", "four-outcome", "edge_claim none", "validation is sealed", "all authorizations are false", "Inspector review only"), "implement_plan")


def _validate_l4_b83_text(target: Path, order_id: str, terms: tuple[str, ...], label: str) -> tuple[list[str], bool, bool]:
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return [f"{order_id}:l4_b83_{label}_unreadable"], False, False
    missing = [term for term in terms if term not in text]
    return ([f"{order_id}:l4_b83_{label}_missing:{term}" for term in missing], not missing, False)


def _validate_l4_b83_validator_registration(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    try:
        scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts", [])
    except (OSError, json.JSONDecodeError):
        return [f"{order_id}:l4_b83_script_registry_unreadable"], False, False
    ok = isinstance(scripts, list) and scripts.count("scripts/validate_l_4_breadth_preregistration_v4.py") == 1
    return ([] if ok else [f"{order_id}:l4_b83_script_registration_mismatch"], ok, False)


def _validate_l4_b84_runtime(target: Path, order_id: str, script: str, project_root: Path, *args: str) -> tuple[list[str], bool, bool]:
    run = subprocess.run([sys.executable, script, *args], cwd=project_root, text=True, capture_output=True, check=False)
    ok = target.is_file() and run.returncode == 0
    return ([] if ok else [f"{order_id}:l4_b84_runtime_failed:{Path(script).name}"], ok, False)


def _validate_l4_b84_historical_defect(target: Path, order_id: str, project_root: Path) -> tuple[list[str], bool, bool]:
    paths = ("experiments/l_4_breadth_b84_activation_contract_v1.json", "scripts/validate_l_4_breadth_b84_preflight_report_v1.py", "tests/fixtures/l4_b84/synthetic_preflight_report.json")
    try:
        ok = all((project_root / path).read_bytes() == subprocess.run(["git", "show", f"8fea0bf:{path}"], cwd=project_root, capture_output=True, check=True).stdout for path in paths)
        gate = (project_root / "experiments/l_4_breadth_b84r_activation_contract_v2.json").read_text(encoding="utf-8")
        ok = ok and "30363935144" in gate and "jsonschema" in gate
    except (OSError, subprocess.CalledProcessError):
        ok = False
    return ([] if ok else [f"{order_id}:l4_b84_historical_defect_audit_failed"], ok, False)


def _validate_l4_b84_manifest(target: Path, order_id: str, project_root: Path) -> tuple[list[str], bool, bool]:
    try:
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line]
        matches = [row for row in rows if row.get("gate_id") == "l_4_breadth_b84_activation_contract_v1"]
        gate = project_root / "experiments/l_4_breadth_b84_activation_contract_v1.json"
        validator = project_root / "scripts/validate_l_4_breadth_b84_activation_contract_v1.py"
        ok = len(matches) == 1 and matches[0].get("artifact_sha256") == hashlib.sha256(gate.read_bytes()).hexdigest() and matches[0].get("validator_sha256") == hashlib.sha256(validator.read_bytes()).hexdigest() and matches[0].get("activation_for_gate_id") == "l_4_breadth_v4"
    except (OSError, json.JSONDecodeError):
        ok = False
    return ([] if ok else [f"{order_id}:l4_b84_manifest_mismatch"], ok, False)



def _validate_l4_b84r_historical(target, order_id, project_root):
    paths=("experiments/l_4_breadth_b84r_activation_contract_v2.json","scripts/run_l_4_breadth_b84r_preflight_v2.py","schemas/l_4_breadth_b84r_preflight_report_v2.schema.json")
    try:
        ok=all((project_root/p).read_bytes()==subprocess.run(["git","show",f"49d07ce:{p}"],cwd=project_root,capture_output=True,check=True).stdout for p in paths)
    except Exception: ok=False
    return ([] if ok else [f"{order_id}:l4_b84r_historical_audit_failed"],ok,False)

def _validate_l4_b84r_manifest(target: Path, order_id: str, project_root: Path) -> tuple[list[str], bool, bool]:
    try:
        rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line]
        row = next(item for item in rows if item.get("gate_id") == "l_4_breadth_b84r_activation_contract_v2")
        gate = project_root / "experiments/l_4_breadth_b84r_activation_contract_v2.json"
        validator = project_root / "scripts/validate_l_4_breadth_b84r_activation_contract_v2.py"
        ok = row.get("supersedes_gate_id") == "l_4_breadth_b84_activation_contract_v1" and row.get("artifact_sha256") == hashlib.sha256(gate.read_bytes()).hexdigest() and row.get("validator_sha256") == hashlib.sha256(validator.read_bytes()).hexdigest()
    except (OSError, StopIteration, json.JSONDecodeError):
        ok = False
    return ([] if ok else [f"{order_id}:l4_b84r_manifest_mismatch"], ok, False)


def _validate_l4_b84_mirror(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return [f"{order_id}:l4_b84_mirror_unreadable"], False, False
    terms = ("B8.4", "E0", "synthetic", "validation sealed", "B8.5", "Inspector")
    if artifact_path == "experiments/hypothesis_registry.json":
        try:
            l4 = next(item for item in json.loads(text).get("hypotheses", []) if item.get("id") == "L-4")
            ok = l4.get("edge_claim") == "none" and any(item.get("decision") == "B8_4_l4_synthetic_preflight_locked_E0" for item in l4.get("decision_log", []) if isinstance(item, dict))
        except (StopIteration, json.JSONDecodeError):
            ok = False
        return ([] if ok else [f"{order_id}:l4_b84_registry_mismatch"], ok, False)
    missing = [term for term in terms if term not in text]
    return ([f"{order_id}:l4_b84_mirror_missing:{term}" for term in missing], not missing, False)


def _validate_l4_b84_scripts(target: Path, order_id: str) -> tuple[list[str], bool, bool]:
    try:
        scripts = json.loads(target.read_text(encoding="utf-8")).get("scripts", [])
    except (OSError, json.JSONDecodeError):
        scripts = []
    required = ("scripts/validate_l_4_breadth_b84_activation_contract_v1.py", "scripts/validate_l_4_breadth_b84_preflight_report_v1.py", "scripts/run_l_4_breadth_b84_preflight_v1.py")
    ok = all(scripts.count(item) == 1 for item in required)
    return ([] if ok else [f"{order_id}:l4_b84_script_registration_mismatch"], ok, False)


def _validate_l3_validator_registration(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l3_script_registry_invalid_json"], False, False
    scripts = payload.get("scripts") if isinstance(payload, dict) else None
    registered = "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py"
    if not isinstance(scripts, list) or scripts.count(registered) != 1:
        return [f"{order_id}:l3_validator_registration_mismatch"], False, False
    return [], True, False


def _validate_l3_v2_validator_registration(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l3_v2_script_registry_invalid_json"], False, False
    scripts = payload.get("scripts") if isinstance(payload, dict) else None
    registered = "scripts/validate_l_3_inverse_volatility_sizing_preregistration_v2.py"
    if not isinstance(scripts, list) or scripts.count(registered) != 1:
        return [f"{order_id}:l3_v2_validator_registration_mismatch"], False, False
    return [], True, False


def _validate_l3_b71_validator_registration(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{order_id}:l3_b71_script_registry_invalid_json"], False, False
    scripts = payload.get("scripts") if isinstance(payload, dict) else None
    registered = "scripts/validate_l_3_falsification_activation_preflight_v1.py"
    if not isinstance(scripts, list) or scripts.count(registered) != 1:
        return [f"{order_id}:l3_b71_validator_registration_mismatch"], False, False
    return [], True, False


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


def _reviewed_noncredential_structural_byte_local(project_root: Path) -> dict[str, str] | None:
    """Allow exactly the reviewed immutable-v1 byte-token local while v2 supersedes it."""
    exception_path = project_root / V1_STRUCTURAL_BYTE_EXCEPTION
    source_path = project_root / V1_STRUCTURAL_BYTE_SOURCE
    manifest_path = project_root / "experiments" / "locked_gates.jsonl"
    try:
        exception = json.loads(exception_path.read_text(encoding="utf-8"))
        source_bytes = source_path.read_bytes()
        source = source_bytes.decode("utf-8")
        gates = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line]
        tree = ast.parse(source)
    except (OSError, json.JSONDecodeError, SyntaxError):
        return None
    expected = {
        "schema_version": "lily_reviewed_noncredential_structural_byte_local_exception_v1",
        "classification": "noncredential_structural_byte_local",
        "reviewer": "Lily Inspector procedural-boundary remediation",
        "path": V1_STRUCTURAL_BYTE_SOURCE,
        "sha256": "aa6eb9c0e9984bc70677c27a1d736d2cb348cb367fa3fa169b5db2533aa6bcf6",
        "identifier": "token",
        "rhs_ast": "self.raw[self.pos]",
        "occurrence_count": 1,
        "active_supersession_gate_id": V1_STRUCTURAL_BYTE_SUPERSESSION,
    }
    if set(exception) != set(expected) or any(exception.get(key) != value for key, value in expected.items()):
        return None
    if hashlib.sha256(source_bytes).hexdigest() != expected["sha256"]:
        return None
    superseding_rows = [
        row for row in gates
        if row.get("gate_id") == V1_STRUCTURAL_BYTE_SUPERSESSION
        and row.get("supersedes_gate_id") == "l_3_b714_date_only_preflight_activation_v1"
    ]
    if len(superseding_rows) != 1:
        return None
    assignments = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "token"
    ]
    if len(assignments) != 1:
        return None
    value = assignments[0].value
    if not (
        isinstance(value, ast.Subscript)
        and isinstance(value.value, ast.Attribute)
        and value.value.attr == "raw"
        and isinstance(value.value.value, ast.Name)
        and value.value.value.id == "self"
        and isinstance(value.slice, ast.Attribute)
        and value.slice.attr == "pos"
        and isinstance(value.slice.value, ast.Name)
        and value.slice.value.id == "self"
    ):
        return None
    return {key: str(exception[key]) for key in ("classification", "reviewer", "path", "identifier", "occurrence_count")}


def _scan_active_artifacts(
    project_root: Path, *, include_reviewed: bool = False
) -> list[str] | tuple[list[str], list[dict[str, str]]]:
    blockers: list[str] = []
    reviewed: list[dict[str, str]] = []
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
                reviewed_exception = _reviewed_noncredential_structural_byte_local(project_root)
                if (
                    relative == V1_STRUCTURAL_BYTE_SOURCE
                    and match.group(1) == "token"
                    and reviewed_exception is not None
                ):
                    reviewed.append(reviewed_exception)
                    continue
                blockers.append(f"credential_like_assignment:{relative}:{match.group(1)}")
                break
    result = sorted(set(blockers))
    if include_reviewed:
        return result, reviewed
    return result


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
    reviewed_credential_false_positive_exceptions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "tracker_path": str(path),
        "blockers": blockers,
        "done_artifacts_checked": checked,
        "unverified": unverified,
        "reviewed_credential_false_positive_exceptions": reviewed_credential_false_positive_exceptions or [],
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



def _validate_l4_b84r2_manifest(target, order_id, project_root):
    try:
        row=next(json.loads(x) for x in target.read_text(encoding="utf-8").splitlines() if "l_4_breadth_b84r2_activation_contract_v3" in x); gate=project_root/"experiments/l_4_breadth_b84r2_activation_contract_v3.json"; validator=project_root/"scripts/validate_l_4_breadth_b84r2_activation_contract_v3.py"; ok=row.get("supersedes_gate_id")=="l_4_breadth_b84r_activation_contract_v2" and row.get("artifact_sha256")==hashlib.sha256(gate.read_bytes()).hexdigest() and row.get("validator_sha256")==hashlib.sha256(validator.read_bytes()).hexdigest()
    except Exception: ok=False
    return ([] if ok else [f"{order_id}:l4_b84r2_manifest_mismatch"],ok,False)


def _validate_l4_b85_phase_a_manifest(target, order_id, project_root):
    try:
        rows=[json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line]
        matches=[row for row in rows if row.get("gate_id")=="l_4_breadth_b85_phase_a_activation_order_v1"]
        gate=project_root/"experiments/l_4_breadth_b85_phase_a_activation_order_v1.json"
        validator=project_root/"scripts/validate_l_4_breadth_b85_phase_a_activation_order_v1.py"
        ok=len(matches)==1 and matches[0].get("activation_for_gate_id")=="l_4_breadth_b84r2_activation_contract_v3" and matches[0].get("artifact_sha256")==hashlib.sha256(gate.read_bytes()).hexdigest() and matches[0].get("validator_sha256")==hashlib.sha256(validator.read_bytes()).hexdigest() and "Phase B is not executed" in matches[0].get("notes","")
    except Exception: ok=False
    return ([] if ok else [f"{order_id}:l4_b85_phase_a_manifest_mismatch"],ok,False)


def _validate_l4_b85r_manifest(target, order_id, project_root):
    try:
        row=next(json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if 'l_4_breadth_b85_phase_a_activation_order_v2' in line)
        gate=project_root/"experiments/l_4_breadth_b85_phase_a_activation_order_v2.json"; validator=project_root/"scripts/validate_l_4_breadth_b85_phase_a_activation_order_v2.py"
        notes=row.get("notes","")
        ok=row.get("supersedes_gate_id")=="l_4_breadth_b85_phase_a_activation_order_v1" and row.get("artifact_sha256")==hashlib.sha256(gate.read_bytes()).hexdigest() and row.get("validator_sha256")==hashlib.sha256(validator.read_bytes()).hexdigest() and "Phase B" in notes and "not executed" in notes
    except Exception: ok=False
    return ([] if ok else [f"{order_id}:l4_b85r_manifest_mismatch"],ok,False)


def _validate_l4_b85r2_manifest(target, order_id, project_root):
    try:
        row=next(json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if 'l_4_breadth_b85r2_phase_a_activation_order_v3' in line)
        gate=project_root/"experiments/l_4_breadth_b85r2_phase_a_activation_order_v3.json"; validator=project_root/"scripts/validate_l_4_breadth_b85r2_phase_a_activation_order_v3.py"
        notes=row.get("notes","")
        ok=row.get("supersedes_gate_id")=="l_4_breadth_b85_phase_a_activation_order_v2" and row.get("artifact_sha256")==hashlib.sha256(gate.read_bytes()).hexdigest() and row.get("validator_sha256")==hashlib.sha256(validator.read_bytes()).hexdigest() and "v2" in notes and "not executed" in notes
    except Exception: ok=False
    return ([] if ok else [f"{order_id}:l4_b85r2_manifest_mismatch"],ok,False)


def _validate_l4_b85r3_manifest(target, order_id, project_root):
    try:
        row=next(json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if 'l_4_breadth_b85r3_phase_a_activation_order_v4' in line)
        gate=project_root/"experiments/l_4_breadth_b85r3_phase_a_activation_order_v4.json"; validator=project_root/"scripts/validate_l_4_breadth_b85r3_phase_a_activation_order_v4.py"
        ok=row.get("supersedes_gate_id")=="l_4_breadth_b85r2_phase_a_activation_order_v3" and row.get("artifact_sha256")==hashlib.sha256(gate.read_bytes()).hexdigest() and row.get("validator_sha256")==hashlib.sha256(validator.read_bytes()).hexdigest() and "v3" in row.get("notes","") and "not executed" in row.get("notes","")
    except Exception: ok=False
    return ([] if ok else [f"{order_id}:l4_b85r3_manifest_mismatch"],ok,False)


def _validate_l4_b85r4_manifest(target, order_id, project_root):
    try:
        row=next(json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if 'l_4_breadth_b85r4_phase_a_activation_order_v5' in line)
        gate=project_root/"experiments/l_4_breadth_b85r4_phase_a_activation_order_v5.json"; validator=project_root/"scripts/validate_l_4_breadth_b85r4_phase_a_activation_order_v5.py"
        ok=row.get("supersedes_gate_id")=="l_4_breadth_b85r3_phase_a_activation_order_v4" and row.get("artifact_sha256")==hashlib.sha256(gate.read_bytes()).hexdigest() and row.get("validator_sha256")==hashlib.sha256(validator.read_bytes()).hexdigest() and "v4" in row.get("notes","") and "not executed" in row.get("notes","")
    except Exception: ok=False
    return ([] if ok else [f"{order_id}:l4_b85r4_manifest_mismatch"],ok,False)


def _validate_l4_b85r5_manifest(target, order_id, project_root):
    try:
        row=next(json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if 'l_4_breadth_b85r5_phase_a_activation_order_v6' in line)
        gate=project_root/"experiments/l_4_breadth_b85r5_phase_a_activation_order_v6.json"; validator=project_root/"scripts/validate_l_4_breadth_b85r5_phase_a_activation_order_v6.py"
        ok=row.get("supersedes_gate_id")=="l_4_breadth_b85r4_phase_a_activation_order_v5" and row.get("artifact_sha256")==hashlib.sha256(gate.read_bytes()).hexdigest() and row.get("validator_sha256")==hashlib.sha256(validator.read_bytes()).hexdigest() and "v5" in row.get("notes","") and "not executed" in row.get("notes","")
    except Exception: ok=False
    return ([] if ok else [f"{order_id}:l4_b85r5_manifest_mismatch"],ok,False)

if __name__ == "__main__":
    raise SystemExit(main())
