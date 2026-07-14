from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.data_contracts import FIXTURE_SCHEMAS, validate_dataset_registry, validate_provider_fixture
from lib.io import load_json, relative_to_root


DEFAULT_REGISTRY = PROJECT_ROOT / "datasets" / "registry.json"
SCHEMA_FILES = {
    "daily_bars": "provider_daily_bars.schema.json",
    "instrument_master": "provider_instrument_master.schema.json",
    "universe_membership": "provider_universe_membership.schema.json",
    "futures_contracts": "provider_futures_contracts.schema.json",
    "continuous_futures": "provider_continuous_futures.schema.json",
}
FIXTURE_FILES = {
    kind: f"provider_{kind}.json"
    for kind in SCHEMA_FILES
}


def validate_data_layer(
    *,
    project_root: Path = PROJECT_ROOT,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    checked: list[dict[str, Any]] = []
    selected_registry = registry_path or project_root / "datasets" / "registry.json"
    registry_schema_path = project_root / "schemas" / "dataset_registry.schema.json"
    registry_schema_blockers = _validate_registry_schema(registry_schema_path)
    blockers.extend(f"dataset_registry_schema:{item}" for item in registry_schema_blockers)
    try:
        registry = load_json(selected_registry)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        blockers.append(f"dataset_registry_unreadable:{exc.__class__.__name__}")
    else:
        registry_blockers = validate_dataset_registry(registry)
        blockers.extend(f"dataset_registry:{item}" for item in registry_blockers)
        checked.append(
            {
                "kind": "dataset_registry",
                "path": relative_to_root(selected_registry, project_root),
                "schema": relative_to_root(registry_schema_path, project_root),
                "status": "pass" if not registry_blockers and not registry_schema_blockers else "blocked",
            }
        )

    fixtures: dict[str, dict[str, Any]] = {}
    for kind, schema_name in SCHEMA_FILES.items():
        schema_path = project_root / "schemas" / schema_name
        fixture_path = project_root / "tests" / "fixtures" / "data" / FIXTURE_FILES[kind]
        schema_blockers = _validate_schema(kind, schema_path)
        fixture_blockers: list[str] = []
        try:
            fixture = load_json(fixture_path)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            fixture_blockers.append(f"fixture_unreadable:{exc.__class__.__name__}")
        else:
            fixture_blockers.extend(validate_provider_fixture(kind, fixture))
            if isinstance(fixture, dict):
                fixtures[kind] = fixture
        blockers.extend(f"schema:{kind}:{item}" for item in schema_blockers)
        blockers.extend(f"fixture:{kind}:{item}" for item in fixture_blockers)
        checked.append(
            {
                "kind": kind,
                "schema": relative_to_root(schema_path, project_root),
                "fixture": relative_to_root(fixture_path, project_root),
                "status": "pass" if not schema_blockers and not fixture_blockers else "blocked",
            }
        )

    blockers.extend(_validate_fixture_references(fixtures))
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "network_used": False,
        "paid_data_used": False,
        "checked": checked,
    }


def _validate_schema(kind: str, path: Path) -> list[str]:
    try:
        schema = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"unreadable:{exc.__class__.__name__}"]
    if not isinstance(schema, dict):
        return ["must_be_object"]
    blockers: list[str] = []
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        blockers.append("must_use_draft_2020_12")
    properties = schema.get("properties", {})
    if properties.get("schema_version", {}).get("const") != FIXTURE_SCHEMAS[kind]:
        blockers.append("schema_version_contract_mismatch")
    if properties.get("boundary_kind", {}).get("const") != kind:
        blockers.append("boundary_kind_contract_mismatch")
    return blockers


def _validate_registry_schema(path: Path) -> list[str]:
    try:
        schema = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [f"unreadable:{exc.__class__.__name__}"]
    if not isinstance(schema, dict):
        return ["must_be_object"]
    blockers: list[str] = []
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        blockers.append("must_use_draft_2020_12")
    expected = schema.get("properties", {}).get("schema_version", {}).get("const")
    if expected != "lily_dataset_registry_v1":
        blockers.append("schema_version_contract_mismatch")
    return blockers


def _validate_fixture_references(fixtures: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    instruments = {
        record.get("instrument_id")
        for record in fixtures.get("instrument_master", {}).get("records", [])
        if isinstance(record, dict)
    }
    for kind in ("daily_bars", "universe_membership"):
        for record in fixtures.get(kind, {}).get("records", []):
            if isinstance(record, dict) and record.get("instrument_id") not in instruments:
                blockers.append(f"fixture_reference_unknown_instrument:{kind}:{record.get('instrument_id')}")
    contracts = {
        record.get("contract_id")
        for record in fixtures.get("futures_contracts", {}).get("records", [])
        if isinstance(record, dict)
    }
    for record in fixtures.get("continuous_futures", {}).get("records", []):
        if isinstance(record, dict) and record.get("active_contract_id") not in contracts:
            blockers.append(
                f"fixture_reference_unknown_contract:continuous_futures:{record.get('active_contract_id')}"
            )
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Lily's provider-neutral B1 data contracts.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()
    result = validate_data_layer(registry_path=args.registry)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
