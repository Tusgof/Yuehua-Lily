"""Closed-world semantic validator for B8.6R7/v9 provisioning reports."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.draft202012_subset import ValidationError, validate as draft
from lib.l4_b86r7_contract_v9 import *
from scripts.run_l_4_breadth_b86r7_provisioning_v9 import CONTRACT, accepted_gate, identities

SCHEMA = ROOT / "schemas/l_4_breadth_b86r7_provisioning_report_v9.schema.json"
ACTIVATION_SCHEMA_PATH = ROOT / "schemas/l_4_breadth_b86r7_provisioning_activation_v9.schema.json"
MANIFEST_SCHEMA_PATH = ROOT / "schemas/l_4_breadth_b86r7_falsification_manifest_v9.schema.json"
PAYLOAD_SCHEMA_PATH = ROOT / "schemas/l_4_breadth_b86r7_u8_session_dates_v9.schema.json"


def git_blob(commit, path):
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def provenance_ok(value, commit, *, blob_loader=git_blob, gate_check=accepted_gate):
    required = {"path", "raw_sha256", "content", "activation_checkpoint_head", "accepted_gate_blob_sha256"}
    if not isinstance(value, dict) or set(value) != required or value.get("path") != ACTIVATION or value.get("activation_checkpoint_head") != commit:
        return False
    if not h64(value.get("raw_sha256")) or not h64(value.get("accepted_gate_blob_sha256")):
        return False
    raw = blob_loader(commit, ACTIVATION)
    if raw is None or raw != canonical(value["content"]) or sha256(raw) != value["raw_sha256"]:
        return False
    try:
        draft(json.loads(ACTIVATION_SCHEMA_PATH.read_text("ascii")), value["content"])
    except (OSError, ValueError, ValidationError):
        return False
    activation = value["content"]
    return (
        activation_ok(activation, value["accepted_gate_blob_sha256"])
        and gate_check(activation["accepted_gate_head_sha"], commit, value["accepted_gate_blob_sha256"])
    )


def output_identities_ok(report, *, root):
    manifest, payload, identities_row = report.get("manifest"), report.get("payload"), report.get("output_artifacts")
    try:
        draft(json.loads(MANIFEST_SCHEMA_PATH.read_text("ascii")), manifest)
        draft(json.loads(PAYLOAD_SCHEMA_PATH.read_text("ascii")), payload)
    except (OSError, ValueError, ValidationError):
        return False
    if not outputs_ok(manifest, payload) or not isinstance(identities_row, dict) or set(identities_row) != {"manifest", "payload"}:
        return False
    if report["dataset_artifact"]["complete_raw_sha256"] != manifest["dataset_sha256"] or report["dataset_artifact"]["observed_byte_count"] != manifest["dataset_byte_count"]:
        return False
    if report.get("structural_summary_sha256") != sha256(canonical({"manifest": manifest, "payload": payload})):
        return False
    for name, path, value in (("manifest", MANIFEST, manifest), ("payload", PAYLOAD, payload)):
        raw = canonical(value)
        if identities_row.get(name) != {"path": path, "raw_sha256": sha256(raw), "byte_count": len(raw)}:
            return False
        try:
            disk = (root / path).read_bytes()
        except OSError:
            return False
        if disk != raw:
            return False
    return True


def validate(report, *, root=ROOT, blob_loader=git_blob, gate_check=accepted_gate):
    blockers = []
    try:
        draft(json.loads(SCHEMA.read_text("ascii")), report)
    except (OSError, ValueError, ValidationError):
        blockers.append("schema")
    if not isinstance(report, dict):
        return {"status": "blocked", "blockers": ["type"]}
    if report.get("contract_artifacts") != identities(root) or report.get("access_counters") != {"return_value_decode_count": 0, "validation_access_count": 0} or report.get("validation_seal") != SEAL:
        blockers.append("contract")
    if report.get("mode") == "synthetic_fixture":
        if report.get("producing_git_commit") != "synthetic_fixture" or report.get("real_provisioning_consumed") or report.get("activation_provenance") is not None:
            blockers.append("mode")
    elif report.get("mode") == "real_one_shot":
        if not report.get("real_provisioning_consumed"):
            blockers.append("mode")
        elif not provenance_ok(report.get("activation_provenance"), report.get("producing_git_commit"), blob_loader=blob_loader, gate_check=gate_check):
            blockers.append("provenance")
    else:
        blockers.append("mode")
    outcome = report.get("outcome")
    if outcome == "provisioning_blocked":
        if report.get("blocker") not in BLOCKERS or not row_ok(report.get("dataset_artifact"), report.get("blocker")):
            blockers.append("blocked")
    elif outcome == "structural_provisioned":
        if report.get("mode") != "real_one_shot" or not row_ok(report.get("dataset_artifact")) or not output_identities_ok(report, root=root):
            blockers.append("outputs")
    else:
        blockers.append("outcome")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


def main(argv):
    if len(argv) != 1:
        return 2
    try:
        report = json.loads(Path(argv[0]).read_text("ascii"))
    except (OSError, ValueError):
        return 1
    result = validate(report); print(json.dumps(result)); return result["status"] != "pass"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
