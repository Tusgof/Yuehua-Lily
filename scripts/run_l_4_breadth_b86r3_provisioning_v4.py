"""Future B8.6R3 one-shot; tests may use only injected synthetic paths."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.l4_b86r2_provisioning_scanner_v3 import MAX_BYTES, ScanError, scan_dataset
from lib.l4_b86r3_contract_v4 import category
from lib.provenance import git_commit

GATE_ID = "l_4_breadth_b86r3_provisioning_gate_v4"
DATASET_RELATIVE = Path("data/normalized/l1_yahoo_daily_v1.json")
DATASET_REFERENCE = DATASET_RELATIVE.as_posix()
EXPECTED_SHA256 = "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd"
ACTIVATION_RELATIVE = Path("experiments/activation_records/l_4_breadth_b86r3_provisioning_activation_v4.json")
REPORT_RELATIVE = Path("reports/experiments/l_4_breadth_b86r3_provisioning_report_v4.json")
MARKER_RELATIVE = Path("reports/experiments/l_4_breadth_b86r3_provisioning_attempt_v4.json")
MANIFEST_RELATIVE = Path("experiments/provisioned/l_4_breadth_b86r3_falsification_manifest_v4.json")
PAYLOAD_RELATIVE = Path("experiments/provisioned/l_4_breadth_b86r3_u8_session_dates_v4.json")
MARKER_BYTES = b'{"schema_version":"lily_l4_b86r3_attempt_v4","state":"consumed"}'
CONTRACT_ARTIFACTS = {
    "phase_a_gate": "experiments/l_4_breadth_b86r3_provisioning_gate_v4.json",
    "phase_a_validator": "scripts/validate_l_4_breadth_b86r3_provisioning_gate_v4.py",
    "blocker_contract": "lib/l4_b86r3_contract_v4.py",
    "scanner": "lib/l4_b86r2_provisioning_scanner_v3.py",
    "runner": "scripts/run_l_4_breadth_b86r3_provisioning_v4.py",
    "report_schema": "schemas/l_4_breadth_b86r3_provisioning_report_v4.schema.json",
    "report_validator": "scripts/validate_l_4_breadth_b86r3_provisioning_report_v4.py",
    "activation_schema": "schemas/l_4_breadth_b86r3_provisioning_activation_v4.schema.json",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def limited(path):
    with path.open("rb") as handle:
        return handle.read(MAX_BYTES + 1)


def identities():
    result = {}
    for name, relative in CONTRACT_ARTIFACTS.items():
        raw = limited(ROOT / relative)
        if len(raw) > MAX_BYTES:
            raise ScanError("contract_artifact_over_limit")
        result[name] = {"path": relative, "sha256": hashlib.sha256(raw).hexdigest()}
    return result


def blob(commit, relative):
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"], cwd=ROOT, capture_output=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


def accepted_gate(accepted_head, checkpoint_head, gate_sha256):
    raw = blob(accepted_head, CONTRACT_ARTIFACTS["phase_a_gate"])
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", accepted_head, checkpoint_head],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    return ancestor.returncode == 0 and raw is not None and hashlib.sha256(raw).hexdigest() == gate_sha256


def activation(raw, *, activation_head, accepted_gate_check=None):
    try:
        value = json.loads(raw.decode("ascii"))
        gate_sha256 = identities()["phase_a_gate"]["sha256"]
    except (UnicodeDecodeError, ValueError, ScanError):
        return None
    if raw != canonical(value):
        return None
    expected = {
        "schema_version": "lily_l4_b86r3_provisioning_activation_v4",
        "gate_id": GATE_ID,
        "gate_sha256": gate_sha256,
        "hermetic_ci_head_sha": value.get("accepted_gate_head_sha"),
        "inspector_decision": "ACCEPTED",
        "owner_authorization_reference": "B8.6R3 one-shot owner authorization",
        "scope": "one_repo_relative_falsification_container_provisioning_only",
        "validation_seal": {"status": "sealed_not_accessed", "accessed": False},
    }
    accepted_head = value.get("accepted_gate_head_sha")
    if (
        not isinstance(value, dict)
        or set(value) != set(expected) | {"accepted_gate_head_sha", "hermetic_ci_run_id"}
        or any(value.get(key) != expected_value for key, expected_value in expected.items())
        or not isinstance(accepted_head, str)
        or len(accepted_head) != 40
        or any(character not in "0123456789abcdef" for character in accepted_head)
        or not isinstance(value.get("hermetic_ci_run_id"), int)
        or value["hermetic_ci_run_id"] < 1
    ):
        return None
    check = accepted_gate_check or accepted_gate
    if not check(accepted_head, activation_head, gate_sha256):
        return None
    return {
        "path": ACTIVATION_RELATIVE.as_posix(),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "content": value,
        "activation_checkpoint_head": activation_head,
    }


def artifact():
    return {
        "attempted_read_count": 0,
        "read_count": 0,
        "observed_byte_count": None,
        "complete_read": False,
        "complete_raw_sha256": None,
        "bounded_prefix_sha256": None,
        "hash_count": 0,
        "scan_count": 0,
        "opaque_unsafe_lexeme_decode_count": 0,
    }


def read(path, row):
    row["attempted_read_count"] = 1
    try:
        raw = limited(path)
    except FileNotFoundError:
        return None, "dataset_missing"
    except OSError:
        return None, "dataset_read_error"
    row.update(
        {
            "read_count": 1,
            "observed_byte_count": len(raw),
            "hash_count": 1,
            "bounded_prefix_sha256": hashlib.sha256(raw).hexdigest(),
        }
    )
    if len(raw) > MAX_BYTES:
        return None, "dataset_input_over_limit"
    row["complete_read"] = True
    row["complete_raw_sha256"] = row["bounded_prefix_sha256"]
    return raw, None


def write_raw(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        position = 0
        while position < len(raw):
            position += os.write(descriptor, raw[position:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)


def claim(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    try:
        os.write(descriptor, MARKER_BYTES)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True


def base(mode, row, provenance):
    return {
        "schema_version": "lily_l4_b86r3_provisioning_report_v4",
        "order_id": "B8.6R3",
        "hypothesis_id": "L-4",
        "mode": mode,
        "evidence_tier": "E0",
        "edge_claim": "none",
        "real_provisioning_consumed": mode == "real_one_shot",
        "dataset_reference": DATASET_REFERENCE,
        "expected_dataset_sha256": EXPECTED_SHA256,
        "dataset_artifact": row,
        "contract_artifacts": identities(),
        "activation_provenance": provenance,
        "access_counters": {
            "return_value_decode_count": 0,
            "opaque_unsafe_lexeme_decode_count": 0,
            "validation_access_count": 0,
        },
        "validation_seal": {"status": "sealed_not_accessed", "accessed": False},
        "producing_git_commit": "synthetic_fixture" if mode == "synthetic_fixture" else git_commit(ROOT),
    }


def outputs(scanned):
    manifest = {
        "dataset_sha256": scanned["dataset_sha256"],
        "dataset_byte_count": scanned["dataset_byte_count"],
        "u8_members_in_order": scanned["u8_members_in_order"],
        "coverage_by_symbol": scanned["coverage_by_symbol"],
        "session_count": scanned["session_count"],
        "max_session_date": scanned["max_session_date"],
    }
    payload = {
        "dataset_sha256": scanned["dataset_sha256"],
        "u8_members_in_order": scanned["u8_members_in_order"],
        "session_dates_by_symbol": scanned["session_dates_by_symbol"],
    }
    return manifest, payload


def identity(path, raw):
    return {"path": path.as_posix(), "raw_sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}


def structural(raw, *, mode="synthetic_fixture", row=None, provenance=None, output_paths=None):
    row = row or {
        **artifact(),
        "attempted_read_count": 1,
        "read_count": 1,
        "observed_byte_count": len(raw),
        "complete_read": len(raw) <= MAX_BYTES,
        "complete_raw_sha256": hashlib.sha256(raw).hexdigest() if len(raw) <= MAX_BYTES else None,
        "bounded_prefix_sha256": hashlib.sha256(raw).hexdigest(),
        "hash_count": 1,
    }
    report = base(mode, row, provenance)
    row["scan_count"] = 1
    try:
        scanned = scan_dataset(
            raw,
            expected_sha256=EXPECTED_SHA256 if mode == "real_one_shot" else hashlib.sha256(raw).hexdigest(),
        )
    except ScanError as error:
        report.update({"outcome": "provisioning_blocked", "blocker": str(error)})
        return report
    manifest, payload = outputs(scanned)
    manifest_raw, payload_raw = canonical(manifest), canonical(payload)
    manifest_path, payload_path = output_paths or (ROOT / MANIFEST_RELATIVE, ROOT / PAYLOAD_RELATIVE)
    report.update(
        {
            "outcome": "structural_provisioned",
            "manifest": manifest,
            "payload": payload,
            "output_artifacts": {
                "manifest": identity(manifest_path, manifest_raw),
                "payload": identity(payload_path, payload_raw),
            },
            "structural_summary_sha256": hashlib.sha256(
                canonical({"manifest": manifest, "payload": payload})
            ).hexdigest(),
        }
    )
    return report


def run_one_shot(
    dataset_path,
    *,
    report_path,
    marker_path,
    manifest_path,
    payload_path,
    activation_raw,
    activation_head,
    accepted_gate_check,
):
    provenance = activation(
        activation_raw, activation_head=activation_head, accepted_gate_check=accepted_gate_check
    )
    if provenance is None:
        return {"outcome": "refused_activation"}
    if not claim(marker_path):
        return {"outcome": "refused_already_consumed"}
    row = artifact()
    raw, error = read(dataset_path, row)
    report = (
        base("real_one_shot", row, provenance)
        if error
        else structural(
            raw,
            mode="real_one_shot",
            row=row,
            provenance=provenance,
            output_paths=(manifest_path, payload_path),
        )
    )
    if error:
        report.update({"outcome": "provisioning_blocked", "blocker": error})
    if report["outcome"] == "structural_provisioned":
        write_raw(manifest_path, canonical(report["manifest"]))
        write_raw(payload_path, canonical(report["payload"]))
    write_raw(report_path, canonical(report))
    return report


def tracked_activation():
    try:
        raw = limited(ROOT / ACTIVATION_RELATIVE)
    except OSError:
        return None
    if len(raw) > MAX_BYTES:
        return None
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ACTIVATION_RELATIVE.as_posix()],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if tracked.returncode or blob("HEAD", ACTIVATION_RELATIVE.as_posix()) != raw:
        return None
    return activation(raw, activation_head=git_commit(ROOT))


def run_phase_b():
    provenance = tracked_activation()
    if provenance is None:
        return {"outcome": "refused_activation"}
    if not claim(ROOT / MARKER_RELATIVE):
        return {"outcome": "refused_already_consumed"}
    row = artifact()
    raw, error = read(ROOT / DATASET_RELATIVE, row)
    report = (
        base("real_one_shot", row, provenance)
        if error
        else structural(
            raw,
            mode="real_one_shot",
            row=row,
            provenance=provenance,
            output_paths=(ROOT / MANIFEST_RELATIVE, ROOT / PAYLOAD_RELATIVE),
        )
    )
    if error:
        report.update({"outcome": "provisioning_blocked", "blocker": error})
    if report["outcome"] == "structural_provisioned":
        write_raw(ROOT / MANIFEST_RELATIVE, canonical(report["manifest"]))
        write_raw(ROOT / PAYLOAD_RELATIVE, canonical(report["payload"]))
    write_raw(ROOT / REPORT_RELATIVE, canonical(report))
    return report


def main(argv):
    if argv != ["--execute-one-shot"]:
        return 2
    return 0 if run_phase_b().get("outcome") == "structural_provisioned" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
