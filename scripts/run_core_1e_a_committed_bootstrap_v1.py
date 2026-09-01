"""Deny-only Phase-A bootstrap; no dataset/container path is resolved here."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVATION = ROOT / "experiments" / "activation_records" / "core_1e_a_activation_v1.json"


def main() -> int:
    if ACTIVATION.is_file():
        outcome = "phase_a_activation_requires_separate_approved_future_runner"
    else:
        outcome = "canonical_activation_absent"
    result = {
        "status": "blocked",
        "outcome": outcome,
        "data_accessed": False,
        "real_data_accessed": False,
        "validation_accessed": False,
        "paths_resolved": [],
        "one_shot_consumed": False,
    }
    print(json.dumps(result, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
