"""Validate the locked, synthetic-only CORE-1E-B1 development contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = PROJECT_ROOT / "experiments" / "core_1e_b1_development_execution_contract_v1.json"
HASH64 = re.compile(r"[0-9a-f]{64}\Z")

EXPECTED_TOP_LEVEL = {
    "schema_version",
    "order_id",
    "work_order_id",
    "gate_id",
    "hypothesis_id",
    "status",
    "evidence_tier",
    "edge_claim",
    "owner_authorization_ref",
    "static_source_bindings",
    "future_container_identity",
    "execution_boundaries",
    "required_future_checks_before_input_decode",
    "authorizations",
    "access_counts",
    "stop_conditions",
}

EXPECTED_STATIC_BINDINGS = {
    "core_1p_preregistration": (
        "experiments/core_1_stable_baseline_preregistration_v1.json",
        "5003d2360bb8729bcd91a39da34ff2e28c92ad2eb75c9b632c3ee85bcda7682f",
    ),
    "core_1e_a_contract": (
        "experiments/core_1e_a_phase_a_execution_contract_v1.json",
        "adcbdbc26d02a287394bbfd5a3893a2d24d027b322e545e7a8b06378a7c35c7d",
    ),
    "accepted_engine": (
        "lib/core_1e_a_synthetic_engine.py",
        "f92b39f7f0bbde1361326eff5b16d875a01e9938f16408dedbe0cd80cd9a1487",
    ),
    "provisioned_manifest": (
        "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json",
        "de00a4b5a5dd732e27a4a9900868a0f696bb80794e04924da9187808311bb008",
    ),
    "u8_session_dates": (
        "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json",
        "f95665db8ad78280433b37e646486ba03954d0eccba13538d41e961ea88c94ef",
    ),
    "provisioning_report": (
        "reports/experiments/l_4_breadth_b86r13_provisioning_report_v15.json",
        "41e35cc1a5f54f5ee45a5eea61f7da18f28bb77d8fd14738668defb1f9f6d846",
    ),
}

EXPECTED_OWNER = "owner_authorized_core_1e_b_development_only_2026-09-01"
EXPECTED_CONTAINER = {
    "path": "data/normalized/l1_yahoo_daily_v1.json",
    "sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd",
    "size_bytes": 8258827,
    "max_date": "2015-12-31",
    "symbols_in_order": ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"],
    "future_only": True,
}
EXPECTED_VALIDATION = {
    "start": "2016-01-04",
    "end": "2026-06-30",
    "status": "sealed_not_accessed",
    "accessed": False,
}
EXPECTED_CHECKS = [
    "gate_identity",
    "exact_ci_head_identity",
    "gate_blob_hash",
    "owner_authorization_ref",
    "future_container_identity",
    "development_cutoff",
]
EXPECTED_AUTHORIZATIONS = {
    "synthetic_fixture_calculation": True,
    "real_dataset_or_container": False,
    "real_return_decode": False,
    "validation_window": False,
    "provider_or_network": False,
    "credentials": False,
    "broker_or_account": False,
    "paid": False,
    "paper_trading": False,
    "real_money": False,
    "activation_creation": False,
    "production_report": False,
    "research_log": False,
    "core_1e_b2": False,
}
EXPECTED_ACCESS_COUNTS = {
    "real_dataset_access": 0,
    "real_container_access": 0,
    "real_return_decode": 0,
    "validation_access": 0,
    "provider_calls": 0,
    "credential_reads": 0,
    "broker_actions": 0,
    "paid_actions": 0,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exact_keys(value: Any, expected: set[str], label: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        blockers.append(f"{label}_must_be_object")
        return
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    blockers.extend(f"{label}_missing:{key}" for key in missing)
    blockers.extend(f"{label}_unknown:{key}" for key in unknown)


def _validate_contract(payload: Any, project_root: Path, verify_static: bool) -> list[str]:
    blockers: list[str] = []
    if not isinstance(payload, dict):
        return ["contract_must_be_object"]
    _exact_keys(payload, EXPECTED_TOP_LEVEL, "contract", blockers)
    if payload.get("schema_version") != "lily_core_1e_b1_development_execution_contract_v1":
        blockers.append("schema_version_changed")
    if payload.get("order_id") != "CORE-1E-B1":
        blockers.append("order_id_changed")
    if payload.get("work_order_id") != "CORE-1E-B1-R2":
        blockers.append("work_order_id_changed")
    if payload.get("gate_id") != "core_1e_b1_development_execution_contract_v1":
        blockers.append("gate_id_changed")
    if payload.get("hypothesis_id") != "L-1":
        blockers.append("hypothesis_id_changed")
    if payload.get("status") != "locked_before_execution":
        blockers.append("status_not_locked_before_execution")
    if payload.get("evidence_tier") != "E0" or payload.get("edge_claim") != "none":
        blockers.append("evidence_claim_boundary_changed")
    if payload.get("owner_authorization_ref") != EXPECTED_OWNER:
        blockers.append("owner_authorization_ref_changed")

    bindings = payload.get("static_source_bindings")
    _exact_keys(bindings, set(EXPECTED_STATIC_BINDINGS), "static_source_bindings", blockers)
    if isinstance(bindings, dict):
        for name, (path, digest) in EXPECTED_STATIC_BINDINGS.items():
            item = bindings.get(name)
            if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
                blockers.append(f"static_binding_shape_changed:{name}")
                continue
            if item.get("path") != path:
                blockers.append(f"static_binding_path_changed:{name}")
            if item.get("sha256") != digest or not HASH64.fullmatch(str(item.get("sha256", ""))):
                blockers.append(f"static_binding_hash_changed:{name}")
            if verify_static:
                target = project_root / path
                if not target.is_file():
                    blockers.append(f"static_binding_missing:{path}")
                elif _sha256(target) != digest:
                    blockers.append(f"static_binding_digest_mismatch:{path}")

    if payload.get("future_container_identity") != EXPECTED_CONTAINER:
        blockers.append("future_container_identity_changed")

    boundaries = payload.get("execution_boundaries")
    expected_boundaries = {
        "mode": "synthetic_only",
        "allowed_input_ref": "tests/fixtures/core1e_a/synthetic_market_v1.json",
        "allowed_input_kind": "committed_fixture_only",
        "development_cutoff": "2015-12-31",
        "reject_on_or_after": "2016-01-04",
        "validation_boundary": EXPECTED_VALIDATION,
        "marker_first": True,
        "max_invocations": 1,
        "retry_allowed": False,
        "project_activation_creation": False,
        "project_marker_creation": False,
        "project_attempt_creation": False,
        "project_report_creation": False,
        "project_result_creation": False,
        "temporary_git_proof_only": True,
    }
    if boundaries != expected_boundaries:
        blockers.append("execution_boundaries_changed")
    if payload.get("required_future_checks_before_input_decode") != EXPECTED_CHECKS:
        blockers.append("pre_decode_check_order_changed")
    if payload.get("authorizations") != EXPECTED_AUTHORIZATIONS:
        blockers.append("authorizations_changed")
    if payload.get("access_counts") != EXPECTED_ACCESS_COUNTS:
        blockers.append("access_counts_changed")
    stops = payload.get("stop_conditions")
    if not isinstance(stops, list) or len(stops) != len(set(stops)) or "second_execution" not in stops:
        blockers.append("stop_conditions_changed")
    return sorted(set(blockers))


def validate_contract(contract_path: Path | None = None, *, project_root: Path = PROJECT_ROOT, verify_static: bool = True) -> dict[str, Any]:
    path = contract_path or (project_root / DEFAULT_CONTRACT.relative_to(PROJECT_ROOT))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "status": "blocked",
            "blockers": [f"contract_unreadable:{exc.__class__.__name__}"],
            "real_data_accessed": False,
            "validation_accessed": False,
        }
    blockers = _validate_contract(payload, project_root, verify_static)
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "contract_path": path.relative_to(project_root).as_posix() if path.is_relative_to(project_root) else str(path),
        "real_data_accessed": False,
        "validation_accessed": False,
        "future_container_checked": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=None)
    parser.add_argument("--no-static-checks", action="store_true")
    args = parser.parse_args()
    result = validate_contract(args.contract, verify_static=not args.no_static_checks)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
