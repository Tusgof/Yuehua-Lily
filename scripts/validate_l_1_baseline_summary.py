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
from lib.provenance import file_sha256, payload_sha256


DEFAULT_JSON = PROJECT_ROOT / "reports" / "experiments" / "l_1_baseline_summary.json"
DEFAULT_MARKDOWN = PROJECT_ROOT / "reports" / "experiments" / "l_1_baseline_summary.md"
DEFAULT_SEARCH_LOG = PROJECT_ROOT / "reports" / "experiments" / "l_1_search_log.jsonl"
DEFAULT_ADVERSARIAL = PROJECT_ROOT / "reports" / "adversarial" / "l_1_baseline_review.json"
PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_1_baseline_preregistration.json"
PREREGISTRATION_VALIDATOR = PROJECT_ROOT / "scripts" / "validate_l_1_baseline_preregistration.py"
EXPECTED_PREREGISTRATION_HASH = "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29"
EXPECTED_VALIDATOR_HASH = "c568f5db8236e253e63056ed2797ead9259397d293c478e7f0abf53bfda70232"
TRIAL_IDS = ["primary_60", "sensitivity_40", "sensitivity_80", "sensitivity_low_cost", "sensitivity_severe_cost"]


def validate_summary(
    report_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MARKDOWN,
    search_log_path: Path = DEFAULT_SEARCH_LOG,
    adversarial_path: Path = DEFAULT_ADVERSARIAL,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        report = load_json(report_path)
        markdown = markdown_path.read_text(encoding="utf-8")
        search_rows = load_jsonl(search_log_path)
        adversarial = load_json(adversarial_path)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        return _result([f"artifact_unreadable:{exc.__class__.__name__}"], report_path, markdown_path)
    expected_root = {
        "schema_version": "lily_l1_baseline_summary_v1",
        "hypothesis_id": "L-1",
        "experiment_id": "L1-BASELINE",
        "evidence_tier": "E1",
        "edge_claim": "none",
    }
    for field, expected in expected_root.items():
        if report.get(field) != expected:
            blockers.append(f"root_field_mismatch:{field}")
    if report.get("decision") not in {"not_falsified_but_not_validated", "underfunded_scope_restricted"}:
        blockers.append("decision_must_remain_E1")
    if not re.fullmatch(r"[0-9a-f]{40}", str(report.get("producing_git_commit", ""))):
        blockers.append("producing_git_commit_invalid")
    if not report.get("tier_blockers"):
        blockers.append("tier_blockers_required")
    if not report.get("exact_next_safe_action"):
        blockers.append("exact_next_safe_action_required")

    gate = report.get("locked_gate", {})
    actual_prereg = file_sha256(project_root / "experiments" / "l_1_baseline_preregistration.json")
    actual_validator = file_sha256(project_root / "scripts" / "validate_l_1_baseline_preregistration.py")
    if actual_prereg != EXPECTED_PREREGISTRATION_HASH or gate.get("preregistration_sha256") != actual_prereg:
        blockers.append("locked_preregistration_hash_mismatch")
    if actual_validator != EXPECTED_VALIDATOR_HASH or gate.get("validator_sha256") != actual_validator:
        blockers.append("locked_validator_hash_mismatch")

    data = report.get("data", {})
    if data.get("maximum_session_accessed") != "2015-12-31":
        blockers.append("falsification_cutoff_mismatch")
    if data.get("untouched_validation", {}).get("status") != "sealed_not_accessed":
        blockers.append("validation_must_remain_sealed")
    if data.get("paid_amount_usd") != 0 or data.get("credentials_used") is not False:
        blockers.append("forbidden_data_or_credentials")
    if len(data.get("dataset_ids", [])) < 2 or not data.get("dataset_hashes"):
        blockers.append("dataset_provenance_incomplete")

    trials = report.get("trials")
    if not isinstance(trials, list) or [row.get("trial_id") for row in trials] != TRIAL_IDS:
        blockers.append("locked_trial_inventory_mismatch")
        trials = []
    elif [row.get("claim_eligible") for row in trials] != [True, False, False, False, False]:
        blockers.append("claim_eligibility_mismatch")
    primary = report.get("primary", {})
    required_primary = {
        "gross", "net", "active_vs_matched_benchmark", "turnover_one_way_notional",
        "executed_asset_trades", "cost_decomposition_return_units", "exposure", "holding_overlap",
        "autocorrelations_lags_1_to_5", "time_effective_observations",
        "cross_sectional_effective_dimensions", "joint_independent_bet_equivalents", "DSR",
        "regime_matrix", "asset_and_region_matrix", "payoff_tests", "concentration_tests", "removals",
    }
    if not isinstance(primary, dict) or required_primary - set(primary):
        blockers.append("primary_metric_inventory_incomplete")
    if trials and primary.get("trial_id") != trials[0].get("trial_id"):
        blockers.append("primary_trial_not_primary_60")

    unlock = report.get("dual_MinTRL_and_unlock", {})
    if unlock.get("unlock_decision") != "remain_sealed" or unlock.get("validation_capacity_verified") is not False:
        blockers.append("unlock_status_invalid")
    actual_joint = primary.get("joint_independent_bet_equivalents")
    if isinstance(actual_joint, (int, float)):
        if unlock.get("falsification_actual_joint_independent_bet_equivalents") != actual_joint:
            blockers.append("joint_bet_value_mismatch")
        if unlock.get("falsification_funded") != (actual_joint >= 3850):
            blockers.append("MinTRL_funding_boolean_mismatch")
    else:
        blockers.append("joint_bet_value_missing")
    if report.get("current_capital_branch", {}).get("status") != "scope_restricted_not_run":
        blockers.append("current_capital_branch_must_be_scope_restricted")
    guardrails = report.get("guardrails", {})
    if any(guardrails.values()):
        blockers.append("forbidden_activity_recorded")

    digest = report.get("report_digest_sha256")
    digest_payload = dict(report)
    digest_payload.pop("report_digest_sha256", None)
    if digest != payload_sha256(digest_payload):
        blockers.append("report_digest_mismatch")
    for required in (str(digest), str(report.get("producing_git_commit")), "E1", "sealed_not_accessed"):
        if not required or required not in markdown:
            blockers.append(f"markdown_missing_machine_value:{required}")

    run_id = report.get("run_id")
    run_rows = [row for row in search_rows if row.get("run_id") == run_id]
    completed = [row for row in run_rows if row.get("event") == "trial_completed"]
    if sum(row.get("event") == "run_started" for row in run_rows) != 1:
        blockers.append("search_log_run_start_mismatch")
    if [row.get("trial_id") for row in completed] != TRIAL_IDS:
        blockers.append("search_log_trial_inventory_mismatch")
    if adversarial.get("status") != "not_started_E1_no_promotion" or adversarial.get("promotion_requested") is not False:
        blockers.append("adversarial_status_misrepresented")
    if adversarial.get("reviewer_is_independent") is not False:
        blockers.append("independent_review_must_not_be_fabricated")
    return _result(blockers, report_path, markdown_path)


def _result(blockers: list[str], report_path: Path, markdown_path: Path) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "report_path": relative_to_root(report_path, PROJECT_ROOT),
        "markdown_path": relative_to_root(markdown_path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the locked L-1 E1 report and trial log.")
    parser.add_argument("--report", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--search-log", type=Path, default=DEFAULT_SEARCH_LOG)
    parser.add_argument("--adversarial", type=Path, default=DEFAULT_ADVERSARIAL)
    args = parser.parse_args()
    result = validate_summary(args.report, args.markdown, args.search_log, args.adversarial)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
