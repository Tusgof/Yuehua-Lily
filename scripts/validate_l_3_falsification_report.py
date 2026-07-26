"""Closed-world validation of the B7.3 invalidated one-run report and ledger."""
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

from lib.io import load_json, relative_to_root
from lib.provenance import file_sha256

REPORT = PROJECT_ROOT / "reports/experiments/l_3_falsification_report.json"
LEDGER = PROJECT_ROOT / "reports/experiments/l_3_falsification_execution_ledger.jsonl"
AUTH = PROJECT_ROOT / "experiments/l_3_one_run_falsification_authorization_v1.json"
REMEDIATION = PROJECT_ROOT / "experiments/l_3_invalid_run_ledger_remediation_v1.json"
ORIGINAL_ROW = {
    "container_sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd",
    "decision": "falsified", "event": "real_return_decision_run",
    "producing_git_commit": "3e3cfc773b8e327dca63bfdd8f2a1b103376173d", "run_id": "B7.3-L3-ONE",
}
ORIGINAL_ROW_SHA256 = "594b8cbbdf7c27769191ab9495275803478481121372cd3bfc6f7e6d3a8a556a"
REPORT_SHA256 = "3a61c2e8126aa8aa6cc53507a7cf7c5ae074c5ee84283d3c9c9a3d28c9486bc9"
INVALIDATION_EVENT = {
    "authoritative_outcome": "scope_restricted", "authorizes_real_return_decision_run": False,
    "event": "real_return_decision_run_invalidated",
    "final_report_path": "reports/experiments/l_3_falsification_report.json", "final_report_sha256": REPORT_SHA256,
    "invalidates_event": "real_return_decision_run", "locked_weekly_observation_ceiling": 465,
    "market_returns_read_count": 0, "observed_weekly_paired_observations": 500,
    "original_ledger_row_sha256": ORIGINAL_ROW_SHA256,
    "producing_git_commit": "3e3cfc773b8e327dca63bfdd8f2a1b103376173d",
    "provisional_metrics_inference_status": "invalid_unusable",
    "reason": "observation_window_started_before_2007-02-05", "run_id": "B7.3-L3-ONE",
    "schema_version": "lily_l3_invalid_run_invalidation_v1", "validation_access_authorized": False,
}
REQUIRED = {
    "schema_version", "order_id", "hypothesis_id", "evidence_tier", "edge_claim", "tier_blockers",
    "producing_git_commit", "authorization_sha256", "validation_seal", "report_mode", "execution_status",
    "decision", "market_returns_read", "preflight", "observation_counts", "primary_statistics",
    "realized_confirmation", "side_effects", "regimes", "mechanism_autopsy", "claim_limits",
    "post_parse_hard_stop",
}
NESTED_FIELDS = {
    "validation_seal": {"start", "end", "status", "validation_access_authorized"},
    "preflight": {"assets", "container_sha256", "date_column", "minimum_date", "maximum_date", "schema"},
    "observation_counts": {"weekly_paired_observations", "effective_independent_bet_equivalents", "mintrl_falsify", "asset_multiplier", "trade_multiplier"},
    "primary_statistics": {"mean_hhi_delta", "one_sided_upper_confidence_bound", "autocorrelations_lags_1_to_5"},
    "realized_confirmation": {"observations", "mean_hhi_delta", "threshold"},
    "side_effects": {"candidate_turnover", "comparator_turnover", "relative_increase", "met"},
    "regimes": {"claims", "rule"},
}


def _closed_object(report: dict[str, Any], key: str, blockers: list[str]) -> dict[str, Any]:
    value = report.get(key)
    if not isinstance(value, dict):
        blockers.append(f"nested_not_object:{key}")
        return {}
    blockers.extend(f"unknown_nested_field:{key}:{name}" for name in sorted(set(value) - NESTED_FIELDS[key]))
    blockers.extend(f"missing_nested_field:{key}:{name}" for name in sorted(NESTED_FIELDS[key] - set(value)))
    return value


