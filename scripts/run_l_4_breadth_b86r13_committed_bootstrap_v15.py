"""Stdlib-only v15 committed bootstrap; project code imports only after preflight."""
from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

GATE = "experiments/l_4_breadth_b86r13_provisioning_gate_v15.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b86r13_provisioning_activation_v15.json"
RUNTIME = "scripts/run_l_4_breadth_b86r13_provisioning_v15.py"
GATE_ID = "l_4_breadth_b86r13_provisioning_gate_v15"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
DEPENDENCIES = (GATE, "scripts/run_l_4_breadth_b86r13_committed_bootstrap_v15.py", RUNTIME, "lib/l4_b86r13_contract_v15.py", "lib/l4_b86r2_provisioning_scanner_v3.py", "lib/draft202012_subset.py", "scripts/validate_l_4_breadth_b86r13_provisioning_gate_v15.py", "scripts/validate_l_4_breadth_b86r13_provisioning_report_v15.py", "scripts/validate_l_4_breadth_b86r13_provisioning_activation_v15.py", "schemas/l_4_breadth_b86r13_provisioning_activation_v15.schema.json", "schemas/l_4_breadth_b86r13_provisioning_report_v15.schema.json", "schemas/l_4_breadth_b86r13_falsification_manifest_v15.schema.json", "schemas/l_4_breadth_b86r13_u8_session_dates_v15.schema.json")
ACTIVATION_KEYS = {"schema_version", "gate_id", "gate_sha256", "accepted_gate_head_sha", "hermetic_ci_head_sha", "hermetic_ci_run_id", "inspector_decision", "owner_authorization_reference", "scope", "validation_seal"}


def sha256(raw): return hashlib.sha256(raw).hexdigest()
def h40(value): return isinstance(value, str) and len(value) == 40 and all(item in "0123456789abcdef" for item in value)
def h64(value): return isinstance(value, str) and len(value) == 64 and all(item in "0123456789abcdef" for item in value)
def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def blob(root, commit, path):
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def identities(root, commit):
    if not h40(commit): return None
    current = {}
    for path in DEPENDENCIES:
        try: working = (root / path).read_bytes()
        except OSError: return None
        committed = blob(root, commit, path)
        if committed is None or working != committed: return None
        current[path] = {"path": path, "sha256": sha256(working)}
    return current


def gate_ok(root, commit, current):
    raw = blob(root, commit, GATE)
    if raw is None: return None
    try: gate = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, ValueError): return None
    expected = {path: current[path] for path in DEPENDENCIES if path != GATE}
    if gate.get("gate_id") != GATE_ID or gate.get("execution_dependencies") != list(DEPENDENCIES) or gate.get("execution_binding") != expected or not isinstance(gate.get("activation_schema_version"), str) or not gate["activation_schema_version"] or not isinstance(gate.get("required_owner_authorization_reference"), str) or not gate["required_owner_authorization_reference"]:
        return None
    return raw, gate


def activation_ok(root, commit, gate_raw, gate):
    raw = blob(root, commit, ACTIVATION)
    if raw is None: return None
    try:
        if (root / ACTIVATION).read_bytes() != raw: return None
        value = json.loads(raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, ValueError): return None
    accepted = value.get("accepted_gate_head_sha")
    if raw != canonical(value) or set(value) != ACTIVATION_KEYS or value.get("schema_version") != gate["activation_schema_version"] or value.get("owner_authorization_reference") != gate["required_owner_authorization_reference"] or value.get("gate_id") != GATE_ID or value.get("gate_sha256") != sha256(gate_raw) or not h64(value.get("gate_sha256")) or not h40(accepted) or value.get("hermetic_ci_head_sha") != accepted or not isinstance(value.get("hermetic_ci_run_id"), int) or isinstance(value.get("hermetic_ci_run_id"), bool) or value["hermetic_ci_run_id"] <= 0 or value.get("inspector_decision") != "ACCEPTED" or value.get("scope") != "one_repo_relative_falsification_container_provisioning_only" or value.get("validation_seal") != SEAL:
        return None
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", accepted, commit], cwd=root, capture_output=True, check=False)
    if ancestor.returncode != 0 or blob(root, accepted, GATE) != gate_raw: return None
    return {"path": ACTIVATION, "raw_sha256": sha256(raw), "content": value, "activation_checkpoint_head": commit, "accepted_gate_blob_sha256": sha256(gate_raw)}


def preflight(root, producing_commit):
    """The sole preflight path, before any project import, marker or data access."""
    root = Path(root).resolve(); current = identities(root, producing_commit)
    if current is None: return {"ready": False, "outcome": "refused_execution_provenance", "dataset_read_count": 0}
    resolved_gate = gate_ok(root, producing_commit, current)
    if resolved_gate is None: return {"ready": False, "outcome": "refused_execution_provenance", "dataset_read_count": 0}
    raw, gate = resolved_gate; activation = activation_ok(root, producing_commit, raw, gate)
    if activation is None: return {"ready": False, "outcome": "refused_activation", "dataset_read_count": 0}
    return {"ready": True, "outcome": "preflight_ready", "dataset_read_count": 0, "dependency_identities": current, "activation": activation}


def run(root, commit):
    checked = preflight(root, commit)
    if not checked["ready"]: return checked
    namespace = runpy.run_path(str(Path(root).resolve() / RUNTIME), run_name="lily_committed_after_preflight")
    return namespace["run_one_shot"](root=Path(root).resolve(), commit=commit, dependency_identities=checked["dependency_identities"], activation=checked["activation"])


def main(argv):
    if len(argv) != 5 or argv[:2] != ["--committed-bootstrap", "--repo-root"] or argv[3] != "--producing-commit" or Path(sys.argv[0]).name != "-": return 2
    return 0 if run(Path(argv[2]), argv[4]).get("outcome") == "structural_provisioned" else 1


if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
