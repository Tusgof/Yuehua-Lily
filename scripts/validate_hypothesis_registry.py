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

from lib.io import load_json, relative_to_root


DEFAULT_REGISTRY = PROJECT_ROOT / "experiments" / "hypothesis_registry.json"
DEFAULT_SCHEMA = PROJECT_ROOT / "schemas" / "hypothesis_registry.schema.json"
ID_PATTERN = re.compile(r"^L-[0-9]+$")
NON_EMPTY_LIST_FIELDS = (
    "testable_predictions",
    "validation_criteria",
    "falsification_criteria",
    "required_data",
    "known_kill_zones",
    "decision_log",
)


def validate_hypothesis_registry(
    registry_path: Path = DEFAULT_REGISTRY,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        registry = load_json(registry_path)
        schema = load_json(schema_path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(registry_path, schema_path, [f"unreadable_input:{exc.__class__.__name__}"], 0)

    if not isinstance(registry, dict) or not isinstance(schema, dict):
        return _result(registry_path, schema_path, ["registry_and_schema_must_be_objects"], 0)

    root_required = schema.get("required", [])
    blockers.extend(
        f"missing_root_field:{field}"
        for field in root_required
        if registry.get(field) in (None, "")
    )
    expected_version = schema.get("properties", {}).get("schema_version", {}).get("const")
    if registry.get("schema_version") != expected_version:
        blockers.append(f"invalid_schema_version:{registry.get('schema_version')}")

    tier_names = set(schema.get("properties", {}).get("evidence_tiers", {}).get("required", []))
    if not isinstance(registry.get("evidence_tiers"), dict) or set(registry["evidence_tiers"]) != tier_names:
        blockers.append("evidence_tier_definitions_must_be_exactly_E0_to_E3")

    item_schema = schema.get("properties", {}).get("hypotheses", {}).get("items", {})
    required_fields = set(item_schema.get("required", []))
    allowed_statuses = set(item_schema.get("properties", {}).get("status", {}).get("enum", []))
    hypotheses = registry.get("hypotheses")
    if not isinstance(hypotheses, list) or not hypotheses:
        blockers.append("hypotheses_must_be_non_empty_list")
        hypotheses = []

    seen_ids: set[str] = set()
    for index, hypothesis in enumerate(hypotheses):
        if not isinstance(hypothesis, dict):
            blockers.append(f"hypothesis_{index}_must_be_object")
            continue
        hypothesis_id = str(hypothesis.get("id", f"index_{index}"))
        missing = sorted(required_fields - set(hypothesis))
        blockers.extend(f"{hypothesis_id}:missing_required_field:{field}" for field in missing)
        if not ID_PATTERN.fullmatch(hypothesis_id):
            blockers.append(f"invalid_hypothesis_id:{hypothesis_id}")
        if hypothesis_id in seen_ids:
            blockers.append(f"duplicate_hypothesis_id:{hypothesis_id}")
        seen_ids.add(hypothesis_id)
        if hypothesis.get("status") not in allowed_statuses:
            blockers.append(f"{hypothesis_id}:invalid_status:{hypothesis.get('status')}")
        if not isinstance(hypothesis.get("counts_toward_family_stop"), bool):
            blockers.append(f"{hypothesis_id}:counts_toward_family_stop_must_be_boolean")
        for field in NON_EMPTY_LIST_FIELDS:
            value = hypothesis.get(field)
            if not isinstance(value, list) or not value:
                blockers.append(f"{hypothesis_id}:{field}_must_be_non_empty_list")
        for field in ("mintrl_falsify", "mintrl_validate"):
            value = hypothesis.get(field)
            if not isinstance(value, dict) or not value:
                blockers.append(f"{hypothesis_id}:{field}_must_be_non_empty_object")
        if not isinstance(hypothesis.get("dependencies"), list):
            blockers.append(f"{hypothesis_id}:dependencies_must_be_list")

        evidence = hypothesis.get("evidence")
        if not isinstance(evidence, list):
            blockers.append(f"{hypothesis_id}:evidence_must_be_list")
            evidence = []
        validated_evidence = False
        for item in evidence:
            if not isinstance(item, dict):
                blockers.append(f"{hypothesis_id}:evidence_item_must_be_object")
                continue
            tier = item.get("evidence_tier")
            if tier not in tier_names:
                blockers.append(f"{hypothesis_id}:invalid_evidence_tier:{tier}")
            if tier in {"E2", "E3"}:
                validated_evidence = True
            if not isinstance(item.get("path"), str) or not item["path"]:
                blockers.append(f"{hypothesis_id}:evidence_item_missing_path")
        if hypothesis.get("status") == "validated" and not validated_evidence:
            blockers.append(f"{hypothesis_id}:validated_status_requires_E2_or_E3_evidence")

    return _result(registry_path, schema_path, blockers, len(hypotheses))


def _result(
    registry_path: Path,
    schema_path: Path,
    blockers: list[str],
    hypothesis_count: int,
) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "registry_path": relative_to_root(registry_path, PROJECT_ROOT),
        "schema_path": relative_to_root(schema_path, PROJECT_ROOT),
        "hypothesis_count": hypothesis_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Lily's hypothesis registry against its schema contract.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args()
    result = validate_hypothesis_registry(args.registry, args.schema)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