def _read_ledger(path: Path, blockers: list[str]) -> tuple[list[bytes], list[dict[str, Any]]]:
    try:
        rows = [line for line in path.read_bytes().splitlines() if line]
        return rows, [json.loads(line) for line in rows]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        blockers.append("ledger_unreadable")
        return [], []


def _validate_invalidation(
    rows: list[bytes], ledger: list[dict[str, Any]], report_path: Path, remediation_path: Path, blockers: list[str]
) -> None:
    runs = [row for row in ledger if row.get("event") == "real_return_decision_run"]
    invalidations = [row for row in ledger if row.get("event") == "real_return_decision_run_invalidated"]
    if len(runs) != 1:
        blockers.append("exactly_one_run_ledger_mismatch")
    if len(invalidations) != 1:
        blockers.append("exactly_one_invalidation_ledger_mismatch")
    if len(ledger) != 2:
        blockers.append("unexpected_ledger_event")
    if not rows or hashlib.sha256(rows[0]).hexdigest() != ORIGINAL_ROW_SHA256 or (runs and runs[0] != ORIGINAL_ROW):
        blockers.append("original_ledger_row_not_byte_preserved")
    if invalidations and invalidations[0] != INVALIDATION_EVENT:
        blockers.append("invalidation_event_mismatch")
    if runs and runs[0].get("decision") == "falsified" and (len(invalidations) != 1 or invalidations[0] != INVALIDATION_EVENT):
        blockers.append("raw_ledger_decision_conflicts_without_valid_invalidation")
    if file_sha256(report_path) != REPORT_SHA256:
        blockers.append("final_report_hash_mismatch")
    try:
        remediation = load_json(remediation_path)
    except Exception as exc:
        blockers.append(f"remediation_unreadable:{type(exc).__name__}")
        return
    required = {"schema_version", "order_id", "hypothesis_id", "status", "authoritative_outcome", "edge_claim", "source_binding", "invalidation", "b7_4_attestation", "hard_stops"}
    if not isinstance(remediation, dict):
        blockers.append("remediation_not_object")
        return
    blockers.extend(f"unknown_remediation_field:{key}" for key in sorted(set(remediation) - required))
    blockers.extend(f"missing_remediation_field:{key}" for key in sorted(required - set(remediation)))
    expected = {
        "schema_version": "lily_l3_invalid_run_ledger_remediation_v1", "order_id": "B7.4", "hypothesis_id": "L-3",
        "status": "locked_invalid_run_ledger_remediation", "authoritative_outcome": "scope_restricted", "edge_claim": "none",
        "source_binding": {
            "original_ledger_row": {"ledger_path": "reports/experiments/l_3_falsification_execution_ledger.jsonl", "event": "real_return_decision_run", "run_id": "B7.3-L3-ONE", "producing_git_commit": "3e3cfc773b8e327dca63bfdd8f2a1b103376173d", "sha256": ORIGINAL_ROW_SHA256},
            "final_report": {"path": "reports/experiments/l_3_falsification_report.json", "sha256": REPORT_SHA256},
        },
        "invalidation": {"reason": "observation_window_started_before_2007-02-05", "observed_weekly_paired_observations": 500, "locked_weekly_observation_ceiling": 465, "provisional_metrics_inference_status": "invalid_unusable", "original_falsified_decision_status": "invalid_unusable"},
        "b7_4_attestation": {"market_returns_read_count": 0, "real_return_decision_run_count": 1, "invalidation_count": 1, "validation_access_authorized": False, "validation_status": "sealed_not_accessed", "second_run_authorized": False},
    }
    for key, value in expected.items():
        if remediation.get(key) != value:
            blockers.append(f"remediation_mismatch:{key}")
    hard_stops = remediation.get("hard_stops")
    if not isinstance(hard_stops, list) or len(hard_stops) != 4 or not any("every provisional metric" in item for item in hard_stops if isinstance(item, str)):
        blockers.append("remediation_hard_stops_incomplete")


