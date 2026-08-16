from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.provenance import file_sha256


DEFAULT_CONTRACT = PROJECT_ROOT / "experiments" / "l_4_breadth_b89_execution_contract_v1.json"
EXPECTED_SCHEMA = "lily_l4_b89d_replacement_execution_contract_v1"
EXPECTED_GATE_ID = "l_4_breadth_b89_execution_contract_v1"
EXPECTED_PREDECESSOR = "l_4_breadth_b88r5_phase_a_execution_contract_v6_hash_correction"
EXPECTED_CLOSURE_COMMIT = "086c445e6ef711d1d553a121c2c80577afa86f99"
LEGACY_MARKER_NAME = "l_4_breadth_" + "b88r5_one_shot_marker_v6.json"
LEGACY_ACTIVATION_NAME = "l_4_breadth_" + "b88r5_scientific_execution_activation_v6.json"
HEX64 = set("0123456789abcdef")
HEX40 = set("0123456789abcdef")

SCIENCE_FIELDS = (
    "research_question",
    "universes",
    "primary_sizing",
    "macro_sleeves",
    "static_capacity",
    "inherited_controls",
    "component_risk",
    "mandatory_metrics",
    "statistics",
    "robustness_and_side_effects",
    "regime_matrix",
    "decision_contract",
    "timing_and_seal",
    "hard_stops",
)

AUTHORIZATION_KEYS = (
    "data",
    "container",
    "market",
    "return",
    "signal",
    "position",
    "covariance",
    "regime",
    "cost",
    "pnl",
    "validation",
    "provider",
    "network",
    "credentials",
    "broker",
    "paid",
    "paper_trade",
    "real_money",
    "activation",
    "execution",
    "report",
    "research_decision",
    "ledger",
)


def _sha256(path: Path) -> str:
    return file_sha256(path)


def _safe_relative(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _binding_records(value: Any, prefix: str = "") -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and "sha256" in value:
            yield prefix or "binding", value
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            yield from _binding_records(child, child_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _binding_records(child, f"{prefix}[{index}]")


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=False
    )


def _json_equal(left: Any, right: Any) -> bool:
    return left == right


def _source_value(contract: dict[str, Any], section: str, name: str) -> tuple[str, str] | None:
    value = contract.get("source_binding", {}).get(section, {}).get(name)
    if not isinstance(value, dict):
        return None
    path = value.get("path")
    digest = value.get("sha256")
    if not isinstance(path, str) or not isinstance(digest, str):
        return None
    return path, digest


def _block(blockers: list[str], condition: bool, message: str) -> None:
    if condition:
        blockers.append(message)


def _validate_header(contract: dict[str, Any], blockers: list[str]) -> None:
    expected_keys = {
        "schema_version",
        "order_id",
        "gate_id",
        "supersedes_gate_id",
        "hypothesis_id",
        "status",
        "evidence_ceiling",
        "edge_claim",
        "owner_authorization",
        "source_binding",
        "closure_provenance",
        "preserved_science",
        "future_namespace",
        "future_lifecycle",
        "future_tracker_semantics",
        "future_cp_a_requirements",
        "future_report_requirements",
        "validation_seal",
        "authorizations",
        "access_counts",
        "hard_stops",
    }
    _block(blockers, set(contract) != expected_keys, "contract_top_level_is_not_closed_world")
    expected = {
        "schema_version": EXPECTED_SCHEMA,
        "order_id": "B8.9-D",
        "gate_id": EXPECTED_GATE_ID,
        "supersedes_gate_id": EXPECTED_PREDECESSOR,
        "hypothesis_id": "L-4",
        "status": "locked_E0_static_design_only",
        "evidence_ceiling": "E0",
        "edge_claim": "none",
    }
    for key, value in expected.items():
        _block(blockers, contract.get(key) != value, f"header_mismatch:{key}")
    _block(
        blockers,
        not isinstance(contract.get("owner_authorization"), str)
        or "B8.9-M" not in contract["owner_authorization"]
        or "B8.9A" not in contract["owner_authorization"],
        "owner_authorization_scope_missing",
    )


def _validate_no_legacy_binding(contract: dict[str, Any], blockers: list[str]) -> None:
    serialized = json.dumps(contract, ensure_ascii=False, sort_keys=True)
    _block(blockers, LEGACY_MARKER_NAME in serialized, "legacy_consumed_marker_bound")
    _block(blockers, LEGACY_ACTIVATION_NAME in serialized, "legacy_consumed_activation_bound")
    _block(
        blockers,
        any(
            isinstance(item.get("path"), str)
            and (LEGACY_MARKER_NAME in item["path"] or LEGACY_ACTIVATION_NAME in item["path"])
            for _, item in _binding_records(contract.get("source_binding"))
        ),
        "legacy_consumed_path_in_source_binding",
    )


def _validate_source_hashes(
    contract: dict[str, Any], project_root: Path, blockers: list[str]
) -> None:
    bindings = list(_binding_records(contract.get("source_binding")))
    _block(blockers, not bindings, "source_binding_empty")
    seen: set[str] = set()
    for label, item in bindings:
        path_value = item.get("path")
        digest = item.get("sha256")
        if not _safe_relative(path_value):
            blockers.append(f"{label}:unsafe_path")
            continue
        if path_value in seen:
            blockers.append(f"{label}:duplicate_path")
        seen.add(path_value)
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in HEX64 for char in digest):
            blockers.append(f"{label}:invalid_sha256")
            continue
        path = project_root / path_value
        if not path.is_file():
            blockers.append(f"{label}:missing_source:{path_value}")
            continue
        if _sha256(path) != digest:
            blockers.append(f"{label}:source_hash_mismatch:{path_value}")


