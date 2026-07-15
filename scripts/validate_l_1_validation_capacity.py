from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root
from lib.market_calendar import nyse_sessions
from lib.provenance import file_sha256, payload_sha256
from lib.statistics import effective_sample_length


DEFAULT_JSON = PROJECT_ROOT / "reports" / "diagnostics" / "l_1_validation_capacity.json"
DEFAULT_MARKDOWN = PROJECT_ROOT / "reports" / "diagnostics" / "l_1_validation_capacity.md"
PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_1_baseline_preregistration.json"
B4_REPORT = PROJECT_ROOT / "reports" / "experiments" / "l_1_baseline_summary.json"
DATABENTO_REPORT = PROJECT_ROOT / "reports" / "data_quality" / "databento_l_1_capability.json"
EXPECTED_PREREGISTRATION_SHA256 = "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29"
EXPECTED_B4_DIGEST = "25985d2f649fa6a01d41b0ea76bde25624ada38f2ff5acc3ea2b35258e056439"


def validate_report(
    report_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MARKDOWN,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        report = load_json(report_path)
        markdown = markdown_path.read_text(encoding="utf-8")
        preregistration = load_json(PREREGISTRATION)
        b4_report = load_json(B4_REPORT)
        databento = load_json(DATABENTO_REPORT)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result([f"artifact_unreadable:{exc.__class__.__name__}"], report_path)

    expected = {
        "schema_version": "lily_l1_validation_capacity_report_v1",
        "order_id": "B4.2",
        "hypothesis_id": "L-1",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "decision": "statistical_capacity_funded_unlock_blocked",
    }
    for field, value in expected.items():
        if report.get(field) != value:
            blockers.append(f"field_mismatch:{field}")
    if file_sha256(PREREGISTRATION) != EXPECTED_PREREGISTRATION_SHA256:
        blockers.append("locked_preregistration_hash_mismatch")
    if b4_report.get("report_digest_sha256") != EXPECTED_B4_DIGEST:
        blockers.append("opened_stage_digest_mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", str(report.get("producing_git_commit", ""))):
        blockers.append("producing_git_commit_invalid")

    window = preregistration["sample_and_unlock_order"]["untouched_validation_window"]
    sessions = nyse_sessions(date.fromisoformat(window["start"]), date.fromisoformat(window["end"]))
    primary = b4_report["primary"]
    time_effective = effective_sample_length(len(sessions), primary["autocorrelations_lags_1_to_5"])
    joint = time_effective * primary["cross_sectional_effective_dimensions"]
    actual = report.get("locked_actual_recalculation", {})
    if report.get("calendar", {}).get("calendar_observations") != 2637 or len(sessions) != 2637:
        blockers.append("calendar_observation_count_mismatch")
    if not math.isclose(actual.get("time_effective_observations", -1), time_effective, rel_tol=0.0, abs_tol=1e-12):
        blockers.append("time_effective_observations_mismatch")
    if not math.isclose(actual.get("joint_independent_bet_equivalents", -1), joint, rel_tol=0.0, abs_tol=1e-9):
        blockers.append("joint_capacity_mismatch")
    binding = preregistration["dual_MinTRL"]["validate"]["binding_required_joint_independent_bet_equivalents"]
    if actual.get("binding_required_joint_independent_bet_equivalents") != binding or actual.get("all_nulls_funded") is not True:
        blockers.append("binding_capacity_decision_mismatch")
    nulls = actual.get("null_plans", [])
    if [row.get("id") for row in nulls] != ["portfolio_excess_zero", "minimum_acceptable_Sharpe", "active_vs_matched_benchmark"]:
        blockers.append("null_inventory_mismatch")
    if any(row.get("funded_under_locked_actual_recalculation") is not True for row in nulls):
        blockers.append("null_funding_mismatch")
    if report.get("planning_sensitivity", {}).get("binding_null_funded") is not False:
        blockers.append("planning_sensitivity_mismatch")

    guardrails = report.get("guardrails", {})
    required_false = (
        "validation_returns_opened",
        "validation_prices_opened",
        "validation_market_data_requested_from_databento",
        "credential_value_recorded",
        "market_data_downloaded",
        "paid_data_used",
        "orders_or_broker_actions",
    )
    if any(guardrails.get(field) is not False for field in required_false):
        blockers.append("guardrail_false_field_mismatch")
    if guardrails.get("maximum_return_date_accessed") != "2015-12-31" or guardrails.get("actual_paid_amount_usd") != 0:
        blockers.append("guardrail_boundary_mismatch")
    if report.get("unlock_assessment", {}).get("validation_window_status") != "sealed_not_accessed":
        blockers.append("validation_seal_mismatch")

    if databento.get("decision") != "not_fit_for_full_l1_validation_or_corporate_actions":
        blockers.append("databento_decision_mismatch")
    if databento.get("guardrails", {}).get("market_data_downloaded") is not False or databento.get("guardrails", {}).get("actual_paid_amount_usd") != 0:
        blockers.append("databento_guardrail_mismatch")
    databento_digest = databento.get("report_digest_sha256")
    databento_payload = dict(databento)
    databento_payload.pop("report_digest_sha256", None)
    if databento_digest != payload_sha256(databento_payload):
        blockers.append("databento_digest_mismatch")

    digest = report.get("report_digest_sha256")
    digest_payload = dict(report)
    digest_payload.pop("report_digest_sha256", None)
    if digest != payload_sha256(digest_payload):
        blockers.append("report_digest_mismatch")
    for required in (str(digest), str(report.get("producing_git_commit")), "E1", "sealed", "Databento"):
        if not required or required not in markdown:
            blockers.append(f"markdown_missing_machine_value:{required}")
    return _result(blockers, report_path)


def _result(blockers: list[str], report_path: Path) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "report_path": relative_to_root(report_path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the B4.2 validation-capacity report pack.")
    parser.add_argument("--report", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    result = validate_report(args.report, args.markdown)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
