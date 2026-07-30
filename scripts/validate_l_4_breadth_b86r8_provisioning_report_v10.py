"""Closed-world report validator for B8.6R8/v10."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.draft202012_subset import ValidationError, validate as draft
from lib.l4_b86r8_contract_v10 import *
from scripts.run_l_4_breadth_b86r8_provisioning_v10 import accepted_gate

SCHEMA = ROOT / "schemas/l_4_breadth_b86r8_provisioning_report_v10.schema.json"
ACTIVATION_SCHEMA_PATH = ROOT / "schemas/l_4_breadth_b86r8_provisioning_activation_v10.schema.json"
MANIFEST_SCHEMA_PATH = ROOT / "schemas/l_4_breadth_b86r8_falsification_manifest_v10.schema.json"
PAYLOAD_SCHEMA_PATH = ROOT / "schemas/l_4_breadth_b86r8_u8_session_dates_v10.schema.json"

def git_blob(commit, path):
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None

def provenance_ok(value, commit, *, blob_loader=git_blob, gate_check=accepted_gate):
    keys = {"path", "raw_sha256", "content", "activation_checkpoint_head", "accepted_gate_blob_sha256"}
    if not isinstance(value, dict) or set(value) != keys or value.get("path") != ACTIVATION or value.get("activation_checkpoint_head") != commit or not h64(value.get("raw_sha256")) or not h64(value.get("accepted_gate_blob_sha256")): return False
    raw = blob_loader(commit, ACTIVATION)
    if raw is None or raw != canonical(value["content"]) or sha256(raw) != value["raw_sha256"]: return False
    try: draft(json.loads(ACTIVATION_SCHEMA_PATH.read_text("ascii")), value["content"])
    except (OSError, ValueError, ValidationError): return False
    return activation_ok(value["content"], value["accepted_gate_blob_sha256"]) and gate_check(value["content"]["accepted_gate_head_sha"], commit, value["accepted_gate_blob_sha256"])

def output_identities_ok(report, *, root):
    manifest, payload, ids = report.get("manifest"), report.get("payload"), report.get("output_artifacts")
    try: draft(json.loads(MANIFEST_SCHEMA_PATH.read_text("ascii")), manifest); draft(json.loads(PAYLOAD_SCHEMA_PATH.read_text("ascii")), payload)
    except (OSError, ValueError, ValidationError): return False
    if not outputs_ok(manifest, payload) or not isinstance(ids, dict) or set(ids) != {"manifest", "payload"} or report["dataset_artifact"]["complete_raw_sha256"] != manifest["dataset_sha256"] or report["dataset_artifact"]["observed_byte_count"] != manifest["dataset_byte_count"] or report.get("structural_summary_sha256") != sha256(canonical({"manifest": manifest, "payload": payload})): return False
    for name, path, value in (("manifest", MANIFEST, manifest), ("payload", PAYLOAD, payload)):
        raw = canonical(value)
        try: disk = (Path(root) / path).read_bytes()
        except OSError: return False
        if ids.get(name) != {"path": path, "raw_sha256": sha256(raw), "byte_count": len(raw)} or disk != raw: return False
    return True

def validate(report, *, root=ROOT, blob_loader=git_blob, gate_check=accepted_gate):
    blockers = []
    try: draft(json.loads(SCHEMA.read_text("ascii")), report)
    except (OSError, ValueError, ValidationError): blockers.append("schema")
    if not isinstance(report, dict): return {"status": "blocked", "blockers": ["type"]}
    if report.get("access_counters") != {"return_value_decode_count": 0, "validation_access_count": 0} or report.get("validation_seal") != SEAL: blockers.append("contract")
    if report.get("mode") == "synthetic_fixture":
        if report.get("producing_git_commit") != "synthetic_fixture" or report.get("real_provisioning_consumed") or report.get("activation_provenance") is not None or report.get("contract_artifacts") != dependency_identities(root): blockers.append("synthetic")
    elif report.get("mode") == "real_one_shot":
        commit = report.get("producing_git_commit")
        identities = execution_provenance_ok(commit, root, blob_loader)
        if not report.get("real_provisioning_consumed") or identities is None or report.get("contract_artifacts") != identities: blockers.append("execution_provenance")
        elif not provenance_ok(report.get("activation_provenance"), commit, blob_loader=blob_loader, gate_check=gate_check): blockers.append("activation_provenance")
    else: blockers.append("mode")
    if report.get("outcome") == "provisioning_blocked":
        if report.get("blocker") not in BLOCKERS or not row_ok(report.get("dataset_artifact"), report.get("blocker")): blockers.append("blocked")
    elif report.get("outcome") == "structural_provisioned":
        if report.get("mode") != "real_one_shot" or not row_ok(report.get("dataset_artifact")) or not output_identities_ok(report, root=root): blockers.append("outputs")
    else: blockers.append("outcome")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}

def main(argv):
    if len(argv) != 1: return 2
    try: report = json.loads(Path(argv[0]).read_text("ascii"))
    except (OSError, ValueError): return 1
    result = validate(report); print(json.dumps(result)); return result["status"] != "pass"
if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
