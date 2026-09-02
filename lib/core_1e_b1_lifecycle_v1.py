"""Fail-closed temporary-Git lifecycle for CORE-1E-B1 synthetic proof.

The project bootstrap remains deny-only.  This module is exercised only by a
future hermetic temporary repository that supplies a committed activation.
All gate, CI, blob, owner, container-identity, cutoff, and checkout checks run
before the synthetic input is resolved or decoded.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from lib.core_1e_b1_synthetic_adapter_v1 import (
    ADAPTER_PATH,
    DEVELOPMENT_CUTOFF,
    FIXTURE_PATH,
    VALIDATION_CUTOFF,
    VALIDATION_SEAL,
    build_synthetic_report,
)


GATE_PATH = "experiments/core_1e_b1_development_execution_contract_v1.json"
ACTIVATION_PATH = "experiments/activation_records/core_1e_b1_activation_v1.json"
EXPECTED_GATE_ID = "core_1e_b1_development_execution_contract_v1"
EXPECTED_ACTIVATION_SCHEMA = "lily_core_1e_b1_activation_v1"
OWNER_AUTHORIZATION_REF = "owner_authorized_core_1e_b_development_only_2026-09-01"
ENGINE_PATH = "lib/core_1e_a_synthetic_engine.py"
SCHEMA_PATH = "schemas/core_1e_b1_synthetic_report_v1.schema.json"
CONTRACT_VALIDATOR_PATH = "scripts/validate_core_1e_b1_development_execution_contract_v1.py"
BOOTSTRAP_PATH = "scripts/run_core_1e_b1_committed_bootstrap_v1.py"
RUNTIME_PATHS = (
    ENGINE_PATH,
    ADAPTER_PATH,
    "lib/core_1e_b1_lifecycle_v1.py",
    CONTRACT_VALIDATOR_PATH,
    SCHEMA_PATH,
    BOOTSTRAP_PATH,
)
EXPECTED_ONE_SHOT_PATHS = {
    "marker_path": "reports/experiments/core_1e_b1_one_shot_marker_v1.json",
    "attempt_path": "reports/experiments/core_1e_b1_execution_attempt_v1.json",
    "report_path": "reports/experiments/core_1e_b1_execution_report_v1.json",
}
ACTIVATION_KEYS = {
    "schema_version",
    "gate_id",
    "gate_sha256",
    "accepted_gate_commit",
    "exact_ci_head_sha",
    "exact_ci_run_id",
    "owner_authorization_ref",
    "runtime_bytes",
    "development_cutoff",
    "validation_boundary",
    "input_ref",
    "input_sha256",
    "input_size_bytes",
    "container_identity",
    "one_shot",
}
ONE_SHOT_KEYS = {
    "marker_path",
    "attempt_path",
    "report_path",
    "max_invocations",
    "claim_before_input_read",
    "retry_allowed",
}
EXPECTED_CONTAINER_IDENTITY = {
    "path": "data/normalized/l1_yahoo_daily_v1.json",
    "sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd",
    "size_bytes": 8258827,
    "max_date": "2015-12-31",
    "symbols_in_order": ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"],
    "future_only": True,
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def hash_file(path: Path) -> str:
    return sha256(path.read_bytes())


def _hash40(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and value == value.lower() and all(char in "0123456789abcdef" for char in value)


def _hash64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and value == value.lower() and all(char in "0123456789abcdef" for char in value)


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
    if not _hash40(commit) or not safe_relative(relative):
        return None
    completed = subprocess.run(
        ["git", "show", f"{commit}:{relative}"], cwd=root, capture_output=True, check=False
    )
    return completed.stdout if completed.returncode == 0 else None


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    if not _hash40(ancestor) or not _hash40(descendant):
        return False
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        capture_output=True,
        check=False,
    ).returncode == 0


def clean_checkout(root: Path) -> bool:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
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
    owner_authorization_ref: str = OWNER_AUTHORIZATION_REF,
    input_size_bytes: int = 0,
    container_identity: dict[str, Any] | None = None,
    hermetic_ci_run_id: int = 1,
) -> dict[str, Any]:
    return {
        "schema_version": EXPECTED_ACTIVATION_SCHEMA,
        "gate_id": EXPECTED_GATE_ID,
        "gate_sha256": gate_sha256,
        "accepted_gate_commit": gate_commit,
        "exact_ci_head_sha": gate_commit,
        "exact_ci_run_id": hermetic_ci_run_id,
        "owner_authorization_ref": owner_authorization_ref,
        "runtime_bytes": dict(runtime_bytes),
        "development_cutoff": DEVELOPMENT_CUTOFF,
        "validation_boundary": dict(VALIDATION_SEAL),
        "input_ref": input_ref,
        "input_sha256": input_sha256,
        "input_size_bytes": input_size_bytes,
        "container_identity": dict(container_identity or EXPECTED_CONTAINER_IDENTITY),
        "one_shot": {
            **EXPECTED_ONE_SHOT_PATHS,
            "max_invocations": 1,
            "claim_before_input_read": True,
            "retry_allowed": False,
        },
    }


def _gate_blob_blockers(gate_raw: bytes | None) -> list[str]:
    if gate_raw is None:
        return ["gate_blob_unavailable"]
    try:
        gate = json.loads(gate_raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ["gate_blob_unreadable"]
    blockers: list[str] = []
    if gate.get("schema_version") != "lily_core_1e_b1_development_execution_contract_v1":
        blockers.append("gate_schema_version_changed")
    if gate.get("order_id") != "CORE-1E-B1" or gate.get("work_order_id") != "CORE-1E-B1-R2":
        blockers.append("gate_order_identity_changed")
    if gate.get("gate_id") != EXPECTED_GATE_ID:
        blockers.append("gate_id_changed")
    if gate.get("owner_authorization_ref") != OWNER_AUTHORIZATION_REF:
        blockers.append("gate_owner_authorization_changed")
    if gate.get("future_container_identity") != EXPECTED_CONTAINER_IDENTITY:
        blockers.append("gate_container_identity_changed")
    boundaries = gate.get("execution_boundaries")
    if not isinstance(boundaries, dict):
        blockers.append("gate_execution_boundaries_missing")
    else:
        if boundaries.get("development_cutoff") != DEVELOPMENT_CUTOFF:
            blockers.append("gate_development_cutoff_changed")
        if boundaries.get("reject_on_or_after") != VALIDATION_CUTOFF:
            blockers.append("gate_validation_cutoff_changed")
        if boundaries.get("validation_boundary") != VALIDATION_SEAL:
            blockers.append("gate_validation_boundary_changed")
        if boundaries.get("marker_first") is not True or boundaries.get("max_invocations") != 1 or boundaries.get("retry_allowed") is not False:
            blockers.append("gate_one_shot_policy_changed")
    if gate.get("required_future_checks_before_input_decode") != [
        "gate_identity",
        "exact_ci_head_identity",
        "gate_blob_hash",
        "owner_authorization_ref",
        "future_container_identity",
        "development_cutoff",
    ]:
        blockers.append("gate_pre_decode_check_order_changed")
    return sorted(set(blockers))


def validate_activation(root: Path, head: str, activation: dict[str, Any]) -> list[str]:
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
    if not isinstance(activation.get("exact_ci_run_id"), int) or isinstance(activation.get("exact_ci_run_id"), bool) or activation["exact_ci_run_id"] < 1:
        blockers.append("activation_exact_sha_ci_missing")
    if activation.get("owner_authorization_ref") != OWNER_AUTHORIZATION_REF:
        blockers.append("activation_owner_authorization_mismatch")
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
            if not _hash64(digest) or accepted_raw is None or sha256(accepted_raw) != digest:
                blockers.append(f"activation_runtime_byte_mismatch:{relative}")
            if not _hash64(digest) or current_raw is None or sha256(current_raw) != digest:
                blockers.append(f"activation_current_runtime_byte_mismatch:{relative}")
    if activation.get("development_cutoff") != DEVELOPMENT_CUTOFF:
        blockers.append("activation_development_cutoff_changed")
    if activation.get("validation_boundary") != VALIDATION_SEAL:
        blockers.append("activation_validation_boundary_changed")
    if activation.get("input_ref") != FIXTURE_PATH or not safe_relative(activation.get("input_ref")):
        blockers.append("activation_input_ref_changed")
    if not _hash64(activation.get("input_sha256")):
        blockers.append("activation_input_hash_invalid")
    if not isinstance(activation.get("input_size_bytes"), int) or isinstance(activation.get("input_size_bytes"), bool) or activation["input_size_bytes"] < 0:
        blockers.append("activation_input_size_invalid")
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
        if one_shot.get("max_invocations") != 1 or one_shot.get("claim_before_input_read") is not True or one_shot.get("retry_allowed") is not False:
            blockers.append("activation_one_shot_policy_changed")
    return sorted(set(blockers))


def _read_activation_from_head(root: Path, head: str) -> tuple[dict[str, Any] | None, bytes | None, str | None]:
    raw = git_blob(root, head, ACTIVATION_PATH)
    if raw is None:
        return None, None, "canonical_activation_absent"
    try:
        activation = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, raw, "canonical_activation_unreadable"
    return activation, raw, None


def preflight(root: Path) -> dict[str, Any]:
    """Verify committed activation and lifecycle state without touching input."""

    base = {
        "status": "blocked",
        "real_data_accessed": False,
        "validation_accessed": False,
        "input_read_count": 0,
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
    existing = [key for key in ("marker_path", "attempt_path", "report_path") if (root / one_shot[key]).is_file()]
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


def run_synthetic_once(
    root: Path,
    *,
    report_builder: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Claim one marker, then read only the committed synthetic fixture."""

    result = preflight(root)
    if result.get("status") != "ready":
        return result
    activation = result["activation"]
    raw_activation = result["activation_raw"]
    head = result["head"]
    one_shot = activation["one_shot"]
    marker_path = root / one_shot["marker_path"]
    marker = {
        "schema_version": "lily_core_1e_b1_marker_v1",
        "status": "claimed",
        "activation_sha256": sha256(raw_activation),
        "input_read_count": 0,
        "retry_allowed": False,
    }
    _atomic_write(marker_path, canonical(marker))
    try:
        if activation["input_ref"] != FIXTURE_PATH:
            raise ValueError("synthetic_input_ref_rejected")
        input_path = root / activation["input_ref"]
        raw_input = input_path.read_bytes()
        marker["input_read_count"] = 1
        if sha256(raw_input) != activation["input_sha256"]:
            raise ValueError("input_hash_mismatch")
        if activation["input_size_bytes"] not in (0, len(raw_input)):
            raise ValueError("input_size_mismatch")
        payload = json.loads(raw_input.decode("utf-8"))
        engine_raw = git_blob(root, head, ENGINE_PATH)
        adapter_raw = git_blob(root, head, ADAPTER_PATH)
        if engine_raw is None or adapter_raw is None:
            raise ValueError("committed_runtime_blob_unavailable")
        if report_builder is None:
            report = build_synthetic_report(
                payload,
                contract_sha256=activation["gate_sha256"],
                fixture_sha256=sha256(raw_input),
                producing_commit=head,
                engine_sha256=sha256(engine_raw),
                adapter_sha256=sha256(adapter_raw),
            )
        else:
            report = report_builder(payload, activation)
        if not isinstance(report, dict):
            raise ValueError("synthetic_report_must_be_object")
        attempt = {
            "schema_version": "lily_core_1e_b1_attempt_v1",
            "status": "completed",
            "input_read_count": 1,
            "marker_path": one_shot["marker_path"],
            "report_path": one_shot["report_path"],
        }
        _atomic_write(root / one_shot["report_path"], canonical(report))
        _atomic_write(root / one_shot["attempt_path"], canonical(attempt))
        marker.update({"status": "completed", "report_path": one_shot["report_path"]})
        _atomic_write(marker_path, canonical(marker))
        return {
            "status": "complete",
            "outcome": "synthetic_completed",
            "real_data_accessed": False,
            "validation_accessed": False,
            "input_read_count": 1,
        }
    except Exception as exc:
        marker.update({"status": "failed", "error": str(exc)})
        _atomic_write(marker_path, canonical(marker))
        return {
            "status": "blocked",
            "outcome": "synthetic_failed_after_marker",
            "real_data_accessed": False,
            "validation_accessed": False,
            "input_read_count": marker["input_read_count"],
            "error": str(exc),
        }
