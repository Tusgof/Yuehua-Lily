"""Closed-world, provenance-bound validation for the R1 synthetic report.

The validator reconstructs the report from the committed real-schema-shaped
fixture, the separately locked expense input, and the accepted calculation
engine.  It never resolves the future container or opens the validation
window.  A report is accepted only when its complete JSON value is identical
to that independently reconstructed value.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.core_1e_b2_empirical_adapter_v2 import (
    ACCESS_COUNTS,
    ADAPTER_PATH,
    ENGINE_PATH,
    EXPENSE_INPUT_PATH,
    FIXTURE_PATH,
    NORMALIZED_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    STOP_RULE,
    U8,
    SYMBOL_SCHEMA_VERSION,
    VALIDATION_SEAL,
    YAHOO_NORMALIZER_PATH,
    build_empirical_report,
    validate_expense_input,
)
from lib.provenance import git_commit
from scripts.validate_core_1e_b2_development_execution_contract_v2 import (
    EXPECTED_CONTRACT_SHA256,
    EXPECTED_STATIC_BINDINGS,
    validate_contract,
)


CONTRACT_PATH = PROJECT_ROOT / "experiments" / "core_1e_b2_development_execution_contract_v2.json"
FIXTURE = PROJECT_ROOT / FIXTURE_PATH
EXPENSE_INPUT = PROJECT_ROOT / EXPENSE_INPUT_PATH
ENGINE = PROJECT_ROOT / ENGINE_PATH
ADAPTER = PROJECT_ROOT / ADAPTER_PATH
YAHOO_NORMALIZER = PROJECT_ROOT / YAHOO_NORMALIZER_PATH
REPORT_SCHEMA = PROJECT_ROOT / "schemas" / "core_1e_b2_empirical_report_v2.schema.json"

# This is deliberately a second binding for the adapter and report schema.
# The contract binds the accepted engine, normalizer, and input bytes; the
# report validator also pins the code that performs the recomputation and the
# schema it claims to enforce.
EXPECTED_ADAPTER_SHA256 = "36a883ccf21d11a34c292873b8fc013afaa0deb0b44b3a661c7b02ac37339e4c"
EXPECTED_REPORT_SCHEMA_SHA256 = "39b0eb6d01c82b94e0884dddc3a71b066b172f38263c1ec5c8bfb866481b40f0"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reject_constant(token: str) -> None:
    raise ValueError(f"nonfinite_json_number:{token}")


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate_json_key:{key}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    return json.loads(
        path.read_bytes().decode("utf-8"),
        object_pairs_hook=_closed_object,
        parse_constant=_reject_constant,
    )


def _shape_diff(actual: Any, expected: Any, label: str, blockers: list[str]) -> None:
    """Find missing and unknown fields at every object level."""

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
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
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


def _verify_static_bytes(project_root: Path) -> None:
    expected = {
        "contract": (project_root / "experiments/core_1e_b2_development_execution_contract_v2.json", EXPECTED_CONTRACT_SHA256),
        "fixture": (project_root / FIXTURE_PATH, EXPECTED_STATIC_BINDINGS["synthetic_fixture"][1]),
        "expense_input": (project_root / EXPENSE_INPUT_PATH, EXPECTED_STATIC_BINDINGS["expense_input"][1]),
        "engine": (project_root / ENGINE_PATH, EXPECTED_STATIC_BINDINGS["accepted_engine"][1]),
        "yahoo_normalizer": (project_root / YAHOO_NORMALIZER_PATH, EXPECTED_STATIC_BINDINGS["yahoo_normalizer"][1]),
        "adapter": (project_root / ADAPTER_PATH, EXPECTED_ADAPTER_SHA256),
        "report_schema": (project_root / "schemas/core_1e_b2_empirical_report_v2.schema.json", EXPECTED_REPORT_SCHEMA_SHA256),
    }
    for label, (path, expected_hash) in expected.items():
        if not isinstance(expected_hash, str) or expected_hash.startswith("__"):
            raise ValueError(f"validator_{label}_hash_not_filled")
        if not path.is_file():
            raise ValueError(f"required_{label}_missing")
        if _sha256(path) != expected_hash:
            raise ValueError(f"required_{label}_hash_mismatch")


def _expected(project_root: Path) -> tuple[dict[str, Any], Any]:
    """Recompute the complete report from explicitly bound synthetic bytes."""

    contract = project_root / "experiments/core_1e_b2_development_execution_contract_v2.json"
    fixture = project_root / FIXTURE_PATH
    expense_input = project_root / EXPENSE_INPUT_PATH
    engine = project_root / ENGINE_PATH
    adapter = project_root / ADAPTER_PATH
    yahoo_normalizer = project_root / YAHOO_NORMALIZER_PATH
    report_schema = project_root / "schemas/core_1e_b2_empirical_report_v2.schema.json"

    _verify_static_bytes(project_root)
    contract_result = validate_contract(contract, project_root=project_root, verify_static=False)
    if contract_result["status"] != "pass":
        raise ValueError("contract_not_valid:" + ",".join(contract_result["blockers"]))
    _load_json(contract)
    fixture_payload = _load_json(fixture)
    expense_payload = _load_json(expense_input)
    if not isinstance(fixture_payload, dict) or not isinstance(expense_payload, dict):
        raise ValueError("bound_synthetic_input_must_be_object")
    expense_blockers = validate_expense_input(expense_payload)
    if expense_blockers:
        raise ValueError("expense_input_invalid:" + ",".join(expense_blockers))
    schema = _load_json(report_schema)
    if not isinstance(schema, dict):
        raise ValueError("report_schema_must_be_object")
    if schema.get("$id") != REPORT_SCHEMA_VERSION:
        raise ValueError("report_schema_id_changed")
    return (
        build_empirical_report(
            fixture_payload,
            expense_payload,
            contract_sha256=_sha256(contract),
            fixture_sha256=_sha256(fixture),
            expense_input_sha256=_sha256(expense_input),
            producing_commit=git_commit(project_root),
            engine_sha256=_sha256(engine),
            adapter_sha256=_sha256(adapter),
            yahoo_normalizer_sha256=_sha256(yahoo_normalizer),
        ),
        schema,
    )


def validate_report_payload(
    report: Any,
    *,
    project_root: Path = PROJECT_ROOT,
    expected_producing_commit: str | None = None,
) -> dict[str, Any]:
    """Validate an in-memory report against independently rebuilt evidence."""

    try:
        expected, schema = _expected(project_root)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
        return {
            "status": "blocked",
            "blockers": [f"expected_report_unreadable:{exc}"],
            "real_data_accessed": False,
            "validation_accessed": False,
            "edge_claim": "none",
        }

    return _validate_report_against_expected(
        report,
        expected,
        schema,
        expected_producing_commit=expected_producing_commit,
    )


def _validate_report_against_expected(
    report: Any,
    expected: dict[str, Any],
    schema: Any,
    *,
    expected_producing_commit: str | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    _schema_closed_world(schema, "schema", blockers)
    _shape_diff(report, expected, "report", blockers)
    _finite(report, "report", blockers)
    if not isinstance(report, dict):
        blockers.append("report_must_be_object")
    else:
        if report.get("schema_version") != REPORT_SCHEMA_VERSION:
            blockers.append("schema_version_changed")
        if report.get("order_id") != "CORE-1E-B2-A" or report.get("work_order_id") != "CORE-1E-B2-A-R1":
            blockers.append("report_order_identity_changed")
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
        source = report.get("source")
        if isinstance(source, dict):
            if source.get("schema_version") != NORMALIZED_SCHEMA_VERSION or source.get("symbol_schema_version") != SYMBOL_SCHEMA_VERSION:
                blockers.append("source_schema_binding_changed")
            if source.get("symbols_in_order") != list(U8):
                blockers.append("source_u8_order_changed")
        provenance = report.get("provenance")
        if not isinstance(provenance, dict):
            blockers.append("provenance_must_be_object")
        elif expected_producing_commit is not None and provenance.get("producing_commit") != expected_producing_commit:
            blockers.append("provenance_producing_commit_changed")
        if report != expected:
            blockers.append("recomputed_decision_evidence_mismatch")

    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "validation_accessed": False,
        "real_data_accessed": False,
        "future_container_checked": False,
        "edge_claim": "none",
        "stop_rule": STOP_RULE,
    }


def validate_report(
    report_path: Path | None = None,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Validate a report file, or the canonical in-memory synthetic report."""

    if report_path is None:
        try:
            expected, schema = _expected(project_root)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
            return {
                "status": "blocked",
                "blockers": [f"expected_report_unreadable:{exc}"],
                "real_data_accessed": False,
                "validation_accessed": False,
            }
        result = _validate_report_against_expected(expected, expected, schema)
        result["report_path"] = "in_memory_synthetic_report"
        result["report_schema_path"] = "schemas/core_1e_b2_empirical_report_v2.schema.json"
        return result

    path = report_path if report_path.is_absolute() else project_root / report_path
    try:
        report = _load_json(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "status": "blocked",
            "blockers": [f"report_unreadable:{exc}"],
            "real_data_accessed": False,
            "validation_accessed": False,
        }
    result = validate_report_payload(report, project_root=project_root)
    try:
        identity = path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        identity = str(path)
    result["report_path"] = identity
    result["report_schema_path"] = "schemas/core_1e_b2_empirical_report_v2.schema.json"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    result = validate_report(args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
