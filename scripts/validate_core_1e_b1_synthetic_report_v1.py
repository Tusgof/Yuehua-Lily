"""Closed-world semantic validation for the CORE-1E-B1 synthetic report."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = PROJECT_ROOT / "experiments" / "core_1e_b1_development_execution_contract_v1.json"
FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "core1e_a" / "synthetic_market_v1.json"
ENGINE = PROJECT_ROOT / "lib" / "core_1e_a_synthetic_engine.py"
ADAPTER = PROJECT_ROOT / "lib" / "core_1e_b1_synthetic_adapter_v1.py"
REPORT_SCHEMA = PROJECT_ROOT / "schemas" / "core_1e_b1_synthetic_report_v1.schema.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.core_1e_b1_synthetic_adapter_v1 import (  # noqa: E402
    ACCESS_COUNTS,
    FIXTURE_ID,
    FIXTURE_PATH,
    REPORT_SCHEMA_VERSION,
    VALIDATION_SEAL,
    build_synthetic_report,
)
from lib.io import load_json  # noqa: E402
from lib.provenance import file_sha256, git_commit  # noqa: E402


TOP_LEVEL = {
    "schema_version",
    "order_id",
    "status",
    "evidence_tier",
    "edge_claim",
    "contract_sha256",
    "fixture",
    "selection",
    "calculation_report",
    "access_counts",
    "validation_seal",
    "lifecycle",
    "provenance",
}
FIXTURE_KEYS = {"path", "sha256", "fixture_id", "max_date"}
LIFECYCLE = {
    "marker_first": True,
    "input_read_count": 1,
    "temporary_git_proof": True,
    "project_artifacts_created": False,
    "real_data_accessed": False,
    "validation_accessed": False,
    "second_execution_refused": False,
}
PROVENANCE_KEYS = {"producing_commit", "engine_path", "engine_sha256", "adapter_path", "adapter_sha256"}


def _keys(value: Any, expected: set[str], label: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        blockers.append(f"{label}_must_be_object")
        return
    blockers.extend(f"{label}_missing:{key}" for key in sorted(expected - set(value)))
    blockers.extend(f"{label}_unknown:{key}" for key in sorted(set(value) - expected))


def _finite(value: Any, label: str, blockers: list[str]) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, float) and not math.isfinite(value):
        blockers.append(f"nonfinite_number:{label}")
    elif isinstance(value, dict):
        for key, child in value.items():
            _finite(child, f"{label}.{key}", blockers)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _finite(child, f"{label}[{index}]", blockers)


def _shape_blockers(report: Any) -> list[str]:
    blockers: list[str] = []
    _keys(report, TOP_LEVEL, "report", blockers)
    if not isinstance(report, dict):
        return blockers
    fixture = report.get("fixture")
    _keys(fixture, FIXTURE_KEYS, "fixture", blockers)
    if isinstance(fixture, dict):
        if fixture.get("path") != FIXTURE_PATH:
            blockers.append("fixture_path_changed")
        if fixture.get("fixture_id") != FIXTURE_ID:
            blockers.append("fixture_id_changed")
    _keys(report.get("access_counts"), set(ACCESS_COUNTS), "access_counts", blockers)
    _keys(report.get("validation_seal"), set(VALIDATION_SEAL), "validation_seal", blockers)
    _keys(report.get("lifecycle"), set(LIFECYCLE), "lifecycle", blockers)
    _keys(report.get("provenance"), PROVENANCE_KEYS, "provenance", blockers)
    if isinstance(report.get("provenance"), dict):
        provenance = report["provenance"]
        if provenance.get("engine_path") != "lib/core_1e_a_synthetic_engine.py":
            blockers.append("engine_path_changed")
        if provenance.get("adapter_path") != "lib/core_1e_b1_synthetic_adapter_v1.py":
            blockers.append("adapter_path_changed")
    if not isinstance(report.get("calculation_report"), dict):
        blockers.append("calculation_report_must_be_object")
    if report.get("selection") != report.get("calculation_report", {}).get("selection"):
        blockers.append("selection_copy_mismatch")
    return sorted(set(blockers))


def _expected(project_root: Path) -> dict[str, Any]:
    contract = project_root / "experiments" / "core_1e_b1_development_execution_contract_v1.json"
    fixture = project_root / "tests" / "fixtures" / "core1e_a" / "synthetic_market_v1.json"
    engine = project_root / "lib" / "core_1e_a_synthetic_engine.py"
    adapter = project_root / "lib" / "core_1e_b1_synthetic_adapter_v1.py"
    payload = load_json(fixture)
    return build_synthetic_report(
        payload,
        contract_sha256=file_sha256(contract),
        fixture_sha256=file_sha256(fixture),
        producing_commit=git_commit(project_root),
        engine_sha256=file_sha256(engine),
        adapter_sha256=file_sha256(adapter),
    )


def validate_report(report_path: Path | None = None, *, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Validate a report against a fresh recomputation from the committed fixture."""

    try:
        expected = _expected(project_root)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
        return {
            "status": "blocked",
            "blockers": [f"expected_report_unreadable:{exc.__class__.__name__}"],
            "real_data_accessed": False,
            "validation_accessed": False,
        }
    if report_path is None:
        report = expected
        identity = "in_memory_synthetic_report"
    else:
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return {
                "status": "blocked",
                "blockers": [f"report_unreadable:{exc.__class__.__name__}"],
                "real_data_accessed": False,
                "validation_accessed": False,
            }
        identity = report_path.relative_to(project_root).as_posix() if report_path.is_relative_to(project_root) else str(report_path)
    blockers = _shape_blockers(report)
    if isinstance(report, dict):
        if report.get("schema_version") != REPORT_SCHEMA_VERSION:
            blockers.append("schema_version_changed")
        if report.get("order_id") != "CORE-1E-B1":
            blockers.append("order_id_changed")
        if report.get("status") != "synthetic_completed":
            blockers.append("status_changed")
        if report.get("evidence_tier") != "E0" or report.get("edge_claim") != "none":
            blockers.append("evidence_claim_boundary_changed")
        if report.get("access_counts") != ACCESS_COUNTS:
            blockers.append("forbidden_access_count_nonzero_or_changed")
        if report.get("validation_seal") != VALIDATION_SEAL:
            blockers.append("validation_window_not_sealed")
        if report.get("lifecycle") != LIFECYCLE:
            blockers.append("lifecycle_attestation_changed")
        _finite(report, "report", blockers)
        if report != expected:
            blockers.append("recomputed_material_decisions_mismatch")
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "report_path": identity,
        "validation_accessed": False,
        "real_data_accessed": False,
        "future_container_checked": False,
        "report_schema_path": str(REPORT_SCHEMA.relative_to(PROJECT_ROOT)) if REPORT_SCHEMA.is_file() else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    result = validate_report(args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
