"""E0-only v6 runner guard with the required shared-lib dependency."""
from __future__ import annotations

import subprocess
from pathlib import Path

from lib.l3_b714_date_only_scanner_v6 import enforce_weekly_pair_ceiling


def guard_workspace_clean(root: Path) -> bool:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=False)
    return result.returncode == 0 and result.stdout == ""


def run_synthetic(*args: object, **kwargs: object) -> int:
    enforce_weekly_pair_ceiling(0)
    return 2


def main() -> int:
    return run_synthetic()


if __name__ == "__main__":
    raise SystemExit(main())
