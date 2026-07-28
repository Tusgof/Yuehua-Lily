"""E0-only v5 runner guard: it has no execution or path acceptance surface."""
from __future__ import annotations

import subprocess
from pathlib import Path


def guard_workspace_clean(root: Path) -> bool:
    """Return true only for a clean index and worktree; never accepts a data path."""
    result = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=False)
    return result.returncode == 0 and result.stdout == ""


def run_synthetic(*args: object, **kwargs: object) -> int:
    """Fail closed: v5 cannot execute any preflight, synthetic or real."""
    if args or kwargs:
        return 2
    return 2


def main() -> int:
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
