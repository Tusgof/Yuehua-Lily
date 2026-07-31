"""Gate-owned, future-only B8.8R2 lifecycle helpers.  They never access market data."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = "experiments/l_4_breadth_b88r2_phase_a_execution_contract_v3.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b88r2_scientific_execution_activation_v3.json"
MARKER = "reports/experiments/l_4_breadth_b88r2_one_shot_marker_v3.json"
ACTIVATION_SCHEMA = "lily_l4_b88r2_activation_v3"
OWNER = "B8.8R2 Phase A owner authorization"
GATE_ID = "l_4_breadth_b88r2_phase_a_execution_contract_v3"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
DEPENDENCIES = (GATE, "lib/l4_b88r2_lifecycle_v3.py", "lib/l4_b88r2_scientific_engine_v3.py", "lib/l4_b88r_scientific_engine_v2.py", "lib/l4_b88_scientific_contract_v1.py", "lib/statistics.py", "lib/trend_baseline.py", "scripts/run_l_4_breadth_b88r2_committed_bootstrap_v3.py", "scripts/run_l_4_breadth_b88r2_scientific_execution_v3.py", "scripts/validate_l_4_breadth_b88r2_phase_a_execution_contract_v3.py", "scripts/validate_l_4_breadth_b88r2_scientific_report_v3.py", "scripts/validate_l_4_breadth_b88r2_activation_v3.py", "scripts/validate_l_4_breadth_preregistration_v4.py", "schemas/l_4_breadth_b88r2_activation_v3.schema.json", "schemas/l_4_breadth_b88r2_scientific_report_v3.schema.json", "tests/fixtures/l4_b88r2/synthetic_blocked_report_v3.json", "experiments/l_4_breadth_preregistration_v4.json", "experiments/l_4_breadth_b87_phase_a_capacity_gate_v1.json", "experiments/l_4_breadth_b87_capacity_report_v1.json", "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json", "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json")
ACTIVATION_KEYS = frozenset(("schema_version", "order_id", "hypothesis_id", "gate_id", "gate_sha256", "accepted_gate_head_sha", "hermetic_ci_head_sha", "hermetic_ci_run_id", "inspector_decision", "owner_reference", "scope", "one_shot_marker_path", "validation_seal"))


def sha(raw: bytes | Path) -> str:
    return hashlib.sha256(raw.read_bytes() if isinstance(raw, Path) else raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def h40(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(character in "0123456789abcdef" for character in value)


def blob(root: Path, commit: str, relative: str) -> bytes | None:
    result = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=root, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def dependency_identities(root: Path, commit: str, dependencies: tuple[str, ...] = DEPENDENCIES) -> dict[str, dict[str, str]] | None:
    if not h40(commit): return None
    identities = {}
    for relative in dependencies:
        try: working = (root / relative).read_bytes()
        except OSError: return None
        committed = blob(root, commit, relative)
        if committed is None or working != committed: return None
        identities[relative] = {"path": relative, "sha256": sha(working)}
    return identities


def pre_import_provenance(*, commit: str, dependencies: dict[str, str] | None = None, root: Path = ROOT) -> list[str]:
    """Compatibility-facing diagnosis: actual bootstrap uses dependency_identities."""
    expected = tuple((dependencies or {item: "" for item in DEPENDENCIES}).keys())
    identities = dependency_identities(Path(root).resolve(), commit, expected)
    if identities is None: return ["dirty_or_missing_dependency"]
    return [f"blob_mismatch:{path}" for path, digest in (dependencies or {}).items() if digest and identities[path]["sha256"] != digest]


def build_activation(*, gate: dict, gate_raw: bytes, accepted_gate_head_sha: str, hermetic_ci_run_id: int) -> dict:
    """Only CI/head inputs are caller-supplied; schema, owner, scope and marker are gate-owned."""
    return {"schema_version": gate["activation"]["schema_version"], "order_id": gate["order_id"], "hypothesis_id": gate["hypothesis_id"], "gate_id": gate["gate_id"], "gate_sha256": sha(gate_raw), "accepted_gate_head_sha": accepted_gate_head_sha, "hermetic_ci_head_sha": accepted_gate_head_sha, "hermetic_ci_run_id": hermetic_ci_run_id, "inspector_decision": "ACCEPTED", "owner_reference": gate["activation"]["owner_reference"], "scope": "one_falsification_window_execution_only", "one_shot_marker_path": gate["activation"]["one_shot_marker"], "validation_seal": SEAL}


def gate_and_activation_ok(root: Path, commit: str, identities: dict[str, dict[str, str]]) -> dict | None:
    raw = blob(root, commit, GATE)
    if raw is None: return None
    try: gate = json.loads(raw.decode("ascii")); activation_raw = blob(root, commit, ACTIVATION)
    except (UnicodeDecodeError, ValueError): return None
    if gate.get("gate_id") != GATE_ID or gate.get("execution_dependencies") != list(DEPENDENCIES) or gate.get("execution_binding") != {path: identities[path] for path in DEPENDENCIES if path != GATE}: return None
    if activation_raw is None:
        return None
    try: activation = json.loads(activation_raw.decode("ascii"))
    except (UnicodeDecodeError, ValueError): return None
    if (root / ACTIVATION).read_bytes() != activation_raw or activation_raw != canonical(activation) or set(activation) != ACTIVATION_KEYS: return None
    accepted = activation.get("accepted_gate_head_sha")
    if activation.get("schema_version") != gate["activation"]["schema_version"] or activation.get("order_id") != gate["order_id"] or activation.get("hypothesis_id") != gate["hypothesis_id"] or activation.get("gate_id") != GATE_ID or activation.get("gate_sha256") != sha(raw) or activation.get("owner_reference") != gate["activation"]["owner_reference"] or activation.get("scope") != "one_falsification_window_execution_only" or activation.get("one_shot_marker_path") != gate["activation"]["one_shot_marker"] or activation.get("validation_seal") != SEAL or activation.get("inspector_decision") != "ACCEPTED" or activation.get("hermetic_ci_head_sha") != accepted or not h40(accepted) or not isinstance(activation.get("hermetic_ci_run_id"), int) or isinstance(activation["hermetic_ci_run_id"], bool) or activation["hermetic_ci_run_id"] <= 0: return None
    if subprocess.run(["git", "merge-base", "--is-ancestor", accepted, commit], cwd=root, capture_output=True, check=False).returncode or blob(root, accepted, GATE) != raw: return None
    return {"activation": activation, "activation_raw_sha256": sha(activation_raw), "accepted_gate_blob_sha256": sha(raw)}
