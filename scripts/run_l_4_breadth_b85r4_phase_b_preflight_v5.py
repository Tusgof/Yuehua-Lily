"""Future v5 preflight; this Phase-A order neither activates nor invokes it."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.environment import require_configured_path
from lib.l4_b85r4_structural_scanner_v5 import MAX_BYTES, ScanError, scan_manifest, scan_payload
from lib.provenance import git_commit

MANIFEST_RELATIVE = Path("sealed/l4_b85r4/l4_b85r4_structural_manifest_v5.json")
PAYLOAD_RELATIVE = Path("sealed/l4_b85r4/l4_b85r4_u8_symbol_session_dates_v5.json")
MANIFEST_REFERENCE = "${LILY_DATA_ROOT}/sealed/l4_b85r4/l4_b85r4_structural_manifest_v5.json"
PAYLOAD_REFERENCE = "${LILY_DATA_ROOT}/sealed/l4_b85r4/l4_b85r4_u8_symbol_session_dates_v5.json"
CONTAINER_IDENTITY = "lily-l4-falsification-pre2016-v5"
GATE_ID = "l_4_breadth_b85r4_phase_a_activation_order_v5"
ACTIVATION_RECORD_RELATIVE = Path("experiments/activation_records/l_4_breadth_b85r4_phase_b_activation_v5.json")
REPORT_RELATIVE = Path("reports/experiments/l_4_breadth_b85r4_phase_b_preflight_report_v5.json")
MARKER_RELATIVE = Path("reports/experiments/l_4_breadth_b85r4_phase_b_preflight_attempt_v5.json")
MARKER_BYTES = b'{"schema_version":"lily_l4_b85r4_attempt_v5","state":"consumed"}'
CONTRACT_ARTIFACTS = {
    "phase_a_gate": "experiments/l_4_breadth_b85r4_phase_a_activation_order_v5.json",
    "phase_a_validator": "scripts/validate_l_4_breadth_b85r4_phase_a_activation_order_v5.py",
    "scanner": "lib/l4_b85r4_structural_scanner_v5.py",
    "runner": "scripts/run_l_4_breadth_b85r4_phase_b_preflight_v5.py",
    "report_schema": "schemas/l_4_breadth_b85r4_structural_preflight_report_v5.schema.json",
    "report_validator": "scripts/validate_l_4_breadth_b85r4_structural_preflight_report_v5.py",
    "activation_schema": "schemas/l_4_breadth_b85r4_phase_b_activation_v5.schema.json",
}


def limited(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(MAX_BYTES + 1)


def identities() -> dict[str, dict[str, str]]:
    result = {}
    for name, path in CONTRACT_ARTIFACTS.items():
        raw = limited(ROOT / path)
        if len(raw) > MAX_BYTES:
            raise ScanError("contract_artifact_over_limit")
        result[name] = {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}
    return result


def _activation(raw: bytes, *, activation_head: str) -> dict[str, Any] | None:
    try:
        record = json.loads(raw.decode("ascii")); gate_sha = identities()["phase_a_gate"]["sha256"]
    except (OSError, ValueError, UnicodeDecodeError, ScanError):
        return None
    if not isinstance(record, dict):
        return None
    expected = {
        "schema_version": "lily_l4_b85r4_phase_b_activation_v5", "gate_id": GATE_ID,
        "gate_sha256": gate_sha, "hermetic_ci_head_sha": record.get("accepted_gate_head_sha"),
        "inspector_decision": "ACCEPTED", "owner_authorization_reference": "B8.5R4 Phase B owner authorization",
        "scope": "one_structural_u8_preflight_only", "validation_seal": {"status": "sealed_not_accessed", "accessed": False},
    }
    if set(record) != set(expected) | {"accepted_gate_head_sha", "hermetic_ci_run_id"}:
        return None
    if not all(record.get(key) == value for key, value in expected.items()):
        return None
    if not isinstance(record["accepted_gate_head_sha"], str) or len(record["accepted_gate_head_sha"]) != 40:
        return None
    if not isinstance(record["hermetic_ci_run_id"], int) or record["hermetic_ci_run_id"] <= 0:
        return None
    return {"path": ACTIVATION_RECORD_RELATIVE.as_posix(), "raw_sha256": hashlib.sha256(raw).hexdigest(), "content": record, "activation_checkpoint_head": activation_head}


def tracked_activation() -> dict[str, Any] | None:
    path = ROOT / ACTIVATION_RECORD_RELATIVE
    try:
        raw = limited(path)
    except OSError:
        return None
    if len(raw) > MAX_BYTES:
        return None
    current = git_commit(ROOT)
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", ACTIVATION_RECORD_RELATIVE.as_posix()], cwd=ROOT, capture_output=True).returncode == 0
    committed = subprocess.run(["git", "show", f"HEAD:{ACTIVATION_RECORD_RELATIVE.as_posix()}"], cwd=ROOT, capture_output=True)
    if not tracked or committed.returncode or committed.stdout != raw:
        return None
    return _activation(raw, activation_head=current)


def _artifact() -> dict[str, Any]:
    return {"attempted_read_count": 0, "read_count": 0, "observed_byte_count": None, "complete_read": False, "complete_raw_sha256": None, "bounded_prefix_sha256": None, "hash_count": 0, "scan_count": 0, "minimal_ascii_decode_count": 0}


def _from_raw(raw: bytes, *, reads: int = 0) -> dict[str, Any]:
    complete = len(raw) <= MAX_BYTES
    return {"attempted_read_count": reads, "read_count": reads, "observed_byte_count": len(raw), "complete_read": complete, "complete_raw_sha256": hashlib.sha256(raw).hexdigest() if complete else None, "bounded_prefix_sha256": hashlib.sha256(raw).hexdigest(), "hash_count": 1, "scan_count": 0, "minimal_ascii_decode_count": 0}


def _read(path: Path, counter: dict[str, Any]) -> tuple[bytes | None, str | None]:
    counter["attempted_read_count"] = 1
    try:
        raw = limited(path)
    except OSError as exc:
        return None, type(exc).__name__
    counter.update({"read_count": 1, "observed_byte_count": len(raw), "hash_count": 1, "bounded_prefix_sha256": hashlib.sha256(raw).hexdigest()})
    if len(raw) > MAX_BYTES:
        return None, "input_over_limit"
    counter["complete_read"] = True; counter["complete_raw_sha256"] = counter["bounded_prefix_sha256"]
    return raw, None


def _base(*, mode: str, consumed: bool, artifacts: dict[str, Any], provenance: dict[str, Any] | None) -> dict[str, Any]:
    return {"schema_version": "lily_l4_b85r4_structural_preflight_report_v5", "order_id": "B8.5R4", "hypothesis_id": "L-4", "mode": mode, "evidence_tier": "E0", "edge_claim": "none", "real_preflight_consumed": consumed, "storage_references": {"manifest": MANIFEST_REFERENCE, "payload": PAYLOAD_REFERENCE}, "container_identity": CONTAINER_IDENTITY, "artifacts": artifacts, "contract_artifacts": identities(), "activation_provenance": provenance, "access_counters": {"return_value_decode_count": 0, "validation_access_count": 0}, "validation_seal": {"status": "sealed_not_accessed", "accessed": False}, "producing_git_commit": "synthetic_fixture" if mode == "synthetic_fixture" else git_commit(ROOT)}


def structural_summary_sha256(manifest: dict[str, Any], payload: dict[str, Any]) -> str:
    raw = json.dumps({"manifest": manifest, "payload": payload}, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def synthetic(manifest_raw: bytes, payload_raw: bytes) -> dict[str, Any]:
    rows = {"manifest": _from_raw(manifest_raw), "payload": _from_raw(payload_raw)}
    report = _base(mode="synthetic_fixture", consumed=False, artifacts=rows, provenance=None)
    try:
        rows["manifest"]["scan_count"] = 1
        manifest = scan_manifest(manifest_raw, expected_identity=CONTAINER_IDENTITY, expected_payload_path=PAYLOAD_RELATIVE.as_posix())
        rows["manifest"]["minimal_ascii_decode_count"] = manifest["minimal_ascii_decode_count"]
        rows["payload"]["scan_count"] = 1; payload = scan_payload(payload_raw)
        rows["payload"]["minimal_ascii_decode_count"] = payload["minimal_ascii_decode_count"]
        if manifest["metadata_sha256"] != payload["complete_raw_sha256"]:
            raise ScanError("manifest_payload_hash_mismatch")
        report.update({"outcome": "structural_pass", "manifest": manifest, "payload": payload, "structural_summary_sha256": structural_summary_sha256(manifest, payload)})
    except (ScanError, TypeError) as exc:
        report.update({"outcome": "preflight_blocked", "blocker": "structural_" + str(exc)})
    return report


def _write_all(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        offset += os.write(descriptor, raw[offset:])


def _durable_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_name(path.name + ".tmp")
    raw = json.dumps(report, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        _write_all(descriptor, raw); os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)


def _claim(marker: Path) -> bool:
    marker.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    try:
        _write_all(descriptor, MARKER_BYTES); os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True


def _blocked(artifacts: dict[str, Any], blocker: str, provenance: dict[str, Any]) -> dict[str, Any]:
    report = _base(mode="real_one_shot", consumed=True, artifacts=artifacts, provenance=provenance)
    report.update({"outcome": "preflight_blocked", "blocker": blocker})
    return report


def _after_claim(root: Path, report_path: Path, provenance: dict[str, Any]) -> dict[str, Any]:
    rows = {"manifest": _artifact(), "payload": _artifact()}
    manifest_raw, manifest_error = _read(root / MANIFEST_RELATIVE, rows["manifest"])
    if manifest_error:
        report = _blocked(rows, "manifest_" + manifest_error, provenance)
    else:
        payload_raw, payload_error = _read(root / PAYLOAD_RELATIVE, rows["payload"])
        if payload_error:
            report = _blocked(rows, "payload_" + payload_error, provenance)
        else:
            report = synthetic(manifest_raw or b"", payload_raw or b"")
            report.update(_base(mode="real_one_shot", consumed=True, artifacts=rows, provenance=provenance))
    _durable_report(report_path, report)
    return report


def run_one_shot(root: Path, *, report_path: Path, attempt_marker_path: Path, activation_raw: bytes, activation_head: str) -> dict[str, Any]:
    """Injected hermetic helper; it never discovers a machine path or config."""
    provenance = _activation(activation_raw, activation_head=activation_head)
    if provenance is None:
        return {"outcome": "refused_activation"}
    if not _claim(attempt_marker_path):
        return {"outcome": "refused_already_consumed"}
    return _after_claim(root, report_path, provenance)


def run_phase_b() -> dict[str, Any]:
    provenance = tracked_activation()
    if provenance is None:
        return {"outcome": "refused_activation"}
    marker = ROOT / MARKER_RELATIVE
    if not _claim(marker):
        return {"outcome": "refused_already_consumed"}
    rows = {"manifest": _artifact(), "payload": _artifact()}
    try:
        root = require_configured_path("LILY_DATA_ROOT")
    except (OSError, ValueError) as exc:
        report = _blocked(rows, "data_root_" + type(exc).__name__, provenance)
        _durable_report(ROOT / REPORT_RELATIVE, report)
        return report
    return _after_claim(root, ROOT / REPORT_RELATIVE, provenance)


def main(argv: list[str]) -> int:
    if argv != ["--execute-one-shot"]:
        return 2
    return 0 if run_phase_b().get("outcome") == "structural_pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
