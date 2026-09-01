"""Validate the append-only CORE-1E-A Phase-A contract without data access."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.core_1e_a_lifecycle_v1 import RUNTIME_PATHS, hash_file, safe_relative
from lib.io import load_json, load_jsonl, relative_to_root


CONTRACT = PROJECT_ROOT / "experiments" / "core_1e_a_phase_a_execution_contract_v1.json"
EXPECTED_CONTRACT_SHA256 = "adcbdbc26d02a287394bbfd5a3893a2d24d027b322e545e7a8b06378a7c35c7d"
UPSTREAM_PREREG = PROJECT_ROOT / "experiments" / "core_1_stable_baseline_preregistration_v1.json"
UPSTREAM_VALIDATOR = PROJECT_ROOT / "scripts" / "validate_core_1_stable_baseline_preregistration_v1.py"
UPSTREAM_MANIFEST = PROJECT_ROOT / "experiments" / "locked_gates_v2.jsonl"
UPSTREAM_MANIFEST_LINE_SHA256 = "5f16a5ac659e52791f9affac19812acee8204cc5f6a10c3a68f307b295769e24"
UPSTREAM_PREREG_SHA256 = "5003d2360bb8729bcd91a39da34ff2e28c92ad2eb75c9b632c3ee85bcda7682f"
UPSTREAM_VALIDATOR_SHA256 = "55b0cf8769276e091bb4cf38cfabb44d98f5a9e5a4d12670e7d710820e1d5da5"
UPSTREAM_GATE_ID = "core_1_stable_baseline_preregistration_v1_validator_hardening_v2"
FUTURE_ACTIVATION = PROJECT_ROOT / "experiments" / "activation_records" / "core_1e_a_activation_v1.json"

TOP_LEVEL_KEYS = {
    "schema_version", "order_id", "gate_id", "hypothesis_id", "status", "evidence_tier", "edge_claim",
    "core_1p_source_binding", "locked_science", "synthetic_fixture", "report_contract", "future_lifecycle",
    "validation_seal", "authorizations", "access_counts", "hard_stops", "execution_dependencies", "execution_binding",
}
SCIENCE_FIELDS = (
    "research_question", "development_candidates_in_locked_order", "candidate_constraints", "universe",
    "portfolio_construction", "timing", "costs", "windows", "search_accounting_and_inference",
    "matched_benchmark", "development_eligibility_gates", "selection_rule", "stop_rule", "claim_ceiling",
    "exact_next_safe_action", "authorizations",
)
EXPECTED_REQUIRED_METRIC_PATHS = [
    "gross.annual_arithmetic_return",
    "gross.annual_geometric_return",
    "gross.annualized_volatility",
    "gross.annualized_sharpe",
    "gross.maximum_drawdown",
    "costs.commission",
    "costs.spread_slippage",
    "costs.sell_surcharge",
    "costs.etf_expense_accrual",
    "costs.execution_cost_primary",
    "costs.execution_cost_two_x",
    "primary_net.one_way_turnover",
    "primary_net.trade_count",
    "primary_net.average_exposure",
    "primary_net.psr",
    "primary_net.dsr",
    "primary_net.autocorrelation_adjusted_sharpe_variance",
    "primary_net.hac_newey_west",
    "primary_net.independent_bet_equivalents",
    "two_x_execution_cost_net.annual_geometric_return",
    "two_x_execution_cost_net.annualized_sharpe",
]
EXPECTED_AUTHORIZATIONS = {
    "phase_a_synthetic_fixture_calculation": True,
    "real_backtest": False,
    "real_dataset_or_container": False,
    "validation_window": False,
    "provider_or_network": False,
    "credentials": False,
    "broker_or_account": False,
    "paid": False,
    "paper_trading": False,
    "real_money": False,
    "research_log": False,
    "activation_creation": False,
    "production_report": False,
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
EXPECTED_HARD_STOPS = [
    "missing_or_invalid_phase_a_contract",
    "core_1p_source_hash_or_manifest_drift",
    "unknown_report_field_or_missing_material_metric",
    "any_validation_window_reference",
    "activation_missing_any_gate_commit_ci_owner_runtime_cutoff_seal_or_one_shot_binding",
    "prior_marker_or_attempt_exists",
    "dirty_or_uncommitted_future_runtime_dependencies",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_line_hashes(path: Path) -> list[tuple[dict[str, Any], str]]:
    result = []
    for raw_line in path.read_bytes().splitlines():
        if not raw_line.strip():
            continue
        result.append((json.loads(raw_line), hashlib.sha256(raw_line).hexdigest()))
    return result


def _projection(prereg: dict[str, Any]) -> dict[str, Any]:
    return {key: prereg[key] for key in SCIENCE_FIELDS}


def validate_contract(path: Path = CONTRACT) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        contract = load_json(path)
        prereg = load_json(UPSTREAM_PREREG)
        manifest_pairs = _manifest_line_hashes(UPSTREAM_MANIFEST)
    except (OSError, json.JSONDecodeError, TypeError, KeyError) as exc:
        return {"status": "blocked", "blockers": [f"unreadable_input:{exc.__class__.__name__}"]}
    if not isinstance(contract, dict) or set(contract) != TOP_LEVEL_KEYS:
        blockers.append("contract_closed_world_changed")
    if _sha(path) != EXPECTED_CONTRACT_SHA256:
        blockers.append("contract_sha256_changed")
    identity = {key: contract.get(key) for key in ("schema_version", "order_id", "gate_id", "hypothesis_id", "status", "evidence_tier", "edge_claim")}
    if identity != {
        "schema_version": "lily_core_1e_a_phase_a_execution_contract_v1",
        "order_id": "CORE-1E-A",
        "gate_id": "core_1e_a_phase_a_execution_contract_v1",
        "hypothesis_id": "L-1",
        "status": "locked_before_execution",
        "evidence_tier": "E0",
        "edge_claim": "none",
    }:
        blockers.append("contract_identity_changed")
    expected_source = {
        "preregistration": {"path": "experiments/core_1_stable_baseline_preregistration_v1.json", "sha256": UPSTREAM_PREREG_SHA256},
        "validator": {"path": "scripts/validate_core_1_stable_baseline_preregistration_v1.py", "sha256": UPSTREAM_VALIDATOR_SHA256},
        "locked_manifest": {
            "path": "experiments/locked_gates_v2.jsonl",
            "gate_id": UPSTREAM_GATE_ID,
            "artifact_sha256": UPSTREAM_PREREG_SHA256,
            "validator_sha256": UPSTREAM_VALIDATOR_SHA256,
            "line_sha256": UPSTREAM_MANIFEST_LINE_SHA256,
        },
    }
    if contract.get("core_1p_source_binding") != expected_source:
        blockers.append("core_1p_source_binding_changed")
    if not UPSTREAM_PREREG.is_file() or _sha(UPSTREAM_PREREG) != UPSTREAM_PREREG_SHA256:
        blockers.append("upstream_preregistration_hash_mismatch")
    if not UPSTREAM_VALIDATOR.is_file() or _sha(UPSTREAM_VALIDATOR) != UPSTREAM_VALIDATOR_SHA256:
        blockers.append("upstream_validator_hash_mismatch")
    matching_manifest = [
        (row, line_hash)
        for row, line_hash in manifest_pairs
        if row.get("gate_id") == UPSTREAM_GATE_ID
    ]
    if len(matching_manifest) != 1 or matching_manifest[0][1] != UPSTREAM_MANIFEST_LINE_SHA256:
        blockers.append("upstream_manifest_identity_mismatch")
    elif any(
        matching_manifest[0][0].get(key) != expected
        for key, expected in {
            "artifact_path": "experiments/core_1_stable_baseline_preregistration_v1.json",
            "validator_path": "scripts/validate_core_1_stable_baseline_preregistration_v1.py",
            "artifact_sha256": UPSTREAM_PREREG_SHA256,
            "validator_sha256": UPSTREAM_VALIDATOR_SHA256,
        }.items()
    ):
        blockers.append("upstream_manifest_hash_binding_mismatch")
    try:
        from scripts.validate_core_1_stable_baseline_preregistration_v1 import validate_preregistration

        if validate_preregistration(UPSTREAM_PREREG).get("status") != "pass":
            blockers.append("upstream_preregistration_validator_failed")
    except (ImportError, OSError, TypeError):
        blockers.append("upstream_preregistration_validator_unavailable")
    if isinstance(contract, dict) and isinstance(prereg, dict):
        if contract.get("locked_science") != _projection(prereg):
            blockers.append("locked_science_reinterpreted")
    fixture = contract.get("synthetic_fixture", {})
    if fixture != {
        "path": "tests/fixtures/core1e_a/synthetic_market_v1.json",
        "schema_version": "lily_core_1e_a_synthetic_market_v1",
        "only_input_allowed_in_phase_a": True,
    }:
        blockers.append("synthetic_fixture_contract_changed")
    report = contract.get("report_contract", {})
    expected_report = {
        "schema_path": "schemas/core_1e_a_synthetic_report_v1.schema.json",
        "validator_path": "scripts/validate_core_1e_a_synthetic_report_v1.py",
        "mode": "synthetic_calculation_only",
        "required_metric_paths": EXPECTED_REQUIRED_METRIC_PATHS,
        "closed_world": True,
        "recompute_material_decisions": True,
        "unknown_fields_rejected": True,
    }
    if report != expected_report:
        blockers.append("report_contract_changed")
    lifecycle = contract.get("future_lifecycle", {})
    expected_lifecycle = {
        "activation_schema_version": "lily_core_1e_a_activation_v1",
        "activation_record_path": "experiments/activation_records/core_1e_a_activation_v1.json",
        "required_bindings": [
            "accepted_phase_a_gate_commit", "successful_exact_sha_ci_for_that_commit", "explicit_owner_authorization_reference",
            "exact_committed_runtime_bytes", "development_only_date_cutoff", "sealed_validation_boundary",
            "one_shot_marker_attempt_report_lifecycle",
        ],
        "marker_path": "reports/experiments/core_1e_a_one_shot_marker_v1.json",
        "attempt_path": "reports/experiments/core_1e_a_execution_attempt_v1.json",
        "report_path": "reports/experiments/core_1e_a_execution_report_v1.json",
        "pre_activation_data_access": "deny",
        "atomic_marker_before_input_read": True,
        "no_retry": True,
        "phase_a_activation_present": False,
    }
    if lifecycle != expected_lifecycle or FUTURE_ACTIVATION.exists():
        blockers.append("future_lifecycle_phase_a_state_changed")
    if contract.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}:
        blockers.append("validation_seal_changed")
    if contract.get("authorizations") != EXPECTED_AUTHORIZATIONS:
        blockers.append("authorizations_changed")
    if contract.get("access_counts") != EXPECTED_ACCESS_COUNTS or contract.get("hard_stops") != EXPECTED_HARD_STOPS:
        blockers.append("access_or_hard_stop_contract_changed")
    dependencies = contract.get("execution_dependencies")
    binding = contract.get("execution_binding")
    expected_dependencies = [*RUNTIME_PATHS]
    if dependencies != expected_dependencies or not isinstance(binding, dict) or set(binding) != set(expected_dependencies):
        blockers.append("execution_dependency_set_changed")
    else:
        for relative in expected_dependencies:
            item = binding.get(relative)
            if item != {"path": relative, "sha256": item.get("sha256") if isinstance(item, dict) else None}:
                blockers.append(f"execution_binding_shape_changed:{relative}")
                continue
            if not safe_relative(relative) or not isinstance(item.get("sha256"), str) or not (PROJECT_ROOT / relative).is_file() or hash_file(PROJECT_ROOT / relative) != item["sha256"]:
                blockers.append(f"execution_binding_hash_mismatch:{relative}")
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "path": relative_to_root(path, PROJECT_ROOT),
        "contract_sha256": _sha(path) if path.is_file() else None,
        "real_data_accessed": False,
        "validation_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate CORE-1E-A's locked Phase-A execution contract.")
    parser.add_argument("--path", type=Path, default=CONTRACT)
    args = parser.parse_args()
    result = validate_contract(args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
