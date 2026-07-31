"""Stdlib-only committed bootstrap.  Project code is unreachable before provenance passes."""
from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

GATE = "experiments/l_4_breadth_b88r2_phase_a_execution_contract_v3.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b88r2_scientific_execution_activation_v3.json"
RUNTIME = "scripts/run_l_4_breadth_b88r2_scientific_execution_v3.py"
GATE_ID = "l_4_breadth_b88r2_phase_a_execution_contract_v3"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
DEPENDENCIES = (GATE, "lib/l4_b88r2_lifecycle_v3.py", "lib/l4_b88r2_scientific_engine_v3.py", "lib/l4_b88r_scientific_engine_v2.py", "lib/l4_b88_scientific_contract_v1.py", "lib/statistics.py", "lib/trend_baseline.py", "scripts/run_l_4_breadth_b88r2_committed_bootstrap_v3.py", RUNTIME, "scripts/validate_l_4_breadth_b88r2_phase_a_execution_contract_v3.py", "scripts/validate_l_4_breadth_b88r2_scientific_report_v3.py", "scripts/validate_l_4_breadth_b88r2_activation_v3.py", "scripts/validate_l_4_breadth_preregistration_v4.py", "schemas/l_4_breadth_b88r2_activation_v3.schema.json", "schemas/l_4_breadth_b88r2_scientific_report_v3.schema.json", "tests/fixtures/l4_b88r2/synthetic_blocked_report_v3.json", "experiments/l_4_breadth_preregistration_v4.json", "experiments/l_4_breadth_b87_phase_a_capacity_gate_v1.json", "experiments/l_4_breadth_b87_capacity_report_v1.json", "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json", "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json")
ACTIVATION_KEYS = {"schema_version", "order_id", "hypothesis_id", "gate_id", "gate_sha256", "accepted_gate_head_sha", "hermetic_ci_head_sha", "hermetic_ci_run_id", "inspector_decision", "owner_reference", "scope", "one_shot_marker_path", "validation_seal"}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
def h40(value): return isinstance(value, str) and len(value) == 40 and all(character in "0123456789abcdef" for character in value)
def blob(root, commit, relative):
    result = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=root, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def identities(root, commit):
    if not h40(commit): return None
    result = {}
    for relative in DEPENDENCIES:
        try: working = (root / relative).read_bytes()
        except OSError: return None
        if blob(root, commit, relative) != working: return None
        result[relative] = {"path": relative, "sha256": sha(working)}
    return result


def preflight(root=None, producing_commit=None):
    """The only route to runtime; checks git-show bytes before imports or activation use."""
    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    if producing_commit is None:
        producing_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    current = identities(root, producing_commit)
    if current is None: return {"ready": False, "status": "blocked", "outcome": "refused_execution_provenance", "real_accessed": False}
    raw = blob(root, producing_commit, GATE)
    try: gate = json.loads(raw.decode("ascii")); activation_raw = blob(root, producing_commit, ACTIVATION)
    except (AttributeError, UnicodeDecodeError, ValueError): return {"ready": False, "status": "blocked", "outcome": "refused_execution_provenance", "real_accessed": False}
    if gate.get("gate_id") != GATE_ID or gate.get("execution_dependencies") != list(DEPENDENCIES) or gate.get("execution_binding") != {path: current[path] for path in DEPENDENCIES if path != GATE}: return {"ready": False, "status": "blocked", "outcome": "refused_execution_provenance", "real_accessed": False}
    if activation_raw is None: return {"ready": False, "status": "blocked", "outcome": "canonical_activation_absent", "real_accessed": False}
    try: activation = json.loads(activation_raw.decode("ascii"))
    except (UnicodeDecodeError, ValueError): return {"ready": False, "status": "blocked", "outcome": "refused_activation", "real_accessed": False}
    accepted = activation.get("accepted_gate_head_sha")
    valid = (root / ACTIVATION).read_bytes() == activation_raw and activation_raw == canonical(activation) and set(activation) == ACTIVATION_KEYS and activation.get("schema_version") == gate.get("activation", {}).get("schema_version") and activation.get("order_id") == gate.get("order_id") and activation.get("hypothesis_id") == gate.get("hypothesis_id") and activation.get("gate_id") == GATE_ID and activation.get("gate_sha256") == sha(raw) and activation.get("owner_reference") == gate.get("activation", {}).get("owner_reference") and activation.get("scope") == "one_falsification_window_execution_only" and activation.get("one_shot_marker_path") == gate.get("activation", {}).get("one_shot_marker") and activation.get("validation_seal") == SEAL and activation.get("inspector_decision") == "ACCEPTED" and activation.get("hermetic_ci_head_sha") == accepted and h40(accepted) and isinstance(activation.get("hermetic_ci_run_id"), int) and not isinstance(activation.get("hermetic_ci_run_id"), bool) and activation["hermetic_ci_run_id"] > 0 and subprocess.run(["git", "merge-base", "--is-ancestor", accepted, producing_commit], cwd=root, capture_output=True, check=False).returncode == 0 and blob(root, accepted, GATE) == raw
    if not valid: return {"ready": False, "status": "blocked", "outcome": "refused_activation", "real_accessed": False}
    return {"ready": True, "status": "ready", "outcome": "preflight_ready", "real_accessed": False, "dependency_identities": current, "activation": activation}


def run(root=None, producing_commit=None):
    checked = preflight(root, producing_commit)
    if not checked["ready"]: return checked
    namespace = runpy.run_path(str(Path(root or Path(__file__).resolve().parents[1]).resolve() / RUNTIME), run_name="lily_after_committed_preflight")
    return namespace["run_one_shot"](checked)


if __name__ == "__main__":
    print(json.dumps(preflight(), sort_keys=True)); raise SystemExit(1)
