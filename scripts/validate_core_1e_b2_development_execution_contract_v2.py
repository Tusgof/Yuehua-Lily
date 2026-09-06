"""Validate the locked CORE-1E-B2-A-R1 contract without touching real data."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json


DEFAULT_CONTRACT = PROJECT_ROOT / "experiments" / "core_1e_b2_development_execution_contract_v2.json"
HASH64 = re.compile(r"^[0-9a-f]{64}$")
U8 = ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]
CANDIDATES = ["CORE1_DC60", "CORE1_DC120", "CORE1_SMA200"]
EXPECTED_CONTRACT_SHA256 = "eb3ed13a2036f83f72a6092193b876e632764f99dfb9dd467984d5de670397d2"
EXPECTED_OWNER = "owner_authorized_core_1e_b2_e0_machinery_only_2026-09-03"
EXPECTED_VALIDATION = {
    "start": "2016-01-04",
    "end": "2026-06-30",
    "status": "sealed_not_accessed",
    "accessed": False,
}
EXPECTED_FINAL_VALIDATION = {"status": "sealed_not_accessed", "accessed": False}
EXPECTED_WINDOWS = {
    "warmup_qa": {"start": "2006-02-03", "end": "2007-02-02", "performance_claim": False},
    "development": {"start": "2007-02-05", "end": "2015-12-31", "mode": "future_e1_development_only"},
    "validation": EXPECTED_VALIDATION | {"forbidden": ["read", "scan", "hash", "count", "infer"]},
}
EXPECTED_NORMALIZED_CONTRACT = {
    "top_level_schema_version": "lily_l1_daily_dataset_v1",
    "top_level_fields": ["schema_version", "acquired_at", "cutoff_inclusive", "symbols"],
    "per_symbol_schema_version": "lily_yahoo_daily_normalized_v1",
    "per_symbol_fields": ["schema_version", "provider", "symbol", "legal_inception", "coverage", "records", "limitations"],
    "coverage_fields": ["start", "end"],
    "record_fields": ["session_date", "availability_timestamp", "raw_close", "cash_distribution", "split", "total_return_close", "trading_currency", "provider_revision", "is_backfilled"],
    "decoded_return_field": "total_return_close",
    "raw_close_decoded": False,
    "adjusted_close_inferred": False,
    "expense_ratios_field_present": False,
    "u8_membership_and_order": U8,
    "common_session_intersection": "set intersection of each symbol records, emitted in VTI record order; no sessions manufactured",
    "availability_timestamp_semantics": "lib/yahoo_daily.py normalizer convention: fixed 16:00 America/New_York label for each session_date; conservative on exchange early-close sessions; not an assertion that every official NYSE close occurs at 16:00; timestamp date must equal session_date",
    "date_rule": "every symbol record session_date is canonical ISO date, sorted unique, on or before cutoff_inclusive, and after legal_inception",
    "cutoff_rule": "cutoff_inclusive must equal 2015-12-31 and every record is rejected before return-value conversion if it is later",
}
EXPECTED_EXPENSE_CONTRACT = {
    "path": "experiments/inputs/core_1e_b2_expense_ratios_v1.json",
    "schema_version": "lily_core_1e_etf_expense_input_v1",
    "input_id": "core_1e_b2r1_etf_expense_ratios_v1",
    "source_path": "lib/trend_baseline.py",
    "source_sha256": "c2ea3a7462a88bb18bb3814d618f6738a9f1024c28cb5b50074184b05d648d28",
    "source_symbol": "CURRENT_EXPENSE_RATIOS",
    "values": {"VTI": 0.0003, "VGK": 0.0006, "EWJ": 0.005, "VWO": 0.0007, "IEF": 0.0015, "TIP": 0.0018, "GLD": 0.004, "DBC": 0.0085},
    "separate_from_yahoo_container": True,
    "current_proxy": True,
    "point_in_time": False,
    "limitation": "Current proxy expense ratios are not point-in-time historical observations; this limitation remains explicit in the future report contract.",
}
EXPECTED_FUTURE_EXECUTION = {
    "mode": "e1_empirical_development_only",
    "activation_required": True,
    "activation_reference_requirement": "separate owner-approved CORE-1E-B2-B activation reference",
    "owner_approval_must_be_distinct_from_r1": True,
    "development_window_only": True,
    "final_validation": EXPECTED_FINAL_VALIDATION,
    "edge_claim": "none",
    "real_access_in_r1": False,
    "report_mode": "lily_core_1e_b2_empirical_report_v2",
}
EXPECTED_LIFECYCLE_BINDING = {
    "activation_schema": "lily_core_1e_b2_activation_v2",
    "active_gate_id": "core_1e_b2_development_execution_contract_v2",
    "required_bindings": ["real_container_path_hash_size", "active_gate_and_blob", "accepted_gate_commit", "exact_sha_ci_head_and_run", "exact_runtime_bytes", "clean_tracked_and_untracked_checkout", "marker_first_atomic_claim", "attempt_identity", "report_identity", "one_shot_second_run_refusal"],
    "one_shot_paths": {"marker_path": "reports/experiments/core_1e_b2r1_one_shot_marker_v2.json", "attempt_path": "reports/experiments/core_1e_b2r1_execution_attempt_v2.json", "report_path": "reports/experiments/core_1e_b2r1_execution_report_v2.json"},
    "activation_record_present": False,
    "project_marker_present": False,
    "project_attempt_present": False,
    "project_report_present": False,
}
EXPECTED_REPORT_CONTRACT = {
    "schema_version": "lily_core_1e_b2_empirical_report_v2",
    "schema_path": "schemas/core_1e_b2_empirical_report_v2.schema.json",
    "source_kind": "committed_synthetic_fixture_only",
    "empirical_result_created": False,
    "required_candidate_count": 3,
    "required_gate_count": 8,
    "required_cost_paths": ["gross", "primary_net", "two_x_execution_cost_net"],
    "closed_world": True,
    "recompute_material_decisions": True,
    "independently_verified_hashes": ["contract", "normalized_fixture", "expense_input", "yahoo_normalizer", "engine", "adapter"],
    "expense_ratios_embedded_in_yahoo_container": False,
    "final_validation_sealed": True,
    "edge_claim": "none",
}
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
    "core_1e_b2_b": False,
}
EXPECTED_STOP_CONDITIONS = ["actual_yahoo_schema_ambiguity", "expense_provenance_ambiguity", "timing_ambiguity", "real_container_or_validation_access_needed", "protected_or_unrelated_dirty_state", "validator_or_locked_science_weakening", "two_focused_implementation_failures", "unrelated_full_suite_failure", "cp_a_not_satisfied", "canonical_activation_missing_or_invalid", "dirty_or_untracked_checkout", "forged_report_decision", "prior_one_shot_artifact", "second_execution", "core_1e_b2_b_without_separate_owner_activation"]
EXPECTED_CONTAINER = {
    "path": "data/normalized/l1_yahoo_daily_v1.json",
    "sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd",
    "size_bytes": 8258827,
    "max_date": "2015-12-31",
    "symbols_in_order": U8,
    "future_only": True,
}
EXPECTED_STATIC_BINDINGS = {
    "core_1p_preregistration": ("experiments/core_1_stable_baseline_preregistration_v1.json", "5003d2360bb8729bcd91a39da34ff2e28c92ad2eb75c9b632c3ee85bcda7682f"),
    "core_1e_a_contract": ("experiments/core_1e_a_phase_a_execution_contract_v1.json", "adcbdbc26d02a287394bbfd5a3893a2d24d027b322e545e7a8b06378a7c35c7d"),
    "core_1e_b1_contract": ("experiments/core_1e_b1_development_execution_contract_v1.json", "adf3169a4d895d17e3e3ea489cc74d66e8a080a2c1ba88267cfb854d6e8ba6e5"),
    "accepted_engine": ("lib/core_1e_a_synthetic_engine.py", "f92b39f7f0bbde1361326eff5b16d875a01e9938f16408dedbe0cd80cd9a1487"),
    "yahoo_normalizer": ("lib/yahoo_daily.py", "c0e94c8e3b2dc11b4022ba6b93418c4d65a1305027d2bfe099c69e243b899417"),
    "expense_source": ("lib/trend_baseline.py", "c2ea3a7462a88bb18bb3814d618f6738a9f1024c28cb5b50074184b05d648d28"),
    "expense_input": ("experiments/inputs/core_1e_b2_expense_ratios_v1.json", "69405624fe3b56561707205b79bd2af2e5ade9a09d4ee71bf6ff9d9c2b019199"),
    "synthetic_fixture": ("tests/fixtures/core1e_b2r1/normalized_market_v2.json", "ed942153f6033034ff716b09062d79b7bac5935306286ce52b10001307888082"),
    "poison_fixture": ("tests/fixtures/core1e_b2r1/adversarial_post_cutoff_before_decode_v2.json", "de60004d5950a3b2ff83872338890311061cf171fd4235ce74a750433a7c4083"),
}
EXPECTED_TOP_LEVEL = {
    "schema_version", "order_id", "work_order_id", "gate_id", "supersedes_gate_id", "hypothesis_id", "status",
    "evidence_tier", "edge_claim", "owner_authorization_ref", "supersession", "static_source_bindings",
    "future_container_identity", "normalized_container_contract", "expense_input_contract", "locked_science",
    "windows", "execution_boundaries", "required_pre_decode_checks", "future_development_execution",
    "future_lifecycle_binding", "report_contract", "authorizations", "access_counts", "stop_conditions",
}
EXPECTED_ACCESS_COUNTS = {
    "real_dataset_access": 0, "real_container_access": 0, "real_return_decode": 0, "validation_access": 0,
    "provider_calls": 0, "credential_reads": 0, "broker_actions": 0, "paid_actions": 0,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exact_keys(value: Any, expected: set[str], label: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        blockers.append(f"{label}_must_be_object")
        return
    blockers.extend(f"{label}_missing:{key}" for key in sorted(expected - set(value)))
    blockers.extend(f"{label}_unknown:{key}" for key in sorted(set(value) - expected))


def _validate_contract(payload: Any, contract_path: Path, project_root: Path, verify_static: bool) -> list[str]:
    blockers: list[str] = []
    if not isinstance(payload, dict):
        return ["contract_must_be_object"]
    _exact_keys(payload, EXPECTED_TOP_LEVEL, "contract", blockers)
    if EXPECTED_CONTRACT_SHA256.startswith("__"):
        blockers.append("validator_contract_hash_not_filled")
    elif _sha256(contract_path) != EXPECTED_CONTRACT_SHA256:
        blockers.append("contract_artifact_hash_changed")
    expected_scalars = {
        "schema_version": "lily_core_1e_b2_development_execution_contract_v2",
        "order_id": "CORE-1E-B2-A",
        "work_order_id": "CORE-1E-B2-A-R1",
        "gate_id": "core_1e_b2_development_execution_contract_v2",
        "supersedes_gate_id": "core_1e_b2_development_execution_contract_v1",
        "hypothesis_id": "L-1",
        "status": "locked_before_execution",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "owner_authorization_ref": EXPECTED_OWNER,
    }
    for key, expected in expected_scalars.items():
        if payload.get(key) != expected:
            blockers.append(f"{key}_changed")
    if payload.get("supersession") != {
        "rejected_commit": "83d3c3fd1bc7058399aecb960eedc17cbc388b19",
        "reason": "Preserve rejected v1 history and add one real-schema-compatible remediation namespace.",
        "validation_boundary_unchanged": True,
    }:
        blockers.append("supersession_binding_changed")

    bindings = payload.get("static_source_bindings")
    _exact_keys(bindings, set(EXPECTED_STATIC_BINDINGS), "static_source_bindings", blockers)
    if isinstance(bindings, dict):
        for name, (path, digest) in EXPECTED_STATIC_BINDINGS.items():
            item = bindings.get(name)
            if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
                blockers.append(f"static_binding_shape_changed:{name}")
                continue
            if item.get("path") != path or item.get("sha256") != digest or not HASH64.fullmatch(str(item.get("sha256", ""))):
                blockers.append(f"static_binding_changed:{name}")
            if verify_static:
                target = project_root / path
                if not target.is_file():
                    blockers.append(f"static_binding_missing:{path}")
                elif _sha256(target) != digest:
                    blockers.append(f"static_binding_digest_mismatch:{path}")

    if payload.get("future_container_identity") != EXPECTED_CONTAINER:
        blockers.append("future_container_identity_changed")
    normalized = payload.get("normalized_container_contract")
    if not isinstance(normalized, dict):
        blockers.append("normalized_container_contract_missing")
    elif normalized != EXPECTED_NORMALIZED_CONTRACT:
        blockers.append("normalized_container_contract_changed")

    expense = payload.get("expense_input_contract")
    if not isinstance(expense, dict):
        blockers.append("expense_input_contract_missing")
    elif expense != EXPECTED_EXPENSE_CONTRACT:
        blockers.append("expense_input_contract_changed")

    science = payload.get("locked_science")
    if not isinstance(science, dict):
        blockers.append("locked_science_missing")
    else:
        if science.get("universe_symbols_in_order") != U8 or science.get("candidates_in_order") != CANDIDATES: blockers.append("locked_universe_or_candidates_changed")
        if science.get("candidate_lookbacks_complete_sessions") != {"CORE1_DC60":60,"CORE1_DC120":120,"CORE1_SMA200":200}: blockers.append("lookbacks_changed")
        if science.get("fixed_sleeve_weight") != 0.125 or science.get("no_trade_band", {}).get("absolute_difference_at_least") != 0.02: blockers.append("portfolio_or_band_changed")
        timing = science.get("weekly_timing", {})
        if timing.get("same_close_execution") is not False or timing.get("same_close_pnl") is not False or timing.get("manufactured_sessions") is not False: blockers.append("timing_policy_changed")
        if science.get("primary_costs") != {"commission_one_way_traded_notional":0.00107,"spread_slippage_one_way":0.0025,"sell_surcharge":0.0001,"etf_expense_accrual":"annual_ratio_divided_by_252_on_held_notional","cash_yield":0.0}: blockers.append("primary_costs_changed")
        if science.get("stress_costs") != {"execution_multiplier":2.0,"expense_multiplier":1.0}: blockers.append("stress_costs_changed")
        if science.get("gates") != list("ABCDEFGH"): blockers.append("gate_inventory_changed")
        if science.get("reported_paths") != ["gross", "primary_net", "two_x_execution_cost_net"]: blockers.append("reported_paths_changed")
        if science.get("benchmark") != "equal_weight_always_long_fixed_sleeves": blockers.append("benchmark_changed")
        if science.get("selection_rule") != "discard failed candidates, rank eligible candidates by highest worst-subperiod net Sharpe, use lower one-way turnover within 0.02, then locked candidate order": blockers.append("selection_rule_changed")
        if science.get("stop_rule") != "If no candidate passes every A-H gate, stop CORE-1 after CORE-1E, keep validation sealed, and require an owner/Inspector decision to reformulate or close this ETF trend family. No fourth candidate, parameter rescue, universe/date/timing/cost change, validation unlock, or remediation layering.": blockers.append("stop_rule_changed")

    boundaries = payload.get("execution_boundaries")
    expected_boundaries = {
        "mode":"synthetic_only","allowed_input_ref":"tests/fixtures/core1e_b2r1/normalized_market_v2.json","allowed_input_kind":"committed_synthetic_fixture_only",
        "expense_input_ref":"experiments/inputs/core_1e_b2_expense_ratios_v1.json","development_cutoff":"2015-12-31","reject_on_or_after":"2016-01-04",
        "validation_boundary":EXPECTED_VALIDATION,"marker_first":True,"max_invocations":1,"retry_allowed":False,
        "project_activation_creation":False,"project_marker_creation":False,"project_attempt_creation":False,"project_report_creation":False,
        "project_result_creation":False,"temporary_git_proof_only":True,
    }
    if boundaries != expected_boundaries: blockers.append("execution_boundaries_changed")
    if payload.get("required_pre_decode_checks") != ["top_level_cutoff","exact_u8_membership_and_order","per_symbol_schema_and_coverage","every_symbol_record_session_date","post_cutoff_rejection_before_return_decode","availability_timestamp_semantics","separate_expense_input_binding"]:
        blockers.append("pre_decode_checks_changed")
    future = payload.get("future_development_execution")
    if future != EXPECTED_FUTURE_EXECUTION:
        blockers.append("future_e1_mode_or_seal_changed")
    report = payload.get("report_contract")
    if report != EXPECTED_REPORT_CONTRACT:
        blockers.append("report_contract_changed")
    if payload.get("windows") != EXPECTED_WINDOWS:
        blockers.append("windows_changed")
    if payload.get("future_lifecycle_binding") != EXPECTED_LIFECYCLE_BINDING:
        blockers.append("future_lifecycle_binding_changed")
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
        payload = load_json(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status":"blocked","blockers":[f"contract_unreadable:{exc.__class__.__name__}"],"real_data_accessed":False,"validation_accessed":False}
    blockers = _validate_contract(payload, path, project_root, verify_static)
    return {
        "status":"pass" if not blockers else "blocked",
        "blockers":blockers,
        "contract_path":path.relative_to(project_root).as_posix() if path.is_relative_to(project_root) else str(path),
        "real_data_accessed":False,
        "validation_accessed":False,
        "future_container_checked":False,
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