def _validate_science_projection(
    contract: dict[str, Any], project_root: Path, blockers: list[str]
) -> None:
    binding = _source_value(contract, "accepted_science", "preregistration")
    if binding is None:
        blockers.append("accepted_science_preregistration_binding_missing")
        return
    path = project_root / binding[0]
    try:
        source = _load_json(path)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        blockers.append(f"accepted_science_unreadable:{type(exc).__name__}")
        return
    preserved = contract.get("preserved_science")
    if not isinstance(preserved, dict):
        blockers.append("preserved_science_missing")
        return
    for field in SCIENCE_FIELDS:
        if field not in source or preserved.get(field) != source[field]:
            blockers.append(f"science_semantics_drift:{field}")
    if preserved.get("universes", {}).get("U4") != ["VTI", "IEF", "GLD", "DBC"]:
        blockers.append("u4_universe_mismatch")
    if preserved.get("universes", {}).get("U8") != ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]:
        blockers.append("u8_universe_mismatch")
    if preserved.get("static_capacity", {}).get("maximum_weekly_slots_before_warmup_missingness_or_evaluable_pair_reductions") != 465:
        blockers.append("static_capacity_mismatch")
    metrics = preserved.get("mandatory_metrics", {})
    if set(metrics) != {"ex_ante_hhi_delta", "realized_hhi_delta", "top_dependency_delta", "n_eff_delta"}:
        blockers.append("mandatory_metric_set_mismatch")
    for metric, details in metrics.items():
        if details.get("falsify", {}).get("expected_mintrl") != 49:
            blockers.append(f"planning_mintrl_mismatch:{metric}")
    _block(
        blockers,
        preserved.get("statistics", {}).get("actual_recalculation", "").find("each metric and each plan separately") < 0,
        "actual_paired_mintrl_recalculation_not_preserved",
    )
    _block(
        blockers,
        preserved.get("decision_contract", {}).get("precedence", "").startswith("scope restriction first") is not True,
        "four_outcome_precedence_not_preserved",
    )


