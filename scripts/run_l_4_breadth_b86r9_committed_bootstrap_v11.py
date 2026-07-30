"""Commit-sourced E0 bootstrap for B8.6R9/v11.

This file is deliberately stdlib-only.  Its production form is executed with
``git show <commit>:scripts/run_l_4_breadth_b86r9_committed_bootstrap_v11.py |
python - ...``; executing its worktree path is refused.
"""
from __future__ import annotations

import hashlib
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

GATE = "experiments/l_4_breadth_b86r9_provisioning_gate_v11.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b86r9_provisioning_activation_v11.json"
RUNTIME = "scripts/run_l_4_breadth_b86r9_provisioning_v11.py"
GATE_ID = "l_4_breadth_b86r9_provisioning_gate_v11"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
DEPENDENCIES = (
    GATE,
    "scripts/run_l_4_breadth_b86r9_committed_bootstrap_v11.py",
    RUNTIME,
    "lib/l4_b86r9_contract_v11.py",
    "lib/l4_b86r8_contract_v10.py",
    "lib/l4_b86r2_provisioning_scanner_v3.py",
    "lib/draft202012_subset.py",
    "scripts/validate_l_4_breadth_b86r9_provisioning_gate_v11.py",
    "scripts/validate_l_4_breadth_b86r9_provisioning_report_v11.py",
    "schemas/l_4_breadth_b86r9_provisioning_activation_v11.schema.json",
    "schemas/l_4_breadth_b86r9_provisioning_report_v11.schema.json",
    "schemas/l_4_breadth_b86r9_falsification_manifest_v11.schema.json",
    "schemas/l_4_breadth_b86r9_u8_session_dates_v11.schema.json",
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def blob(root: Path, commit: str, path: str) -> bytes | None:
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def identities(root: Path, commit: str) -> dict[str, dict[str, str]] | None:
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        return None
    result = {}
    for path in DEPENDENCIES:
        try:
            current = (root / path).read_bytes()
        except OSError:
            return None
        committed = blob(root, commit, path)
        if committed is None or current != committed:
            return None
        result[path] = {"path": path, "sha256": sha256(current)}
    return result


def gate_ok(root: Path, commit: str, current: dict[str, dict[str, str]]) -> tuple[dict, str] | None:
    raw = blob(root, commit, GATE)
    if raw is None:
        return None
    try:
        gate = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return None
    expected = {path: current[path] for path in DEPENDENCIES if path != GATE}
    if not isinstance(gate, dict) or gate.get("gate_id") != GATE_ID or gate.get("execution_dependencies") != list(DEPENDENCIES) or gate.get("source_binding") != expected:
        return None
    return gate, sha256(raw)


def activation_ok(root: Path, commit: str, gate_hash: str) -> dict | None:
    raw = blob(root, commit, ACTIVATION)
    if raw is None:
        return None
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return None
    required = {"schema_version", "gate_id", "gate_sha256", "accepted_gate_head_sha", "hermetic_ci_head_sha", "hermetic_ci_run_id", "inspector_decision", "owner_authorization_reference", "scope", "validation_seal"}
    if set(value) != required or value.get("schema_version") != "lily_l4_b86r9_provisioning_activation_v11" or value.get("gate_id") != GATE_ID or value.get("gate_sha256") != gate_hash or value.get("accepted_gate_head_sha") != value.get("hermetic_ci_head_sha") or value.get("inspector_decision") != "ACCEPTED" or value.get("scope") != "one_repo_relative_falsification_container_provisioning_only" or value.get("validation_seal") != SEAL:
        return None
    return {"raw_sha256": sha256(raw), "content": value}


def run(root: Path, commit: str) -> dict:
    current = identities(root, commit)
    if current is None:
        return {"outcome": "refused_execution_provenance", "dataset_read_count": 0}
    checked = gate_ok(root, commit, current)
    if checked is None:
        return {"outcome": "refused_execution_provenance", "dataset_read_count": 0}
    activation = activation_ok(root, commit, checked[1])
    if activation is None:
        return {"outcome": "refused_activation", "dataset_read_count": 0}
    namespace = runpy.run_path(str(root / RUNTIME), run_name="lily_committed_after_provenance")
    return namespace["run_one_shot"](root=root, commit=commit, dependency_identities=current, activation=activation)


def main(argv: list[str]) -> int:
    if len(argv) != 5 or argv[0] != "--committed-bootstrap" or argv[1] != "--repo-root" or argv[3] != "--producing-commit" or Path(sys.argv[0]).name != "-":
        return 2
    try:
        root = Path(argv[2]).resolve()
    except OSError:
        return 2
    return 0 if run(root, argv[4]).get("outcome") == "structural_provisioned" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
