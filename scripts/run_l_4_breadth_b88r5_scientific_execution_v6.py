"""Future v6 runtime; unreachable in this E0 remediation order."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from lib.l4_b88r5_lifecycle_v6 import GATE, MARKER, SEAL, canonical, clean_checkout, sha
from lib.l4_b88r5_scientific_engine_v6 import U8, derive


def _claim_marker(root: Path, preflight: dict) -> Path | None:
    marker = root / MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return None
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(canonical({"schema_version": "lily_l4_b88r5_marker_v6", "producing_commit": preflight["producing_commit"], "activation_sha256": sha(canonical(preflight["activation"]))}))
        handle.flush()
        os.fsync(handle.fileno())
    return marker


def _safe_path(root: Path, relative: str) -> Path | None:
    path = (root / relative).resolve()
    return path if root in path.parents and str(path.relative_to(root)).replace("\\", "/") == relative else None


def _read_structural_identities(root: Path, activation: dict) -> tuple[bytes, dict, bytes, dict] | None:
    manifest_path = _safe_path(root, activation["structural_manifest_path"])
    sessions_path = _safe_path(root, activation["u8_sessions_path"])
    if manifest_path is None or sessions_path is None:
        return None
    try:
        manifest_raw = manifest_path.read_bytes()
        sessions_raw = sessions_path.read_bytes()
        manifest = json.loads(manifest_raw.decode("ascii"))
        sessions = json.loads(sessions_raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if hashlib.sha256(manifest_raw).hexdigest() != activation["structural_manifest_sha256"] or hashlib.sha256(sessions_raw).hexdigest() != activation["u8_sessions_sha256"]:
        return None
    dates = sessions.get("session_dates_by_symbol")
    if (
        manifest.get("dataset_reference") != activation["container_path"]
        or manifest.get("dataset_sha256") != activation["container_sha256"]
        or manifest.get("max_session_date") != activation["cutoff_inclusive"]
        or manifest.get("u8_members_in_order") != list(U8)
        or manifest.get("validation_seal") != SEAL
        or sessions.get("dataset_sha256") != activation["container_sha256"]
        or sessions.get("u8_members_in_order") != list(U8)
        or not isinstance(dates, dict)
        or set(dates) != set(U8)
        or any(not isinstance(value, list) or value != sorted(set(value)) or any(date > activation["cutoff_inclusive"] for date in value) for date in dates.values())
    ):
        return None
    return manifest_raw, manifest, sessions_raw, sessions


def run_one_shot(preflight: dict, *, root: Path) -> dict:
    """Claim first, prove provisioned structural identities, then read once."""
    activation = preflight.get("activation")
    if not preflight.get("ready") or not isinstance(activation, dict):
        return {"status": "blocked", "outcome": "refused_preflight", "real_accessed": False}
    if not clean_checkout(root):
        return {"status": "blocked", "outcome": "refused_dirty_checkout", "real_accessed": False}
    marker = _claim_marker(root, preflight)
    if marker is None:
        return {"status": "blocked", "outcome": "refused_second_invocation", "real_accessed": False, "one_shot_marker_created": False}
    outputs = tuple(root / name for name in (
        "reports/experiments/l_4_breadth_b88r5_scientific_report_v6.json",
        "reports/experiments/l_4_breadth_b88r5_execution_ledger_v6.json",
        "reports/experiments/l_4_breadth_b88r5_execution_attempt_v6.json",
    ))
    if any(path.exists() for path in outputs):
        return {"status": "blocked", "outcome": "refused_existing_output", "real_accessed": False, "one_shot_marker_created": True}
    structural = _read_structural_identities(root, activation)
    if structural is None:
        return {"status": "blocked", "outcome": "refused_provisioned_structural_identity", "real_accessed": False, "one_shot_marker_created": True}
    manifest_raw, manifest, sessions_raw, sessions = structural
    del manifest_raw, manifest, sessions_raw, sessions
    container_path = _safe_path(root, activation["container_path"])
    if container_path is None:
        return {"status": "blocked", "outcome": "refused_container_path", "real_accessed": False, "one_shot_marker_created": True}
    try:
        raw = container_path.read_bytes()
    except OSError:
        return {"status": "blocked", "outcome": "refused_container_read", "real_accessed": False, "one_shot_marker_created": True}
    if hashlib.sha256(raw).hexdigest() != activation["container_sha256"]:
        return {"status": "blocked", "outcome": "refused_container_hash", "real_accessed": True, "one_shot_marker_created": True}
    try:
        container = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {"status": "blocked", "outcome": "refused_container_decode", "real_accessed": True, "one_shot_marker_created": True}
    if container.get("cutoff_inclusive") != activation["cutoff_inclusive"] or container.get("universe") != list(U8) or container.get("sessions") is None:
        return {"status": "blocked", "outcome": "refused_structural_calendar", "real_accessed": True, "one_shot_marker_created": True}
    result = derive(container, config={"u8_sessions": container["sessions"]})
    if result is None:
        return {"status": "blocked", "outcome": "refused_container_contract", "real_accessed": True, "one_shot_marker_created": True}
    identities = preflight.get("runtime_dependency_identities")
    if not isinstance(identities, dict) or not identities or any(not isinstance(path, str) or not isinstance(digest, str) or len(digest) != 64 for path, digest in identities.items()):
        return {"status": "blocked", "outcome": "refused_runtime_dependencies", "real_accessed": True, "one_shot_marker_created": True}
    report = {
        "schema_version": "lily_l4_b88r5_scientific_report_v6",
        "order_id": "B8.8R5",
        "hypothesis_id": "L-4",
        "mode": "future_falsification_only",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "provenance": {
            "producing_commit": preflight["producing_commit"],
            "accepted_gate_head_sha": activation["accepted_gate_head_sha"],
            "hermetic_ci_head_sha": activation["hermetic_ci_head_sha"],
            "hermetic_ci_run_id": activation["hermetic_ci_run_id"],
            "gate_path": GATE,
            "gate_sha256": sha((root / GATE).read_bytes()),
            "activation_path": "experiments/activation_records/l_4_breadth_b88r5_scientific_execution_activation_v6.json",
            "activation_sha256": sha(canonical(activation)),
            "marker_path": MARKER,
            "marker_sha256": hashlib.sha256(marker.read_bytes()).hexdigest(),
            "container_path": activation["container_path"],
            "container_sha256": activation["container_sha256"],
            "structural_manifest_path": activation["structural_manifest_path"],
            "structural_manifest_sha256": activation["structural_manifest_sha256"],
            "u8_sessions_path": activation["u8_sessions_path"],
            "u8_sessions_sha256": activation["u8_sessions_sha256"],
            "u8_members_in_order": activation["u8_members_in_order"],
            "cutoff_inclusive": activation["cutoff_inclusive"],
            "runtime_dependency_identities": identities,
        },
        "validation_seal": SEAL,
        "access_counts": {
            "activation_count": 1,
            "production_execution_count": 1,
            "production_report_count": 1,
            "ledger_count": 1,
            "real_container_read_hash_scan_count": 1,
            "market_return_signal_position_covariance_regime_cost_pnl_count": 1,
            "validation_access_count": 0,
            "provider_network_credentials_broker_paid_paper_real_money_count": 0,
        },
        "container_sha256": activation["container_sha256"],
        "derived": result,
        "outcome": result["outcome"],
    }
    output, ledger, attempt = outputs
    from scripts.validate_l_4_breadth_b88r5_scientific_report_v6 import validate_value

    checked = validate_value(report, container, raw)
    if checked["status"] != "pass":
        return {"status": "blocked", "outcome": "refused_report_validation", "blockers": checked["blockers"], "real_accessed": True, "one_shot_marker_created": True}
    output.write_bytes(canonical(report))
    ledger.write_bytes(canonical({"schema_version": "lily_l4_b88r5_execution_ledger_v6", "report_sha256": sha(canonical(report)), "marker_path": MARKER, "marker_sha256": hashlib.sha256(marker.read_bytes()).hexdigest(), "container_sha256": activation["container_sha256"]}))
    attempt.write_bytes(canonical({"schema_version": "lily_l4_b88r5_execution_attempt_v6", "status": "completed_once", "marker_path": MARKER, "report_sha256": sha(canonical(report))}))
    return {"status": "complete", "outcome": result["outcome"], "report_path": str(output), "ledger_path": str(ledger), "attempt_path": str(attempt), "real_accessed": True, "one_shot_marker_created": True}
