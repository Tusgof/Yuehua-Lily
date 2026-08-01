"""The v4 future-only entry point.  Phase A only ever returns a refusal."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = "experiments/l_4_breadth_b88r3_phase_a_execution_contract_v4.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b88r3_scientific_execution_activation_v4.json"
RUNTIME = "scripts/run_l_4_breadth_b88r3_scientific_execution_v4.py"


def preflight(root: Path | None = None, producing_commit: str | None = None) -> dict:
    root = Path(root or ROOT).resolve()
    if producing_commit is None:
        producing_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if subprocess.run(["git", "diff", "--quiet"], cwd=root, check=False).returncode or subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root, check=False).returncode:
        return {"ready": False, "status": "blocked", "outcome": "dirty_checkout", "real_accessed": False}
    # No import of project execution code, no container path lookup, and no
    # marker creation occurs before a committed canonical activation exists.
    if not (root / ACTIVATION).is_file():
        return {"ready": False, "status": "blocked", "outcome": "canonical_activation_absent", "real_accessed": False}
    from lib.l4_b88r3_lifecycle_v4 import activation_ok
    activation = activation_ok(root, producing_commit)
    if activation is None:
        return {"ready": False, "status": "blocked", "outcome": "refused_activation", "real_accessed": False}
    return {"ready": True, "status": "ready", "outcome": "preflight_ready", "activation": activation, "producing_commit": producing_commit, "real_accessed": False}


def run(root: Path | None = None, producing_commit: str | None = None) -> dict:
    checked = preflight(root, producing_commit)
    if not checked["ready"]:
        return checked
    from scripts.run_l_4_breadth_b88r3_scientific_execution_v4 import run_one_shot
    return run_one_shot(checked, root=Path(root or ROOT).resolve())


if __name__ == "__main__":
    print(json.dumps(preflight(), sort_keys=True)); raise SystemExit(1)
