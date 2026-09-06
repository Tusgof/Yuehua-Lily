"""Fail-closed future-shaped lifecycle for CORE-1E-B2-A-R1.

The project bootstrap is deny-only.  This lifecycle is exercised only in a
temporary Git repository seeded with committed synthetic bytes.  It never
resolves or inspects the real container.  Gate, Exact-SHA CI, Git-blob,
runtime-byte, owner, cutoff, clean-checkout, and one-shot checks happen before
the synthetic input is read.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, MutableMapping

from lib.core_1e_a_synthetic_engine import DEVELOPMENT_END, VALIDATION_END, VALIDATION_START
from lib.core_1e_b2_empirical_adapter_v2 import (
    ADAPTER_PATH,
    EXPENSE_INPUT_PATH,
    FIXTURE_PATH,
    NORMALIZED_SCHEMA_PATH,
    POISON_FIXTURE_PATH,
    REPORT_SCHEMA_VERSION,
    YAHOO_NORMALIZER_PATH,
    VALIDATION_SEAL,
    build_empirical_report,
    decode_normalized_bytes,
    preflight_normalized_bytes,
)


GATE_PATH = "experiments/core_1e_b2_development_execution_contract_v2.json"
ACTIVATION_PATH = "experiments/activation_records/core_1e_b2_activation_v2.json"
EXPECTED_GATE_ID = "core_1e_b2_development_execution_contract_v2"
EXPECTED_ACTIVATION_SCHEMA = "lily_core_1e_b2_activation_v2"
OWNER_AUTHORIZATION_REF = "owner_authorized_core_1e_b2_e0_machinery_only_2026-09-03"
B2_B_ACTIVATION_REFERENCE = "owner_approved_CORE-1E-B2-B_activation_reference_required"
EXECUTION_MODE = "future_e1_empirical_development"
DEVELOPMENT_CUTOFF = DEVELOPMENT_END.isoformat()
VALIDATION_CUTOFF = VALIDATION_START.isoformat()
ENGINE_PATH = "lib/core_1e_a_synthetic_engine.py"
SCHEMA_PATH = "schemas/core_1e_b2_empirical_report_v2.schema.json"
ACTIVATION_SCHEMA_PATH = "schemas/core_1e_b2_activation_v2.schema.json"
CONTAINER_SCHEMA_PATH = NORMALIZED_SCHEMA_PATH
CONTRACT_VALIDATOR_PATH = "scripts/validate_core_1e_b2_development_execution_contract_v2.py"
REPORT_VALIDATOR_PATH = "scripts/validate_core_1e_b2_empirical_report_v2.py"
BOOTSTRAP_PATH = "scripts/run_core_1e_b2_committed_bootstrap_v2.py"
RUNTIME_PATHS = (
    ENGINE_PATH,
    YAHOO_NORMALIZER_PATH,
    ADAPTER_PATH,
    "lib/core_1e_b2_lifecycle_v2.py",
    CONTRACT_VALIDATOR_PATH,
    REPORT_VALIDATOR_PATH,
    CONTAINER_SCHEMA_PATH,
    ACTIVATION_SCHEMA_PATH,
    SCHEMA_PATH,
    BOOTSTRAP_PATH,
)
EXPECTED_CONTAINER_IDENTITY = {
    "path": "data/normalized/l1_yahoo_daily_v1.json",
    "sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd",
    "size_bytes": 8258827,
    "max_date": "2015-12-31",
    "symbols_in_order": ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"],
    "future_only": True,
}
EXPECTED_VALIDATION = {
    "start": VALIDATION_START.isoformat(),
    "end": VALIDATION_END.isoformat(),
    "status": "sealed_not_accessed",
    "accessed": False,
}
EXPECTED_FINAL_VALIDATION = {"status": "sealed_not_accessed", "accessed": False}
EXPECTED_ONE_SHOT_PATHS = {
    "marker_path": "reports/experiments/core_1e_b2r1_one_shot_marker_v2.json",
    "attempt_path": "reports/experiments/core_1e_b2r1_execution_attempt_v2.json",
    "report_path": "reports/experiments/core_1e_b2r1_execution_report_v2.json",
}
EXPECTED_ONE_SHOT_SCHEMAS = {
    "marker_schema_version": "lily_core_1e_b2r1_marker_v2",
    "attempt_schema_version": "lily_core_1e_b2r1_attempt_v2",
    "report_schema_version": REPORT_SCHEMA_VERSION,
}
ACTIVATION_KEYS = {
    "schema_version",
    "gate_id",
    "gate_sha256",
    "accepted_gate_commit",
    "exact_ci_head_sha",
    "exact_ci_run_id",
    "owner_authorization_ref",
    "execution_mode",
    "b2_b_activation_reference_required",
    "b2_b_activation_reference",
    "runtime_bytes",
    "development_cutoff",
    "validation_boundary",
    "input_ref",
    "input_sha256",
    "input_size_bytes",
    "expense_input_ref",
    "expense_input_sha256",
    "expense_input_size_bytes",
    "container_identity",
    "one_shot",
}
ONE_SHOT_KEYS = {
    "marker_path",
    "attempt_path",
    "report_path",
    "marker_schema_version",
    "attempt_schema_version",
    "report_schema_version",
    "max_invocations",
    "claim_before_input_read",
    "retry_allowed",
}
EXPECTED_PRE_DECODE_CHECKS = [
    "gate_identity",
    "exact_ci_head_identity",
    "gate_blob_hash",
    "owner_authorization_ref",
    "future_container_identity",
    "development_cutoff",
    "activation_schema_and_canonical_bytes",
    "runtime_byte_hashes",
    "clean_checkout",
    "prior_one_shot_absence",
    "container_structure_and_all_session_dates",
    "separate_expense_input_binding",
]


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def hash_file(path: Path) -> str:
    """Hash an explicitly supplied file, used only by temporary synthetic tests."""

    return sha256(path.read_bytes())


def _hash40(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and value == value.lower() and all(
        char in "0123456789abcdef" for char in value
    )


def _hash64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and value == value.lower() and all(
        char in "0123456789abcdef" for char in value
    )


def safe_relative(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts and path.as_posix() == value


def git_head(root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False
    )
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and _hash40(value) else None


def git_blob(root: Path, commit: str, relative: str) -> bytes | None:
    """Read a safe, explicitly named committed blob; never resolve a data path."""

    if not _hash40(commit) or not safe_relative(relative):
        return None
    completed = subprocess.run(
        ["git", "show", f"{commit}:{relative}"], cwd=root, capture_output=True, check=False
    )
    return completed.stdout if completed.returncode == 0 else None


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    if not _hash40(ancestor) or not _hash40(descendant):
        return False
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=root,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )


def clean_checkout(root: Path) -> bool:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--ignored=matching"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0 and completed.stdout == ""


def build_synthetic_activation(
    *,
    gate_commit: str,
    gate_sha256: str,
    runtime_bytes: dict[str, str],
    input_ref: str,
    input_sha256: str,
    input_size_bytes: int,
    expense_input_sha256: str,
    expense_input_size_bytes: int,
    owner_authorization_ref: str = OWNER_AUTHORIZATION_REF,
    expense_input_ref: str = EXPENSE_INPUT_PATH,
    container_identity: dict[str, Any] | None = None,
    hermetic_ci_run_id: int = 1,
) -> dict[str, Any]:
    """Construct a future E1-shaped activation for a temporary synthetic proof."""

    return {
        "schema_version": EXPECTED_ACTIVATION_SCHEMA,
        "gate_id": EXPECTED_GATE_ID,
        "gate_sha256": gate_sha256,
        "accepted_gate_commit": gate_commit,
        "exact_ci_head_sha": gate_commit,
        "exact_ci_run_id": hermetic_ci_run_id,
        "owner_authorization_ref": owner_authorization_ref,
        "execution_mode": EXECUTION_MODE,
        "b2_b_activation_reference_required": True,
        "b2_b_activation_reference": B2_B_ACTIVATION_REFERENCE,
        "runtime_bytes": dict(runtime_bytes),
        "development_cutoff": DEVELOPMENT_CUTOFF,
        "validation_boundary": dict(EXPECTED_VALIDATION),
        "input_ref": input_ref,
        "input_sha256": input_sha256,
        "input_size_bytes": input_size_bytes,
        "expense_input_ref": expense_input_ref,
        "expense_input_sha256": expense_input_sha256,
        "expense_input_size_bytes": expense_input_size_bytes,
        "container_identity": dict(container_identity or EXPECTED_CONTAINER_IDENTITY),
        "one_shot": {
            **EXPECTED_ONE_SHOT_PATHS,
            **EXPECTED_ONE_SHOT_SCHEMAS,
            "max_invocations": 1,
            "claim_before_input_read": True,
            "retry_allowed": False,
        },
    }


def _gate_blob_blockers(gate_raw: bytes | None) -> list[str]:
    if gate_raw is None:
        return ["gate_blob_unavailable"]
    try:
        gate = json.loads(gate_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ["gate_blob_unreadable"]
    if not isinstance(gate, dict):
        return ["gate_not_object"]
    blockers: list[str] = []
    if gate.get("schema_version") != "lily_core_1e_b2_development_execution_contract_v2":
        blockers.append("gate_schema_version_changed")
    if gate.get("order_id") != "CORE-1E-B2-A" or gate.get("work_order_id") != "CORE-1E-B2-A-R1":
        blockers.append("gate_order_identity_changed")
    if gate.get("gate_id") != EXPECTED_GATE_ID:
        blockers.append("gate_id_changed")
    if gate.get("owner_authorization_ref") != OWNER_AUTHORIZATION_REF:
        blockers.append("gate_owner_authorization_changed")
    if gate.get("future_container_identity") != EXPECTED_CONTAINER_IDENTITY:
        blockers.append("gate_container_identity_changed")
    normalized = gate.get("normalized_container_contract")
    if not isinstance(normalized, dict):
        blockers.append("gate_normalized_container_contract_missing")
    else:
        if normalized.get("top_level_schema_version") != "lily_l1_daily_dataset_v1":
            blockers.append("gate_top_level_schema_changed")
        if normalized.get("top_level_fields") != ["schema_version", "acquired_at", "cutoff_inclusive", "symbols"]:
            blockers.append("gate_top_level_fields_changed")
        if normalized.get("per_symbol_schema_version") != "lily_yahoo_daily_normalized_v1":
            blockers.append("gate_symbol_schema_changed")
        if normalized.get("record_fields") != [
            "session_date", "availability_timestamp", "raw_close", "cash_distribution", "split",
            "total_return_close", "trading_currency", "provider_revision", "is_backfilled",
        ]:
            blockers.append("gate_record_fields_changed")
        if normalized.get("decoded_return_field") != "total_return_close" or normalized.get("raw_close_decoded") is not False:
            blockers.append("gate_return_decode_policy_changed")
        if normalized.get("expense_ratios_field_present") is not False:
            blockers.append("gate_expense_container_policy_changed")
        if normalized.get("u8_membership_and_order") != EXPECTED_CONTAINER_IDENTITY["symbols_in_order"]:
            blockers.append("gate_u8_order_changed")
    boundaries = gate.get("execution_boundaries")
    if not isinstance(boundaries, dict):
        blockers.append("gate_execution_boundaries_missing")
    else:
        if boundaries.get("mode") != "synthetic_only":
            blockers.append("gate_execution_mode_changed")
        if boundaries.get("allowed_input_ref") != FIXTURE_PATH or boundaries.get("expense_input_ref") != EXPENSE_INPUT_PATH:
            blockers.append("gate_input_binding_changed")
        if boundaries.get("development_cutoff") != DEVELOPMENT_CUTOFF:
            blockers.append("gate_development_cutoff_changed")
        if boundaries.get("reject_on_or_after") != VALIDATION_CUTOFF:
            blockers.append("gate_validation_cutoff_changed")
        if boundaries.get("validation_boundary") != EXPECTED_VALIDATION:
            blockers.append("gate_validation_boundary_changed")
        if (
            boundaries.get("marker_first") is not True
            or boundaries.get("max_invocations") != 1
            or boundaries.get("retry_allowed") is not False
        ):
            blockers.append("gate_one_shot_policy_changed")
    future = gate.get("future_development_execution")
    if not isinstance(future, dict):
        blockers.append("gate_future_e1_mode_missing")
    else:
        if future.get("mode") != "e1_empirical_development_only":
            blockers.append("gate_future_e1_mode_changed")
        if future.get("activation_required") is not True:
            blockers.append("gate_future_activation_requirement_changed")
        if future.get("activation_reference_requirement") != "separate owner-approved CORE-1E-B2-B activation reference":
            blockers.append("gate_b2_b_reference_requirement_changed")
        if future.get("final_validation") != EXPECTED_FINAL_VALIDATION or future.get("edge_claim") != "none":
            blockers.append("gate_future_validation_seal_changed")
    report_contract = gate.get("report_contract")
    if not isinstance(report_contract, dict) or report_contract.get("schema_version") != REPORT_SCHEMA_VERSION or report_contract.get("schema_path") != SCHEMA_PATH:
        blockers.append("gate_report_contract_changed")
    return sorted(set(blockers))


def validate_activation(root: Path, head: str, activation: dict[str, Any]) -> list[str]:
    """Validate activation and committed provenance without touching inputs."""

    blockers: list[str] = []
    if not isinstance(activation, dict) or set(activation) != ACTIVATION_KEYS:
        return ["activation_closed_world_changed"]
    accepted = activation.get("accepted_gate_commit")
    if activation.get("schema_version") != EXPECTED_ACTIVATION_SCHEMA:
        blockers.append("activation_schema_version_changed")
    if activation.get("gate_id") != EXPECTED_GATE_ID:
        blockers.append("activation_gate_id_changed")
    if not _hash64(activation.get("gate_sha256")):
        blockers.append("activation_gate_hash_invalid")
    if not _hash40(accepted) or activation.get("exact_ci_head_sha") != accepted:
        blockers.append("activation_gate_ci_identity_mismatch")
    if not is_ancestor(root, accepted, head):
        blockers.append("activation_gate_not_ancestor")
    run_id = activation.get("exact_ci_run_id")
    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id < 1:
        blockers.append("activation_exact_sha_ci_missing")
    if activation.get("owner_authorization_ref") != OWNER_AUTHORIZATION_REF:
        blockers.append("activation_owner_authorization_mismatch")
    if activation.get("execution_mode") != EXECUTION_MODE:
        blockers.append("activation_execution_mode_changed")
    if activation.get("b2_b_activation_reference_required") is not True:
        blockers.append("activation_b2_b_reference_requirement_changed")
    if activation.get("b2_b_activation_reference") != B2_B_ACTIVATION_REFERENCE:
        blockers.append("activation_b2_b_reference_changed")

    gate_raw = git_blob(root, accepted, GATE_PATH)
    if gate_raw is None or sha256(gate_raw) != activation.get("gate_sha256"):
        blockers.append("activation_gate_blob_mismatch")
    blockers.extend(_gate_blob_blockers(gate_raw))
    current_gate_raw = git_blob(root, head, GATE_PATH)
    if current_gate_raw is None or sha256(current_gate_raw) != activation.get("gate_sha256"):
        blockers.append("activation_current_gate_blob_mismatch")
    blockers.extend(_gate_blob_blockers(current_gate_raw))

    runtime = activation.get("runtime_bytes")
    if not isinstance(runtime, dict) or set(runtime) != set(RUNTIME_PATHS):
        blockers.append("activation_runtime_byte_set_changed")
    else:
        for relative in RUNTIME_PATHS:
            digest = runtime.get(relative)
            accepted_raw = git_blob(root, accepted, relative)
            current_raw = git_blob(root, head, relative)
            if not safe_relative(relative) or not _hash64(digest) or accepted_raw is None or sha256(accepted_raw) != digest:
                blockers.append(f"activation_runtime_byte_mismatch:{relative}")
            if not _hash64(digest) or current_raw is None or sha256(current_raw) != digest:
                blockers.append(f"activation_current_runtime_byte_mismatch:{relative}")

    if activation.get("development_cutoff") != DEVELOPMENT_CUTOFF:
        blockers.append("activation_development_cutoff_changed")
    if activation.get("validation_boundary") != EXPECTED_VALIDATION:
        blockers.append("activation_validation_boundary_changed")
    if activation.get("input_ref") != FIXTURE_PATH or not safe_relative(activation.get("input_ref")):
        blockers.append("activation_input_ref_changed")
    if not _hash64(activation.get("input_sha256")):
        blockers.append("activation_input_hash_invalid")
    input_size = activation.get("input_size_bytes")
    if not isinstance(input_size, int) or isinstance(input_size, bool) or input_size <= 0:
        blockers.append("activation_input_size_invalid")
    if activation.get("expense_input_ref") != EXPENSE_INPUT_PATH or not safe_relative(activation.get("expense_input_ref")):
        blockers.append("activation_expense_input_ref_changed")
    if not _hash64(activation.get("expense_input_sha256")):
        blockers.append("activation_expense_input_hash_invalid")
    expense_size = activation.get("expense_input_size_bytes")
    if not isinstance(expense_size, int) or isinstance(expense_size, bool) or expense_size <= 0:
        blockers.append("activation_expense_input_size_invalid")
    if activation.get("container_identity") != EXPECTED_CONTAINER_IDENTITY:
        blockers.append("activation_container_identity_mismatch")

    one_shot = activation.get("one_shot")
    if not isinstance(one_shot, dict) or set(one_shot) != ONE_SHOT_KEYS:
        blockers.append("activation_one_shot_shape_changed")
    else:
        paths = [one_shot.get(key) for key in ("marker_path", "attempt_path", "report_path")]
        if len(set(paths)) != 3:
            blockers.append("activation_one_shot_paths_not_distinct")
        for key in ("marker_path", "attempt_path", "report_path"):
            if not safe_relative(one_shot.get(key)):
                blockers.append(f"activation_one_shot_path_invalid:{key}")
            if one_shot.get(key) != EXPECTED_ONE_SHOT_PATHS[key]:
                blockers.append(f"activation_one_shot_path_changed:{key}")
        for key, expected in EXPECTED_ONE_SHOT_SCHEMAS.items():
            if one_shot.get(key) != expected:
                blockers.append(f"activation_one_shot_schema_changed:{key}")
        if (
            one_shot.get("max_invocations") != 1
            or one_shot.get("claim_before_input_read") is not True
            or one_shot.get("retry_allowed") is not False
        ):
            blockers.append("activation_one_shot_policy_changed")
    return sorted(set(blockers))


def _read_activation_from_head(root: Path, head: str) -> tuple[dict[str, Any] | None, bytes | None, str | None]:
    raw = git_blob(root, head, ACTIVATION_PATH)
    if raw is None:
        return None, None, "canonical_activation_absent"
    try:
        activation = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, raw, "canonical_activation_unreadable"
    return activation, raw, None


def preflight(root: Path) -> dict[str, Any]:
    """Verify committed activation/lifecycle state without resolving inputs."""

    base = {
        "status": "blocked",
        "real_data_accessed": False,
        "validation_accessed": False,
        "input_read_count": 0,
        "expense_input_read_count": 0,
    }
    head = git_head(root)
    if head is None:
        return base | {"outcome": "git_head_unavailable"}
    activation, raw, error = _read_activation_from_head(root, head)
    if error:
        return base | {"outcome": error, "head": head}
    blockers = validate_activation(root, head, activation)
    if raw != canonical(activation):
        blockers.append("activation_not_canonical")
    if blockers:
        return base | {"outcome": "activation_invalid", "head": head, "blockers": sorted(set(blockers))}
    one_shot = activation["one_shot"]
    existing = [
        key for key in ("marker_path", "attempt_path", "report_path") if (root / one_shot[key]).is_file()
    ]
    if existing:
        return base | {"outcome": "refused_prior_invocation", "head": head, "existing": existing}
    if not clean_checkout(root):
        return base | {"outcome": "dirty_checkout", "head": head}
    return base | {
        "status": "ready",
        "outcome": "canonical_activation_ready",
        "head": head,
        "activation": activation,
        "activation_raw": raw,
    }


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(raw)
    os.replace(temporary, path)


def _load_expense_bytes(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("expense_input_json_unreadable") from exc
    if not isinstance(value, dict):
        raise ValueError("expense_input_must_be_object")
    return value


def run_synthetic_once(
    root: Path,
    *,
    report_builder: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
    input_reader: Callable[[Path], bytes] | None = None,
) -> dict[str, Any]:
    """Claim one marker, then read only the committed synthetic inputs."""

    result = preflight(root)
    if result.get("status") != "ready":
        return result
    activation = result["activation"]
    raw_activation = result["activation_raw"]
    head = result["head"]
    one_shot = activation["one_shot"]
    marker_path = root / one_shot["marker_path"]
    marker = {
        "schema_version": EXPECTED_ONE_SHOT_SCHEMAS["marker_schema_version"],
        "marker_id": "core_1e_b2r1_one_shot_marker_v2",
        "status": "claimed",
        "activation_sha256": sha256(raw_activation),
        "input_read_count": 0,
        "expense_input_read_count": 0,
        "attempt_path": one_shot["attempt_path"],
        "report_path": one_shot["report_path"],
        "retry_allowed": False,
    }
    _atomic_write(marker_path, canonical(marker))
    try:
        if activation["input_ref"] != FIXTURE_PATH or activation["expense_input_ref"] != EXPENSE_INPUT_PATH:
            raise ValueError("synthetic_input_ref_rejected")
        input_path = root / activation["input_ref"]
        reader = input_reader or (lambda path: path.read_bytes())
        raw_input = reader(input_path)
        if not isinstance(raw_input, bytes):
            raise ValueError("synthetic_input_must_be_bytes")
        marker["input_read_count"] = 1
        if sha256(raw_input) != activation["input_sha256"]:
            raise ValueError("input_hash_mismatch")
        if len(raw_input) != activation["input_size_bytes"]:
            raise ValueError("input_size_mismatch")

        expense_path = root / activation["expense_input_ref"]
        raw_expense = expense_path.read_bytes()
        marker["expense_input_read_count"] = 1
        if sha256(raw_expense) != activation["expense_input_sha256"]:
            raise ValueError("expense_input_hash_mismatch")
        if len(raw_expense) != activation["expense_input_size_bytes"]:
            raise ValueError("expense_input_size_mismatch")
        expense_input = _load_expense_bytes(raw_expense)

        # Structural validation is deliberately separate from numeric decode.
        normalized, metadata = preflight_normalized_bytes(raw_input)
        if metadata["row_count"] < 201:
            raise ValueError("synthetic_fixture_requires_at_least_201_common_sessions")
        decode_counter: MutableMapping[str, int] = {}
        decode_normalized_bytes(raw_input, expense_input, decode_counter=decode_counter)
        if decode_counter.get("count", 0) <= 0:
            raise ValueError("synthetic_return_decode_missing")

        engine_raw = git_blob(root, head, ENGINE_PATH)
        adapter_raw = git_blob(root, head, ADAPTER_PATH)
        yahoo_raw = git_blob(root, head, YAHOO_NORMALIZER_PATH)
        if engine_raw is None or adapter_raw is None or yahoo_raw is None:
            raise ValueError("committed_runtime_blob_unavailable")
        if report_builder is None:
            report = build_empirical_report(
                normalized,
                expense_input,
                contract_sha256=activation["gate_sha256"],
                fixture_sha256=sha256(raw_input),
                expense_input_sha256=sha256(raw_expense),
                producing_commit=head,
                engine_sha256=sha256(engine_raw),
                adapter_sha256=sha256(adapter_raw),
                yahoo_normalizer_sha256=sha256(yahoo_raw),
            )
        else:
            report = report_builder(normalized, activation)
        if not isinstance(report, dict):
            raise ValueError("synthetic_report_must_be_object")
        raw_report = canonical(report)
        report_path = root / one_shot["report_path"]
        _atomic_write(report_path, raw_report)
        attempt = {
            "schema_version": EXPECTED_ONE_SHOT_SCHEMAS["attempt_schema_version"],
            "attempt_id": "core_1e_b2r1_execution_attempt_v2",
            "status": "completed",
            "activation_sha256": sha256(raw_activation),
            "marker_path": one_shot["marker_path"],
            "report_id": "core_1e_b2r1_execution_report_v2",
            "report_path": one_shot["report_path"],
            "report_sha256": sha256(raw_report),
            "input_ref": activation["input_ref"],
            "input_read_count": 1,
            "expense_input_ref": activation["expense_input_ref"],
            "expense_input_read_count": 1,
            "return_values_decoded": decode_counter["count"],
            "row_count": metadata["row_count"],
            "development_cutoff": DEVELOPMENT_CUTOFF,
            "validation_accessed": False,
            "edge_claim": "none",
        }
        raw_attempt = canonical(attempt)
        _atomic_write(root / one_shot["attempt_path"], raw_attempt)
        marker.update(
            {
                "status": "completed",
                "attempt_id": attempt["attempt_id"],
                "attempt_path": one_shot["attempt_path"],
                "attempt_sha256": sha256(raw_attempt),
                "report_id": attempt["report_id"],
                "report_sha256": sha256(raw_report),
                "completion_count": 1,
            }
        )
        _atomic_write(marker_path, canonical(marker))
        return {
            "status": "complete",
            "outcome": "synthetic_completed",
            "real_data_accessed": False,
            "validation_accessed": False,
            "input_read_count": 1,
            "expense_input_read_count": 1,
            "return_values_decoded": decode_counter["count"],
            "completion_count": 1,
        }
    except Exception as exc:
        marker.update({"status": "failed", "error": str(exc), "completion_count": 0})
        _atomic_write(marker_path, canonical(marker))
        return {
            "status": "blocked",
            "outcome": "synthetic_failed_after_marker",
            "real_data_accessed": False,
            "validation_accessed": False,
            "input_read_count": marker["input_read_count"],
            "expense_input_read_count": marker["expense_input_read_count"],
            "error": str(exc),
        }
