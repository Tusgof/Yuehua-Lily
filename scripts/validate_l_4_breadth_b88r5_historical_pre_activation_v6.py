"""Prove historical B8.8R5 denial through preflight only.

The frozen accepted-gate commit predates the canonical activation record.  This
validator imports the activation-capable module only to call ``preflight``;
production ``run``/``run_one_shot`` entry points are never called.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_COMMIT = "fc727d78fc38a70e7bef7c85fb22d3e8fe2c7006"


def validate(root: Path = ROOT) -> dict[str, object]:
    root = Path(root).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from scripts import run_l_4_breadth_b88r5_committed_bootstrap_v6 as bootstrap

        checked = bootstrap.preflight(root, HISTORICAL_COMMIT)
    except (ImportError, OSError, ValueError) as exc:
        return {
            "status": "blocked",
            "outcome": "validator_unavailable",
            "ready": False,
            "real_accessed": False,
            "blockers": [type(exc).__name__],
        }
    expected = {
        "status": "blocked",
        "outcome": "refused_activation",
        "ready": False,
        "real_accessed": False,
    }
    blockers = []
    for key, value in expected.items():
        if checked.get(key) != value:
            blockers.append(f"{key}_mismatch")
    return {
        "status": "pass" if not blockers else "blocked",
        "outcome": checked.get("outcome"),
        "ready": checked.get("ready"),
        "real_accessed": checked.get("real_accessed"),
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate historical B8.8R5 pre-activation denial safely.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = validate(args.root)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
