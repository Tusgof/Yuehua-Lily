from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.environment import interpreter_metadata
from lib.io import load_json, write_json
from lib.market_calendar import nyse_sessions
from lib.provenance import file_sha256, git_commit, payload_sha256
from lib.report import render_markdown_report
from lib.statistics import effective_sample_length


PREREGISTRATION = PROJECT_ROOT / "experiments" / "l_1_baseline_preregistration.json"
B4_REPORT = PROJECT_ROOT / "reports" / "experiments" / "l_1_baseline_summary.json"
DATABENTO_INPUT = PROJECT_ROOT / "experiments" / "inputs" / "b4_2_databento_metadata_probe.json"
MAIN_JSON = PROJECT_ROOT / "reports" / "diagnostics" / "l_1_validation_capacity.json"
MAIN_MARKDOWN = PROJECT_ROOT / "reports" / "diagnostics" / "l_1_validation_capacity.md"
DATABENTO_REPORT = PROJECT_ROOT / "reports" / "data_quality" / "databento_l_1_capability.json"

EXPECTED_PREREGISTRATION_SHA256 = "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29"
EXPECTED_B4_DIGEST = "25985d2f649fa6a01d41b0ea76bde25624ada38f2ff5acc3ea2b35258e056439"


def main() -> int:
    if file_sha256(PREREGISTRATION) != EXPECTED_PREREGISTRATION_SHA256:
        raise ValueError("locked L-1 preregistration hash changed")
    preregistration = load_json(PREREGISTRATION)
    b4_report = load_json(B4_REPORT)
    databento_input = load_json(DATABENTO_INPUT)
    if b4_report.get("report_digest_sha256") != EXPECTED_B4_DIGEST:
        raise ValueError("opened-stage report digest changed")

    produced_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    start = date.fromisoformat(preregistration["sample_and_unlock_order"]["untouched_validation_window"]["start"])
    end = date.fromisoformat(preregistration["sample_and_unlock_order"]["untouched_validation_window"]["end"])
    sessions = nyse_sessions(start, end)
    primary = b4_report["primary"]
    autocorrelations = [float(value) for value in primary["autocorrelations_lags_1_to_5"]]
    cross_dimension = float(primary["cross_sectional_effective_dimensions"])
    time_effective = effective_sample_length(len(sessions), autocorrelations)
    joint_capacity = time_effective * cross_dimension

    validation_plan = preregistration["dual_MinTRL"]["validate"]
    null_rows = []
    for plan in validation_plan["null_plans"]:
        required = int(plan["required_joint_independent_bet_equivalents"])
        null_rows.append(
            {
                "id": plan["id"],
                "required_joint_independent_bet_equivalents": required,
                "projected_joint_independent_bet_equivalents": joint_capacity,
                "funded_under_locked_actual_recalculation": joint_capacity >= required,
                "capacity_ratio": joint_capacity / required,
            }
        )

    planning_autocorrelations = [float(value) for value in preregistration["dual_MinTRL"]["planning_autocorrelations_lags_1_to_5"]]
    planning_dimension = float(preregistration["dual_MinTRL"]["planning_cross_sectional_effective_dimensions"])
    planning_time_effective = effective_sample_length(len(sessions), planning_autocorrelations)
    planning_joint_capacity = planning_time_effective * planning_dimension
    binding_required = int(validation_plan["binding_required_joint_independent_bet_equivalents"])

    databento_report = _databento_report(databento_input, produced_at)
    write_json(DATABENTO_REPORT, databento_report)
    payload: dict[str, object] = {
        "schema_version": "lily_l1_validation_capacity_report_v1",
        "order_id": "B4.2",
        "hypothesis_id": "L-1",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "decision": "statistical_capacity_funded_unlock_blocked",
        "produced_at": produced_at,
        "producing_git_commit": git_commit(PROJECT_ROOT),
        "environment": interpreter_metadata(),
        "locked_inputs": {
            "l_1_preregistration_path": "experiments/l_1_baseline_preregistration.json",
            "l_1_preregistration_sha256": file_sha256(PREREGISTRATION),
            "opened_stage_report_path": "reports/experiments/l_1_baseline_summary.json",
            "opened_stage_report_sha256": file_sha256(B4_REPORT),
            "opened_stage_report_digest_sha256": b4_report["report_digest_sha256"],
        },
        "calendar": {
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "source_type": "calendar_rules_only_no_market_observations",
            "calendar_observations": len(sessions),
            "first_session": sessions[0].isoformat(),
            "last_session": sessions[-1].isoformat(),
            "sessions_by_year": {str(year): count for year, count in sorted(Counter(item.year for item in sessions).items())},
            "early_closes_count_as_sessions": True,
            "special_full_day_closures": ["2018-12-05", "2025-01-09"],
            "sources": [
                "https://www.nyse.com/markets/hours-calendars",
                "https://ir.theice.com/press/news-details/2018/New-York-Stock-Exchange-to-Honor-President-George-H-W-Bush/default.aspx",
                "https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx",
            ],
        },
        "locked_actual_recalculation": {
            "source": "B4 primary opened-stage dependence fields",
            "autocorrelations_lags_1_to_5": autocorrelations,
            "cross_sectional_effective_dimensions": cross_dimension,
            "time_effective_observations": time_effective,
            "joint_independent_bet_equivalents": joint_capacity,
            "binding_required_joint_independent_bet_equivalents": binding_required,
            "binding_capacity_margin": joint_capacity - binding_required,
            "binding_capacity_ratio": joint_capacity / binding_required,
            "all_nulls_funded": all(row["funded_under_locked_actual_recalculation"] for row in null_rows),
            "null_plans": null_rows,
        },
        "planning_sensitivity": {
            "purpose": "Report the founding planning assumptions as a non-binding sensitivity; they may not replace the locked actual-recalculation rule.",
            "autocorrelations_lags_1_to_5": planning_autocorrelations,
            "cross_sectional_effective_dimensions": planning_dimension,
            "time_effective_observations": planning_time_effective,
            "joint_independent_bet_equivalents": planning_joint_capacity,
            "binding_null_funded": planning_joint_capacity >= binding_required,
        },
        "databento_capability": {
            "report_path": "reports/data_quality/databento_l_1_capability.json",
            "report_digest_sha256": databento_report["report_digest_sha256"],
            "decision": databento_report["decision"],
            "actual_paid_amount_usd": 0,
        },
        "unlock_assessment": {
            "statistical_capacity_condition": "funded",
            "validation_returns_permission": "not_granted",
            "validation_window_status": "sealed_not_accessed",
            "blocking_conditions": [
                "Independent point-in-time corporate-action provenance remains unavailable for the full L-1 path.",
                "VGK and VWO remain outside the locked daily corporate-action reconciliation tolerance.",
                "Databento metadata does not cover 2016-01-04 through 2018-04-30 and exposes no dedicated corporate-actions history for this purpose.",
                "A separate owner-approved unlock gate has not been created.",
            ],
        },
        "guardrails": {
            "validation_returns_opened": False,
            "validation_prices_opened": False,
            "validation_market_data_requested_from_databento": False,
            "maximum_return_date_accessed": "2015-12-31",
            "provider_metadata_credential_used": True,
            "credential_value_recorded": False,
            "market_data_downloaded": False,
            "paid_data_used": False,
            "actual_paid_amount_usd": 0,
            "orders_or_broker_actions": False,
        },
        "methodology_sources": [
            {"path": "wiki/concepts/minimum-track-record-length.md", "sha256": "ca65225740673bd363be7461b8022281da08ae32e6ff42f8887f1072eb51ad81"},
            {"path": "wiki/concepts/sharpe-ratio-inference.md", "sha256": "4a13ed9ba9d8e6539544a1259f933a5cc1137fbdb899f04e91fa49fa6f7e6f5e"},
            {"path": "wiki/concepts/backtest-validation-protocol.md", "sha256": "c7f843310706d902120651e677429e66cbde9ce96ee526544de5419ee99aefa0"},
        ],
        "tier_blockers": [
            "Capacity is a prospective arithmetic check and contains no validation performance evidence.",
            "The favorable locked actual-dependence projection funds MinTRL, while the original planning sensitivity does not fund the binding null.",
            "Corporate-action point-in-time provenance and locked daily reconciliation blockers remain unresolved.",
            "No validation unlock, adversarial review, E2 promotion, broker action, paper trade, or real-money action occurred.",
        ],
        "exact_next_safe_action": "Keep validation returns sealed. Resolve or formally source-restrict point-in-time corporate actions, confirm the Databento credit is backed by real payment before any paid request, and create a separate owner-approved validation unlock gate only if the remaining data blockers are cleared.",
    }
    payload["report_digest_sha256"] = payload_sha256(payload)
    write_json(MAIN_JSON, payload)
    MAIN_MARKDOWN.parent.mkdir(parents=True, exist_ok=True)
    MAIN_MARKDOWN.write_text(_markdown(payload), encoding="utf-8", newline="\n")
    print(json.dumps({"status": "completed_E1", "digest": payload["report_digest_sha256"]}, indent=2))
    return 0


