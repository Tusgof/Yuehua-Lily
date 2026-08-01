"""Real future v4 runtime; it is intentionally unreachable in E0 Phase A."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from lib.l4_b88r3_lifecycle_v4 import GATE, MARKER, canonical, sha
from lib.l4_b88r3_scientific_engine_v4 import SEAL, derive


def _claim_marker(root: Path, preflight: dict) -> Path | None:
    marker = root / MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return None
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(canonical({"schema_version":"lily_l4_b88r3_marker_v4","producing_commit":preflight["producing_commit"],"activation_sha256":sha(canonical(preflight["activation"]))}))
        handle.flush(); os.fsync(handle.fileno())
    return marker


def run_one_shot(preflight: dict, *, root: Path) -> dict:
    """Claim first, then exactly one bounded read/hash/decode, with no retry."""
    activation = preflight.get("activation")
    if not preflight.get("ready") or not isinstance(activation, dict):
        return {"status":"blocked","outcome":"refused_preflight","real_accessed":False}
    marker = _claim_marker(root, preflight)
    if marker is None:
        return {"status":"blocked","outcome":"refused_second_invocation","real_accessed":False,"one_shot_marker_created":False}
    outputs = tuple(root / name for name in ("reports/experiments/l_4_breadth_b88r3_scientific_report_v4.json", "reports/experiments/l_4_breadth_b88r3_execution_ledger_v4.json", "reports/experiments/l_4_breadth_b88r3_execution_attempt_v4.json"))
    if any(path.exists() for path in outputs):
        return {"status":"blocked","outcome":"refused_existing_output","real_accessed":False,"one_shot_marker_created":True}
    manifest_path = (root / activation["structural_manifest_path"]).resolve()
    if root not in manifest_path.parents or str(manifest_path.relative_to(root)).replace("\\", "/") != activation["structural_manifest_path"]:
        return {"status":"blocked","outcome":"refused_manifest_path","real_accessed":False,"one_shot_marker_created":True}
    try:
        manifest_raw = manifest_path.read_bytes(); manifest = json.loads(manifest_raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {"status":"blocked","outcome":"refused_manifest_read","real_accessed":False,"one_shot_marker_created":True}
    if hashlib.sha256(manifest_raw).hexdigest() != activation["structural_manifest_sha256"] or manifest.get("dataset_reference") != activation["container_path"] or manifest.get("dataset_sha256") != activation["container_sha256"] or manifest.get("max_session_date") != "2015-12-31":
        return {"status":"blocked","outcome":"refused_manifest_identity","real_accessed":False,"one_shot_marker_created":True}
    path = (root / activation["container_path"]).resolve()
    if root not in path.parents or str(path.relative_to(root)).replace("\\", "/") != activation["container_path"]:
        return {"status":"blocked","outcome":"refused_container_path","real_accessed":False,"one_shot_marker_created":True}
    # The sole container operation follows the atomic claim.  Post-cutoff is
    # rejected by the decoder's structural checks before any derived value is used.
    try:
        raw = path.read_bytes()
    except OSError:
        return {"status":"blocked","outcome":"refused_container_read","real_accessed":False,"one_shot_marker_created":True}
    if hashlib.sha256(raw).hexdigest() != activation["container_sha256"]:
        return {"status":"blocked","outcome":"refused_container_hash","real_accessed":True,"one_shot_marker_created":True}
    try:
        container = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {"status":"blocked","outcome":"refused_container_decode","real_accessed":True,"one_shot_marker_created":True}
    sessions = container.get("sessions")
    if not isinstance(sessions, list) or hashlib.sha256(canonical(sessions)).hexdigest() != activation["u8_sessions_sha256"] or container.get("cutoff_inclusive") != "2015-12-31":
        return {"status":"blocked","outcome":"refused_structural_calendar","real_accessed":True,"one_shot_marker_created":True}
    result = derive(container, config={"u8_sessions": sessions})
    if result is None:
        return {"status":"blocked","outcome":"refused_container_contract","real_accessed":True,"one_shot_marker_created":True}
    runtime_files=("lib/l4_b88r3_scientific_engine_v4.py","lib/l4_b88r3_lifecycle_v4.py","scripts/run_l_4_breadth_b88r3_scientific_execution_v4.py","scripts/validate_l_4_breadth_b88r3_scientific_report_v4.py")
    identities={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in runtime_files}
    report = {"schema_version":"lily_l4_b88r3_scientific_report_v4","order_id":"B8.8R3","hypothesis_id":"L-4","mode":"future_falsification_only","evidence_tier":"E1","edge_claim":"none","provenance":{"producing_commit":preflight["producing_commit"],"accepted_gate_head_sha":activation["accepted_gate_head_sha"],"hermetic_ci_head_sha":activation["hermetic_ci_head_sha"],"hermetic_ci_run_id":activation["hermetic_ci_run_id"],"gate_path":GATE,"gate_sha256":sha((root/GATE).read_bytes()),"activation_path":"experiments/activation_records/l_4_breadth_b88r3_scientific_execution_activation_v4.json","activation_sha256":sha(canonical(activation)),"marker_path":MARKER,"marker_sha256":hashlib.sha256(marker.read_bytes()).hexdigest(),"container_path":activation["container_path"],"container_sha256":activation["container_sha256"],"structural_manifest_path":activation["structural_manifest_path"],"structural_manifest_sha256":activation["structural_manifest_sha256"],"u8_sessions_sha256":activation["u8_sessions_sha256"],"cutoff_inclusive":"2015-12-31","runtime_dependency_identities":identities},"validation_seal":SEAL,"access_counts":{"activation_count":1,"production_execution_count":1,"production_report_count":1,"ledger_count":1,"real_container_read_hash_scan_count":1,"market_return_signal_position_covariance_regime_cost_pnl_count":1,"validation_access_count":0,"provider_network_credentials_broker_paid_paper_real_money_count":0},"container_sha256":activation["container_sha256"],"derived":result,"outcome":result["outcome"]}
    output, ledger, attempt = outputs
    from scripts.validate_l_4_breadth_b88r3_scientific_report_v4 import validate_value
    checked = validate_value(report, container, raw)
    if checked["status"] != "pass":
        return {"status":"blocked","outcome":"refused_report_validation","blockers":checked["blockers"],"real_accessed":True,"one_shot_marker_created":True}
    output.write_bytes(canonical(report)); ledger.write_bytes(canonical({"report_sha256":sha(canonical(report)),"marker_path":MARKER,"container_sha256":activation["container_sha256"]})); attempt.write_bytes(canonical({"status":"completed_once","marker_path":MARKER}))
    return {"status":"complete","outcome":result["outcome"],"report_path":str(output),"ledger_path":str(ledger),"attempt_path":str(attempt),"real_accessed":True,"one_shot_marker_created":True}
