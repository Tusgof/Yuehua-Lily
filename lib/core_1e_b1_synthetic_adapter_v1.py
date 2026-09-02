"""B1 adapter around the accepted CORE-1E-A synthetic calculation engine.

The adapter accepts an already decoded committed synthetic fixture.  It never
resolves or reads a project data root, provider input, or validation window.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from lib.core_1e_a_synthetic_engine import (
    DEVELOPMENT_END,
    VALIDATION_START,
    build_report as build_core_1e_a_report,
    validate_fixture,
)


REPORT_SCHEMA_VERSION = "lily_core_1e_b1_synthetic_report_v1"
ORDER_ID = "CORE-1E-B1"
FIXTURE_PATH = "tests/fixtures/core1e_a/synthetic_market_v1.json"
FIXTURE_ID = "core1e_a_synthetic_market_v1"
ENGINE_PATH = "lib/core_1e_a_synthetic_engine.py"
ADAPTER_PATH = "lib/core_1e_b1_synthetic_adapter_v1.py"
DEVELOPMENT_CUTOFF = DEVELOPMENT_END.isoformat()
VALIDATION_CUTOFF = VALIDATION_START.isoformat()
VALIDATION_SEAL = {
    "start": "2016-01-04",
    "end": "2026-06-30",
    "status": "sealed_not_accessed",
    "accessed": False,
}
ACCESS_COUNTS = {
    "real_dataset_access": 0,
    "real_container_access": 0,
    "real_return_decode": 0,
    "validation_access": 0,
    "provider_calls": 0,
    "credential_reads": 0,
    "broker_actions": 0,
    "paid_actions": 0,
}
STOP_RULE = (
    "Synthetic development machinery is E0 only; no validation opening, edge claim, "
    "or B2 execution is authorized."
)


def fixture_max_date(fixture: dict[str, Any]) -> str:
    """Return the latest fixture session date after structural validation."""

    values = fixture.get("session_dates")
    if not isinstance(values, list) or not values:
        raise ValueError("fixture_session_dates_missing")
    try:
        parsed = [date.fromisoformat(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError("fixture_session_dates_invalid") from exc
    maximum = max(parsed)
    if maximum >= VALIDATION_START:
        raise ValueError("input_contains_date_on_or_after_2016-01-04")
    if maximum > DEVELOPMENT_END:
        raise ValueError("input_exceeds_development_cutoff")
    return maximum.isoformat()


def build_synthetic_report(
    fixture: dict[str, Any],
    *,
    contract_sha256: str,
    fixture_sha256: str,
    producing_commit: str,
    engine_sha256: str,
    adapter_sha256: str,
    stop_rule: str = STOP_RULE,
) -> dict[str, Any]:
    """Adapt one fixture into a closed-world B1 report."""

    blockers = validate_fixture(fixture)
    if blockers:
        raise ValueError("fixture_invalid:" + ",".join(blockers))
    maximum = fixture_max_date(fixture)
    calculation = build_core_1e_a_report(
        fixture,
        contract_sha256=contract_sha256,
        fixture_sha256=fixture_sha256,
        producing_commit=producing_commit,
        engine_sha256=engine_sha256,
        stop_rule=stop_rule,
    )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "order_id": ORDER_ID,
        "status": "synthetic_completed",
        "evidence_tier": "E0",
        "edge_claim": "none",
        "contract_sha256": contract_sha256,
        "fixture": {
            "path": FIXTURE_PATH,
            "sha256": fixture_sha256,
            "fixture_id": FIXTURE_ID,
            "max_date": maximum,
        },
        "selection": calculation["selection"],
        "calculation_report": calculation,
        "access_counts": dict(ACCESS_COUNTS),
        "validation_seal": dict(VALIDATION_SEAL),
        "lifecycle": {
            "marker_first": True,
            "input_read_count": 1,
            "temporary_git_proof": True,
            "project_artifacts_created": False,
            "real_data_accessed": False,
            "validation_accessed": False,
            "second_execution_refused": False,
        },
        "provenance": {
            "producing_commit": producing_commit,
            "engine_path": ENGINE_PATH,
            "engine_sha256": engine_sha256,
            "adapter_path": ADAPTER_PATH,
            "adapter_sha256": adapter_sha256,
        },
    }


adapt_synthetic_fixture = build_synthetic_report
