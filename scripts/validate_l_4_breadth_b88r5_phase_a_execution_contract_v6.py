"""Validate the B8.8R5/v6 E0 gate without touching the real container."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/l_4_breadth_b88r5_phase_a_execution_contract_v6.json"
MARKER = ROOT / "reports/experiments/l_4_breadth_b88r5_one_shot_marker_v6.json"
SEAL = {"status": "sealed_not_accessed", "accessed": False}
U8 = ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]
U4 = ["VTI", "IEF", "GLD", "DBC"]
PROVISIONED_IDENTITY = {
    "container": {
        "path": "data/normalized/l1_yahoo_daily_v1.json",
        "sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd",
    },
    "structural_manifest": {
        "path": "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json",
        "sha256": "de00a4b5a5dd732e27a4a9900868a0f696bb80794e04924da9187808311bb008",
        "schema_version": "lily_l4_b86r13_falsification_manifest_v15",
        "dataset_reference": "data/normalized/l1_yahoo_daily_v1.json",
        "dataset_sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd",
        "max_session_date": "2015-12-31",
        "u8_members_in_order": U8,
        "validation_seal": SEAL,
    },
    "u8_sessions": {
        "path": "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json",
        "sha256": "f95665db8ad78280433b37e646486ba03954d0eccba13538d41e961ea88c94ef",
        "schema_version": "lily_l4_b86r13_u8_session_dates_v15",
        "dataset_sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd",
        "u8_members_in_order": U8,
    },
    "u8_members_in_order": U8,
    "cutoff_inclusive": "2015-12-31",
}
REQUIRED = {
    "schema_version", "order_id", "gate_id", "supersedes_gate_id", "hypothesis_id",
    "status", "evidence_ceiling", "edge_claim", "owner_literal", "inspector_rejection",
    "sources", "science", "provisioned_identity", "decision_vectors", "activation",
    "execution_dependencies", "execution_binding", "validation_seal", "authorizations",
    "access_counts", "hard_stops",
}
EXPECTED_IDENTITY = {
    "schema_version": "lily_l4_b88r5_phase_a_execution_contract_v6",
    "order_id": "B8.8R5",
    "gate_id": "l_4_breadth_b88r5_phase_a_execution_contract_v6",
    "supersedes_gate_id": "l_4_breadth_b88r4_phase_a_execution_contract_v5",
    "hypothesis_id": "L-4",
    "status": "locked_E0_future_contract_v6",
    "evidence_ceiling": "E0",
    "edge_claim": "none",
    "owner_literal": "continue the work till we complete L4",
}
EXPECTED_SCIENCE = {
    "preregistration_path": "experiments/l_4_breadth_preregistration_v4.json",
    "universe": U8,
    "u4": U4,
    "cutoff_inclusive": "2015-12-31",
    "timing": "actual last eligible U8 weekly session; next U8 common/NYSE session; next 20 sessions strictly after execution",
    "breakdown_contract": {
        "dimensions": ["asset", "macro_sleeve", "country_or_region"],
        "asset": "dominant U8 component-risk share; ties use U8 order",
        "macro_sleeve": "dominant U8 grouped macro-sleeve component-risk share; ties use fixed sleeve order",
        "country_or_region": "dominant U8 region component-risk share; ties use fixed region order",
        "assignment": "each paired week belongs to exactly one bucket in each breakdown dimension; no full-sample duplication",
    },
}
EXPECTED_ACTIVATION = {
    "path": "experiments/activation_records/l_4_breadth_b88r5_scientific_execution_activation_v6.json",
    "schema_version": "lily_l4_b88r5_activation_v6",
    "marker_path": MARKER.relative_to(ROOT).as_posix(),
    "gate_owns_schema_owner_literal_and_provisioned_identity": True,
    "one_read_after_atomic_marker_only": True,
    "no_retry": True,
}
EXPECTED_AUTHORIZATIONS = {
    "data": False, "container": False, "market": False, "return": False,
    "signal": False, "position": False, "covariance": False, "regime": False,
    "cost": False, "pnl": False, "validation": False, "provider": False,
    "network": False, "credentials": False, "broker": False, "paid": False,
    "paper_trade": False, "real_money": False, "activation": False,
    "execution": False, "report": False, "research_decision": False, "ledger": False,
}
EXPECTED_COUNTS = {
    "activation_count": 0, "production_execution_count": 0, "production_report_count": 0,
    "ledger_count": 0, "real_container_read_hash_scan_count": 0,
    "market_return_signal_position_covariance_regime_cost_pnl_count": 0,
    "validation_access_count": 0,
    "provider_network_credentials_broker_paid_paper_real_money_count": 0,
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _h64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _safe_relative(value: object) -> bool:
    path = Path(value) if isinstance(value, str) else None
    return path is not None and not path.is_absolute() and ".." not in path.parts and path.as_posix() == value


def _file_binding(blockers: list[str], mapping: dict[str, str], *, forbid: set[str] | None = None) -> None:
    for relative, expected in mapping.items():
        if forbid and relative in forbid:
            blockers.append(f"forbidden_source:{relative}")
        if not _safe_relative(relative) or not _h64(expected):
            blockers.append(f"invalid_source_binding:{relative}")
            continue
        path = ROOT / relative
        if not path.is_file():
            blockers.append(f"missing_source:{relative}")
        else:
            try:
                if sha(path) != expected:
                    blockers.append(f"source_hash_mismatch:{relative}")
            except OSError:
                blockers.append(f"unreadable_source:{relative}")


def _structural_artifacts_ok(gate: dict) -> bool:
    identity = gate.get("provisioned_identity")
    if identity != PROVISIONED_IDENTITY:
        return False
    manifest_path = ROOT / PROVISIONED_IDENTITY["structural_manifest"]["path"]
    sessions_path = ROOT / PROVISIONED_IDENTITY["u8_sessions"]["path"]
    try:
        manifest_raw = manifest_path.read_bytes()
        sessions_raw = sessions_path.read_bytes()
        manifest = json.loads(manifest_raw.decode("ascii"))
        sessions = json.loads(sessions_raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    dates = sessions.get("session_dates_by_symbol")
    return (
        sha(manifest_path) == PROVISIONED_IDENTITY["structural_manifest"]["sha256"]
        and sha(sessions_path) == PROVISIONED_IDENTITY["u8_sessions"]["sha256"]
        and manifest.get("schema_version") == PROVISIONED_IDENTITY["structural_manifest"]["schema_version"]
        and manifest.get("dataset_reference") == PROVISIONED_IDENTITY["container"]["path"]
        and manifest.get("dataset_sha256") == PROVISIONED_IDENTITY["container"]["sha256"]
        and manifest.get("max_session_date") == "2015-12-31"
        and manifest.get("u8_members_in_order") == U8
        and manifest.get("validation_seal") == SEAL
        and sessions.get("schema_version") == PROVISIONED_IDENTITY["u8_sessions"]["schema_version"]
        and sessions.get("dataset_sha256") == PROVISIONED_IDENTITY["container"]["sha256"]
        and sessions.get("u8_members_in_order") == U8
        and isinstance(dates, dict)
        and set(dates) == set(U8)
        and all(isinstance(value, list) and value == sorted(set(value)) for value in dates.values())
    )


def validate() -> dict:
    blockers: list[str] = []
    try:
        value = json.loads(GATE.read_text("ascii"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {"status": "blocked", "blockers": ["unreadable"]}
    if set(value) != REQUIRED:
        blockers.append("closed_world")
    if any(value.get(key) != expected for key, expected in EXPECTED_IDENTITY.items()):
        blockers.append("identity")
    if value.get("validation_seal") != SEAL or value.get("authorizations") != EXPECTED_AUTHORIZATIONS or value.get("access_counts") != EXPECTED_COUNTS:
        blockers.append("seals")
    if value.get("science") != EXPECTED_SCIENCE:
        blockers.append("science")
    if value.get("activation") != EXPECTED_ACTIVATION:
        blockers.append("future_contract")
    if not _structural_artifacts_ok(value):
        blockers.append("provisioned_identity")
    sources = value.get("sources")
    if not isinstance(sources, dict) or not sources:
        blockers.append("sources")
    else:
        _file_binding(blockers, sources, forbid={PROVISIONED_IDENTITY["container"]["path"]})
    vectors = value.get("decision_vectors")
    if not isinstance(vectors, dict) or not _safe_relative(vectors.get("path")) or not _h64(vectors.get("sha256")):
        blockers.append("decision_vectors")
    elif not (ROOT / vectors["path"]).is_file() or sha(ROOT / vectors["path"]) != vectors["sha256"]:
        blockers.append("decision_vectors")
    dependencies = value.get("execution_dependencies")
    binding = value.get("execution_binding")
    if not isinstance(dependencies, list) or not dependencies or not isinstance(binding, dict) or set(dependencies) != set(binding):
        blockers.append("execution_binding")
    else:
        expected = {path: item.get("sha256") for path, item in binding.items() if isinstance(item, dict) and item.get("path") == path}
        if set(expected) != set(dependencies):
            blockers.append("execution_binding")
        else:
            _file_binding(blockers, expected)
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers)), "gate_sha256": sha(GATE)}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