def _validate_capacity_and_structure(
    contract: dict[str, Any], project_root: Path, blockers: list[str]
) -> None:
    capacity_gate_binding = _source_value(contract, "capacity", "gate")
    capacity_report_binding = _source_value(contract, "capacity", "report")
    manifest_binding = _source_value(contract, "structural_predecessor", "structural_manifest")
    dates_binding = _source_value(contract, "structural_predecessor", "u8_session_dates")
    if not all((capacity_gate_binding, capacity_report_binding, manifest_binding, dates_binding)):
        blockers.append("capacity_or_structural_binding_missing")
        return
    try:
        capacity_gate = _load_json(project_root / capacity_gate_binding[0])
        capacity_report = _load_json(project_root / capacity_report_binding[0])
        manifest = _load_json(project_root / manifest_binding[0])
        dates = _load_json(project_root / dates_binding[0])
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        blockers.append(f"capacity_or_structural_source_unreadable:{type(exc).__name__}")
        return
    _block(blockers, capacity_gate.get("hypothesis_id") != "L-4", "capacity_gate_hypothesis_mismatch")
    _block(blockers, capacity_gate.get("evidence_ceiling") != "E0", "capacity_gate_evidence_ceiling_mismatch")
    _block(blockers, capacity_gate.get("edge_claim") != "none", "capacity_gate_edge_claim_mismatch")
    _block(blockers, capacity_gate.get("capacity", {}).get("weekly_paired_capacity") != 465, "capacity_gate_weekly_slots_mismatch")
    _block(blockers, capacity_report.get("capacity", {}).get("weekly_paired_capacity") != 465, "capacity_report_weekly_slots_mismatch")
    planned = capacity_report.get("capacity", {}).get("planning_mintrl_falsify_by_metric", {})
    _block(blockers, set(planned) != {"ex_ante_hhi_delta", "realized_hhi_delta", "top_dependency_delta", "n_eff_delta"}, "capacity_report_metric_set_mismatch")
    _block(blockers, any(value != 49 for value in planned.values()), "capacity_report_mintrl_mismatch")
    _block(blockers, capacity_report.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}, "capacity_report_validation_open")
    expected_u8 = ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]
    _block(blockers, manifest.get("u8_members_in_order") != expected_u8, "structural_manifest_u8_mismatch")
    _block(blockers, dates.get("u8_members_in_order") != expected_u8, "structural_dates_u8_mismatch")
    _block(blockers, manifest.get("max_session_date") != "2015-12-31", "structural_manifest_cutoff_mismatch")
    _block(blockers, dates.get("dataset_sha256") != manifest.get("dataset_sha256"), "structural_dataset_identity_mismatch")
    _block(blockers, manifest.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}, "structural_manifest_validation_open")


def _validate_incident_source(
    contract: dict[str, Any], project_root: Path, blockers: list[str]
) -> None:
    binding = _source_value(contract, "incident", "report")
    if binding is None:
        blockers.append("incident_report_binding_missing")
        return
    try:
        incident = _load_json(project_root / binding[0])
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        blockers.append(f"incident_report_unreadable:{type(exc).__name__}")
        return
    _block(blockers, incident.get("order_id") != "B8.8R5AR-X", "incident_order_mismatch")
    _block(blockers, incident.get("evidence_tier") != "E0", "incident_evidence_tier_mismatch")
    _block(blockers, incident.get("edge_claim") != "none", "incident_edge_claim_mismatch")
    _block(blockers, incident.get("scientific_outcome") != "none", "incident_scientific_outcome_mismatch")
    _block(blockers, incident.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}, "incident_validation_open")
    lifecycle = incident.get("lifecycle", {})
    _block(blockers, lifecycle.get("retry_allowed") is not False, "incident_retry_rule_missing")
    _block(blockers, lifecycle.get("new_owner_approved_gate_required") is not True, "incident_new_gate_requirement_missing")
    _block(blockers, lifecycle.get("new_namespace_required") is not True, "incident_new_namespace_requirement_missing")
    bounds = incident.get("access_bounds", {}).get("container_return_access", {})
    _block(blockers, bounds != {"classification": "unknown_not_durably_proven", "lower_bound": 0, "upper_bound": 1}, "incident_access_bounds_changed")
    _block(blockers, incident.get("operational_access_counts") != {"provider": 0, "network": 0, "credentials": 0, "broker": 0, "paid": 0, "paper_trade": 0, "real_money": 0}, "incident_operational_access_changed")


