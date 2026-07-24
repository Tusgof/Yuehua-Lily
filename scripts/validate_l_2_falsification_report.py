from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root

HASH = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
V2_SHA256 = "84a7bb45070b54846a709573506c8213a3bc62d28cfa25f4982415d40d94e1f3"
V3_SHA256 = "507bf40a0a6ac1690ff0c6898bf20dc79c3b8dee78d18251c5835e45d7b60afc"
FALSIFICATION_WINDOW = {"start": "2007-02-05", "end": "2015-12-31"}
SEALED = {"status": "sealed_not_accessed", "prices_opened": False, "returns_opened": False, "signals_opened": False, "positions_opened": False, "regimes_opened": False, "benchmarks_opened": False, "PnL_opened": False}


def validate_report(path: Path) -> dict[str, Any]:
    try:
        report = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"report_unreadable:{exc.__class__.__name__}"])
    blockers: list[str] = []
    for field, expected in {"schema_version": "lily_l2_falsification_report_v1", "order_id": "B6.1", "hypothesis_id": "L-2", "evidence_tier": "E1", "edge_claim": "none", "v2_sha256": V2_SHA256, "v3_sha256": V3_SHA256, "falsification_window": FALSIFICATION_WINDOW, "validation_return_seal": SEALED}.items():
        if report.get(field) != expected:
            blockers.append(f"field_mismatch:{field}")
    if report.get("report_mode") not in {"synthetic_fixture", "falsification_execution"}:
        blockers.append("invalid_report_mode")
    if report.get("execution_status") not in {"not_run", "scope_restricted", "falsified", "not_falsified_not_validated"} or report.get("decision") != report.get("execution_status"):
        blockers.append("execution_status_or_decision_mismatch")
    if not COMMIT.fullmatch(str(report.get("producing_git_commit", ""))) or not HASH.fullmatch(str(report.get("contract_sha256", ""))):
        blockers.append("invalid_provenance_hash")
    if report.get("report_mode") == "synthetic_fixture" and report.get("market_returns_read") is not False:
        blockers.append("synthetic_fixture_must_not_read_market_returns")
    if report.get("execution_status") == "not_run" and report.get("market_returns_read") is not False:
        blockers.append("not_run_must_not_read_market_returns")
    if not isinstance(report.get("blockers"), list) or not report["blockers"]:
        blockers.append("blockers_missing")
    if not isinstance(report.get("claim_limits"), list) or len(report["claim_limits"]) < 3:
        blockers.append("claim_limits_missing")
    return _result(path, blockers)


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "report_path": relative_to_root(path, PROJECT_ROOT)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = validate_report(args.report)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
