"""Closed-world, provenance-bound validation for the B2 synthetic report."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = PROJECT_ROOT / "experiments" / "core_1e_b2_development_execution_contract_v1.json"
FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "core1e_b2" / "normalized_market_v1.json"
ENGINE = PROJECT_ROOT / "lib" / "core_1e_a_synthetic_engine.py"
ADAPTER = PROJECT_ROOT / "lib" / "core_1e_b2_empirical_adapter_v1.py"
REPORT_SCHEMA = PROJECT_ROOT / "schemas" / "core_1e_b2_empirical_report_v1.schema.json"
HASH40 = re.compile(r"^[0-9a-f]{40}$")
HASH64 = re.compile(r"^[0-9a-f]{64}$")

if str(PROJECT_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(PROJECT_ROOT))

from lib.core_1e_b2_empirical_adapter_v1 import (  # noqa: E402
    ACCESS_COUNTS,
    ADAPTER_PATH,
    ENGINE_PATH,
    REPORT_SCHEMA_VERSION,
    STOP_RULE,
    VALIDATION_SEAL,
    build_empirical_report,
)
from lib.io import load_json  # noqa: E402
from lib.provenance import file_sha256, git_commit  # noqa: E402


def _shape_diff(actual: Any, expected: Any, label: str, blockers: list[str]) -> None:
    """Report missing/unknown fields at every object level."""

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            blockers.append(f"{label}_must_be_object")
            return
        blockers.extend(f"{label}_missing:{key}" for key in sorted(set(expected) - set(actual)))
        blockers.extend(f"{label}_unknown:{key}" for key in sorted(set(actual) - set(expected)))
        for key in sorted(set(actual) & set(expected)):
            _shape_diff(actual[key], expected[key], f"{label}.{key}", blockers)
    elif isinstance(expected, list):
        if not isinstance(actual, list):
            blockers.append(f"{label}_must_be_list")
            return
        if len(actual) != len(expected):
            blockers.append(f"{label}_length_changed")
        for index, (left, right) in enumerate(zip(actual, expected, strict=False)):
            _shape_diff(left, right, f"{label}[{index}]", blockers)


def _finite(value: Any, label: str, blockers: list[str]) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        blockers.append(f"nonfinite_number:{label}")
    elif isinstance(value, dict):
        for key, child in value.items():
            _finite(child, f"{label}.{key}", blockers)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _finite(child, f"{label}[{index}]", blockers)


def _schema_closed_world(schema: Any, label: str, blockers: list[str]) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object" and schema.get("additionalProperties") is not False:
            blockers.append(f"schema_open_object:{label}")
        for key, child in schema.items():
            _schema_closed_world(child, f"{label}.{key}", blockers)
    elif isinstance(schema, list):
        for index, child in enumerate(schema):
            _schema_closed_world(child, f"{label}[{index}]", blockers)


def _expected(project_root: Path) -> dict[str, Any]:
    contract = project_root / "experiments" / "core_1e_b2_development_execution_contract_v1.json"
    fixture = project_root / "tests" / "fixtures" / "core1e_b2" / "normalized_market_v1.json"
    engine = project_root / "lib" / "core_1e_a_synthetic_engine.py"
    adapter = project_root / "lib" / "core_1e_b2_empirical_adapter_v1.py"
    payload = load_json(fixture)
    return build_empirical_report(
        payload,
        contract_sha256=file_sha256(contract),
        fixture_sha256=file_sha256(fixture),
        producing_commit=git_commit(project_root),
        engine_sha256=file_sha256(engine),
        adapter_sha256=file_sha256(adapter),
    )


def validate_report(
    report_path: Path | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Recompute all decision evidence from the committed synthetic fixture."""

    blockers: list[str] = []
    try:
        expected = _expected(project_root)
        schema_path = project_root / "schemas" / "core_1e_b2_empirical_report_v1.schema.json"
        schema = load_json(schema_path)
        _schema_closed_world(schema, "schema", blockers)
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
        identity = (
            report_path.relative_to(project_root).as_posix()
            if report_path.is_relative_to(project_root)
            else str(report_path)
        )

    _shape_diff(report, expected, "report", blockers)
    _finite(report, "report", blockers)
    if isinstance(report, dict):
        if report.get("schema_version") != REPORT_SCHEMA_VERSION:
            blockers.append("schema_version_changed")
        if report.get("order_id") != "CORE-1E-B2-A":
            blockers.append("order_id_changed")
        if report.get("status") != "synthetic_completed":
            blockers.append("status_changed")
        if report.get("evidence_tier") != "E0" or report.get("edge_claim") != "none":
            blockers.append("evidence_claim_boundary_changed")
        if report.get("result_kind") != "synthetic_fixture_only" or report.get("empirical_result_created") is not False:
            blockers.append("empirical_claim_boundary_changed")
        if report.get("access_counts") != ACCESS_COUNTS:
            blockers.append("forbidden_access_count_nonzero_or_changed")
        if report.get("validation_seal") != VALIDATION_SEAL:
            blockers.append("validation_window_not_sealed")
        provenance = report.get("provenance")
        if isinstance(provenance, dict):
            if not HASH40.fullmatch(str(provenance.get("producing_commit", ""))):
                blockers.append("producing_commit_invalid")
            if not HASH64.fullmatch(str(provenance.get("contract_sha256", ""))):
                blockers.append("provenance_contract_hash_invalid")
            if not HASH64.fullmatch(str(provenance.get("engine_sha256", ""))):
                blockers.append("provenance_engine_hash_invalid")
            if not HASH64.fullmatch(str(provenance.get("adapter_sha256", ""))):
                blockers.append("provenance_adapter_hash_invalid")
            if provenance.get("engine_path") != ENGINE_PATH or provenance.get("adapter_path") != ADAPTER_PATH:
                blockers.append("provenance_source_path_changed")
        else:
            blockers.append("provenance_must_be_object")
        if report != expected:
            blockers.append("recomputed_decision_evidence_mismatch")

    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "report_path": identity,
        "report_schema_path": "schemas/core_1e_b2_empirical_report_v1.schema.json",
        "validation_accessed": False,
        "real_data_accessed": False,
        "future_container_checked": False,
        "edge_claim": "none",
        "stop_rule": STOP_RULE,
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