def _validate_closure_provenance(
    contract: dict[str, Any], project_root: Path, blockers: list[str]
) -> None:
    closure = contract.get("closure_provenance")
    if not isinstance(closure, dict) or closure.get("closure_commit") != EXPECTED_CLOSURE_COMMIT:
        blockers.append("closure_commit_mismatch")
        return
    commit = str(closure["closure_commit"])
    exists = _git("cat-file", "-e", f"{commit}^{{commit}}", cwd=project_root)
    _block(blockers, exists.returncode != 0, "closure_commit_missing")
    ancestor = _git("merge-base", "--is-ancestor", commit, "HEAD", cwd=project_root)
    _block(blockers, ancestor.returncode != 0, "closure_commit_not_ancestor")
    files = closure.get("provenance_files")
    if not isinstance(files, list) or not files:
        blockers.append("closure_provenance_files_missing")
        return
    for item in files:
        if not isinstance(item, dict) or not _safe_relative(item.get("path")):
            blockers.append("closure_provenance_path_invalid")
            continue
        path = str(item["path"])
        expected_blob = item.get("git_blob_sha1")
        if not isinstance(expected_blob, str) or len(expected_blob) != 40 or any(char not in HEX40 for char in expected_blob):
            blockers.append(f"closure_blob_invalid:{path}")
            continue
        actual = _git("rev-parse", f"{commit}:{path}", cwd=project_root)
        if actual.returncode != 0 or actual.stdout.strip() != expected_blob:
            blockers.append(f"closure_blob_mismatch:{path}")


def _validate_future_namespace(
    contract: dict[str, Any], project_root: Path, blockers: list[str]
) -> None:
    namespace = contract.get("future_namespace")
    if not isinstance(namespace, dict) or namespace.get("namespace_id") != "b89":
        blockers.append("future_namespace_identity_mismatch")
        return
    paths = [namespace.get(name) for name in ("activation_path", "marker_path", "report_path", "ledger_path", "attempt_path")]
    if any(not _safe_relative(path) for path in paths):
        blockers.append("future_namespace_path_invalid")
    if len(set(paths)) != len(paths):
        blockers.append("future_namespace_paths_not_unique")
    for path in paths:
        if isinstance(path, str):
            if "b89" not in path or "b88r5" in path or (project_root / path).exists():
                blockers.append(f"future_namespace_path_not_new:{path}")
    _block(blockers, namespace.get("paths_are_new_and_absent") is not True, "future_namespace_absence_not_locked")
    _block(blockers, namespace.get("legacy_namespace_reuse_forbidden") is not True, "legacy_namespace_reuse_not_forbidden")


def _validate_future_controls(contract: dict[str, Any], blockers: list[str]) -> None:
    lifecycle = contract.get("future_lifecycle", {})
    expected_stages = ["B8.9-D", "CP-A design review", "B8.9-M", "CP-A machinery review", "owner-approved B8.9A"]
    _block(blockers, lifecycle.get("stages") != expected_stages, "future_stage_sequence_mismatch")
    for key in ("implementation_authorized", "activation_authorized", "execution_authorized"):
        _block(blockers, lifecycle.get(key) is not False, f"future_{key}_must_be_false")
    _block(blockers, lifecycle.get("current_stage") != "B8.9-D", "future_current_stage_mismatch")
    tracker = contract.get("future_tracker_semantics", {})
    _block(blockers, tracker.get("required_existence_check") != "existence_only", "future_tracker_not_existence_only")
    _block(blockers, tracker.get("denial_proof") != "pure_preflight_result", "future_denial_proof_mismatch")
    _block(blockers, "invoke_activation_capable_runner" not in tracker.get("forbidden_denial_proof", ""), "future_activation_runner_denial_not_forbidden")
    _block(blockers, tracker.get("preflight_must_be_pure") is not True, "future_preflight_not_pure")
    _block(blockers, tracker.get("fail_closed_on_preflight_or_provenance_error") is not True, "future_preflight_not_fail_closed")
    cp_a = contract.get("future_cp_a_requirements", {})
    for key in ("pure_preflight_path_required", "poison_test_required", "clean_temporary_git_synthetic_lifecycle_proof_required", "all_required_before_machinery_review", "no_b89m_or_b89a_under_this_gate"):
        _block(blockers, cp_a.get(key) is not True, f"future_cp_a_requirement_missing:{key}")
    report = contract.get("future_report_requirements", {})
    required_true = ("closed_world", "producing_git_commit", "actual_paired_mintrl_recalculation", "u4_u8_matching", "n_eff", "hhi", "regimes", "robustness", "costs_and_turnover", "side_effects", "four_outcome_precedence")
    for key in required_true:
        _block(blockers, report.get(key) is not True, f"future_report_requirement_missing:{key}")
    _block(blockers, report.get("mechanism_autopsy") != "required_for_falsified_outcome", "future_mechanism_autopsy_requirement_missing")


