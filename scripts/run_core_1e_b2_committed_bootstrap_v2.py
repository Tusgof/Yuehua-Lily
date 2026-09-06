"""Deny-only project bootstrap for CORE-1E-B2-A-R1.

R1 defines the future E1-shaped lifecycle but authorizes only committed
synthetic machinery.  This project-level entry point must therefore refuse
without resolving an activation or any data path.  The future-shaped path is
tested separately in a temporary Git repository.
"""

from __future__ import annotations

import json


def main() -> int:
    result = {
        "status": "blocked",
        "outcome": "canonical_activation_absent",
        "data_accessed": False,
        "real_data_accessed": False,
        "validation_accessed": False,
        "paths_resolved": [],
        "input_read_count": 0,
        "project_artifacts_created": False,
        "one_shot_consumed": False,
    }
    print(json.dumps(result, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
