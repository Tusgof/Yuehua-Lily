"""Semantic, closed-world validation for the one permitted L-3 B7.3 report."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, load_jsonl, relative_to_root
from lib.provenance import file_sha256

REPORT = PROJECT_ROOT / "reports/experiments/l_3_falsification_report.json"
LEDGER = PROJECT_ROOT / "reports/experiments/l_3_falsification_execution_ledger.jsonl"
AUTH = PROJECT_ROOT / "experiments/l_3_one_run_falsification_authorization_v1.json"
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


def validate_report(
    path: Path = REPORT, *, ledger_path: Path = LEDGER, authorization_path: Path = AUTH
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        report = load_json(path)
        ledger = load_jsonl(ledger_path)
    except Exception as exc:
        return {"status": "blocked", "blockers": [f"report_unreadable:{type(exc).__name__}"]}
    if not isinstance(report, dict):
        return {"status": "blocked", "blockers": ["report_not_object"]}
    blockers.extend(f"unknown_field:{field}" for field in sorted(set(report) - REQUIRED))
    blockers.extend(f"missing_field:{field}" for field in sorted(REQUIRED - set(report)))
    for key, value in {
        "schema_version": "lily_l3_falsification_report_v1", "order_id": "B7.3", "hypothesis_id": "L-3",
        "evidence_tier": "E1", "edge_claim": "none", "market_returns_read": True,
    }.items():
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
    if preflight.get("maximum_date") != "2015-12-31" or preflight.get("date_column") != "session_date":
        blockers.append("preflight_boundary_or_schema_mismatch")
    counts = _closed_object(report, "observation_counts", blockers)
    statistics = _closed_object(report, "primary_statistics", blockers)
    realized = _closed_object(report, "realized_confirmation", blockers)
    side_effects = _closed_object(report, "side_effects", blockers)
    _closed_object(report, "regimes", blockers)
    if counts.get("asset_multiplier") != 1 or counts.get("trade_multiplier") != 1:
        blockers.append("pseudo_replication")
    if counts.get("mintrl_falsify") != 49 or not isinstance(counts.get("weekly_paired_observations"), int):
        blockers.append("observation_contract_mismatch")
    if not isinstance(counts.get("effective_independent_bet_equivalents"), (int, float)):
        blockers.append("independent_bet_count_missing")
    if not isinstance(statistics.get("autocorrelations_lags_1_to_5"), list) or len(statistics["autocorrelations_lags_1_to_5"]) != 5:
        blockers.append("serial_dependence_accounting_missing")
    if not isinstance(realized.get("observations"), int) or not isinstance(side_effects.get("met"), bool):
        blockers.append("confirmation_or_side_effect_missing")
    runs = [row for row in ledger if isinstance(row, dict) and row.get("event") == "real_return_decision_run"]
    if len(runs) != 1:
        blockers.append("exactly_one_run_ledger_mismatch")
    elif (
        runs[0].get("run_id") != "B7.3-L3-ONE"
        or runs[0].get("producing_git_commit") != report.get("producing_git_commit")
        or runs[0].get("container_sha256") != preflight.get("container_sha256")
    ):
        blockers.append("ledger_provenance_mismatch")
    decision = report.get("decision")
    if decision not in {"falsified", "not_falsified_not_validated", "scope_restricted"}:
        blockers.append("decision_invalid")
    if report.get("execution_status") != decision:
        blockers.append("decision_status_mismatch")
    funded = counts.get("effective_independent_bet_equivalents", 0) >= 49
    if decision in {"falsified", "not_falsified_not_validated"} and not funded:
        blockers.append("unfunded_inference")
    if decision == "falsified" and not isinstance(report.get("mechanism_autopsy"), dict):
        blockers.append("mechanism_autopsy_missing")
    if decision == "scope_restricted":
        hard_stop = report.get("post_parse_hard_stop")
        if not isinstance(hard_stop, str) or not hard_stop:
            blockers.append("scope_restriction_reason_missing")
        if counts.get("weekly_paired_observations", 0) > 465 and (
            report.get("report_mode") != "execution_invalidated_post_parse" or "465" not in str(hard_stop)
        ):
            blockers.append("weekly_capacity_ceiling_breached")
    elif report.get("post_parse_hard_stop") is not None:
        blockers.append("unexpected_post_parse_hard_stop")
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "report_path": relative_to_root(path, PROJECT_ROOT)}


def main() -> int:
    result = validate_report()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