def _validate_seals_and_access(contract: dict[str, Any], blockers: list[str]) -> None:
    _block(blockers, contract.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}, "contract_validation_open")
    authorizations = contract.get("authorizations")
    if not isinstance(authorizations, dict) or set(authorizations) != set(AUTHORIZATION_KEYS):
        blockers.append("authorization_set_mismatch")
    else:
        for key in AUTHORIZATION_KEYS:
            _block(blockers, authorizations[key] is not False, f"authorization_not_false:{key}")
    counts = contract.get("access_counts")
    if not isinstance(counts, dict) or set(counts) != set(AUTHORIZATION_KEYS):
        blockers.append("access_count_set_mismatch")
    else:
        for key in AUTHORIZATION_KEYS:
            _block(blockers, counts[key] != 0, f"access_count_not_zero:{key}")


def _validate_manifest(contract: dict[str, Any], project_root: Path, blockers: list[str]) -> None:
    manifest_path = project_root / "experiments" / "locked_gates_v2.jsonl"
    try:
        rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        blockers.append(f"manifest_unreadable:{type(exc).__name__}")
        return
    matches = [row for row in rows if isinstance(row, dict) and row.get("gate_id") == EXPECTED_GATE_ID]
    _block(blockers, len(matches) != 1, "b89d_manifest_row_count_mismatch")
    if len(matches) != 1:
        return
    row = matches[0]
    artifact_path = "experiments/l_4_breadth_b89_execution_contract_v1.json"
    validator_path = "scripts/validate_l_4_breadth_b89_execution_contract_v1.py"
    _block(blockers, row.get("supersedes_gate_id") != EXPECTED_PREDECESSOR, "b89d_manifest_predecessor_mismatch")
    _block(blockers, row.get("artifact_path") != artifact_path, "b89d_manifest_artifact_path_mismatch")
    _block(blockers, row.get("validator_path") != validator_path, "b89d_manifest_validator_path_mismatch")
    _block(blockers, row.get("artifact_sha256") != _sha256(project_root / artifact_path), "b89d_manifest_artifact_hash_mismatch")
    _block(blockers, row.get("validator_sha256") != _sha256(project_root / validator_path), "b89d_manifest_validator_hash_mismatch")
    _block(blockers, not isinstance(row.get("human_approval"), str) or not row["human_approval"].strip(), "b89d_manifest_human_approval_missing")
    _block(blockers, not isinstance(row.get("reviewed_by"), str) or not row["reviewed_by"].strip(), "b89d_manifest_reviewer_missing")


def validate(
    contract_path: Path = DEFAULT_CONTRACT, *, project_root: Path = PROJECT_ROOT
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        contract = _load_json(Path(contract_path))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        return {"status": "blocked", "blockers": [f"contract_unreadable:{type(exc).__name__}"]}
    if not isinstance(contract, dict):
        return {"status": "blocked", "blockers": ["contract_must_be_object"]}
    _validate_header(contract, blockers)
    _validate_no_legacy_binding(contract, blockers)
    _validate_source_hashes(contract, project_root, blockers)
    _validate_science_projection(contract, project_root, blockers)
    _validate_capacity_and_structure(contract, project_root, blockers)
    _validate_incident_source(contract, project_root, blockers)
    _validate_closure_provenance(contract, project_root, blockers)
    _validate_future_namespace(contract, project_root, blockers)
    _validate_future_controls(contract, blockers)
    _validate_seals_and_access(contract, blockers)
    _validate_manifest(contract, project_root, blockers)
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "contract_path": str(Path(contract_path).as_posix()),
        "gate_id": contract.get("gate_id"),
        "evidence_ceiling": contract.get("evidence_ceiling"),
        "edge_claim": contract.get("edge_claim"),
        "real_access": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Lily B8.9-D static L-4 replacement design.")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    args = parser.parse_args()
    result = validate(args.contract)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