def validate_report(
    path: Path = REPORT, *, ledger_path: Path = LEDGER, authorization_path: Path = AUTH, remediation_path: Path = REMEDIATION
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        report = load_json(path)
    except Exception as exc:
        return {"status": "blocked", "blockers": [f"report_unreadable:{type(exc).__name__}"]}
    rows, ledger = _read_ledger(ledger_path, blockers)
    if not isinstance(report, dict):
        return {"status": "blocked", "blockers": ["report_not_object"]}
    blockers.extend(f"unknown_field:{field}" for field in sorted(set(report) - REQUIRED))
    blockers.extend(f"missing_field:{field}" for field in sorted(REQUIRED - set(report)))
    for key, value in {"schema_version": "lily_l3_falsification_report_v1", "order_id": "B7.3", "hypothesis_id": "L-3", "evidence_tier": "E1", "edge_claim": "none", "market_returns_read": True, "report_mode": "execution_invalidated_post_parse", "execution_status": "scope_restricted", "decision": "scope_restricted"}.items():
        if report.get(key) != value:
            blockers.append(f"root_mismatch:{key}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(report.get("producing_git_commit", ""))):
        blockers.append("producing_git_commit_invalid")
    if report.get("authorization_sha256") != file_sha256(authorization_path):
        blockers.append("authorization_provenance_mismatch")
    seal = _closed_object(report, "validation_seal", blockers)
    if seal != {"start": "2016-01-04", "end": "2026-06-30", "status": "sealed_not_accessed", "validation_access_authorized": False}:
        blockers.append("validation_seal_mismatch")
    preflight = _closed_object(report, "preflight", blockers)
    counts = _closed_object(report, "observation_counts", blockers)
    statistics = _closed_object(report, "primary_statistics", blockers)
    realized = _closed_object(report, "realized_confirmation", blockers)
    side_effects = _closed_object(report, "side_effects", blockers)
    _closed_object(report, "regimes", blockers)
    if preflight.get("maximum_date") != "2015-12-31" or preflight.get("date_column") != "session_date":
        blockers.append("preflight_boundary_or_schema_mismatch")
    if counts.get("asset_multiplier") != 1 or counts.get("trade_multiplier") != 1:
        blockers.append("pseudo_replication")
    if counts.get("mintrl_falsify") != 49 or counts.get("weekly_paired_observations") != 500:
        blockers.append("observation_contract_mismatch")
    if not isinstance(counts.get("effective_independent_bet_equivalents"), (int, float)):
        blockers.append("independent_bet_count_missing")
    if not isinstance(statistics.get("autocorrelations_lags_1_to_5"), list) or len(statistics["autocorrelations_lags_1_to_5"]) != 5:
        blockers.append("serial_dependence_accounting_missing")
    if not isinstance(realized.get("observations"), int) or not isinstance(side_effects.get("met"), bool):
        blockers.append("confirmation_or_side_effect_missing")
    if not isinstance(report.get("post_parse_hard_stop"), str) or "465" not in report["post_parse_hard_stop"]:
        blockers.append("scope_restriction_reason_missing")
    _validate_invalidation(rows, ledger, path, remediation_path, blockers)
    return {
        "status": "pass" if not blockers else "blocked", "blockers": blockers,
        "report_path": relative_to_root(path, PROJECT_ROOT), "market_returns_read_count": 0,
        "real_return_decision_run_count": sum(row.get("event") == "real_return_decision_run" for row in ledger),
        "invalidation_count": sum(row.get("event") == "real_return_decision_run_invalidated" for row in ledger),
        "authoritative_outcome": "scope_restricted", "validation_status": "sealed_not_accessed",
    }


def main() -> int:
    result = validate_report()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
