"""Fail-closed, no-return validator for the B7.5 corrected L-3 rerun schedule gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_jsonl, relative_to_root

GATE = PROJECT_ROOT / "experiments/l_3_corrected_rerun_pre_return_schedule_v1.json"
MANIFEST = PROJECT_ROOT / "experiments/locked_gates.jsonl"
LEDGER = PROJECT_ROOT / "reports/experiments/l_3_falsification_execution_ledger.jsonl"

START = "2007-02-05"
END = "2015-12-31"
VALIDATION_START = "2016-01-04"
ASSETS = ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]
MAX_WEEKLY_OBSERVATIONS = 465
AUTHORIZATIONS = {
    "data_access_authorized": False,
    "container_inspection_authorized": False,
    "date_column_inspection_authorized": False,
    "return_parsing_authorized": False,
    "execution_authorized": False,
    "report_decision_authorized": False,
    "validation_access_authorized": False,
    "provider_network_authorized": False,
    "credentials_authorized": False,
    "acquisition_authorized": False,
    "paid_action_authorized": False,
    "broker_authorized": False,
    "paper_trade_authorized": False,
    "real_money_authorized": False,
}
MANIFEST_IDENTITIES = {
    "active_l3_v2": {
        "gate_id": "l_3_inverse_volatility_sizing_v2",
        "artifact_path": "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json",
        "artifact_sha256": "83a68792614ee0def3ddb96349d6d95c7f0aeb0ac8b1c984c1e3d29ed74e709e",
        "validator_path": "scripts/validate_l_3_inverse_volatility_sizing_preregistration_v2.py",
        "validator_sha256": "1556108bb69f7621ebedcaeb046e53d12b5b7eea473fe36454f02c56399b9ea6",
    },
    "immutable_l3_v1": {
        "gate_id": "l_3_inverse_volatility_sizing_v1",
        "artifact_path": "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json",
        "artifact_sha256": "0e0aaf281c75a450bbdf1015c1f400fc7ce8a398952ea25ddbb0ba2f4557c2b0",
        "validator_path": "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py",
        "validator_sha256": "948dd2737e0f04f6f9c256ad91bb2cb348bbe48eb58db3d77150b6ef4abd55be",
    },
    "b7_1_preflight": {
        "gate_id": "l_3_falsification_activation_preflight_v1",
        "artifact_path": "experiments/l_3_falsification_activation_preflight_v1.json",
        "artifact_sha256": "b27827ba15b2f7cbd89d10f771da1639d26d54087195ad275df4a72cf39ab5c3",
        "validator_path": "scripts/validate_l_3_falsification_activation_preflight_v1.py",
        "validator_sha256": "3a7c48478f722532a631eecd0288f6a4ffe0e745cc70e73ac725e9c6fb7c7569",
    },
    "b7_3_one_run_authorization": {
        "gate_id": "l_3_one_run_falsification_authorization_v1",
        "artifact_path": "experiments/l_3_one_run_falsification_authorization_v1.json",
        "artifact_sha256": "640264a8db7efaabfc6071788fbde337ca174b39605ccf2fdbf8a2e8668a10da",
        "validator_path": "scripts/validate_l_3_one_run_falsification_authorization_v1.py",
        "validator_sha256": "2bcd55f7440c0b0ad93795b75ad9811197ece157f874b72e848c8bda1f0d8796",
    },
}
SOURCE_PATHS = {
    "active_l3_v2": ("experiments/l_3_inverse_volatility_sizing_preregistration_v2.json", "83a68792614ee0def3ddb96349d6d95c7f0aeb0ac8b1c984c1e3d29ed74e709e"),
    "immutable_l3_v1": ("experiments/l_3_inverse_volatility_sizing_preregistration_v1.json", "0e0aaf281c75a450bbdf1015c1f400fc7ce8a398952ea25ddbb0ba2f4557c2b0"),
    "b7_1_preflight": ("experiments/l_3_falsification_activation_preflight_v1.json", "b27827ba15b2f7cbd89d10f771da1639d26d54087195ad275df4a72cf39ab5c3"),
    "b7_3_one_run_authorization": ("experiments/l_3_one_run_falsification_authorization_v1.json", "640264a8db7efaabfc6071788fbde337ca174b39605ccf2fdbf8a2e8668a10da"),
    "b7_3_final_invalidated_report": ("reports/experiments/l_3_falsification_report.json", "3a61c2e8126aa8aa6cc53507a7cf7c5ae074c5ee84283d3c9c9a3d28c9486bc9"),
    "b7_4_remediation": ("experiments/l_3_invalid_run_ledger_remediation_v1.json", "c36194863346290c01583ef362a38fb64b2eb397145067fbbeec888ebcdaa51d"),
}
REQUIRED_TOP_LEVEL = {
    "schema_version", "order_id", "checkpoint", "gate_id", "hypothesis_id", "status", "evidence_ceiling",
    "edge_claim", "owner_authorization", "source_binding", "preserved_research_semantics",
    "corrected_execution_window_control", "pre_return_schedule_attestation_contract", "future_rerun_namespace",
    "authorizations", "b7_5_attestation", "hard_stops",
}


def canonical_schedule_sha256(selected_decision_dates: list[str]) -> str:
    payload = json.dumps(selected_decision_dates, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_pre_return_schedule_attestation(
    attestation: Any, date_only_sessions: list[str], *, expected_container_identity: dict[str, Any]
) -> dict[str, Any]:
    """Validate only date metadata supplied by a future authorized caller; never open a container."""
    blockers: list[str] = []
    required = {
        "schema_version", "container_identity", "date_column", "first_decision_date", "last_decision_date",
        "execution_date_boundary", "t_plus_20_max_date", "selected_weekly_paired_observations",
        "exclusions_by_reason", "selected_decision_dates", "execution_dates", "realized_confirmation_end_dates",
        "schedule_sha256", "validation_seal_status", "return_fields_accessed",
    }
    if not isinstance(attestation, dict):
        return {"status": "blocked", "blockers": ["attestation_not_object"]}
    _exact_keys(attestation, required, "attestation", blockers)
    if attestation.get("schema_version") != "lily_l3_pre_return_schedule_attestation_v1":
        blockers.append("attestation_schema_mismatch")
    if isinstance(expected_container_identity, dict):
        _exact_keys(attestation.get("container_identity"), set(expected_container_identity), "attestation_container_identity", blockers)
    if attestation.get("container_identity") != expected_container_identity:
        blockers.append("attestation_container_identity_mismatch")
    if attestation.get("date_column") != "session_date":
        blockers.append("attestation_date_column_mismatch")
    if attestation.get("validation_seal_status") != "sealed_not_accessed":
        blockers.append("attestation_validation_seal_mismatch")
    if attestation.get("return_fields_accessed") is not False:
        blockers.append("attestation_return_fields_accessed_before_schedule_pass")
    selected = attestation.get("selected_decision_dates")
    executions = attestation.get("execution_dates")
    ends = attestation.get("realized_confirmation_end_dates")
    if not isinstance(selected, list) or not all(isinstance(value, str) for value in selected):
        blockers.append("selected_schedule_not_string_list")
        selected = []
    if not isinstance(executions, list) or not isinstance(ends, list):
        blockers.append("schedule_interval_lists_missing")
        executions, ends = [], []
    _validate_date_list(date_only_sessions, "date_only_sessions", blockers)
    _validate_date_list(selected, "selected_decision_dates", blockers)
    _validate_date_list(executions, "execution_dates", blockers)
    _validate_date_list(ends, "realized_confirmation_end_dates", blockers)
    if not date_only_sessions:
        blockers.append("date_only_sessions_missing")
    else:
        if date_only_sessions != sorted(date_only_sessions) or len(date_only_sessions) != len(set(date_only_sessions)):
            blockers.append("date_only_sessions_not_strictly_monotonic")
        if any(value >= VALIDATION_START for value in date_only_sessions):
            blockers.append("mixed_validation_date_hard_stop")
    if len(selected) > MAX_WEEKLY_OBSERVATIONS:
        blockers.append("weekly_paired_observation_ceiling_exceeded")
    if len(selected) != attestation.get("selected_weekly_paired_observations"):
        blockers.append("selected_observation_count_mismatch")
    if len(selected) != len(set(selected)):
        blockers.append("duplicate_weekly_decision")
    if selected != sorted(selected):
        blockers.append("non_monotonic_weekly_decision")
    week_keys = []
    for value in selected:
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            continue
        iso_year, iso_week, _ = parsed.isocalendar()
        week_keys.append((iso_year, iso_week))
    if len(week_keys) != len(set(week_keys)):
        blockers.append("duplicate_weekly_decision")
    if any(value < START for value in selected):
        blockers.append("pre_start_weekly_decision")
    if any(value > END for value in selected):
        blockers.append("post_end_weekly_decision")
    if len(executions) != len(selected) or len(ends) != len(selected):
        blockers.append("schedule_interval_count_mismatch")
    for index, decision in enumerate(selected):
        if decision not in date_only_sessions:
            blockers.append("decision_not_in_date_only_sessions")
            continue
        decision_index = date_only_sessions.index(decision)
        if decision_index + 20 >= len(date_only_sessions):
            blockers.append("incomplete_t_plus_20_interval")
            continue
        if index < len(executions) and executions[index] != date_only_sessions[decision_index + 1]:
            blockers.append("next_actual_eligible_session_execution_mismatch")
        if index < len(ends) and ends[index] != date_only_sessions[decision_index + 20]:
            blockers.append("t_plus_20_actual_session_mismatch")
    if any(value > END for value in ends):
        blockers.append("t_plus_20_crosses_falsification_end")
    if selected:
        expected_scalars = {
            "first_decision_date": selected[0], "last_decision_date": selected[-1],
            "execution_date_boundary": max(executions) if executions else None,
            "t_plus_20_max_date": max(ends) if ends else None,
            "schedule_sha256": canonical_schedule_sha256(selected),
        }
        for field, expected in expected_scalars.items():
            if attestation.get(field) != expected:
                blockers.append(f"attestation_{field}_mismatch")
    else:
        blockers.append("selected_schedule_empty")
    if not isinstance(attestation.get("exclusions_by_reason"), dict):
        blockers.append("exclusions_by_reason_missing")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


def validate_gate(gate_path: Path = GATE, *, manifest_path: Path = MANIFEST) -> dict[str, Any]:
    blockers: list[str] = []
    gate = _read_json(gate_path, "gate", blockers)
    if gate is None:
        return _result(gate_path, blockers)
    _exact_keys(gate, REQUIRED_TOP_LEVEL, "top_level", blockers)
    expected_root = {
        "schema_version": "lily_l3_corrected_rerun_pre_return_schedule_v1", "order_id": "B7.5",
        "checkpoint": "corrected_rerun_preregistration_pre_return_schedule_only",
        "gate_id": "l_3_corrected_rerun_pre_return_schedule_v1", "hypothesis_id": "L-3",
        "status": "locked_pre_return_schedule_execution_not_authorized", "evidence_ceiling": "E0", "edge_claim": "none",
        "owner_authorization": "Owner explicitly authorized B7.5 on 2026-07-27 to prepare and hash-lock a corrected no-data L-3 rerun preregistration and pre-return schedule contract after Inspector accepted B7.4 commit 941564e10094e9e5c22da1fccefaa40fad68e82c; it authorizes neither data/container/date-column access nor return parsing, execution, report decision, validation, provider, credential, acquisition, broker, paper-trade, or real-money action.",
    }
    _require_values(gate, expected_root, "governance_mismatch", blockers)
    _validate_source_binding(gate.get("source_binding"), manifest_path, blockers)
    _validate_semantics(gate.get("preserved_research_semantics"), blockers)
    _validate_window_control(gate.get("corrected_execution_window_control"), blockers)
    _validate_attestation_contract(gate.get("pre_return_schedule_attestation_contract"), blockers)
    _validate_namespace(gate.get("future_rerun_namespace"), blockers)
    _exact_keys(gate.get("authorizations"), set(AUTHORIZATIONS), "authorizations", blockers)
    if gate.get("authorizations") != AUTHORIZATIONS:
        blockers.append("authorization_drift")
    expected_attestation = {
        "market_data_or_date_column_read_count": 0, "market_returns_read_count": 0,
        "new_real_return_decision_run_count": 0, "new_ledger_rows_created": 0,
        "validation_status": "sealed_not_accessed", "b7_3_real_return_decision_run_count": 1,
        "b7_3_invalidation_count": 1,
    }
    _exact_keys(gate.get("b7_5_attestation"), set(expected_attestation), "b7_5_attestation", blockers)
    _require_values(gate.get("b7_5_attestation"), expected_attestation, "b7_5_attestation_mismatch", blockers)
    required_stops = {
        "B7.5 is no-data governance only: no dataset, container, date column, market return, price, signal, position, covariance, regime, cost, or PnL may be opened, read, hashed, parsed, or computed.",
        "No execution, report decision, new real-return decision ledger row, validation access, provider/network call, credential or environment-variable read, acquisition, paid action, broker action, paper trade, or real-money action is authorized.",
        "A future runner must hard-stop before return parsing for any pre-start or post-end decision, duplicate or non-monotonic week, incomplete t+20 interval, count above 465, mixed validation date, missing or extra asset, schedule/hash drift, or attempted in-memory filtering.",
        "The B7.3 report and ledger are immutable invalidated history: they may not be overwritten, reused as the rerun namespace, or cited as an L-3 result; no second B7.3 run is authorized.",
        "This gate preserves the locked L-3 research semantics and validation seal; it changes only execution-window control and fresh future-run artifact paths, with edge_claim none.",
    }
    if set(gate.get("hard_stops", [])) != required_stops:
        blockers.append("hard_stops_incomplete_or_open")
    return _result(gate_path, blockers)


def _validate_source_binding(binding: Any, manifest_path: Path, blockers: list[str]) -> None:
    expected_keys = set(SOURCE_PATHS) | {"b7_4_original_run_row", "b7_4_invalidation_event", "whole_manifest_hash_binding", "self_or_circular_hash_binding"}
    _exact_keys(binding, expected_keys, "source_binding", blockers)
    if not isinstance(binding, dict):
        return
    for label, (relative, digest) in SOURCE_PATHS.items():
        value = binding.get(label)
        expected_keys = {"path", "sha256"}
        if label in MANIFEST_IDENTITIES:
            expected_keys.add("manifest_identity")
        if label == "immutable_l3_v1":
            expected_keys.add("through_active_v2_only")
        if label == "b7_3_final_invalidated_report":
            expected_keys.add("authoritative_outcome")
        if label == "b7_4_remediation":
            expected_keys.update({"authoritative_outcome", "provisional_metrics_inference_status"})
        _exact_keys(value, expected_keys, f"source_binding_{label}", blockers)
        if not isinstance(value, dict) or value.get("path") != relative or value.get("sha256") != digest:
            blockers.append(f"source_binding_declaration_mismatch:{label}")
        if label == "immutable_l3_v1" and (not isinstance(value, dict) or value.get("through_active_v2_only") is not True):
            blockers.append("source_binding_declaration_mismatch:immutable_l3_v1_through_active_v2_only")
        if label == "b7_3_final_invalidated_report" and (not isinstance(value, dict) or value.get("authoritative_outcome") != "scope_restricted"):
            blockers.append("source_binding_declaration_mismatch:b7_3_final_invalidated_report_outcome")
        if label == "b7_4_remediation" and (not isinstance(value, dict) or value.get("authoritative_outcome") != "scope_restricted" or value.get("provisional_metrics_inference_status") != "invalid_unusable"):
            blockers.append("source_binding_declaration_mismatch:b7_4_remediation_state")
        if _sha(PROJECT_ROOT / relative) != digest:
            blockers.append(f"source_binding_hash_mismatch:{label}")
    for label, identity in MANIFEST_IDENTITIES.items():
        value = binding.get(label)
        if isinstance(value, dict):
            _exact_keys(value.get("manifest_identity"), set(identity), f"manifest_identity_{label}", blockers)
        if not isinstance(value, dict) or value.get("manifest_identity") != identity:
            blockers.append(f"source_manifest_identity_declaration_mismatch:{label}")
    expected_b74_original = {
        "path": "reports/experiments/l_3_falsification_execution_ledger.jsonl", "event": "real_return_decision_run",
        "run_id": "B7.3-L3-ONE", "producing_git_commit": "3e3cfc773b8e327dca63bfdd8f2a1b103376173d",
        "sha256": "594b8cbbdf7c27769191ab9495275803478481121372cd3bfc6f7e6d3a8a556a",
    }
    expected_b74_invalidation = {
        "path": "reports/experiments/l_3_falsification_execution_ledger.jsonl", "event": "real_return_decision_run_invalidated",
        "run_id": "B7.3-L3-ONE", "sha256": "ce53b723b3394c38ea0b0c85c7411e5aa59a6cc7b20dddf5fe5bf18a5aebb766",
        "authoritative_outcome": "scope_restricted", "reason": "observation_window_started_before_2007-02-05",
    }
    _exact_keys(binding.get("b7_4_original_run_row"), set(expected_b74_original), "b7_4_original_run_row", blockers)
    _exact_keys(binding.get("b7_4_invalidation_event"), set(expected_b74_invalidation), "b7_4_invalidation_event", blockers)
    if binding.get("b7_4_original_run_row") != expected_b74_original:
        blockers.append("b7_4_original_run_row_binding_mismatch")
    if binding.get("b7_4_invalidation_event") != expected_b74_invalidation:
        blockers.append("b7_4_invalidation_event_binding_mismatch")
    if binding.get("whole_manifest_hash_binding") is not False or binding.get("self_or_circular_hash_binding") is not False:
        blockers.append("whole_manifest_or_circular_binding")
    try:
        rows = [line for line in LEDGER.read_bytes().splitlines() if line]
        parsed = [json.loads(line) for line in rows]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        blockers.append("b7_4_ledger_unreadable")
        parsed, rows = [], []
    if len(rows) != 2 or len(parsed) != 2 or _sha_bytes(rows[0] if rows else b"") != expected_b74_original["sha256"]:
        blockers.append("b7_4_original_run_row_hash_mismatch")
    if len(rows) < 2 or _sha_bytes(rows[1]) != expected_b74_invalidation["sha256"]:
        blockers.append("b7_4_invalidation_event_hash_mismatch")
    if len(parsed) == 2 and (parsed[0].get("event") != "real_return_decision_run" or parsed[1].get("event") != "real_return_decision_run_invalidated"):
        blockers.append("b7_4_ledger_event_order_mismatch")
    try:
        manifest_rows = load_jsonl(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError):
        blockers.append("manifest_unreadable")
        return
    for label, identity in MANIFEST_IDENTITIES.items():
        matches = [row for row in manifest_rows if isinstance(row, dict) and row.get("gate_id") == identity["gate_id"]]
        if len(matches) != 1 or any(matches[0].get(key) != value for key, value in identity.items()):
            blockers.append(f"source_manifest_identity_mismatch:{label}")


def _validate_semantics(value: Any, blockers: list[str]) -> None:
    expected = {
        "research_universe_tickers_in_order": ASSETS,
        "candidate_raw_score": "q[i,t] / max(annualized_volatility[i,t], 0.05)", "comparator_raw_score": "q[i,t]",
        "inherited_signal": "L1 60_day_directional_count_raw only",
        "decision_index_and_timing": "weekly decision index after the official close of the last NYSE session of each week; next actual NYSE close execution only",
        "inherited_constraints_and_cost_accounting": "L1 90% gross normalization, 10% minimum cash, 25% absolute asset cap, 60-session EWMA PSD-clipped covariance, target-volatility scale-down-only, and locked L1 cost accounting",
        "missing_sessions_policy": "Inherited L1 missing-data policy is mandatory: no price forward fill; any required missing input makes the affected paired date non-evaluable and scope_restricted rather than silently dropped.",
        "observation_unit": "one weekly paired portfolio observation; never multiply by assets, days, 20-session confirmation rows, sleeves, or trades",
        "mintrl_falsify_weekly_paired_observations": 49, "optimistic_weekly_capacity_ceiling": 465,
        "optimistic_regime_eligible_weekly_capacity_ceiling": 366,
        "regime_inference": "Every regime claim separately needs its actual recomputed requirement and cannot pool regimes.",
        "validation_seal": {"start": "2016-01-04", "end": "2026-06-30", "opened": False, "pooled_with_falsification": False},
    }
    _exact_keys(value, set(expected), "preserved_research_semantics", blockers)
    _require_values(value, expected, "research_semantics_mismatch", blockers)
    if isinstance(value, dict):
        _exact_keys(value.get("validation_seal"), set(expected["validation_seal"]), "preserved_validation_seal", blockers)


def _validate_window_control(value: Any, blockers: list[str]) -> None:
    expected = {
        "falsification_start": START, "falsification_end": END,
        "warm_up_rule": "Raw warm-up rows before 2007-02-05 may be used only as future signal and volatility history after a separate authorization; they never count as observations, turnover, HHI deltas, realized confirmation, regimes, side effects, or report metrics.",
        "decision_schedule_rule": "Every selected weekly decision date is unique, monotonically increasing, and within 2007-02-05 through 2015-12-31 inclusive; execution is the next actual eligible session close.",
        "realized_confirmation_rule": "Every realized-confirmation interval t+1 through t+20 actual eligible sessions is fully contained on or before 2015-12-31.",
        "weekly_paired_observation_ceiling": 465,
        "mixed_validation_container_rule": "Any container with a validation date hard-stops before return parsing and must never be filtered in memory.",
    }
    _exact_keys(value, set(expected), "corrected_execution_window_control", blockers)
    _require_values(value, expected, "execution_window_control_mismatch", blockers)


def _validate_attestation_contract(value: Any, blockers: list[str]) -> None:
    expected = {
        "required_fields": ["schema_version", "container_identity", "date_column", "first_decision_date", "last_decision_date", "execution_date_boundary", "t_plus_20_max_date", "selected_weekly_paired_observations", "exclusions_by_reason", "selected_decision_dates", "execution_dates", "realized_confirmation_end_dates", "schedule_sha256", "validation_seal_status", "return_fields_accessed"],
        "schema_version": "lily_l3_pre_return_schedule_attestation_v1",
        "container_identity_rule": "Records the future authorized repo-relative container identity and SHA-256 after metadata/date-only inspection; no return field may be accessed before this attestation passes.",
        "schedule_sha256_rule": "SHA-256 of canonical UTF-8 JSON with sorted keys and compact separators for selected_decision_dates only.",
        "future_report_binding_rule": "A future report must bind this attestation SHA-256 and may not be produced before it passes.",
    }
    _exact_keys(value, set(expected), "pre_return_schedule_attestation_contract", blockers)
    _require_values(value, expected, "attestation_contract_mismatch", blockers)


def _validate_namespace(value: Any, blockers: list[str]) -> None:
    expected = {
        "rerun_id": "L-3-B7.5-CORRECTED-RERUN-ONE",
        "report_path": "reports/experiments/l_3_corrected_rerun_falsification_report.json",
        "ledger_path": "reports/experiments/l_3_corrected_rerun_execution_ledger.jsonl",
        "ledger_initial_state": "new_empty_append_only_ledger_required", "maximum_real_return_decision_runs": 1,
        "activation_requirement": "Only after Inspector acceptance of B7.5 and a new explicit owner-approved activation/execution order may a fresh authorization bind this gate and create one run in this fresh ledger.",
    }
    _exact_keys(value, set(expected), "future_rerun_namespace", blockers)
    _require_values(value, expected, "future_namespace_mismatch", blockers)
    if isinstance(value, dict) and value.get("report_path") == "reports/experiments/l_3_falsification_report.json":
        blockers.append("b7_3_report_namespace_reused")
    if isinstance(value, dict) and value.get("ledger_path") == "reports/experiments/l_3_falsification_execution_ledger.jsonl":
        blockers.append("b7_3_ledger_namespace_reused")


def _validate_date_list(values: Any, label: str, blockers: list[str]) -> None:
    if not isinstance(values, list):
        blockers.append(f"{label}_not_list")
        return
    for value in values:
        if not isinstance(value, str):
            blockers.append(f"{label}_non_string_date")
            continue
        try:
            date.fromisoformat(value)
        except ValueError:
            blockers.append(f"{label}_invalid_date")


def _read_json(path: Path, label: str, blockers: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        blockers.append(f"{label}_missing")
        return None
    except json.JSONDecodeError:
        blockers.append(f"{label}_invalid_json")
        return None
    if not isinstance(value, dict):
        blockers.append(f"{label}_not_object")
        return None
    return value


def _exact_keys(value: Any, expected: set[str], label: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        blockers.append(f"{label}_not_object")
        return
    blockers.extend(f"unknown_{label}_field:{key}" for key in sorted(set(value) - expected))
    blockers.extend(f"missing_{label}_field:{key}" for key in sorted(expected - set(value)))


def _require_values(value: Any, expected: dict[str, Any], prefix: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        return
    blockers.extend(f"{prefix}:{key}" for key, required in expected.items() if value.get(key) != required)


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers)), "gate_path": relative_to_root(path, PROJECT_ROOT), "market_data_or_date_column_read_count": 0, "market_returns_read_count": 0, "new_real_return_decision_run_count": 0, "validation_status": "sealed_not_accessed"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the B7.5 no-return corrected L-3 schedule gate.")
    parser.add_argument("--gate", type=Path, default=GATE)
    args = parser.parse_args()
    result = validate_gate(args.gate)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
