"""Independently validate a future B8.8R5/v6 report.

The CLI is a future-only path.  The unit-testable ``validate_value`` function
accepts synthetic in-memory containers, while the production CLI reads only
the explicitly supplied report/container paths after activation provenance has
been checked.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.l4_b88r5_lifecycle_v6 import (  # noqa: E402
    ACTIVATION,
    GATE,
    MARKER,
    SEAL,
    activation_ok,
    blob,
    canonical as lifecycle_canonical,
    dependencies_ok,
    h40,
    h64,
    safe_relative,
)
from lib.l4_b88r5_scientific_engine_v6 import U8, derive  # noqa: E402
from scripts.validate_l_4_breadth_b88r5_phase_a_execution_contract_v6 import validate as validate_gate  # noqa: E402

FIELDS = {
    "schema_version", "order_id", "hypothesis_id", "mode", "evidence_tier", "edge_claim",
    "provenance", "validation_seal", "access_counts", "container_sha256", "derived", "outcome",
}
PROVENANCE_FIELDS = {
    "producing_commit", "accepted_gate_head_sha", "hermetic_ci_head_sha", "hermetic_ci_run_id",
    "gate_path", "gate_sha256", "activation_path", "activation_sha256", "marker_path",
    "marker_sha256", "container_path", "container_sha256", "structural_manifest_path",
    "structural_manifest_sha256", "u8_sessions_path", "u8_sessions_sha256", "u8_members_in_order",
    "cutoff_inclusive", "runtime_dependency_identities",
}
COUNTS = {
    "activation_count": 1,
    "production_execution_count": 1,
    "production_report_count": 1,
    "ledger_count": 1,
    "real_container_read_hash_scan_count": 1,
    "market_return_signal_position_covariance_regime_cost_pnl_count": 1,
    "validation_access_count": 0,
    "provider_network_credentials_broker_paid_paper_real_money_count": 0,
}


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_exact(path: Path, expected_sha: str | None = None) -> bytes | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    return raw if expected_sha is None or digest(raw) == expected_sha else None


def _provenance_ok(provenance: dict[str, Any], raw: bytes) -> bool:
    commit = provenance.get("producing_commit")
    if not h40(commit) or not all(safe_relative(provenance.get(key)) for key in ("gate_path", "activation_path", "marker_path", "container_path", "structural_manifest_path", "u8_sessions_path")):
        return False
    gate_raw = blob(ROOT, commit, GATE)
    activation_raw = blob(ROOT, commit, ACTIVATION)
    if gate_raw is None or activation_raw is None:
        return False
    if _read_exact(ROOT / GATE) != gate_raw or _read_exact(ROOT / ACTIVATION) != activation_raw:
        return False
    try:
        gate = json.loads(gate_raw.decode("ascii"))
        activation = json.loads(activation_raw.decode("ascii"))
        marker_raw = _read_exact(ROOT / provenance["marker_path"])
        manifest_raw = _read_exact(ROOT / provenance["structural_manifest_path"], provenance["structural_manifest_sha256"])
        sessions_raw = _read_exact(ROOT / provenance["u8_sessions_path"], provenance["u8_sessions_sha256"])
        marker = json.loads(marker_raw.decode("ascii")) if marker_raw is not None else None
        manifest = json.loads(manifest_raw.decode("ascii")) if manifest_raw is not None else None
        sessions = json.loads(sessions_raw.decode("ascii")) if sessions_raw is not None else None
    except (UnicodeDecodeError, ValueError, KeyError, TypeError):
        return False
    expected_dependencies = {
        path: item["sha256"]
        for path, item in gate.get("execution_binding", {}).items()
        if isinstance(item, dict) and set(item) == {"path", "sha256"} and item.get("path") == path
    }
    expected_marker = {
        "schema_version": "lily_l4_b88r5_marker_v6",
        "producing_commit": commit,
        "activation_sha256": provenance.get("activation_sha256"),
    }
    return (
        validate_gate().get("status") == "pass"
        and provenance.get("gate_path") == GATE
        and provenance.get("gate_sha256") == digest(gate_raw)
        and provenance.get("activation_path") == ACTIVATION
        and provenance.get("activation_sha256") == digest(activation_raw)
        and activation_raw == lifecycle_canonical(activation)
        and activation_ok(ROOT, commit) == activation
        and provenance.get("accepted_gate_head_sha") == activation.get("accepted_gate_head_sha")
        and provenance.get("hermetic_ci_head_sha") == activation.get("hermetic_ci_head_sha")
        and provenance.get("hermetic_ci_run_id") == activation.get("hermetic_ci_run_id")
        and provenance.get("marker_path") == activation.get("marker_path") == MARKER
        and marker_raw is not None
        and provenance.get("marker_sha256") == digest(marker_raw)
        and marker == expected_marker
        and marker_raw == canonical(marker)
        and provenance.get("container_path") == activation.get("container_path") == "data/normalized/l1_yahoo_daily_v1.json"
        and provenance.get("container_sha256") == activation.get("container_sha256")
        and provenance.get("container_sha256") == digest(raw)
        and provenance.get("structural_manifest_path") == activation.get("structural_manifest_path")
        and provenance.get("structural_manifest_sha256") == activation.get("structural_manifest_sha256")
        and provenance.get("u8_sessions_path") == activation.get("u8_sessions_path")
        and provenance.get("u8_sessions_sha256") == activation.get("u8_sessions_sha256")
        and provenance.get("u8_members_in_order") == list(U8)
        and provenance.get("cutoff_inclusive") == "2015-12-31"
        and isinstance(manifest, dict)
        and manifest.get("dataset_reference") == provenance.get("container_path")
        and manifest.get("dataset_sha256") == provenance.get("container_sha256")
        and manifest.get("max_session_date") == "2015-12-31"
        and manifest.get("u8_members_in_order") == list(U8)
        and manifest.get("validation_seal") == SEAL
        and isinstance(sessions, dict)
        and sessions.get("dataset_sha256") == provenance.get("container_sha256")
        and sessions.get("u8_members_in_order") == list(U8)
        and isinstance(sessions.get("session_dates_by_symbol"), dict)
        and set(sessions["session_dates_by_symbol"]) == set(U8)
        and provenance.get("runtime_dependency_identities") == expected_dependencies
        and dependencies_ok(ROOT, commit, gate)
        and blob(ROOT, activation.get("accepted_gate_head_sha"), GATE) == gate_raw
    )


def _output_artifacts_ok(report: dict[str, Any]) -> bool:
    report_raw = canonical(report)
    report_sha = digest(report_raw)
    try:
        ledger_raw = (ROOT / "reports/experiments/l_4_breadth_b88r5_execution_ledger_v6.json").read_bytes()
        attempt_raw = (ROOT / "reports/experiments/l_4_breadth_b88r5_execution_attempt_v6.json").read_bytes()
        ledger = json.loads(ledger_raw.decode("ascii"))
        attempt = json.loads(attempt_raw.decode("ascii"))
        marker_raw = (ROOT / report["provenance"]["marker_path"]).read_bytes()
    except (OSError, UnicodeDecodeError, ValueError, KeyError):
        return False
    marker_sha = digest(marker_raw)
    return (
        ledger_raw == canonical(ledger)
        and attempt_raw == canonical(attempt)
        and ledger == {
            "schema_version": "lily_l4_b88r5_execution_ledger_v6",
            "report_sha256": report_sha,
            "marker_path": report["provenance"]["marker_path"],
            "marker_sha256": marker_sha,
            "container_sha256": report["container_sha256"],
        }
        and attempt == {
            "schema_version": "lily_l4_b88r5_execution_attempt_v6",
            "status": "completed_once",
            "marker_path": report["provenance"]["marker_path"],
            "report_sha256": report_sha,
        }
    )


def validate_value(report: dict[str, Any], container: dict[str, Any], raw: bytes, *, require_output_artifacts: bool = False) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(report, dict) or set(report) != FIELDS:
        blockers.append("closed_world")
    if not isinstance(report, dict) or {key: report.get(key) for key in ("schema_version", "order_id", "hypothesis_id", "mode", "evidence_tier", "edge_claim", "validation_seal")} != {
        "schema_version": "lily_l4_b88r5_scientific_report_v6",
        "order_id": "B8.8R5", "hypothesis_id": "L-4", "mode": "future_falsification_only",
        "evidence_tier": "E1", "edge_claim": "none", "validation_seal": SEAL,
    }:
        blockers.append("identity")
    if not isinstance(report, dict) or report.get("access_counts") != COUNTS:
        blockers.append("access_counts")
    provenance = report.get("provenance") if isinstance(report, dict) else None
    if not isinstance(provenance, dict) or set(provenance) != PROVENANCE_FIELDS or provenance.get("u8_members_in_order") != list(U8) or provenance.get("cutoff_inclusive") != "2015-12-31" or not h40(provenance.get("producing_commit")) or not h40(provenance.get("accepted_gate_head_sha")) or provenance.get("hermetic_ci_head_sha") != provenance.get("accepted_gate_head_sha") or not isinstance(provenance.get("hermetic_ci_run_id"), int) or isinstance(provenance["hermetic_ci_run_id"], bool) or provenance["hermetic_ci_run_id"] < 1 or provenance.get("gate_path") != GATE or not all(h64(value) for key, value in provenance.items() if key.endswith("_sha256")) or not isinstance(provenance.get("runtime_dependency_identities"), dict) or not provenance["runtime_dependency_identities"] or not all(isinstance(path, str) and h64(value) for path, value in provenance["runtime_dependency_identities"].items()):
        blockers.append("provenance")
    if not isinstance(raw, bytes) or digest(raw) != report.get("container_sha256") or not isinstance(provenance, dict) or digest(raw) != provenance.get("container_sha256"):
        blockers.append("container_hash")
    if not isinstance(provenance, dict) or not _provenance_ok(provenance, raw):
        blockers.append("provenance_binding")
    if blockers:
        return {"status": "blocked", "blockers": sorted(set(blockers))}
    derived = derive(container, config={"u8_sessions": container.get("sessions")})
    if derived is None or report.get("derived") != derived:
        blockers.append("derived")
    elif report.get("outcome") != derived["outcome"]:
        blockers.append("outcome")
    if require_output_artifacts and not _output_artifacts_ok(report):
        blockers.append("output_artifacts")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


def validate(report_path: Path, container_path: Path | None = None) -> dict:
    try:
        report_raw = Path(report_path).read_bytes()
        report = json.loads(report_raw.decode("ascii"))
        path = Path(container_path or ROOT / report.get("provenance", {}).get("container_path", ""))
        raw = path.read_bytes()
        container = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        return {"status": "blocked", "blockers": ["unreadable_or_container"]}
    result = validate_value(report, container, raw, require_output_artifacts=True)
    if report_raw != canonical(report):
        result = {"status": "blocked", "blockers": sorted(set(result["blockers"] + ["report_not_canonical"]))}
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--container", type=Path)
    args = parser.parse_args()
    result = validate(args.report, args.container)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
