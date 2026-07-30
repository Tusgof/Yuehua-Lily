"""Closed-world B8.6R12/v14 report validator."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.l4_b86r12_contract_v14 import ACTIVATION, BLOCKERS, COMMON_REPORT_KEYS, MANIFEST, MARKER, PAYLOAD, REPORT_SCHEMA, SEAL, artifact, canonical, h40, outputs_ok, row_ok, sha256
from scripts.run_l_4_breadth_b86r12_committed_bootstrap_v14 import DEPENDENCIES, GATE, preflight


def blob(commit, path):
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def artifacts_ok(report):
    commit, identities = report.get("producing_git_commit"), report.get("contract_artifacts")
    return h40(commit) and isinstance(identities, dict) and set(identities) == set(DEPENDENCIES) and all((raw := blob(commit, path)) is not None and identities[path] == {"path": path, "sha256": sha256(raw)} for path in DEPENDENCIES)


def activation_ok(report):
    commit = report.get("producing_git_commit")
    if not h40(commit):
        return False
    checked = preflight(ROOT, commit)
    return checked.get("ready") is True and report.get("activation_provenance") == checked["activation"]


def outputs_identity_ok(report, root=ROOT):
    manifest, payload, identities = report.get("manifest"), report.get("payload"), report.get("output_artifacts")
    if not outputs_ok(manifest, payload) or not isinstance(identities, dict) or set(identities) != {"manifest", "payload"} or report["dataset_artifact"].get("complete_raw_sha256") != manifest["dataset_sha256"] or report["dataset_artifact"].get("observed_byte_count") != manifest["dataset_byte_count"] or report.get("structural_summary_sha256") != sha256(canonical({"manifest": manifest, "payload": payload})):
        return False
    for name, path, value in (("manifest", MANIFEST, manifest), ("payload", PAYLOAD, payload)):
        raw = canonical(value)
        try:
            disk = (Path(root) / path).read_bytes()
        except OSError:
            return False
        if identities[name] != {"path": path, "raw_sha256": sha256(raw), "byte_count": len(raw)} or disk != raw:
            return False
    return True


def validate(report, *, root=ROOT):
    blockers = []
    common = isinstance(report, dict) and set(report) >= COMMON_REPORT_KEYS
    if not common or report.get("schema_version") != REPORT_SCHEMA or report.get("order_id") != "B8.6R12" or report.get("hypothesis_id") != "L-4" or report.get("evidence_tier") != "E0" or report.get("edge_claim") != "none" or report.get("dataset_reference") != "data/normalized/l1_yahoo_daily_v1.json" or report.get("expected_dataset_sha256") != "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd" or report.get("access_counters") != {"return_value_decode_count": 0, "validation_access_count": 0} or report.get("validation_seal") != SEAL:
        blockers.append("contract")
    mode, outcome = report.get("mode"), report.get("outcome")
    expected = (COMMON_REPORT_KEYS | {"blocker"}) if outcome == "provisioning_blocked" else (COMMON_REPORT_KEYS | {"manifest", "payload", "output_artifacts", "structural_summary_sha256"}) if mode == "real_one_shot" and outcome == "structural_provisioned" else set()
    if not expected or not isinstance(report, dict) or set(report) != expected:
        blockers.append("closed_world")
    if mode == "synthetic_fixture":
        if outcome != "provisioning_blocked" or report.get("real_provisioning_consumed") is not False or report.get("activation_provenance") is not None or report.get("producing_git_commit") != "synthetic_fixture" or report.get("contract_artifacts") != {}:
            blockers.append("synthetic")
    elif mode == "real_one_shot":
        if report.get("real_provisioning_consumed") is not True or not artifacts_ok(report) or not activation_ok(report):
            blockers.append("provenance")
    else:
        blockers.append("mode")
    if outcome == "provisioning_blocked":
        if report.get("blocker") not in BLOCKERS or not row_ok(report.get("dataset_artifact"), report.get("blocker")):
            blockers.append("blocked")
    elif outcome == "structural_provisioned":
        if mode != "real_one_shot" or not row_ok(report.get("dataset_artifact")) or not outputs_identity_ok(report, root):
            blockers.append("outputs")
    else:
        blockers.append("outcome")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    try:
        value = json.loads(Path(sys.argv[1]).read_text("ascii"))
    except (IndexError, OSError, ValueError):
        raise SystemExit(2)
    result = validate(value)
    print(json.dumps(result))
    raise SystemExit(result["status"] != "pass")
