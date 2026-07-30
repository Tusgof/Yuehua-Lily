"""Future checkpoint validator: raw worktree activation must equal its commit blob."""
from __future__ import annotations
import importlib, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ACTIVATION = "experiments/activation_records/l_4_breadth_b86r13_provisioning_activation_v15.json"
def validate(root=ROOT, producing_commit=None):
    root = Path(root).resolve()
    if producing_commit is None: producing_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    boot = importlib.import_module("scripts.run_l_4_breadth_b86r13_committed_bootstrap_v15")
    try:
        clean = (root / ACTIVATION).read_bytes() == boot.blob(root, producing_commit, ACTIVATION)
    except OSError:
        clean = False
    return {"status": "pass" if clean and boot.preflight(root, producing_commit).get("ready") else "blocked"}
