"""Future activation validator.  It invokes the exact stdlib committed preflight."""
from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVATION = "experiments/activation_records/l_4_breadth_b88r2_scientific_execution_activation_v3.json"


def validate(root: Path = ROOT, producing_commit: str | None = None) -> dict:
    root = Path(root).resolve()
    if producing_commit is None: producing_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    boot = importlib.import_module("scripts.run_l_4_breadth_b88r2_committed_bootstrap_v3")
    try: clean = (root / ACTIVATION).read_bytes() == boot.blob(root, producing_commit, ACTIVATION)
    except OSError: clean = False
    checked = boot.preflight(root, producing_commit)
    return {"status": "pass" if clean and checked.get("ready") else "blocked", "outcome": checked.get("outcome")}


if __name__ == "__main__":
    result = validate(); print(result); raise SystemExit(result["status"] != "pass")
