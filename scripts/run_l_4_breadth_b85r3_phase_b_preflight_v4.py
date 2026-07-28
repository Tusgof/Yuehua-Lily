"""Future B8.5R3 preflight. Bare CLI invocation is deliberately inert."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.environment import require_configured_path
from lib.l4_b85r3_structural_scanner_v4 import MAX_BYTES, ScanError, scan_manifest, scan_payload
from lib.provenance import git_commit

MANIFEST_RELATIVE = Path("sealed/l4_b85r3/l4_b85r3_structural_manifest_v4.json")
PAYLOAD_RELATIVE = Path("sealed/l4_b85r3/l4_b85r3_u8_symbol_session_dates_v4.json")
MANIFEST_REFERENCE = "${LILY_DATA_ROOT}/sealed/l4_b85r3/l4_b85r3_structural_manifest_v4.json"
PAYLOAD_REFERENCE = "${LILY_DATA_ROOT}/sealed/l4_b85r3/l4_b85r3_u8_symbol_session_dates_v4.json"
CONTAINER_IDENTITY = "lily-l4-falsification-pre2016-v4"
REPORT_RELATIVE = Path("reports/experiments/l_4_breadth_b85r3_phase_b_preflight_report_v4.json")
ATTEMPT_MARKER_RELATIVE = Path("reports/experiments/l_4_breadth_b85r3_phase_b_preflight_attempt_v4.json")
ACTIVATION_RECORD_RELATIVE = Path("experiments/activation_records/l_4_breadth_b85r3_phase_b_activation_v4.json")
GATE_ID = "l_4_breadth_b85r3_phase_a_activation_order_v4"
ACTIVATION_SCHEMA = "lily_l4_b85r3_phase_b_activation_v4"
MARKER_BYTES = b'{"schema_version":"lily_l4_b85r3_attempt_v4","state":"consumed"}'
CONTRACT_ARTIFACTS = {
    "phase_a_gate": "experiments/l_4_breadth_b85r3_phase_a_activation_order_v4.json",
    "phase_a_validator": "scripts/validate_l_4_breadth_b85r3_phase_a_activation_order_v4.py",
    "scanner": "lib/l4_b85r3_structural_scanner_v4.py",
    "runner": "scripts/run_l_4_breadth_b85r3_phase_b_preflight_v4.py",
    "report_schema": "schemas/l_4_breadth_b85r3_structural_preflight_report_v4.schema.json",
    "report_validator": "scripts/validate_l_4_breadth_b85r3_structural_preflight_report_v4.py",
    "activation_schema": "schemas/l_4_breadth_b85r3_phase_b_activation_v4.schema.json",
}


def _read_limited(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(MAX_BYTES + 1)


def _sha(path: Path) -> str:
    raw = _read_limited(path)
    if len(raw) > MAX_BYTES:
        raise ScanError("contract_artifact_over_limit")
    return hashlib.sha256(raw).hexdigest()


def contract_identities() -> dict[str, dict[str, str]]:
    return {name: {"path": path, "sha256": _sha(ROOT / path)} for name, path in CONTRACT_ARTIFACTS.items()}


def _artifact() -> dict[str, Any]:
    return {"attempted_read_count": 0, "read_count": 0, "observed_byte_count": None, "complete_read": False, "complete_raw_sha256": None, "bounded_prefix_sha256": None, "hash_count": 0, "scan_count": 0, "minimal_ascii_decode_count": 0}


def _from_raw(raw: bytes) -> dict[str, Any]:
    return {"attempted_read_count": 0, "read_count": 0, "observed_byte_count": len(raw), "complete_read": len(raw) <= MAX_BYTES, "complete_raw_sha256": hashlib.sha256(raw).hexdigest() if len(raw) <= MAX_BYTES else None, "bounded_prefix_sha256": hashlib.sha256(raw[: MAX_BYTES + 1]).hexdigest(), "hash_count": 1, "scan_count": 0, "minimal_ascii_decode_count": 0}


def _record_read(path: Path, counter: dict[str, Any]) -> tuple[bytes | None, str | None]:
    counter["attempted_read_count"] = 1
    try:
        raw = _read_limited(path)
    except OSError as exc:
        return None, type(exc).__name__
    counter["read_count"] = 1; counter["observed_byte_count"] = len(raw); counter["hash_count"] = 1; counter["bounded_prefix_sha256"] = hashlib.sha256(raw).hexdigest()
    if len(raw) > MAX_BYTES:
        return None, "input_over_limit"
    counter["complete_read"] = True; counter["complete_raw_sha256"] = counter["bounded_prefix_sha256"]
    return raw, None


def _base(*, mode: str, consumed: bool, artifacts: dict[str, Any], attempt_state: str) -> dict[str, Any]:
    return {"schema_version":"lily_l4_b85r3_structural_preflight_report_v4","order_id":"B8.5R3","hypothesis_id":"L-4","mode":mode,"evidence_tier":"E0","edge_claim":"none","real_preflight_consumed":consumed,"storage_references":{"manifest":MANIFEST_REFERENCE,"payload":PAYLOAD_REFERENCE},"container_identity":CONTAINER_IDENTITY,"artifacts":artifacts,"contract_artifacts":contract_identities(),"access_counters":{"return_value_decode_count":0,"validation_access_count":0},"validation_seal":{"status":"sealed_not_accessed","accessed":False},"attempt":{"state":attempt_state,"repo_relative_marker_path":ATTEMPT_MARKER_RELATIVE.as_posix(),"marker_raw_sha256":hashlib.sha256(MARKER_BYTES).hexdigest() if attempt_state=="consumed" else None},"producing_git_commit":git_commit(ROOT)}


def preflight_from_raw(manifest_raw: bytes, payload_raw: bytes, *, mode: str = "synthetic_fixture", consumed: bool = False, artifacts: dict[str, Any] | None = None, attempt_state: str = "not_consumed") -> dict[str, Any]:
    rows = artifacts or {"manifest": _from_raw(manifest_raw), "payload": _from_raw(payload_raw)}
    report = _base(mode=mode, consumed=consumed, artifacts=rows, attempt_state=attempt_state)
    try:
        rows["manifest"]["scan_count"] = 1
        manifest = scan_manifest(manifest_raw, expected_identity=CONTAINER_IDENTITY, expected_payload_path=PAYLOAD_RELATIVE.as_posix())
        rows["manifest"]["minimal_ascii_decode_count"] = manifest["minimal_ascii_decode_count"]
        rows["payload"]["scan_count"] = 1
        payload = scan_payload(payload_raw)
        rows["payload"]["minimal_ascii_decode_count"] = payload["minimal_ascii_decode_count"]
        if manifest["metadata_sha256"] != payload["complete_raw_sha256"]:
            raise ScanError("manifest_payload_hash_mismatch")
    except (ScanError, TypeError) as exc:
        report.update({"outcome":"preflight_blocked","blocker":"structural_" + str(exc)})
        return report
    report.update({"outcome":"structural_pass","manifest":manifest,"payload":payload})
    return report


def _write_all(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw): offset += os.write(descriptor, raw[offset:])


def _durable_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_name(path.name + ".tmp")
    raw = json.dumps(report, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try: _write_all(descriptor, raw); os.fsync(descriptor)
    finally: os.close(descriptor)
    os.replace(temporary, path)


def _claim(marker: Path) -> bool:
    marker.parent.mkdir(parents=True, exist_ok=True)
    try: descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError: return False
    try: _write_all(descriptor, MARKER_BYTES); os.fsync(descriptor)
    finally: os.close(descriptor)
    return True


def activation_is_valid(path: Path) -> bool:
    try: raw = _read_limited(path)
    except OSError: return False
    if len(raw) > MAX_BYTES: return False
    try: record = json.loads(raw.decode("ascii")); identities = contract_identities()
    except (ValueError, UnicodeDecodeError, ScanError): return False
    expected = {"schema_version":ACTIVATION_SCHEMA,"gate_id":GATE_ID,"gate_sha256":identities["phase_a_gate"]["sha256"],"accepted_head_sha":git_commit(ROOT),"hermetic_ci_head_sha":git_commit(ROOT),"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.5R3 Phase B owner authorization","scope":"one_structural_u8_preflight_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}}
    return isinstance(record, dict) and set(record) == set(expected) | {"hermetic_ci_run_id"} and all(record.get(key) == value for key, value in expected.items()) and isinstance(record.get("hermetic_ci_run_id"), int) and record["hermetic_ci_run_id"] > 0


def _blocked(*, artifacts: dict[str, Any], blocker: str) -> dict[str, Any]:
    report = _base(mode="real_one_shot", consumed=True, artifacts=artifacts, attempt_state="consumed")
    report.update({"outcome":"preflight_blocked","blocker":blocker})
    return report


def _after_claim(root: Path, *, report_path: Path) -> dict[str, Any]:
    artifacts = {"manifest":_artifact(),"payload":_artifact()}
    manifest_raw, manifest_error = _record_read(root / MANIFEST_RELATIVE, artifacts["manifest"])
    if manifest_error:
        report = _blocked(artifacts=artifacts, blocker="manifest_" + manifest_error)
    else:
        payload_raw, payload_error = _record_read(root / PAYLOAD_RELATIVE, artifacts["payload"])
        if payload_error: report = _blocked(artifacts=artifacts, blocker="payload_" + payload_error)
        else: report = preflight_from_raw(manifest_raw or b"", payload_raw or b"", mode="real_one_shot", consumed=True, artifacts=artifacts, attempt_state="consumed")
    _durable_report(report_path, report)
    return report


def run_one_shot(root: Path, *, report_path: Path, attempt_marker_path: Path, activation_record_path: Path) -> dict[str, Any]:
    """Injected test helper; root and activation record are never discovered."""
    if not activation_is_valid(activation_record_path): return {"outcome":"refused_activation"}
    if not _claim(attempt_marker_path): return {"outcome":"refused_already_consumed"}
    return _after_claim(root, report_path=report_path)


def run_phase_b() -> dict[str, Any]:
    if not activation_is_valid(ROOT / ACTIVATION_RECORD_RELATIVE): return {"outcome":"refused_activation"}
    report_path, marker = ROOT / REPORT_RELATIVE, ROOT / ATTEMPT_MARKER_RELATIVE
    if not _claim(marker): return {"outcome":"refused_already_consumed"}
    try: root = require_configured_path("LILY_DATA_ROOT")
    except (OSError, ValueError) as exc:
        report = _blocked(artifacts={"manifest":_artifact(),"payload":_artifact()}, blocker="data_root_" + type(exc).__name__)
        _durable_report(report_path, report); return report
    return _after_claim(root, report_path=report_path)


def main(argv: list[str]) -> int:
    if argv != ["--execute-one-shot"]:
        return 2
    return 0 if run_phase_b().get("outcome") == "structural_pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