def _databento_report(source: dict[str, object], produced_at: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "lily_databento_l1_capability_report_v1",
        "order_id": "B4.2",
        "hypothesis_id": "L-1",
        "evidence_tier": "E1",
        "edge_claim": "none",
        "decision": "not_fit_for_full_l1_validation_or_corporate_actions",
        "produced_at": produced_at,
        "producing_git_commit": git_commit(PROJECT_ROOT),
        "source_probe_path": "experiments/inputs/b4_2_databento_metadata_probe.json",
        "source_probe_sha256": file_sha256(DATABENTO_INPUT),
        "authentication": source["authentication"],
        "key_environment_name": source["key_environment_name"],
        "key_provenance": source["key_provenance"],
        "account_credit_usd": source["account_credit_usd"],
        "relevant_datasets": source["relevant_datasets"],
        "field_audit": source["field_audit"],
        "official_sources": source["official_sources"],
        "tier_blockers": source["reasons"],
        "guardrails": {
            "credential_value_recorded": False,
            "validation_market_data_requested": False,
            "market_data_downloaded": False,
            "actual_paid_amount_usd": 0,
            "account_balance_api_verified": False,
        },
    }
    payload["report_digest_sha256"] = payload_sha256(payload)
    return payload


def _markdown(payload: dict[str, object]) -> str:
    actual = payload["locked_actual_recalculation"]
    planning = payload["planning_sensitivity"]
    calendar = payload["calendar"]
    unlock = payload["unlock_assessment"]
    assert all(isinstance(value, dict) for value in (actual, planning, calendar, unlock))
    sections = [
        (
            "สถานะ",
            f"- Order: `B4.2`\n- Evidence: `E1`\n- Edge claim: `none`\n- Decision: `{payload['decision']}`\n- Producing commit: `{payload['producing_git_commit']}`\n- Machine digest: `{payload['report_digest_sha256']}`",
        ),
        (
            "คำถาม",
            "ช่วง validation ที่ยังปิดผนึกมีจำนวน session เพียงพอสำหรับ MinTRL_validate ทั้งสาม null หรือไม่ เมื่อใช้ dependence จากช่วง falsification ตามกติกาที่ล็อกไว้ โดยไม่อ่านราคาและผลตอบแทน validation",
        ),
        (
            "ปฏิทินที่ใช้",
            f"ช่วง `{calendar['window_start']}` ถึง `{calendar['window_end']}` มี {calendar['calendar_observations']:,} NYSE sessions การนับใช้กฎวันหยุดและวันปิดพิเศษเท่านั้น ไม่มี market observations และวันปิดเร็วถือเป็น session",
        ),
        (
            "ผล capacity ตามกติกาที่ล็อก",
            f"Time-effective observations: {actual['time_effective_observations']:,.2f}\n\nCross-sectional effective dimensions: {actual['cross_sectional_effective_dimensions']:.4f}\n\nProjected joint independent-bet equivalents: {actual['joint_independent_bet_equivalents']:,.2f}\n\nBinding MinTRL_validate: {actual['binding_required_joint_independent_bet_equivalents']:,}\n\nCapacity ratio: {actual['binding_capacity_ratio']:.2f} เท่า\n\nNull ทั้งหมด funded: `{str(actual['all_nulls_funded']).lower()}`",
        ),
        (
            "Sensitivity ที่ต้องระวัง",
            f"เมื่อใช้ planning assumptions เดิมแทน dependence ที่วัดได้ จะได้ joint independent-bet equivalents เพียง {planning['joint_independent_bet_equivalents']:,.2f} และ binding null funded = `{str(planning['binding_null_funded']).lower()}` ผล funded จึงพึ่งพา dependence ที่สืบทอดจากช่วงก่อนปี 2016 อย่างมีนัยสำคัญ",
        ),
        (
            "Databento",
            "Key ใช้ metadata ได้และไม่มีการซื้อข้อมูล แต่ coverage หุ้นสหรัฐที่เกี่ยวข้องเริ่มปี 2018 หรือช้ากว่า และไม่มี dedicated corporate-actions schema จึงใช้แทนข้อมูลทั้ง validation window หรือแก้ point-in-time corporate actions ไม่ได้",
        ),
        (
            "เหตุที่ยังเปิด validation ไม่ได้",
            "\n".join(f"- {item}" for item in unlock["blocking_conditions"]),
        ),
        ("ขั้นต่อไปที่ปลอดภัย", str(payload["exact_next_safe_action"])),
    ]
    return render_markdown_report("Lily L-1 Validation Funding Capacity", sections)


if __name__ == "__main__":
    raise SystemExit(main())
