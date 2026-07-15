from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root
from lib.provenance import file_sha256


DEFAULT_PATH = PROJECT_ROOT / "experiments" / "l_1_corporate_action_scope_decision.json"
B4_4_REPORT = PROJECT_ROOT / "reports" / "data_quality" / "l_1_alpha_vantage_corporate_actions.json"
EXPECTED_B4_4_FILE_SHA256 = "8301c355cf19b74f4af225a5cacf1fde6b9f5702b3aee3aca8cca356ab2b58e3"
EXPECTED_B4_4_DIGEST = "838f8d674e32e9d53b5eb8af25dd5ed04cfa63124724ebb175608d9a3bfec854"


def validate_decision(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        payload = load_json(path)
        b4_4 = load_json(B4_4_REPORT)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"artifact_unreadable:{exc.__class__.__name__}"])

    expected = {
        "schema_version": "lily_l1_corporate_action_scope_decision_v1",
        "order_id": "B4.5",
        "hypothesis_id": "L-1",
        "status": "accepted_owner_decision",
        "evidence_tier": "E1",
        "edge_claim": "none",
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            blockers.append(f"field_mismatch:{field}")

    if file_sha256(B4_4_REPORT) != EXPECTED_B4_4_FILE_SHA256:
        blockers.append("B4_4_file_hash_mismatch")
    basis = payload.get("basis", {})
    if basis.get("b4_4_report_file_sha256") != EXPECTED_B4_4_FILE_SHA256:
        blockers.append("B4_4_basis_file_hash_mismatch")
    if basis.get("b4_4_report_digest_sha256") != EXPECTED_B4_4_DIGEST:
        blockers.append("B4_4_basis_digest_mismatch")
    if b4_4.get("report_digest_sha256") != EXPECTED_B4_4_DIGEST:
        blockers.append("B4_4_report_digest_mismatch")
    if "cannot prove" not in str(basis.get("historical_claim_limit", "")):
        blockers.append("historical_claim_limit_incomplete")

    decision = payload.get("decision", {})
    expected_decision = {
        "l1_status": "scope_restricted_E1",
        "corporate_action_historical_status": "accepted_current_snapshot_limitation",
        "point_in_time_source_search_status": "paused_by_owner",
        "validation_window_status": "sealed_not_accessed",
        "validation_unlock_authorized": False,
        "e2_promotion_authorized": False,
        "paper_trade_authorized_by_this_decision": False,
        "real_money_authorized": False,
    }
    if decision != expected_decision:
        blockers.append("decision_boundary_mismatch")

    paused = payload.get("paused_source_program", {})
    if paused.get("new_corporate_action_provider_search") is not False:
        blockers.append("source_search_must_be_paused")
    if paused.get("paid_corporate_action_data_purchase") is not False:
        blockers.append("paid_source_search_must_be_paused")
    if paused.get("provider_value_selection") != "forbidden_if_selected_by_return_or_performance_impact":
        blockers.append("anti_selection_rule_mismatch")
    if len(paused.get("reopen_triggers", [])) != 4:
        blockers.append("reopen_trigger_inventory_mismatch")

    shadow = payload.get("prospective_shadow_accounting", {})
    expected_shadow = {
        "status": "planned_not_started",
        "required_evidence_tier": "E0",
        "edge_claim": "none",
        "paper_trade_role": "operational_dry_run_only",
        "separate_preregistration_required": True,
        "broker_capability_probe_required_first": True,
        "materiality_threshold_status": "must_be_locked_before_first_observation",
    }
    for field, value in expected_shadow.items():
        if shadow.get(field) != value:
            blockers.append(f"shadow_field_mismatch:{field}")
    if len(shadow.get("comparison_streams_to_lock_later", [])) != 3:
        blockers.append("shadow_stream_inventory_mismatch")
    if len(shadow.get("minimum_fields_to_record", [])) < 10:
        blockers.append("shadow_minimum_field_inventory_incomplete")
    if len(shadow.get("materiality_dimensions_to_preregister", [])) != 5:
        blockers.append("shadow_materiality_inventory_mismatch")
    prohibited = set(shadow.get("prohibited_interpretations", []))
    if prohibited != {
        "strategy edge",
        "historical return correctness",
        "historical discrepancy immateriality",
        "E2 validation",
        "deployment readiness",
    }:
        blockers.append("shadow_prohibited_interpretation_mismatch")
    if "too few relevant events" not in str(shadow.get("insufficient_event_rule", "")):
        blockers.append("insufficient_event_rule_incomplete")

    seal = payload.get("validation_return_seal", {})
    if seal.get("untouched_start") != "2016-01-04" or seal.get("untouched_end") != "2026-06-30":
        blockers.append("validation_window_mismatch")
    if seal.get("status") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
    for field in (
        "prices_opened",
        "adjusted_prices_opened",
        "returns_opened",
        "signals_opened",
        "positions_opened",
        "regimes_opened",
        "benchmarks_opened",
        "pnl_opened",
    ):
        if seal.get(field) is not False:
            blockers.append(f"validation_seal_false_field_mismatch:{field}")
    if "Webull Thailand read-only capability probe" not in str(payload.get("next_safe_action", "")):
        blockers.append("next_safe_action_mismatch")
    return _result(path, blockers)


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "decision_path": relative_to_root(path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Lily B4.5 scope decision.")
    parser.add_argument("--decision", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    result = validate_decision(args.decision)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
