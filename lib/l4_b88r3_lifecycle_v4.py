"""Gate-owned v4 activation and immutable provenance helpers; no data I/O."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE = "experiments/l_4_breadth_b88r3_phase_a_execution_contract_v4.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b88r3_scientific_execution_activation_v4.json"
MARKER = "reports/experiments/l_4_breadth_b88r3_one_shot_marker_v4.json"
OWNER_LITERAL = "continue the work till we complete L4"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
ACTIVATION_KEYS = frozenset(("schema_version", "gate_id", "gate_sha256", "owner_literal", "accepted_gate_head_sha", "hermetic_ci_head_sha", "hermetic_ci_run_id", "inspector_decision", "container_path", "container_sha256", "structural_manifest_path", "structural_manifest_sha256", "u8_sessions_sha256", "cutoff_inclusive", "marker_path", "validation_seal"))


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
    """Every executable/schema byte used by future execution is gate-bound."""
    paths, binding = gate.get("execution_dependencies"), gate.get("execution_binding")
    if not isinstance(paths, list) or not paths or not isinstance(binding, dict) or set(paths) != set(binding):
        return False
    for relative in paths:
        item = binding.get(relative)
        raw = blob(root, commit, relative)
        if not isinstance(relative, str) or not isinstance(item, dict) or item != {"path": relative, "sha256": item.get("sha256")} or not h64(item.get("sha256")) or raw is None or sha(raw) != item["sha256"]:
            return False
    return True


def clean_checkout(root: Path) -> bool:
    return all(subprocess.run(["git", "diff", "--quiet", *args], cwd=root, capture_output=True, check=False).returncode == 0 for args in ((), ("--cached",)))


def build_activation(*, gate_raw: bytes, accepted_gate_head_sha: str, hermetic_ci_run_id: int, container_path: str, container_sha256: str, structural_manifest_path: str, structural_manifest_sha256: str, u8_sessions_sha256: str) -> dict[str, Any]:
    """Schema, owner literal, gate identity and marker are not caller inputs."""
    return {"schema_version": "lily_l4_b88r3_activation_v4", "gate_id": "l_4_breadth_b88r3_phase_a_execution_contract_v4", "gate_sha256": sha(gate_raw), "owner_literal": OWNER_LITERAL, "accepted_gate_head_sha": accepted_gate_head_sha, "hermetic_ci_head_sha": accepted_gate_head_sha, "hermetic_ci_run_id": hermetic_ci_run_id, "inspector_decision": "ACCEPTED", "container_path": container_path, "container_sha256": container_sha256, "structural_manifest_path": structural_manifest_path, "structural_manifest_sha256": structural_manifest_sha256, "u8_sessions_sha256": u8_sessions_sha256, "cutoff_inclusive": "2015-12-31", "marker_path": MARKER, "validation_seal": SEAL}


def activation_ok(root: Path, commit: str) -> dict[str, Any] | None:
    raw_gate, raw = blob(root, commit, GATE), blob(root, commit, ACTIVATION)
    if raw_gate is None or raw is None:
        return None
    try:
        activation = json.loads(raw.decode("ascii")); gate = json.loads(raw_gate.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return None
    accepted = activation.get("accepted_gate_head_sha")
    if not clean_checkout(root) or set(activation) != ACTIVATION_KEYS or raw != canonical(activation) or not h40(accepted):
        return None
    expected = build_activation(gate_raw=raw_gate, accepted_gate_head_sha=accepted, hermetic_ci_run_id=activation.get("hermetic_ci_run_id"), container_path=activation.get("container_path"), container_sha256=activation.get("container_sha256"), structural_manifest_path=activation.get("structural_manifest_path"), structural_manifest_sha256=activation.get("structural_manifest_sha256"), u8_sessions_sha256=activation.get("u8_sessions_sha256"))
    if activation != expected or gate.get("owner_literal") != OWNER_LITERAL or not all(h64(activation[key]) for key in ("container_sha256", "structural_manifest_sha256", "u8_sessions_sha256")) or not all(safe_relative(activation[key]) for key in ("container_path", "structural_manifest_path", "marker_path")):
        return None
    if activation.get("hermetic_ci_head_sha") != accepted or not isinstance(activation.get("hermetic_ci_run_id"), int) or activation["hermetic_ci_run_id"] < 1:
        return None
    if subprocess.run(["git", "merge-base", "--is-ancestor", accepted, commit], cwd=root, capture_output=True, check=False).returncode or blob(root, accepted, GATE) != raw_gate or not dependencies_ok(root, commit, gate):
        return None
    return activation
