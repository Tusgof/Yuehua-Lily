"""Closed-world static validator for a future B8.6R9/v11 report."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.draft202012_subset import ValidationError, validate as draft
from lib.l4_b86r9_contract_v11 import BLOCKERS, REPORT_SCHEMA, SEAL, row_ok
from scripts.run_l_4_breadth_b86r9_committed_bootstrap_v11 import DEPENDENCIES

SCHEMA = ROOT / "schemas/l_4_breadth_b86r9_provisioning_report_v11.schema.json"


def blob(commit: str, path: str) -> bytes | None:
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def provenance_ok(report: dict) -> bool:
    commit = report.get("producing_git_commit")
    artifacts = report.get("contract_artifacts")
    if not isinstance(commit, str) or not isinstance(artifacts, dict) or set(artifacts) != set(DEPENDENCIES):
        return False
    for path in DEPENDENCIES:
        raw = blob(commit, path)
        if raw is None or artifacts.get(path) != {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}:
            return False
    return True


def validate(report: dict) -> dict:
    blockers = []
    try:
        draft(json.loads(SCHEMA.read_text("ascii")), report)
    except (OSError, ValueError, ValidationError):
        blockers.append("schema")
    if not isinstance(report, dict) or report.get("schema_version") != REPORT_SCHEMA or report.get("mode") != "real_one_shot" or not report.get("real_provisioning_consumed") or report.get("access_counters") != {"return_value_decode_count": 0, "validation_access_count": 0} or report.get("validation_seal") != SEAL:
        blockers.append("contract")
    if isinstance(report, dict) and not provenance_ok(report):
        blockers.append("execution_provenance")
    if isinstance(report, dict) and report.get("outcome") == "provisioning_blocked":
        if report.get("blocker") not in BLOCKERS or not row_ok(report.get("dataset_artifact"), report.get("blocker")):
            blockers.append("blocked")
    elif isinstance(report, dict) and report.get("outcome") != "structural_provisioned":
        blockers.append("outcome")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    try:
        report = json.loads(Path(sys.argv[1]).read_text("ascii"))
    except (IndexError, OSError, ValueError):
        raise SystemExit(2)
    result = validate(report); print(json.dumps(result)); raise SystemExit(result["status"] != "pass")
