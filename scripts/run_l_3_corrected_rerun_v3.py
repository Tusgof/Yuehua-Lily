"""B7.8 fixture-only scanner; it exposes no real-container interface."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests/fixtures/l3_corrected_rerun_v3"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.l3_corrected_rerun_v3 import build_canonical_schedule, scan_synthetic_envelope


def main() -> int:
    parser = argparse.ArgumentParser(description="Run only a committed B7.8 synthetic fixture.")
    parser.add_argument("--synthetic-fixture", type=Path, required=True)
    args = parser.parse_args()
    try:
        fixture = args.synthetic_fixture.resolve(strict=True)
        fixture.relative_to(FIXTURE_ROOT.resolve())
    except (OSError, ValueError):
        print(json.dumps({"status": "blocked", "blockers": ["synthetic_fixture_path_required"]}, sort_keys=True))
        return 1
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    result = scan_synthetic_envelope(payload)
    if result["status"] == "pass":
        result["schedule"] = build_canonical_schedule(result["common_sessions"])
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
