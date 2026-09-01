"""Fail-closed future lifecycle helpers for CORE-1E-A.

The production Phase-A bootstrap never calls the input-reading function in
this module.  The only runnable proof is explicitly synthetic and accepts
only a committed ``tests/fixtures/`` reference in a temporary Git repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable


GATE_PATH = "experiments/core_1e_a_phase_a_execution_contract_v1.json"
ACTIVATION_PATH = "experiments/activation_records/core_1e_a_activation_v1.json"
EXPECTED_GATE_ID = "core_1e_a_phase_a_execution_contract_v1"
EXPECTED_ACTIVATION_SCHEMA = "lily_core_1e_a_activation_v1"
EXPECTED_CUTOFF = "2015-12-31"
EXPECTED_VALIDATION_BOUNDARY = {
    "start": "2016-01-04",
    "end": "2026-06-30",
    "status": "sealed_not_accessed",
    "accessed": False,
}
RUNTIME_PATHS = (
    "lib/core_1e_a_synthetic_engine.py",
    "lib/core_1e_a_lifecycle_v1.py",
    "scripts/run_core_1e_a_committed_bootstrap_v1.py",
    "scripts/validate_core_1e_a_synthetic_report_v1.py",
    "schemas/core_1e_a_activation_v1.schema.json",
    "schemas/core_1e_a_synthetic_report_v1.schema.json",
)
MARKER_PATH = "reports/experiments/core_1e_a_one_shot_marker_v1.json"
ATTEMPT_PATH = "reports/experiments/core_1e_a_execution_attempt_v1.json"
REPORT_PATH = "reports/experiments/core_1e_a_execution_report_v1.json"
EXPECTED_ONE_SHOT_PATHS = {
    "marker_path": MARKER_PATH,
    "attempt_path": ATTEMPT_PATH,
    "report_path": REPORT_PATH,
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
    "one_shot",
}
ONE_SHOT_KEYS = {"marker_path", "attempt_path", "report_path", "max_invocations", "claim_before_input_read", "retry_allowed"}


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
    owner_authorization_ref: str,
    input_ref: str,
    input_sha256: str,
    hermetic_ci_run_id: int = 1,
) -> dict[str, Any]:
    """Build the exact activation shape used only by the temp-Git proof."""

    return {
        "schema_version": EXPECTED_ACTIVATION_SCHEMA,
        "gate_id": EXPECTED_GATE_ID,
        "gate_sha256": gate_sha256,
        "accepted_gate_commit": gate_commit,
        "exact_ci_head_sha": gate_commit,
        "exact_ci_run_id": hermetic_ci_run_id,
        "owner_authorization_ref": owner_authorization_ref,
        "runtime_bytes": runtime_bytes,
        "development_cutoff": EXPECTED_CUTOFF,
        "validation_boundary": EXPECTED_VALIDATION_BOUNDARY,
        "input_ref": input_ref,
        "input_sha256": input_sha256,
        "one_shot": {
            **EXPECTED_ONE_SHOT_PATHS,
            "max_invocations": 1,
            "claim_before_input_read": True,
            "retry_allowed": False,
        },
    }


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
    if not isinstance(activation.get("owner_authorization_ref"), str) or not activation["owner_authorization_ref"].strip():
        blockers.append("activation_owner_authorization_missing")
    gate_raw = git_blob(root, accepted, GATE_PATH)
    if gate_raw is None or sha256(gate_raw) != activation.get("gate_sha256"):
        blockers.append("activation_gate_blob_mismatch")
    runtime = activation.get("runtime_bytes")
    if not isinstance(runtime, dict) or set(runtime) != set(RUNTIME_PATHS):
        blockers.append("activation_runtime_byte_set_changed")
    else:
        for relative in RUNTIME_PATHS:
            digest = runtime.get(relative)
            raw = git_blob(root, accepted, relative)
            if not _hash64(digest) or raw is None or sha256(raw) != digest:
                blockers.append(f"activation_runtime_byte_mismatch:{relative}")
            current_raw = git_blob(root, head, relative)
            if not _hash64(digest) or current_raw is None or sha256(current_raw) != digest:
                blockers.append(f"activation_current_runtime_byte_mismatch:{relative}")
    if activation.get("development_cutoff") != EXPECTED_CUTOFF:
        blockers.append("activation_development_cutoff_changed")
    if activation.get("validation_boundary") != EXPECTED_VALIDATION_BOUNDARY:
        blockers.append("activation_validation_boundary_changed")
    input_ref = activation.get("input_ref")
    if not safe_relative(input_ref):
        blockers.append("activation_input_ref_invalid")
    if not _hash64(activation.get("input_sha256")):
        blockers.append("activation_input_hash_invalid")
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
    """Check all gate/provenance state without resolving the input reference."""

    head = git_head(root)
    base = {"status": "blocked", "real_data_accessed": False, "validation_accessed": False, "input_read_count": 0}
    if head is None:
        return base | {"outcome": "git_head_unavailable"}
    activation, raw, error = _read_activation_from_head(root, head)
    if error:
        return base | {"outcome": error, "head": head}
    blockers = validate_activation(root, head, activation)
    if raw != canonical(activation):
        blockers.append("activation_not_canonical")
    if blockers:
        return base | {"outcome": "activation_invalid", "head": head, "blockers": blockers}
    one_shot = activation["one_shot"]
    existing = [key for key in ("marker_path", "attempt_path", "report_path") if (root / one_shot[key]).is_file()]
    if existing:
        return base | {"outcome": "refused_prior_invocation", "head": head, "existing": existing}
    if not clean_checkout(root):
        return base | {"outcome": "dirty_checkout", "head": head}
    return base | {"status": "ready", "outcome": "canonical_activation_ready", "head": head, "activation": activation, "activation_raw": raw}


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
    """Run one explicitly synthetic lifecycle proof after atomic marker claim."""

    result = preflight(root)
    if result.get("status") != "ready":
        return result
    activation = result["activation"]
    raw_activation = result["activation_raw"]
    one_shot = activation["one_shot"]
    marker_path = root / one_shot["marker_path"]
    marker = {
        "schema_version": "lily_core_1e_a_marker_v1",
        "status": "claimed",
        "activation_sha256": sha256(raw_activation),
        "input_read_count": 0,
        "retry_allowed": False,
    }
    _atomic_write(marker_path, canonical(marker))
    if not activation["input_ref"].startswith("tests/fixtures/"):
        marker.update({"status": "failed", "error": "synthetic_proof_requires_committed_fixture_ref"})
        _atomic_write(marker_path, canonical(marker))
        return {"status": "blocked", "outcome": "synthetic_input_ref_rejected", "real_data_accessed": False, "validation_accessed": False, "input_read_count": 0}
    input_path = root / activation["input_ref"]
    try:
        raw_input = input_path.read_bytes()
        marker["input_read_count"] = 1
        if sha256(raw_input) != activation["input_sha256"]:
            raise ValueError("input_hash_mismatch")
        payload = json.loads(raw_input.decode("utf-8"))
        if report_builder is None:
            report = {
                "schema_version": "lily_core_1e_a_lifecycle_proof_report_v1",
                "status": "synthetic_completed",
                "input_sha256": sha256(raw_input),
                "validation_seal": EXPECTED_VALIDATION_BOUNDARY,
                "real_data_accessed": False,
                "validation_accessed": False,
            }
        else:
            report = report_builder(payload, activation)
        attempt = {
            "schema_version": "lily_core_1e_a_attempt_v1",
            "status": "completed",
            "input_read_count": 1,
            "marker_path": one_shot["marker_path"],
            "report_path": one_shot["report_path"],
        }
        _atomic_write(root / one_shot["report_path"], canonical(report))
        _atomic_write(root / one_shot["attempt_path"], canonical(attempt))
        marker.update({"status": "completed", "report_path": one_shot["report_path"]})
        _atomic_write(marker_path, canonical(marker))
        return {"status": "complete", "outcome": "synthetic_completed", "real_data_accessed": False, "validation_accessed": False, "input_read_count": 1}
    except Exception as exc:  # The marker is deliberately retained as a no-retry failure.
        marker.update({"status": "failed", "error": str(exc)})
        _atomic_write(marker_path, canonical(marker))
        return {"status": "blocked", "outcome": "synthetic_failed_after_marker", "real_data_accessed": False, "validation_accessed": False, "input_read_count": marker["input_read_count"], "error": str(exc)}
