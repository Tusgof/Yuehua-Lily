"""Stdlib-only B8.8R5/v6 committed bootstrap.

The bootstrap refuses any dirty or untracked checkout before the one-shot
marker can be claimed.  It does not import project code until gate-owned
runtime bytes, activation, and the provisioned structural identities pass.
"""
from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

GATE = "experiments/l_4_breadth_b88r5_phase_a_execution_contract_v6.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b88r5_scientific_execution_activation_v6.json"
RUNTIME = "scripts/run_l_4_breadth_b88r5_scientific_execution_v6.py"
GATE_ID = "l_4_breadth_b88r5_phase_a_execution_contract_v6"
ACTIVATION_SCHEMA = "lily_l4_b88r5_activation_v6"
OWNER_LITERAL = "continue the work till we complete L4"
MARKER = "reports/experiments/l_4_breadth_b88r5_one_shot_marker_v6.json"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
ACTIVATION_KEYS = {
    "schema_version", "gate_id", "gate_sha256", "owner_literal",
    "accepted_gate_head_sha", "hermetic_ci_head_sha", "hermetic_ci_run_id",
    "inspector_decision", "container_path", "container_sha256",
    "structural_manifest_path", "structural_manifest_sha256",
    "u8_sessions_path", "u8_sessions_sha256", "u8_members_in_order",
    "cutoff_inclusive", "marker_path", "validation_seal",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def h40(value):
    return isinstance(value, str) and len(value) == 40 and all(item in "0123456789abcdef" for item in value)


def h64(value):
    return isinstance(value, str) and len(value) == 64 and all(item in "0123456789abcdef" for item in value)


def safe_relative(value):
    path = Path(value) if isinstance(value, str) else None
    return path is not None and not path.is_absolute() and ".." not in path.parts and str(path).replace("\\", "/") == value


def blob(root, commit, path):
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def clean_checkout(root):
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout == b""


def _gate_and_dependencies(root, commit):
    raw = blob(root, commit, GATE)
    try:
        if raw is None or (root / GATE).read_bytes() != raw:
            return None
        gate = json.loads(raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    paths, binding = gate.get("execution_dependencies"), gate.get("execution_binding")
    if gate.get("gate_id") != GATE_ID or not isinstance(paths, list) or not paths or not isinstance(binding, dict) or set(paths) != set(binding):
        return None
    identities = {}
    for path in paths:
        try:
            working = (root / path).read_bytes()
        except OSError:
            return None
        committed = blob(root, commit, path)
        expected = {"path": path, "sha256": sha256(working)}
        if not isinstance(path, str) or committed is None or working != committed or binding.get(path) != expected:
            return None
        identities[path] = expected["sha256"]
    return raw, gate, identities


def _identity(gate):
    value = gate.get("provisioned_identity")
    if not isinstance(value, dict):
        return None
    container, manifest, sessions = value.get("container"), value.get("structural_manifest"), value.get("u8_sessions")
    if not all(isinstance(item, dict) for item in (container, manifest, sessions)):
        return None
    return {
        "container_path": container.get("path"),
        "container_sha256": container.get("sha256"),
        "structural_manifest_path": manifest.get("path"),
        "structural_manifest_sha256": manifest.get("sha256"),
        "u8_sessions_path": sessions.get("path"),
        "u8_sessions_sha256": sessions.get("sha256"),
        "u8_members_in_order": value.get("u8_members_in_order"),
        "cutoff_inclusive": value.get("cutoff_inclusive"),
    }


def _activation(root, commit, gate_raw, gate):
    raw = blob(root, commit, ACTIVATION)
    try:
        if raw is None or (root / ACTIVATION).read_bytes() != raw:
            return None
        value = json.loads(raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    identity = _identity(gate)
    accepted = value.get("accepted_gate_head_sha")
    if identity is None:
        return None
    expected = {
        "schema_version": ACTIVATION_SCHEMA,
        "gate_id": GATE_ID,
        "gate_sha256": sha256(gate_raw),
        "owner_literal": OWNER_LITERAL,
        "accepted_gate_head_sha": accepted,
        "hermetic_ci_head_sha": accepted,
        "hermetic_ci_run_id": value.get("hermetic_ci_run_id"),
        "inspector_decision": "ACCEPTED",
        **identity,
        "marker_path": MARKER,
        "validation_seal": SEAL,
    }
    if set(value) != ACTIVATION_KEYS or raw != canonical(value) or value != expected:
        return None
    if not h40(accepted) or not all(h64(value[key]) for key in ("gate_sha256", "container_sha256", "structural_manifest_sha256", "u8_sessions_sha256")):
        return None
    if not isinstance(value["hermetic_ci_run_id"], int) or isinstance(value["hermetic_ci_run_id"], bool) or value["hermetic_ci_run_id"] < 1:
        return None
    if not all(safe_relative(value[key]) for key in ("container_path", "structural_manifest_path", "u8_sessions_path", "marker_path")):
        return None
    if subprocess.run(["git", "merge-base", "--is-ancestor", accepted, commit], cwd=root, capture_output=True, check=False).returncode != 0:
        return None
    if blob(root, accepted, GATE) != gate_raw:
        return None
    return value


def preflight(root=None, producing_commit=None):
    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    if producing_commit is None:
        producing_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if not h40(producing_commit):
        return {"ready": False, "status": "blocked", "outcome": "refused_commit", "real_accessed": False}
    resolved = _gate_and_dependencies(root, producing_commit)
    if resolved is None:
        return {"ready": False, "status": "blocked", "outcome": "refused_execution_provenance", "real_accessed": False}
    gate_raw, gate, identities = resolved
    if not clean_checkout(root):
        return {"ready": False, "status": "blocked", "outcome": "dirty_checkout", "real_accessed": False}
    activation = _activation(root, producing_commit, gate_raw, gate)
    if activation is None:
        return {"ready": False, "status": "blocked", "outcome": "refused_activation", "real_accessed": False}
    outputs = (
        "reports/experiments/l_4_breadth_b88r5_scientific_report_v6.json",
        "reports/experiments/l_4_breadth_b88r5_execution_ledger_v6.json",
        "reports/experiments/l_4_breadth_b88r5_execution_attempt_v6.json",
        activation["marker_path"],
    )
    if any((root / path).exists() for path in outputs):
        return {"ready": False, "status": "blocked", "outcome": "refused_prior_invocation", "real_accessed": False}
    return {
        "ready": True,
        "status": "ready",
        "outcome": "preflight_ready",
        "activation": activation,
        "producing_commit": producing_commit,
        "runtime_dependency_identities": identities,
        "real_accessed": False,
    }


def run(root=None, producing_commit=None):
    checked = preflight(root, producing_commit)
    if not checked["ready"]:
        return checked
    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    namespace = runpy.run_path(str(root / RUNTIME), run_name="lily_b88r5_committed_after_preflight")
    return namespace["run_one_shot"](checked, root=root)


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result.get("status") == "complete" else 1)
