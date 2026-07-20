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


DEFAULT_REGISTRY = PROJECT_ROOT / "experiments" / "hypothesis_registry.json"
DEFAULT_REPORTS_ROOT = PROJECT_ROOT / "reports"
ALLOWED_TIERS = {"E0", "E1", "E2", "E3"}
CLAIM_FIELDS = {
    "acceptance_status",
    "claim",
    "conclusion",
    "decision",
    "edge_claim",
    "research_decision",
    "result",
    "status",
}
POSITIVE_CLAIMS = {
    "accept",
    "accepted",
    "approve",
    "approved",
    "edge",
    "edge exists",
    "pass",
    "passed",
    "positive edge",
    "validated",
    "ผ่าน",
    "มี edge",
}
RESEARCH_REPORT_FOLDERS = {"adversarial", "baselines", "data_quality", "diagnostics", "experiments", "feasibility"}


def validate_evidence_tiers(
    reports_root: Path = DEFAULT_REPORTS_ROOT,
    registry_path: Path = DEFAULT_REGISTRY,
) -> dict[str, Any]:
    blockers: list[str] = []
    checked: list[dict[str, Any]] = []
    try:
        registry = load_json(registry_path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(reports_root, registry_path, [f"registry_unreadable:{exc.__class__.__name__}"], checked)
    known_ids = {
        item.get("id")
        for item in registry.get("hypotheses", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }

    for path in _research_reports(reports_root):
        try:
            payload = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            blockers.append(f"report_unreadable:{relative_to_root(path, PROJECT_ROOT)}:{exc.__class__.__name__}")
            continue
        if not isinstance(payload, dict):
            blockers.append(f"report_must_be_object:{relative_to_root(path, PROJECT_ROOT)}")
            continue
        report_blockers = validate_report_payload(payload, known_ids=known_ids)
        relative = relative_to_root(path, PROJECT_ROOT)
        blockers.extend(f"{relative}:{item}" for item in report_blockers)
        checked.append(
            {
                "path": relative,
                "hypothesis_id": payload.get("hypothesis_id"),
                "evidence_tier": payload.get("evidence_tier"),
                "blockers": report_blockers,
            }
        )
    return _result(reports_root, registry_path, blockers, checked)


def validate_report_payload(payload: dict[str, Any], *, known_ids: set[str]) -> list[str]:
    blockers: list[str] = []
    hypothesis_id = payload.get("hypothesis_id")
    evidence_tier = payload.get("evidence_tier")
    tier_blockers = payload.get("tier_blockers")
    if (
        tier_blockers is None
        and payload.get("schema_version") == "lily_l0_webull_th_fractional_preview_report_v1"
    ):
        tier_blockers = payload.get("claim_limits")

    if hypothesis_id not in known_ids:
        blockers.append(f"unknown_hypothesis_id:{hypothesis_id}")
    if evidence_tier not in ALLOWED_TIERS:
        blockers.append(f"invalid_evidence_tier:{evidence_tier}")
    if not isinstance(tier_blockers, list):
        blockers.append("tier_blockers_must_be_list")
    elif evidence_tier in {"E0", "E1"} and not tier_blockers:
        blockers.append(f"{evidence_tier}_requires_tier_blockers")

    claims = _positive_claims(payload)
    if claims and evidence_tier not in {"E2", "E3"}:
        blockers.extend(f"acceptance_or_edge_claim_below_E2:{field}:{value}" for field, value in claims)

    if evidence_tier in {"E2", "E3"}:
        blockers.extend(_validate_adversarial_review(payload.get("adversarial_review")))
    return blockers


def _validate_adversarial_review(review: Any) -> list[str]:
    if not isinstance(review, dict):
        return ["E2_requires_adversarial_review"]
    blockers: list[str] = []
    if review.get("status") not in {"completed", "passed"}:
        blockers.append("adversarial_review_not_completed")
    if not isinstance(review.get("reviewed_by"), str) or not review["reviewed_by"].strip():
        blockers.append("adversarial_review_missing_reviewer_identity")
    if review.get("reviewer_is_independent") is not True:
        blockers.append("adversarial_review_must_be_independent")
    attempts = review.get("refutation_attempts")
    if not isinstance(attempts, list) or not attempts:
        blockers.append("adversarial_review_requires_refutation_attempts")
    critical = review.get("unresolved_critical_issues")
    if not isinstance(critical, list):
        blockers.append("adversarial_review_requires_critical_issue_list")
    elif critical:
        blockers.append("adversarial_review_has_unresolved_critical_issue")
    return blockers


def _positive_claims(payload: Any, prefix: str = "") -> list[tuple[str, str]]:
    claims: list[tuple[str, str]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            field = f"{prefix}.{key}" if prefix else key
            is_claim_field = key.lower() in CLAIM_FIELDS and (key.lower() != "status" or not prefix)
            if is_claim_field and isinstance(value, str):
                normalized = " ".join(value.strip().lower().split())
                if normalized in POSITIVE_CLAIMS:
                    claims.append((field, value))
            claims.extend(_positive_claims(value, field))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            claims.extend(_positive_claims(value, f"{prefix}[{index}]"))
    return claims


def _research_reports(root: Path) -> list[Path]:
    if not root.exists():
        return []
    paths: list[Path] = []
    for folder_name in sorted(RESEARCH_REPORT_FOLDERS):
        folder = root / folder_name
        if folder.exists():
            paths.extend(sorted(folder.rglob("*.json")))
    return paths


def _result(
    reports_root: Path,
    registry_path: Path,
    blockers: list[str],
    checked: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "reports_root": relative_to_root(reports_root, PROJECT_ROOT),
        "registry_path": relative_to_root(registry_path, PROJECT_ROOT),
        "report_count": len(checked),
        "checked": checked,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Reject Lily evidence-tier overstatement.")
    parser.add_argument("--reports-root", type=Path, default=DEFAULT_REPORTS_ROOT)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    result = validate_evidence_tiers(args.reports_root, args.registry)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
