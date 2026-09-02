"""Deny-only project bootstrap for CORE-1E-B2-A.

This milestone never creates or discovers an activation.  The future
temporary-Git lifecycle is intentionally separate and is exercised only by
synthetic tests.
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
