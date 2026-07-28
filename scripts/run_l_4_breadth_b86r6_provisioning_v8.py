"""B8.6R6/v8 one-shot runner; production needs a later accepted activation record."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.l4_b86r6_contract_v8 import *

CONTRACT = {
    "gate": GATE_PATH, "runner": "scripts/run_l_4_breadth_b86r6_provisioning_v8.py",
    "contract": "lib/l4_b86r6_contract_v8.py", "report_schema": "schemas/l_4_breadth_b86r6_provisioning_report_v8.schema.json",
    "activation_schema": "schemas/l_4_breadth_b86r6_provisioning_activation_v8.schema.json",
    "manifest_schema": "schemas/l_4_breadth_b86r6_falsification_manifest_v8.schema.json",
    "payload_schema": "schemas/l_4_breadth_b86r6_u8_session_dates_v8.schema.json",
    "report_validator": "scripts/validate_l_4_breadth_b86r6_provisioning_report_v8.py",
}

def identities(root=ROOT):
    return {name: {"path": path, "sha256": hashlib.sha256((root / path).read_bytes()).hexdigest()} for name, path in CONTRACT.items()}

def git_blob(commit, path):
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None

def git_head(root=ROOT):
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()

def accepted_gate(accepted, checkpoint, gate_sha):
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", accepted, checkpoint], cwd=ROOT, capture_output=True, check=False)
    raw = git_blob(accepted, GATE_PATH)
    return ancestor.returncode == 0 and raw is not None and hashlib.sha256(raw).hexdigest() == gate_sha

def valid_activation(raw, *, head, root=ROOT, blob_loader=git_blob, gate_check=accepted_gate):
    try: value = json.loads(raw.decode("ascii")); gate_sha = hashlib.sha256((root / GATE_PATH).read_bytes()).hexdigest()
    except (OSError, UnicodeDecodeError, ValueError): return None
    expected = {"schema_version": ACTIVATION_SCHEMA, "gate_id": GATE_ID, "gate_sha256": gate_sha, "hermetic_ci_head_sha": value.get("accepted_gate_head_sha"), "inspector_decision": "ACCEPTED", "owner_authorization_reference": "B8.6R6 one-shot owner authorization", "scope": "one_repo_relative_falsification_container_provisioning_only", "validation_seal": SEAL}
    if raw != canonical(value) or set(value) != set(expected) | {"accepted_gate_head_sha", "hermetic_ci_run_id"} or any(value.get(key) != wanted for key, wanted in expected.items()) or value.get("accepted_gate_head_sha") != value.get("hermetic_ci_head_sha") or not isinstance(value.get("hermetic_ci_run_id"), int) or value["hermetic_ci_run_id"] < 1 or blob_loader(head, ACTIVATION) != raw or not gate_check(value["accepted_gate_head_sha"], head, gate_sha): return None
    return {"path": ACTIVATION, "raw_sha256": hashlib.sha256(raw).hexdigest(), "content": value, "activation_checkpoint_head": head}

def base(mode, row, provenance, root=ROOT, commit=None):
    return {"schema_version": REPORT_SCHEMA, "order_id": "B8.6R6", "hypothesis_id": "L-4", "mode": mode, "evidence_tier": "E0", "edge_claim": "none", "real_provisioning_consumed": mode == "real_one_shot", "dataset_reference": DATASET, "expected_dataset_sha256": EXPECTED_DATASET_SHA256, "dataset_artifact": row, "contract_artifacts": identities(), "activation_provenance": provenance, "access_counters": {"return_value_decode_count": 0, "validation_access_count": 0}, "validation_seal": SEAL, "producing_git_commit": "synthetic_fixture" if mode == "synthetic_fixture" else (commit or git_head(root))}

def run_one_shot(*, root=ROOT, head=None, blob_loader=git_blob, gate_check=accepted_gate):
    head = head or git_head(root)
    try: raw_activation = (root / ACTIVATION).read_bytes()
    except OSError: return {"outcome": "refused_activation", "dataset_read_count": 0}
    provenance = valid_activation(raw_activation, head=head, root=root, blob_loader=blob_loader, gate_check=gate_check)
    if provenance is None: return {"outcome": "refused_activation", "dataset_read_count": 0}
    if not claim_once(root / MARKER): return {"outcome": "refused_already_consumed", "dataset_read_count": 0}
    row = artifact(); raw, error = read_once(root / DATASET, row)
    report = base("real_one_shot", row, provenance, root, head) if error else base("real_one_shot", row, provenance, root, head) | structural(raw, row)
    if error: report |= {"outcome": "provisioning_blocked", "blocker": error}
    if report["outcome"] == "structural_provisioned":
        manifest_raw, payload_raw = canonical(report["manifest"]), canonical(report["payload"])
        write_atomic(root / MANIFEST, manifest_raw); write_atomic(root / PAYLOAD, payload_raw)
        report["output_artifacts"] = {"manifest": {"path": MANIFEST, "raw_sha256": hashlib.sha256(manifest_raw).hexdigest(), "byte_count": len(manifest_raw)}, "payload": {"path": PAYLOAD, "raw_sha256": hashlib.sha256(payload_raw).hexdigest(), "byte_count": len(payload_raw)}}
        report["structural_summary_sha256"] = hashlib.sha256(canonical({"manifest": report["manifest"], "payload": report["payload"]})).hexdigest()
    write_atomic(root / REPORT, canonical(report)); return report

def main(argv):
    if argv != ["--execute-one-shot"]: return 2
    return 0 if run_one_shot().get("outcome") == "structural_provisioned" else 1

if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
