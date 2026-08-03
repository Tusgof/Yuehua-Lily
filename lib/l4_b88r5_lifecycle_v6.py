"""Gate-owned v6 activation and structural-provenance helpers; no data I/O."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE = "experiments/l_4_breadth_b88r5_phase_a_execution_contract_v6.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b88r5_scientific_execution_activation_v6.json"
MARKER = "reports/experiments/l_4_breadth_b88r5_one_shot_marker_v6.json"
GATE_ID = "l_4_breadth_b88r5_phase_a_execution_contract_v6"
ACTIVATION_SCHEMA = "lily_l4_b88r5_activation_v6"
OWNER_LITERAL = "continue the work till we complete L4"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
ACTIVATION_KEYS = frozenset(
    (
        "schema_version", "gate_id", "gate_sha256", "owner_literal",
        "accepted_gate_head_sha", "hermetic_ci_head_sha", "hermetic_ci_run_id",
        "inspector_decision", "container_path", "container_sha256",
        "structural_manifest_path", "structural_manifest_sha256",
        "u8_sessions_path", "u8_sessions_sha256", "u8_members_in_order",
        "cutoff_inclusive", "marker_path", "validation_seal",
    )
)
U8 = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
PROVISIONED_IDENTITY = {
    "container_path": "data/normalized/l1_yahoo_daily_v1.json",
    "container_sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd",
    "structural_manifest_path": "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json",
    "structural_manifest_sha256": "de00a4b5a5dd732e27a4a9900868a0f696bb80794e04924da9187808311bb008",
    "u8_sessions_path": "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json",
    "u8_sessions_sha256": "f95665db8ad78280433b37e646486ba03954d0eccba13538d41e961ea88c94ef",
    "u8_members_in_order": list(U8),
    "cutoff_inclusive": "2015-12-31",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def h40(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def h64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def safe_relative(value: object) -> bool:
    path = Path(value) if isinstance(value, str) else None
    return path is not None and not path.is_absolute() and ".." not in path.parts and str(path).replace("\\", "/") == value


def blob(root: Path, commit: str, relative: str) -> bytes | None:
    result = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=root, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def dependencies_ok(root: Path, commit: str, gate: dict[str, Any]) -> bool:
    paths, binding = gate.get("execution_dependencies"), gate.get("execution_binding")
    if not isinstance(paths, list) or not paths or not isinstance(binding, dict) or set(paths) != set(binding):
        return False
    for relative in paths:
        item = binding.get(relative)
        raw = blob(root, commit, relative)
        if (
            not isinstance(relative, str)
            or not isinstance(item, dict)
            or item != {"path": relative, "sha256": item.get("sha256")}
            or not h64(item.get("sha256"))
            or raw is None
            or sha(raw) != item["sha256"]
        ):
            return False
    return True


def clean_checkout(root: Path) -> bool:
    """Reject tracked changes and every untracked path before marker claim."""
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout == b""


def _identity_from_gate(gate: dict[str, Any]) -> dict[str, Any] | None:
    identity = gate.get("provisioned_identity")
    if not isinstance(identity, dict):
        return None
    container = identity.get("container")
    manifest = identity.get("structural_manifest")
    sessions = identity.get("u8_sessions")
    if not all(isinstance(item, dict) for item in (container, manifest, sessions)):
        return None
    identity_value = {
        "container_path": container.get("path"),
        "container_sha256": container.get("sha256"),
        "structural_manifest_path": manifest.get("path"),
        "structural_manifest_sha256": manifest.get("sha256"),
        "u8_sessions_path": sessions.get("path"),
        "u8_sessions_sha256": sessions.get("sha256"),
        "u8_members_in_order": identity.get("u8_members_in_order"),
        "cutoff_inclusive": identity.get("cutoff_inclusive"),
    }
    return identity_value if identity_value == PROVISIONED_IDENTITY else None


def build_activation(*, gate_raw: bytes, accepted_gate_head_sha: str, hermetic_ci_run_id: int) -> dict[str, Any]:
    """Build canonical activation from gate-owned identity; no path is caller-supplied."""
    gate = json.loads(gate_raw.decode("ascii"))
    identity = _identity_from_gate(gate)
    if identity is None:
        raise ValueError("invalid_gate_identity")
    return {
        "schema_version": ACTIVATION_SCHEMA,
        "gate_id": GATE_ID,
        "gate_sha256": sha(gate_raw),
        "owner_literal": OWNER_LITERAL,
        "accepted_gate_head_sha": accepted_gate_head_sha,
        "hermetic_ci_head_sha": accepted_gate_head_sha,
        "hermetic_ci_run_id": hermetic_ci_run_id,
        "inspector_decision": "ACCEPTED",
        **identity,
        "marker_path": MARKER,
        "validation_seal": SEAL,
    }


def _structural_identity_ok(root: Path, commit: str, gate: dict[str, Any], activation: dict[str, Any]) -> bool:
    identity = _identity_from_gate(gate)
    if identity is None or any(activation.get(key) != value for key, value in identity.items()):
        return False
    manifest_raw = blob(root, commit, identity["structural_manifest_path"])
    sessions_raw = blob(root, commit, identity["u8_sessions_path"])
    if manifest_raw is None or sessions_raw is None or sha(manifest_raw) != identity["structural_manifest_sha256"] or sha(sessions_raw) != identity["u8_sessions_sha256"]:
        return False
    try:
        manifest = json.loads(manifest_raw.decode("ascii"))
        sessions = json.loads(sessions_raw.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return False
    return (
        manifest.get("dataset_reference") == identity["container_path"]
        and manifest.get("dataset_sha256") == identity["container_sha256"]
        and manifest.get("max_session_date") == identity["cutoff_inclusive"]
        and manifest.get("u8_members_in_order") == list(U8)
        and manifest.get("validation_seal") == SEAL
        and sessions.get("dataset_sha256") == identity["container_sha256"]
        and sessions.get("u8_members_in_order") == list(U8)
        and set(sessions.get("session_dates_by_symbol", {})) == set(U8)
    )


def activation_ok(root: Path, commit: str) -> dict[str, Any] | None:
    gate_raw, raw = blob(root, commit, GATE), blob(root, commit, ACTIVATION)
    if gate_raw is None or raw is None:
        return None
    try:
        activation = json.loads(raw.decode("ascii"))
        gate = json.loads(gate_raw.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return None
    accepted = activation.get("accepted_gate_head_sha")
    if set(activation) != ACTIVATION_KEYS or raw != canonical(activation) or not h40(accepted):
        return None
    try:
        expected = build_activation(
            gate_raw=gate_raw,
            accepted_gate_head_sha=accepted,
            hermetic_ci_run_id=activation.get("hermetic_ci_run_id"),
        )
    except (TypeError, ValueError, UnicodeDecodeError):
        return None
    if activation != expected or not all(h64(activation[key]) for key in ("gate_sha256", "container_sha256", "structural_manifest_sha256", "u8_sessions_sha256")):
        return None
    if activation.get("hermetic_ci_head_sha") != accepted or not isinstance(activation.get("hermetic_ci_run_id"), int) or isinstance(activation.get("hermetic_ci_run_id"), bool) or activation["hermetic_ci_run_id"] < 1:
        return None
    if not all(safe_relative(activation[key]) for key in ("container_path", "structural_manifest_path", "u8_sessions_path", "marker_path")):
        return None
    if subprocess.run(["git", "merge-base", "--is-ancestor", accepted, commit], cwd=root, capture_output=True, check=False).returncode:
        return None
    if blob(root, accepted, GATE) != gate_raw or not _structural_identity_ok(root, commit, gate, activation) or not dependencies_ok(root, commit, gate):
        return None
    return activation
