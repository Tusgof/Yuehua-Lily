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
from lib.provenance import payload_sha256
from scripts.run_l_0_sizing_feasibility import (
    DEFAULT_INPUTS,
    DEFAULT_JSON,
    DEFAULT_MARKDOWN,
    DEFAULT_PREREGISTRATION,
    build_report_payload,
    render_markdown,
)


def validate_report(
    report_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MARKDOWN,
    preregistration_path: Path = DEFAULT_PREREGISTRATION,
    inputs_path: Path = DEFAULT_INPUTS,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        report = load_json(report_path)
        preregistration = load_json(preregistration_path)
        inputs = load_json(inputs_path)
        markdown = markdown_path.read_text(encoding="utf-8")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result([f"unreadable_input:{exc.__class__.__name__}"], report_path, markdown_path)

    if report.get("schema_version") != "lily_l0_sizing_feasibility_report_v1":
        blockers.append("invalid_schema_version")
    if report.get("hypothesis_id") != "L-0":
        blockers.append("hypothesis_id_must_be_L-0")
    if report.get("evidence_tier") != "E0" or report.get("edge_claim") != "none":
        blockers.append("report_must_be_E0_with_no_edge_claim")
    if report.get("decision") != "scope_restricted":
        blockers.append("decision_must_be_scope_restricted")
    if any(report.get("guardrails", {}).values()):
        blockers.append("forbidden_guardrail_activity_recorded")
    producing_commit = report.get("producing_git_commit")
    if not isinstance(producing_commit, str) or len(producing_commit) != 40:
        blockers.append("invalid_producing_git_commit")
    else:
        expected = build_report_payload(
            preregistration,
            inputs,
            producing_commit=producing_commit,
        )
        actual_without_provenance = {key: value for key, value in report.items() if key != "provenance"}
        if actual_without_provenance != expected:
            blockers.append("machine_report_does_not_match_locked_calculation")
        if markdown != render_markdown(expected).rstrip() + "\n":
            blockers.append("markdown_does_not_match_machine_report")

    digest_payload = {
        key: value
        for key, value in report.items()
        if key not in {"provenance", "report_digest_sha256"}
    }
    if report.get("report_digest_sha256") != payload_sha256(digest_payload):
        blockers.append("report_digest_mismatch")

    micro = report.get("futures", {}).get("micro", [])
    full = report.get("futures", {}).get("full_size_comparator", [])
    if [row.get("minimum_capital_usd") for row in micro] != [40600, 54200, 95400]:
        blockers.append("unexpected_micro_minimum_capital")
    if [row.get("minimum_capital_usd") for row in full] != [405900, 541200, 1614600]:
        blockers.append("unexpected_full_size_minimum_capital")
    broker_results = report.get("etf", {}).get("broker_results", [])
    expected_pairs = {
        (capital, broker)
        for capital in (1000, 2000)
        for broker in (
            "Webull_Thailand_manual_fractional",
            "Webull_Thailand_OpenAPI_fractional",
            "IBKR_fractional_reference",
        )
    }
    actual_pairs = {(row.get("capital_usd"), row.get("broker_path")) for row in broker_results}
    if actual_pairs != expected_pairs or any(row.get("classification") != "scope_restricted" for row in broker_results):
        blockers.append("broker_path_classification_incomplete")
    return _result(blockers, report_path, markdown_path)


def _result(blockers: list[str], report_path: Path, markdown_path: Path) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "report_path": relative_to_root(report_path, PROJECT_ROOT),
        "markdown_path": relative_to_root(markdown_path, PROJECT_ROOT),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the locked L-0 sizing report pair.")
    parser.add_argument("--report", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--preregistration", type=Path, default=DEFAULT_PREREGISTRATION)
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    args = parser.parse_args()
    result = validate_report(args.report, args.markdown, args.preregistration, args.inputs)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
