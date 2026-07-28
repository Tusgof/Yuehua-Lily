"""One-shot B8.5R2 structural preflight; Phase-A tests use injected helpers only."""
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
from lib.l4_b85r2_structural_scanner_v3 import MAX_BYTES, ScanError, read_bounded, scan_manifest, scan_payload
from lib.provenance import git_commit

MANIFEST_RELATIVE = Path("sealed/l4_b85r2/l4_b85r2_structural_manifest_v3.json")
PAYLOAD_RELATIVE = Path("sealed/l4_b85r2/l4_b85r2_u8_symbol_session_dates_v3.json")
MANIFEST_REFERENCE = "${LILY_DATA_ROOT}/sealed/l4_b85r2/l4_b85r2_structural_manifest_v3.json"
PAYLOAD_REFERENCE = "${LILY_DATA_ROOT}/sealed/l4_b85r2/l4_b85r2_u8_symbol_session_dates_v3.json"
CONTAINER_IDENTITY = "lily-l4-falsification-pre2016-v3"
REPORT_RELATIVE = Path("reports/experiments/l_4_breadth_b85r2_phase_b_preflight_report_v3.json")
ATTEMPT_MARKER_RELATIVE = Path("reports/experiments/l_4_breadth_b85r2_phase_b_preflight_attempt_v3.json")
CONTRACT_ARTIFACTS = {
    "phase_a_gate": "experiments/l_4_breadth_b85r2_phase_a_activation_order_v3.json",
    "phase_a_validator": "scripts/validate_l_4_breadth_b85r2_phase_a_activation_order_v3.py",
    "scanner": "lib/l4_b85r2_structural_scanner_v3.py",
    "runner": "scripts/run_l_4_breadth_b85r2_phase_b_preflight_v3.py",
    "report_schema": "schemas/l_4_breadth_b85r2_structural_preflight_report_v3.schema.json",
    "report_validator": "scripts/validate_l_4_breadth_b85r2_structural_preflight_report_v3.py",
}
ATTEMPT_MARKER_BYTES = b'{"schema_version":"lily_l4_b85r2_attempt_v3","state":"consumed"}'


def _bounded_sha256(path: Path) -> str:
    return hashlib.sha256(read_bounded(path)).hexdigest()


def contract_identities() -> dict[str, dict[str, str]]:
    return {name: {"path": relative, "sha256": _bounded_sha256(ROOT / relative)} for name, relative in CONTRACT_ARTIFACTS.items()}


def _artifact() -> dict[str, int | str | None]:
    return {"attempted_read_count": 0, "read_count": 0, "byte_count": None, "hash_count": 0, "scan_count": 0, "raw_sha256": None}


def _supplied_artifact(raw: bytes) -> dict[str, int | str | None]:
    return {"attempted_read_count": 0, "read_count": 0, "byte_count": len(raw), "hash_count": 1, "scan_count": 0, "raw_sha256": hashlib.sha256(raw).hexdigest()}


def _common(*, mode: str, consumed: bool, artifacts: dict[str, dict[str, int | str | None]], attempt_state: str) -> dict[str, Any]:
    return {
        "schema_version": "lily_l4_b85r2_structural_preflight_report_v3",
        "order_id": "B8.5R2",
        "hypothesis_id": "L-4",
        "mode": mode,
        "evidence_tier": "E0",
        "edge_claim": "none",
        "real_preflight_consumed": consumed,
        "storage_references": {"manifest": MANIFEST_REFERENCE, "payload": PAYLOAD_REFERENCE},
        "container_identity": CONTAINER_IDENTITY,
        "artifacts": artifacts,
        "contract_artifacts": contract_identities(),
        "access_counters": {"return_value_decode_count": 0, "validation_access_count": 0},
        "validation_seal": {"status": "sealed_not_accessed", "accessed": False},
        "attempt": {
            "state": attempt_state,
            "repo_relative_marker_path": ATTEMPT_MARKER_RELATIVE.as_posix(),
            "marker_raw_sha256": hashlib.sha256(ATTEMPT_MARKER_BYTES).hexdigest() if attempt_state == "consumed" else None,
        },
        "producing_git_commit": git_commit(ROOT),
    }


def preflight_from_raw(manifest_raw: bytes, payload_raw: bytes, *, mode: str = "synthetic_fixture", consumed: bool = False, artifacts: dict[str, dict[str, int | str | None]] | None = None, attempt_state: str = "not_consumed") -> dict[str, Any]:
    observed = artifacts or {"manifest": _supplied_artifact(manifest_raw), "payload": _supplied_artifact(payload_raw)}
    report = _common(mode=mode, consumed=consumed, artifacts=observed, attempt_state=attempt_state)
    try:
        observed["manifest"]["scan_count"] = int(observed["manifest"]["scan_count"] or 0) + 1
        manifest = scan_manifest(manifest_raw, expected_identity=CONTAINER_IDENTITY, expected_payload_path=PAYLOAD_RELATIVE.as_posix())
        observed["payload"]["scan_count"] = int(observed["payload"]["scan_count"] or 0) + 1
        payload = scan_payload(payload_raw)
        if manifest["metadata_sha256"] != payload["raw_sha256"]:
            raise ScanError("manifest_payload_hash_mismatch")
    except (ScanError, TypeError) as exc:
        report.update({"outcome": "preflight_blocked", "blocker": str(exc)})
        return report
    report.update({"outcome": "structural_pass", "manifest": manifest, "payload": payload})
    return report


