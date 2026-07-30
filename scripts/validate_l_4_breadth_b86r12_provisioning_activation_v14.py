"""Future activation validator; it invokes the actual bootstrap preflight."""
from __future__ import annotations

import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = "experiments/l_4_breadth_b86r12_provisioning_gate_v14.json"
ACTIVATION = "experiments/activation_records/l_4_breadth_b86r12_provisioning_activation_v14.json"


def validate(root=ROOT, producing_commit=None):
    root = Path(root).resolve()
    if producing_commit is None:
        import subprocess
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
        producing_commit = result.stdout.strip()
    try:
        gate = json.loads((root / GATE).read_text("ascii"))
        value = json.loads((root / ACTIVATION).read_text("ascii"))
        if value.get("schema_version") != gate.get("activation_schema_version"):
            return {"status": "blocked"}
        bootstrap = importlib.import_module("scripts.run_l_4_breadth_b86r12_committed_bootstrap_v14")
        checked = bootstrap.preflight(root, producing_commit)
        return {"status": "pass" if checked.get("ready") is True else "blocked"}
    except Exception:
        return {"status": "blocked"}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result))
    raise SystemExit(result["status"] != "pass")
