"""Independently recompute and provenance-check a B8.8R4/v5 report."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.l4_b88r4_scientific_engine_v5 import SEAL, derive
from lib.l4_b88r4_lifecycle_v5 import ACTIVATION, GATE, activation_ok, blob, canonical as lifecycle_canonical, dependencies_ok, h40, h64, safe_relative
from scripts.validate_l_4_breadth_b88r4_phase_a_execution_contract_v5 import validate as validate_gate

FIELDS = {"schema_version", "order_id", "hypothesis_id", "mode", "evidence_tier", "edge_claim", "provenance", "validation_seal", "access_counts", "container_sha256", "derived", "outcome"}
PROVENANCE_FIELDS = {"producing_commit", "accepted_gate_head_sha", "hermetic_ci_head_sha", "hermetic_ci_run_id", "gate_path", "gate_sha256", "activation_path", "activation_sha256", "marker_path", "marker_sha256", "container_path", "container_sha256", "structural_manifest_path", "structural_manifest_sha256", "u8_sessions_sha256", "cutoff_inclusive", "runtime_dependency_identities"}
COUNTS = {"activation_count": 1, "production_execution_count": 1, "production_report_count": 1, "ledger_count": 1, "real_container_read_hash_scan_count": 1, "market_return_signal_position_covariance_regime_cost_pnl_count": 1, "validation_access_count": 0, "provider_network_credentials_broker_paid_paper_real_money_count": 0}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _read_exact(path: Path, expected_sha: str | None = None) -> bytes | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    return raw if expected_sha is None or hashlib.sha256(raw).hexdigest() == expected_sha else None


def _common_sessions(payload: dict) -> list[str] | None:
    dates = payload.get("session_dates_by_symbol")
    if not isinstance(dates, dict) or set(dates) != {"VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"}:
        return None
    lists = list(dates.values())
    if not all(isinstance(value, list) and value == sorted(set(value)) for value in lists):
        return None
    return [item for item in dates["VTI"] if all(item in values for values in lists)]


def _provenance_ok(provenance: dict, raw: bytes) -> bool:
    """Check all future-execution identities against the producing commit."""
    commit = provenance.get("producing_commit")
    if not h40(commit):
        return False
    gate_raw = blob(ROOT, commit, GATE)
    activation_raw = blob(ROOT, commit, ACTIVATION)
    if gate_raw is None or activation_raw is None or _read_exact(ROOT / GATE) != gate_raw or _read_exact(ROOT / ACTIVATION) != activation_raw:
        return False
    try:
        gate = json.loads(gate_raw.decode("ascii"))
        activation = json.loads(activation_raw.decode("ascii"))
        marker_raw = _read_exact(ROOT / provenance["marker_path"])
        manifest_raw = _read_exact(ROOT / provenance["structural_manifest_path"])
        manifest = json.loads(manifest_raw.decode("ascii")) if manifest_raw is not None else None
        container_path = ROOT / provenance["container_path"]
    except (UnicodeDecodeError, ValueError, KeyError, TypeError):
        return False
    if not all(safe_relative(provenance.get(key)) for key in ("marker_path", "container_path", "structural_manifest_path")):
        return False
    if marker_raw is None or manifest is None:
        return False
    try:
        marker = json.loads(marker_raw.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return False
    expected_dependencies = {path: item["sha256"] for path, item in gate.get("execution_binding", {}).items() if isinstance(item, dict) and set(item) == {"path", "sha256"} and item.get("path") == path}
    expected_marker = {"schema_version": "lily_l4_b88r4_marker_v5", "producing_commit": commit, "activation_sha256": provenance.get("activation_sha256")}
    sessions = _common_sessions({"session_dates_by_symbol": {symbol: container.get("sessions") for symbol in ()}})  # sentinel: never trust an implicit structural payload
    del sessions
    return (
        validate_gate().get("status") == "pass"
        and provenance["gate_path"] == GATE
        and provenance["gate_sha256"] == hashlib.sha256(gate_raw).hexdigest()
        and provenance["activation_path"] == ACTIVATION
        and provenance["activation_sha256"] == hashlib.sha256(activation_raw).hexdigest()
        and activation_raw == lifecycle_canonical(activation)
        and activation_ok(ROOT, commit) == activation
        and provenance["accepted_gate_head_sha"] == activation.get("accepted_gate_head_sha")
        and provenance["hermetic_ci_head_sha"] == activation.get("hermetic_ci_head_sha")
        and provenance["hermetic_ci_run_id"] == activation.get("hermetic_ci_run_id")
        and provenance["marker_path"] == activation.get("marker_path")
        and provenance["marker_sha256"] == hashlib.sha256(marker_raw).hexdigest()
        and marker == expected_marker and marker_raw == canonical(marker)
        and provenance["container_path"] == activation.get("container_path")
        and provenance["container_sha256"] == hashlib.sha256(raw).hexdigest() == activation.get("container_sha256")
        and container_path.is_file()
        and provenance["structural_manifest_path"] == activation.get("structural_manifest_path")
        and provenance["structural_manifest_sha256"] == hashlib.sha256(manifest_raw).hexdigest() == activation.get("structural_manifest_sha256")
        and manifest == {"schema_version": manifest.get("schema_version"), "dataset_reference": provenance["container_path"], "dataset_sha256": provenance["container_sha256"], "max_session_date": "2015-12-31", "u8_members_in_order": ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"], "validation_seal": SEAL, **{key: value for key, value in manifest.items() if key not in {"schema_version", "dataset_reference", "dataset_sha256", "max_session_date", "u8_members_in_order", "validation_seal"}}}
        and manifest.get("dataset_reference") == provenance["container_path"]
        and manifest.get("dataset_sha256") == provenance["container_sha256"]
        and manifest.get("max_session_date") == "2015-12-31"
        and manifest.get("u8_members_in_order") == ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]
        and manifest.get("validation_seal") == SEAL
        and provenance["u8_sessions_sha256"] == activation.get("u8_sessions_sha256")
        and provenance["runtime_dependency_identities"] == expected_dependencies
        and dependencies_ok(ROOT, commit, gate)
        and blob(ROOT, activation["accepted_gate_head_sha"], GATE) == gate_raw
    )


def _output_artifacts_ok(report: dict) -> bool:
    report_raw = canonical(report)
    paths = {
        "ledger": ROOT / "reports/experiments/l_4_breadth_b88r4_execution_ledger_v5.json",
        "attempt": ROOT / "reports/experiments/l_4_breadth_b88r4_execution_attempt_v5.json",
    }
    try:
        ledger_raw, attempt_raw = paths["ledger"].read_bytes(), paths["attempt"].read_bytes()
        ledger, attempt = json.loads(ledger_raw.decode("ascii")), json.loads(attempt_raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    marker_path = report["provenance"]["marker_path"]
    report_sha = hashlib.sha256(report_raw).hexdigest()
    return (
        ledger_raw == canonical(ledger)
        and attempt_raw == canonical(attempt)
        and ledger == {"schema_version": "lily_l4_b88r4_execution_ledger_v5", "report_sha256": report_sha, "marker_path": marker_path, "marker_sha256": report["provenance"]["marker_sha256"], "container_sha256": report["container_sha256"]}
        and attempt == {"schema_version": "lily_l4_b88r4_execution_attempt_v5", "status": "completed_once", "marker_path": marker_path, "report_sha256": report_sha}
    )


def validate_value(report: dict, container: dict, raw: bytes, *, require_output_artifacts: bool = False) -> dict:
    blockers = []
    if set(report) != FIELDS:
        blockers.append("closed_world")
    if {key: report.get(key) for key in ("schema_version", "order_id", "hypothesis_id", "mode", "evidence_tier", "edge_claim", "validation_seal")} != {"schema_version": "lily_l4_b88r4_scientific_report_v5", "order_id": "B8.8R4", "hypothesis_id": "L-4", "mode": "future_falsification_only", "evidence_tier": "E1", "edge_claim": "none", "validation_seal": SEAL}:
        blockers.append("identity")
    if report.get("access_counts") != COUNTS:
        blockers.append("access_counts")
    provenance = report.get("provenance")
    if not isinstance(provenance, dict) or set(provenance) != PROVENANCE_FIELDS or provenance.get("cutoff_inclusive") != "2015-12-31" or not h40(provenance.get("producing_commit")) or not h40(provenance.get("accepted_gate_head_sha")) or provenance.get("hermetic_ci_head_sha") != provenance.get("accepted_gate_head_sha") or not isinstance(provenance.get("hermetic_ci_run_id"), int) or isinstance(provenance.get("hermetic_ci_run_id"), bool) or provenance["hermetic_ci_run_id"] < 1 or provenance.get("gate_path") != GATE or not all(h64(value) for key, value in provenance.items() if key.endswith("_sha256")) or not isinstance(provenance.get("runtime_dependency_identities"), dict) or not provenance["runtime_dependency_identities"] or not all(isinstance(path, str) and h64(digest) for path, digest in provenance["runtime_dependency_identities"].items()):
        blockers.append("provenance")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != report.get("container_sha256") or not isinstance(provenance, dict) or digest != provenance.get("container_sha256"):
        blockers.append("container_hash")
    if not isinstance(provenance, dict) or not _provenance_ok(provenance, raw):
        blockers.append("provenance_binding")
    # Provenance/contract drift is rejected before any expensive numerical
    # recomputation.  Besides making failure explicit, this prevents a forged
    # report from using a malformed container as an oracle.
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
    except Exception:
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
