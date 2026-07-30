"""B8.6R7/v9 one-shot runner.  Do not invoke outside a later activation order."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.l4_b86r2_provisioning_scanner_v3 import ScanError, scan_dataset
from lib.l4_b86r7_contract_v9 import *

CONTRACT = {
    "gate": GATE, "contract": "lib/l4_b86r7_contract_v9.py",
    "runner": "scripts/run_l_4_breadth_b86r7_provisioning_v9.py",
    "gate_validator": "scripts/validate_l_4_breadth_b86r7_provisioning_gate_v9.py",
    "report_validator": "scripts/validate_l_4_breadth_b86r7_provisioning_report_v9.py",
    "report_schema": "schemas/l_4_breadth_b86r7_provisioning_report_v9.schema.json",
    "activation_schema": "schemas/l_4_breadth_b86r7_provisioning_activation_v9.schema.json",
    "manifest_schema": "schemas/l_4_breadth_b86r7_falsification_manifest_v9.schema.json",
    "payload_schema": "schemas/l_4_breadth_b86r7_u8_session_dates_v9.schema.json",
}


def identities(root=ROOT):
    return {name: {"path": path, "sha256": sha256((root / path).read_bytes())} for name, path in CONTRACT.items()}


def git_blob(commit, path):
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def accepted_gate(accepted, checkpoint, gate_sha256):
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", accepted, checkpoint], cwd=ROOT, capture_output=True, check=False)
    raw = git_blob(accepted, GATE)
    return ancestor.returncode == 0 and raw is not None and sha256(raw) == gate_sha256


def activation_provenance(raw, *, head, root=ROOT, blob_loader=git_blob, gate_check=accepted_gate):
    try:
        value = json.loads(raw.decode("ascii"))
        gate_sha256 = sha256((root / GATE).read_bytes())
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if (
        raw != canonical(value) or not activation_ok(value, gate_sha256)
        or blob_loader(head, ACTIVATION) != raw
        or not gate_check(value["accepted_gate_head_sha"], head, gate_sha256)
    ):
        return None
    return {
        "path": ACTIVATION, "raw_sha256": sha256(raw), "content": value,
        "activation_checkpoint_head": head, "accepted_gate_blob_sha256": gate_sha256,
    }


def base(row, provenance, commit):
    return {
        "schema_version": REPORT_SCHEMA, "order_id": "B8.6R7", "hypothesis_id": "L-4",
        "mode": "real_one_shot", "evidence_tier": "E0", "edge_claim": "none",
        "real_provisioning_consumed": True, "dataset_reference": DATASET,
        "expected_dataset_sha256": EXPECTED_DATASET_SHA256, "dataset_artifact": row,
        "contract_artifacts": identities(), "activation_provenance": provenance,
        "access_counters": {"return_value_decode_count": 0, "validation_access_count": 0},
        "validation_seal": SEAL, "producing_git_commit": commit,
    }


def run_one_shot(*, root=ROOT, head=None, blob_loader=git_blob, gate_check=accepted_gate):
    if head is None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    try:
        raw_activation = (root / ACTIVATION).read_bytes()
    except OSError:
        return {"outcome": "refused_activation", "dataset_read_count": 0}
    provenance = activation_provenance(raw_activation, head=head, root=root, blob_loader=blob_loader, gate_check=gate_check)
    if provenance is None:
        return {"outcome": "refused_activation", "dataset_read_count": 0}
    if not claim_once(root / MARKER):
        return {"outcome": "refused_already_consumed", "dataset_read_count": 0}
    row = artifact(); row["attempted_read_count"] = 1
    try:
        with (root / DATASET).open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except FileNotFoundError:
        raw, blocker = None, "dataset_missing"
    except OSError:
        raw, blocker = None, "dataset_read_error"
    else:
        blocker = None
        row.update({"read_count": 1, "observed_byte_count": len(raw), "hash_count": 1, "bounded_prefix_sha256": sha256(raw)})
        if len(raw) > MAX_BYTES:
            blocker = "dataset_input_over_limit"
        else:
            row.update({"complete_read": True, "complete_raw_sha256": row["bounded_prefix_sha256"], "scan_count": 1})
    report = base(row, provenance, head)
    if blocker:
        report.update({"outcome": "provisioning_blocked", "blocker": blocker})
    else:
        try:
            scanned = scan_dataset(raw, expected_sha256=EXPECTED_DATASET_SHA256)
        except ScanError as error:
            report.update({"outcome": "provisioning_blocked", "blocker": str(error)})
        else:
            manifest = {
                "schema_version": MANIFEST_SCHEMA, "dataset_reference": DATASET,
                "dataset_sha256": scanned["dataset_sha256"], "dataset_byte_count": scanned["dataset_byte_count"],
                "u8_members_in_order": list(U8), "coverage_by_symbol": scanned["coverage_by_symbol"],
                "session_count": scanned["session_count"], "max_session_date": scanned["max_session_date"], "validation_seal": SEAL,
            }
            payload = {
                "schema_version": PAYLOAD_SCHEMA, "dataset_sha256": scanned["dataset_sha256"],
                "u8_members_in_order": list(U8), "session_dates_by_symbol": scanned["session_dates_by_symbol"],
            }
            manifest_raw, payload_raw = canonical(manifest), canonical(payload)
            atomic_write_all(((root / MANIFEST, manifest_raw), (root / PAYLOAD, payload_raw)))
            report.update({
                "outcome": "structural_provisioned", "manifest": manifest, "payload": payload,
                "output_artifacts": {
                    "manifest": {"path": MANIFEST, "raw_sha256": sha256(manifest_raw), "byte_count": len(manifest_raw)},
                    "payload": {"path": PAYLOAD, "raw_sha256": sha256(payload_raw), "byte_count": len(payload_raw)},
                },
                "structural_summary_sha256": sha256(canonical({"manifest": manifest, "payload": payload})),
            })
    atomic_write_all(((root / REPORT, canonical(report)),))
    return report


def main(argv):
    return 2 if argv != ["--execute-one-shot"] else (0 if run_one_shot().get("outcome") == "structural_provisioned" else 1)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
