"""Fail-closed hermetic validator for the L-3 B7.2 source-provenance remediation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GATE = PROJECT_ROOT / "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json"
V1_GATE = PROJECT_ROOT / "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json"
V1_VALIDATOR = PROJECT_ROOT / "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py"
MANIFEST = PROJECT_ROOT / "experiments/locked_gates.jsonl"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_jsonl, relative_to_root


V1_GATE_HASH = "0e0aaf281c75a450bbdf1015c1f400fc7ce8a398952ea25ddbb0ba2f4557c2b0"
V1_VALIDATOR_HASH = "948dd2737e0f04f6f9c256ad91bb2cb348bbe48eb58db3d77150b6ef4abd55be"
V1_MANIFEST_IDENTITY = {
    "gate_id": "l_3_inverse_volatility_sizing_v1",
    "artifact_path": "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json",
    "artifact_sha256": V1_GATE_HASH,
    "validator_path": "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py",
    "validator_sha256": V1_VALIDATOR_HASH,
}
SNAPSHOTS = [
    {
        "wiki_relative_path": "wiki/concepts/inverse-volatility-weighting.md",
        "snapshot_path": "methodology_snapshots/l3_inverse_volatility_sizing_v1/wiki/concepts/inverse-volatility-weighting.md",
        "sha256": "c59b512d3df9499a738b1ee256d388376f04edee1c59727f2f79ddcc905e7f72",
    },
    {
        "wiki_relative_path": "wiki/concepts/position-sizing.md",
        "snapshot_path": "methodology_snapshots/l3_inverse_volatility_sizing_v1/wiki/concepts/position-sizing.md",
        "sha256": "6d24c4ffc6770590baaeb90402af4e413040ff6856b0585773657da85dc68343",
    },
    {
        "wiki_relative_path": "wiki/concepts/minimum-track-record-length.md",
        "snapshot_path": "methodology_snapshots/l3_inverse_volatility_sizing_v1/wiki/concepts/minimum-track-record-length.md",
        "sha256": "ca65225740673bd363be7461b8022281da08ae32e6ff42f8887f1072eb51ad81",
    },
]
REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "order_id",
    "checkpoint",
    "gate_id",
    "hypothesis_id",
    "status",
    "evidence_ceiling",
    "edge_claim",
    "supersedes_gate_id",
    "owner_authorization",
    "source_binding",
    "research_semantics",
    "hermeticity_remediation",
    "validation_seal",
    "b7_1",
    "hard_stops",
}


def validate_gate(
    gate_path: Path = GATE,
    *,
    project_root: Path = PROJECT_ROOT,
    manifest_path: Path = MANIFEST,
    v1_gate_path: Path = V1_GATE,
    v1_validator_path: Path = V1_VALIDATOR,
) -> dict[str, Any]:
    blockers: list[str] = []
    gate = _load_json(gate_path, "gate", blockers)
    if gate is None:
        return _result(gate_path, blockers, project_root)

    _require_exact_keys(gate, REQUIRED_TOP_LEVEL_FIELDS, "top_level", blockers)
    _validate_fixed_governance(gate, blockers)
    _validate_v1_binding(gate, v1_gate_path, v1_validator_path, manifest_path, blockers)
    _validate_snapshots(gate, project_root, blockers)
    return _result(gate_path, blockers, project_root)


def _validate_fixed_governance(gate: dict[str, Any], blockers: list[str]) -> None:
    expected = {
        "schema_version": "lily_l3_inverse_volatility_sizing_preregistration_v2",
        "order_id": "B7.2",
        "checkpoint": "B7.2_hermetic_source_provenance_remediation_only",
        "gate_id": "l_3_inverse_volatility_sizing_v2",
        "hypothesis_id": "L-3",
        "status": "locked_before_execution",
        "evidence_ceiling": "E0",
        "edge_claim": "none",
        "supersedes_gate_id": "l_3_inverse_volatility_sizing_v1",
        "owner_authorization": "Inspector-authorized B7.2 hermetic source-provenance remediation only; it does not authorize B7.1, data access, validation access, or execution.",
        "validation_seal": {"start": "2016-01-04", "end": "2026-06-30", "opened": False, "pooled_with_falsification": False},
        "b7_1": {
            "authorized": False,
            "data_access_authorized": False,
            "execution_authorized": False,
            "next_safe_action": "Separate owner authorization and a new B7.1 gate are required before any data, return, signal, position, covariance, execution, or decision observation.",
        },
    }
    _require_values(gate, expected, "governance_mismatch", blockers)
    if gate.get("research_semantics") != {
        "inherits_immutable_v1_artifact": "All L-3 research question, candidate/comparator, metric, threshold, realized-confirmation, statistics, capacity, regime, side-effect, decision-matrix, validation-seal, B7.1, and hard-stop semantics are exactly those in the source-bound v1 preregistration.",
        "v1_artifact_sha256": V1_GATE_HASH,
    }:
        blockers.append("research_semantics_inheritance_mismatch")
    if gate.get("hermeticity_remediation") != {
        "scope": "Supersedes only v1 external-Wiki source verification with byte-preserving repository snapshots; no research semantic is replaced or relaxed.",
        "hermetic_validator_rule": "The default validator reads only repository files and must pass in a clean clone.",
        "external_wiki_verification": "Not part of hermetic CI and not required by this gate; any future external-Wiki comparison is a separately invoked state-audit check.",
    }:
        blockers.append("hermeticity_remediation_contract_mismatch")
    required_stops = {
        "No dataset, market price, market return, signal, position, covariance estimate, regime observation, benchmark, or PnL read or computation.",
        "No validation-window access or falsification/validation pooling.",
        "No B7.1 activity, execution, broker/provider call, credential use, paid action, paper trade, or real-money action.",
        "No threshold weakening, source substitution, locked-history edit, edge claim, E1/E2 promotion, deployment, or real-money claim.",
    }
    if set(gate.get("hard_stops", [])) != required_stops:
        blockers.append("hard_stops_incomplete_or_open")


def _validate_v1_binding(
    gate: dict[str, Any],
    v1_gate_path: Path,
    v1_validator_path: Path,
    manifest_path: Path,
    blockers: list[str],
) -> None:
    source_binding = gate.get("source_binding")
    required_keys = {"v1_preregistration", "v1_validator", "v1_manifest_row", "methodology_snapshots"}
    _require_exact_keys(source_binding, required_keys, "source_binding", blockers)
    if not isinstance(source_binding, dict):
        return
    expected_v1_gate = {"path": V1_MANIFEST_IDENTITY["artifact_path"], "sha256": V1_GATE_HASH}
    expected_v1_validator = {"path": V1_MANIFEST_IDENTITY["validator_path"], "sha256": V1_VALIDATOR_HASH}
    if source_binding.get("v1_preregistration") != expected_v1_gate:
        blockers.append("v1_preregistration_declaration_mismatch")
    if source_binding.get("v1_validator") != expected_v1_validator:
        blockers.append("v1_validator_declaration_mismatch")
    if source_binding.get("v1_manifest_row") != V1_MANIFEST_IDENTITY:
        blockers.append("v1_manifest_row_declaration_mismatch")
    if _sha256(v1_gate_path) != V1_GATE_HASH:
        blockers.append("v1_preregistration_hash_mismatch")
    if _sha256(v1_validator_path) != V1_VALIDATOR_HASH:
        blockers.append("v1_validator_hash_mismatch")
    rows = _load_jsonl(manifest_path, blockers)
    if rows is None:
        return
    matching = [row for row in rows if row.get("gate_id") == V1_MANIFEST_IDENTITY["gate_id"]]
    if len(matching) != 1 or any(matching[0].get(key) != value for key, value in V1_MANIFEST_IDENTITY.items()):
        blockers.append("v1_manifest_row_identity_mismatch")


def _validate_snapshots(gate: dict[str, Any], project_root: Path, blockers: list[str]) -> None:
    source_binding = gate.get("source_binding")
    if not isinstance(source_binding, dict):
        return
    declared = source_binding.get("methodology_snapshots")
    if declared != SNAPSHOTS:
        blockers.append("methodology_snapshot_declarations_mismatch")
        return
    for snapshot in SNAPSHOTS:
        path = project_root / snapshot["snapshot_path"]
        if _sha256(path) != snapshot["sha256"]:
            blockers.append(f"methodology_snapshot_hash_mismatch:{snapshot['wiki_relative_path']}")


def _load_json(path: Path, label: str, blockers: list[str]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        blockers.append(f"{label}_missing")
        return None
    except json.JSONDecodeError:
        blockers.append(f"{label}_invalid_json")
        return None
    if not isinstance(payload, dict):
        blockers.append(f"{label}_not_object")
        return None
    return payload


def _load_jsonl(path: Path, blockers: list[str]) -> list[dict[str, Any]] | None:
    try:
        rows = load_jsonl(path)
    except FileNotFoundError:
        blockers.append("manifest_missing")
        return None
    except json.JSONDecodeError:
        blockers.append("manifest_invalid_jsonl")
        return None
    if any(not isinstance(row, dict) for row in rows):
        blockers.append("manifest_row_not_object")
        return None
    return rows


def _require_exact_keys(value: Any, expected: set[str], label: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        blockers.append(f"{label}_not_object")
        return
    for key in sorted(set(value) - expected):
        blockers.append(f"unknown_{label}_field:{key}")
    for key in sorted(expected - set(value)):
        blockers.append(f"missing_{label}_field:{key}")


def _require_values(value: dict[str, Any], expected: dict[str, Any], prefix: str, blockers: list[str]) -> None:
    for key, required in expected.items():
        if value.get(key) != required:
            blockers.append(f"{prefix}:{key}")


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _result(path: Path, blockers: list[str], project_root: Path) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "gate_path": relative_to_root(path, project_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", type=Path, default=GATE)
    args = parser.parse_args()
    result = validate_gate(args.gate)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
