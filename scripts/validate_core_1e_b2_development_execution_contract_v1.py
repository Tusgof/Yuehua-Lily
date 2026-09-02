"""Validate the locked, synthetic-only CORE-1E-B2-A execution contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = PROJECT_ROOT / "experiments" / "core_1e_b2_development_execution_contract_v1.json"
HASH64 = re.compile(r"[0-9a-f]{64}\Z")

U8 = ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]
EXPECTED_TOP_LEVEL = {
    "schema_version", "order_id", "work_order_id", "gate_id", "hypothesis_id", "status", "evidence_tier", "edge_claim",
    "owner_authorization_ref", "static_source_bindings", "future_container_identity", "normalized_container_contract",
    "execution_boundaries", "required_future_checks_before_input_decode", "locked_science", "report_contract",
    "authorizations", "access_counts", "stop_conditions",
}
EXPECTED_STATIC_BINDINGS = {
    "core_1p_preregistration": ("experiments/core_1_stable_baseline_preregistration_v1.json", "5003d2360bb8729bcd91a39da34ff2e28c92ad2eb75c9b632c3ee85bcda7682f"),
    "core_1e_a_contract": ("experiments/core_1e_a_phase_a_execution_contract_v1.json", "adcbdbc26d02a287394bbfd5a3893a2d24d027b322e545e7a8b06378a7c35c7d"),
    "accepted_engine": ("lib/core_1e_a_synthetic_engine.py", "f92b39f7f0bbde1361326eff5b16d875a01e9938f16408dedbe0cd80cd9a1487"),
    "core_1e_b1_contract": ("experiments/core_1e_b1_development_execution_contract_v1.json", "adf3169a4d895d17e3e3ea489cc74d66e8a080a2c1ba88267cfb854d6e8ba6e5"),
}
EXPECTED_OWNER = "owner_authorized_core_1e_b2_e0_machinery_only_2026-09-02"
EXPECTED_CONTAINER = {
    "path": "data/normalized/l1_yahoo_daily_v1.json",
    "sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd",
    "size_bytes": 8258827,
    "max_date": "2015-12-31",
    "symbols_in_order": U8,
    "future_only": True,
}
EXPECTED_VALIDATION = {"start": "2016-01-04", "end": "2026-06-30", "status": "sealed_not_accessed", "accessed": False}
EXPECTED_NORMALIZED = {
    "schema_version": "lily_l1_yahoo_daily_v1",
    "container_id": "l1_yahoo_daily_v1",
    "top_level_fields": ["schema_version", "container_id", "symbols_in_order", "rows", "expense_ratios"],
    "row_fields": ["session_date", "observations"],
    "observation_fields": ["total_return_close"],
    "expense_field": "expense_ratios",
    "session_date_format": "ISO-8601 calendar date",
    "session_calendar": "actual NYSE sessions supplied by the container; no sessions manufactured",
    "availability_semantics": "A row is available at its official session close; weekly decisions use only rows through the last actual session of the ISO week and execute on the next supplied actual session.",
    "return_semantics": "total_return_close is the only decoded close field; no price or adjusted-close field is inferred",
    "expense_semantics": "expense_ratios must be explicitly supplied for every U8 symbol as annual decimal ratios; no future value is inferred",
}
EXPECTED_CHECKS = [
    "gate_identity", "exact_ci_head_identity", "gate_blob_hash", "owner_authorization_ref", "future_container_identity",
    "development_cutoff", "activation_schema_and_canonical_bytes", "runtime_byte_hashes", "clean_checkout",
    "prior_one_shot_absence", "container_structure_and_all_session_dates",
]
EXPECTED_AUTHORIZATIONS = {
    "synthetic_fixture_calculation": True, "real_dataset_or_container": False, "real_return_decode": False,
    "validation_window": False, "provider_or_network": False, "credentials": False, "broker_or_account": False,
    "paid": False, "paper_trading": False, "real_money": False, "activation_creation": False,
    "production_report": False, "research_log": False, "core_1e_b2_b": False,
}
EXPECTED_ACCESS_COUNTS = {
    "real_dataset_access": 0, "real_container_access": 0, "real_return_decode": 0, "validation_access": 0,
    "provider_calls": 0, "credential_reads": 0, "broker_actions": 0, "paid_actions": 0,
}
EXPECTED_LOCKED_SCIENCE = {
    "universe_symbols_in_order": U8,
    "candidates_in_order": ["CORE1_DC60", "CORE1_DC120", "CORE1_SMA200"],
    "long_only_cash_only": True,
    "fixed_sleeve_weight": 0.125,
    "no_trade_band": 0.02,
    "weekly_next_actual_session_execution": True,
    "same_close_execution": False,
    "pnl_start": "after_that_execution_close",
    "warmup_qa": {"start": "2006-02-03", "end": "2007-02-02", "performance_claim": False},
    "development": {"start": "2007-02-05", "end": "2015-12-31"},
    "validation": EXPECTED_VALIDATION,
    "primary_costs": {
        "commission_one_way_traded_notional": 0.00107,
        "spread_slippage_one_way": 0.0025,
        "sell_surcharge": 0.0001,
        "etf_expense_accrual": "annual_ratio_divided_by_252_on_held_notional",
        "cash_yield": 0.0,
    },
    "stress_costs": {"execution_multiplier": 2.0, "expense_multiplier": 1.0},
    "reported_paths": ["gross", "primary_net", "two_x_execution_cost_net"],
    "benchmark": "equal_weight_always_long_fixed_sleeves",
    "gates": ["A", "B", "C", "D", "E", "F", "G", "H"],
    "selection": "discard_failed_candidates_then_highest_worst_subperiod_sharpe_with_locked_near_tie_turnover_rule",
    "stop_rule": "No fourth candidate, parameter rescue, universe/date/timing/cost change, validation unlock, or remediation layering.",
}
EXPECTED_REPORT_CONTRACT = {
    "schema_path": "schemas/core_1e_b2_empirical_report_v1.schema.json",
    "schema_version": "lily_core_1e_b2_empirical_report_v1",
    "source_kind": "committed_synthetic_fixture_only",
    "empirical_result_created": False,
    "required_candidate_count": 3,
    "required_gate_count": 8,
    "required_cost_paths": ["primary_net", "two_x_execution_cost_net"],
    "decision_evidence_binding": "validator recomputes the adapter and accepted engine from the committed fixture and compares every closed-world report field",
}
EXPECTED_BOUNDARIES = {
    "mode": "synthetic_only", "allowed_input_ref": "tests/fixtures/core1e_b2/normalized_market_v1.json", "allowed_input_kind": "committed_fixture_only",
    "development_cutoff": "2015-12-31", "reject_on_or_after": "2016-01-04", "validation_boundary": EXPECTED_VALIDATION,
    "marker_first": True, "max_invocations": 1, "retry_allowed": False, "project_activation_creation": False,
    "project_marker_creation": False, "project_attempt_creation": False, "project_report_creation": False,
    "project_result_creation": False, "temporary_git_proof_only": True,
}
EXPECTED_STOP_CONDITIONS = [
    "canonical_activation_absent_or_invalid", "gate_ci_blob_owner_container_or_cutoff_mismatch", "dirty_or_untracked_checkout",
    "validation_boundary_opened", "input_hash_or_identity_mismatch", "input_contains_date_after_2015-12-31",
    "post_cutoff_row_before_return_decode", "forged_report_selection_or_gate_decision", "prior_marker_attempt_or_report_exists",
    "second_execution", "unknown_or_missing_closed_world_field",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exact_keys(value: Any, expected: set[str], label: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        blockers.append(f"{label}_must_be_object")
        return
    blockers.extend(f"{label}_missing:{key}" for key in sorted(expected - set(value)))
    blockers.extend(f"{label}_unknown:{key}" for key in sorted(set(value) - expected))


def _validate_contract(payload: Any, project_root: Path, verify_static: bool) -> list[str]:
    blockers: list[str] = []
    if not isinstance(payload, dict):
        return ["contract_must_be_object"]
    _exact_keys(payload, EXPECTED_TOP_LEVEL, "contract", blockers)
    expected_scalars = {
        "schema_version": "lily_core_1e_b2_development_execution_contract_v1", "order_id": "CORE-1E-B2-A",
        "work_order_id": "CORE-1E-B2-A", "gate_id": "core_1e_b2_development_execution_contract_v1", "hypothesis_id": "L-1",
        "status": "locked_before_execution", "evidence_tier": "E0", "edge_claim": "none", "owner_authorization_ref": EXPECTED_OWNER,
    }
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            blockers.append(f"{key}_changed")
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
    if payload.get("normalized_container_contract") != EXPECTED_NORMALIZED:
        blockers.append("normalized_container_contract_changed")
    if payload.get("execution_boundaries") != EXPECTED_BOUNDARIES:
        blockers.append("execution_boundaries_changed")
    if payload.get("required_future_checks_before_input_decode") != EXPECTED_CHECKS:
        blockers.append("pre_decode_check_order_changed")
    if payload.get("locked_science") != EXPECTED_LOCKED_SCIENCE:
        blockers.append("locked_science_changed")
    if payload.get("report_contract") != EXPECTED_REPORT_CONTRACT:
        blockers.append("report_contract_changed")
    if payload.get("authorizations") != EXPECTED_AUTHORIZATIONS:
        blockers.append("authorizations_changed")
    if payload.get("access_counts") != EXPECTED_ACCESS_COUNTS:
        blockers.append("access_counts_changed")
    if payload.get("stop_conditions") != EXPECTED_STOP_CONDITIONS:
        blockers.append("stop_conditions_changed")
    return sorted(set(blockers))


def validate_contract(
    contract_path: Path | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
    verify_static: bool = True,
) -> dict[str, Any]:
    path = contract_path or DEFAULT_CONTRACT
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [f"contract_unreadable:{exc.__class__.__name__}"], "real_data_accessed": False, "validation_accessed": False}
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
