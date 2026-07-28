"""Closed-world semantic validator for B8.6R6/v8 reports."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.draft202012_subset import ValidationError, validate as draft
from lib.l4_b86r6_contract_v8 import *
from scripts.run_l_4_breadth_b86r6_provisioning_v8 import CONTRACT, accepted_gate, canonical, identities

SCHEMA = ROOT / "schemas/l_4_breadth_b86r6_provisioning_report_v8.schema.json"
ACTIVATION_SCHEMA_PATH = ROOT / "schemas/l_4_breadth_b86r6_provisioning_activation_v8.schema.json"

def git_blob(commit, path):
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None

def row_ok(row, blocker):
    keys = set(artifact())
    if not isinstance(row, dict) or set(row) != keys or row.get("return_value_decode_count") != 0: return False
    if blocker in {"dataset_missing", "dataset_read_error"}:
        return row == artifact() | {"attempted_read_count": 1}
    if blocker == "dataset_input_over_limit":
        return row["attempted_read_count"] == row["read_count"] == row["hash_count"] == 1 and row["observed_byte_count"] == 32 * 1024 * 1024 + 1 and not row["complete_read"] and isinstance(row["bounded_prefix_sha256"], str) and row["scan_count"] == 0
    return row["attempted_read_count"] == row["read_count"] == row["hash_count"] == row["scan_count"] == 1 and row["complete_read"] and isinstance(row["complete_raw_sha256"], str) and row["bounded_prefix_sha256"] == row["complete_raw_sha256"]

def provenance_ok(value, commit, *, blob_loader=git_blob, gate_check=accepted_gate):
    if not isinstance(value, dict) or set(value) != {"path", "raw_sha256", "content", "activation_checkpoint_head"} or value.get("path") != ACTIVATION or value.get("activation_checkpoint_head") != commit: return False
    raw = blob_loader(commit, ACTIVATION)
    if raw is None or raw != canonical(value["content"]) or hashlib.sha256(raw).hexdigest() != value.get("raw_sha256"): return False
    try: draft(json.loads(ACTIVATION_SCHEMA_PATH.read_text("ascii")), value["content"])
    except (OSError, ValueError, ValidationError): return False
    content = value["content"]
    return content["accepted_gate_head_sha"] == content["hermetic_ci_head_sha"] and gate_check(content["accepted_gate_head_sha"], commit, content["gate_sha256"])

def validate(report, *, root=ROOT, blob_loader=git_blob, gate_check=accepted_gate):
    blockers = []
    try: draft(json.loads(SCHEMA.read_text("ascii")), report)
    except (OSError, ValueError, ValidationError): blockers.append("schema")
    if not isinstance(report, dict): return {"status": "blocked", "blockers": ["type"]}
    if report.get("contract_artifacts") != identities(root) or report.get("access_counters") != {"return_value_decode_count": 0, "validation_access_count": 0} or report.get("validation_seal") != SEAL: blockers.append("contract")
    mode = report.get("mode")
    if mode == "synthetic_fixture":
        if report.get("producing_git_commit") != "synthetic_fixture" or report.get("real_provisioning_consumed") or report.get("activation_provenance") is not None: blockers.append("mode")
    elif mode == "real_one_shot":
        if not report.get("real_provisioning_consumed") or not provenance_ok(report.get("activation_provenance"), report.get("producing_git_commit"), blob_loader=blob_loader, gate_check=gate_check): blockers.append("provenance")
    else: blockers.append("mode")
    if report.get("outcome") == "provisioning_blocked":
        if report.get("blocker") not in BLOCKERS or not row_ok(report.get("dataset_artifact"), report.get("blocker")): blockers.append("blocked")
    elif report.get("outcome") == "structural_provisioned":
        manifest, payload, artifacts = report.get("manifest"), report.get("payload"), report.get("output_artifacts")
        if not row_ok(report.get("dataset_artifact"), "dataset_hash_mismatch") or not validate_outputs(manifest, payload) or set(artifacts or ()) != {"manifest", "payload"}: blockers.append("outputs")
        else:
            if report["dataset_artifact"]["complete_raw_sha256"] != manifest["dataset_sha256"] or report["dataset_artifact"]["observed_byte_count"] != manifest["dataset_byte_count"] or report.get("structural_summary_sha256") != hashlib.sha256(canonical({"manifest": manifest, "payload": payload})).hexdigest(): blockers.append("binding")
            for name, rel, value in (("manifest", MANIFEST, manifest), ("payload", PAYLOAD, payload)):
                raw = canonical(value); expected = {"path": rel, "raw_sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}
                if artifacts.get(name) != expected: blockers.append("identity")
                elif mode == "real_one_shot":
                    try: disk = (root / rel).read_bytes()
                    except OSError: disk = None
                    if disk != raw: blockers.append("disk")
    else: blockers.append("outcome")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}

def main(argv):
    if len(argv) != 1: return 2
    try: report = json.loads(Path(argv[0]).read_text("ascii"))
    except (OSError, ValueError): return 1
    result = validate(report); print(json.dumps(result)); return result["status"] != "pass"

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