def _write_all(descriptor: int, raw: bytes) -> None:
    offset = 0
    while offset < len(raw):
        offset += os.write(descriptor, raw[offset:])


def _durable_replace(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        _write_all(descriptor, raw)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    _fsync_parent(path)


def _fsync_parent(path: Path) -> None:
    try:
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        pass


def _claim_attempt(marker_path: Path) -> tuple[bool, str | None]:
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(marker_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False, "attempt_already_consumed"
    try:
        _write_all(descriptor, ATTEMPT_MARKER_BYTES)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_parent(marker_path)
    return True, None


def _record_read(path: Path, counter: dict[str, int | str | None]) -> bytes:
    counter["attempted_read_count"] = int(counter["attempted_read_count"] or 0) + 1
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    counter["read_count"] = int(counter["read_count"] or 0) + 1
    counter["byte_count"] = len(raw)
    counter["hash_count"] = 1
    counter["raw_sha256"] = hashlib.sha256(raw).hexdigest()
    if len(raw) > MAX_BYTES:
        raise ScanError("input_over_limit")
    return raw


def _blocked(*, mode: str, consumed: bool, artifacts: dict[str, dict[str, int | str | None]], attempt_state: str, blocker: str) -> dict[str, Any]:
    report = _common(mode=mode, consumed=consumed, artifacts=artifacts, attempt_state=attempt_state)
    report.update({"outcome": "preflight_blocked", "blocker": blocker})
    return report


def _run_after_claim(root: Path, *, report_path: Path, marker_path: Path) -> dict[str, Any]:
    artifacts = {"manifest": _artifact(), "payload": _artifact()}
    try:
        manifest_raw = _record_read(root / MANIFEST_RELATIVE, artifacts["manifest"])
    except (OSError, ScanError) as exc:
        report = _blocked(mode="real_one_shot", consumed=True, artifacts=artifacts, attempt_state="consumed", blocker=f"manifest_{type(exc).__name__}")
    else:
        try:
            payload_raw = _record_read(root / PAYLOAD_RELATIVE, artifacts["payload"])
        except (OSError, ScanError) as exc:
            report = _blocked(mode="real_one_shot", consumed=True, artifacts=artifacts, attempt_state="consumed", blocker=f"payload_{type(exc).__name__}")
        else:
            report = preflight_from_raw(manifest_raw, payload_raw, mode="real_one_shot", consumed=True, artifacts=artifacts, attempt_state="consumed")
    _durable_replace(report_path, report)
    return report


def run_one_shot(root: Path, *, report_path: Path, attempt_marker_path: Path) -> dict[str, Any]:
    """Injected helper for hermetic tests; it never resolves configuration."""
    claimed, blocker = _claim_attempt(attempt_marker_path)
    if not claimed:
        report = _blocked(mode="real_one_shot", consumed=False, artifacts={"manifest": _artifact(), "payload": _artifact()}, attempt_state="already_consumed", blocker=blocker or "attempt_already_consumed")
        _durable_replace(report_path, report)
        return report
    return _run_after_claim(root, report_path=report_path, marker_path=attempt_marker_path)


def run_phase_b() -> dict[str, Any]:
    """Production CLI: claim once before the sole permitted environment resolution."""
    report_path, marker_path = ROOT / REPORT_RELATIVE, ROOT / ATTEMPT_MARKER_RELATIVE
    claimed, blocker = _claim_attempt(marker_path)
    if not claimed:
        report = _blocked(mode="real_one_shot", consumed=False, artifacts={"manifest": _artifact(), "payload": _artifact()}, attempt_state="already_consumed", blocker=blocker or "attempt_already_consumed")
        _durable_replace(report_path, report)
        return report
    try:
        root = require_configured_path("LILY_DATA_ROOT")
    except (OSError, ValueError) as exc:
        report = _blocked(mode="real_one_shot", consumed=True, artifacts={"manifest": _artifact(), "payload": _artifact()}, attempt_state="consumed", blocker=f"data_root_{type(exc).__name__}")
        _durable_replace(report_path, report)
        return report
    return _run_after_claim(root, report_path=report_path, marker_path=marker_path)


if __name__ == "__main__":
    result = run_phase_b()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0 if result["outcome"] == "structural_pass" else 1)
