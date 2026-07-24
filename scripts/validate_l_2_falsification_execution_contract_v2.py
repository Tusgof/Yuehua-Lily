from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, load_jsonl, relative_to_root


DEFAULT_CONTRACT = PROJECT_ROOT / "experiments" / "l_2_falsification_execution_contract_v2.json"
MANIFEST = PROJECT_ROOT / "experiments" / "locked_gates.jsonl"
GATE_ID = "l_2_falsification_execution_contract_v2"
V1 = PROJECT_ROOT / "experiments" / "l_2_falsification_execution_contract.json"
V2 = PROJECT_ROOT / "experiments" / "l_2_multi_lookback_tstat_preregistration_v2.json"
V3 = PROJECT_ROOT / "experiments" / "l_2_multi_lookback_tstat_preregistration_v3.json"
V1_SHA256 = "129ff83c13e90e3c0d5538474a6092112ae27f0aad0f2f39215c1c474b54886e"
V2_SHA256 = "84a7bb45070b54846a709573506c8213a3bc62d28cfa25f4982415d40d94e1f3"
V3_SHA256 = "507bf40a0a6ac1690ff0c6898bf20dc79c3b8dee78d18251c5835e45d7b60afc"


def validate_contract(path: Path = DEFAULT_CONTRACT, *, require_manifest: bool = True) -> dict[str, Any]:
    try:
        contract = load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(path, [f"contract_unreadable:{exc.__class__.__name__}"])
    blockers: list[str] = []
    expected = {
        "schema_version": "lily_l2_falsification_execution_contract_v2",
        "order_id": "B6.2",
        "hypothesis_id": "L-2",
        "supersedes_gate_id": "l_2_falsification_execution_contract_v1",
        "status": "locked_report_contract_remediated_execution_not_authorized",
        "evidence_ceiling": "E1",
        "edge_claim": "none",
    }
    for field, value in expected.items():
        if contract.get(field) != value:
            blockers.append(f"field_mismatch:{field}")
    sources = contract.get("locked_sources", {})
    expected_sources = {"b6_v1_sha256": V1_SHA256, "v2_sha256": V2_SHA256, "v3_sha256": V3_SHA256}
    if not isinstance(sources, dict) or any(sources.get(key) != value for key, value in expected_sources.items()):
        blockers.append("locked_source_reference_mismatch")
    if _sha256(V1) != V1_SHA256 or _sha256(V2) != V2_SHA256 or _sha256(V3) != V3_SHA256:
        blockers.append("locked_source_hash_mismatch")
    state = contract.get("machinery_state", {})
    expected_state = {
        "execution_authorized_by_B6_2": False,
        "activation_order_planned": "B6.1",
        "activation_gate_required": "l_2_falsification_execution_activation_v1",
    }
    if not isinstance(state, dict) or any(state.get(key) != value for key, value in expected_state.items()):
        blockers.append("execution_authorization_boundary_changed")
    artifacts = contract.get("machine_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        blockers.append("machine_artifacts_missing")
    else:
        for row in artifacts:
            artifact = PROJECT_ROOT / str(row.get("path", "")) if isinstance(row, dict) else PROJECT_ROOT / "<invalid>"
            if not artifact.is_file() or not isinstance(row, dict) or row.get("sha256") != _sha256(artifact):
                blockers.append(f"machine_artifact_hash_mismatch:{row.get('path') if isinstance(row, dict) else '<invalid>'}")
    if require_manifest:
        blockers.extend(_validate_manifest(path))
    return _result(path, blockers)


def _validate_manifest(contract_path: Path) -> list[str]:
    try:
        rows = load_jsonl(MANIFEST)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return ["manifest_unreadable"]
    matches = [row for row in rows if isinstance(row, dict) and row.get("gate_id") == GATE_ID]
    if len(matches) != 1:
        return ["manifest_gate_entry_mismatch"]
    row = matches[0]
    expected = {
        "artifact_path": relative_to_root(contract_path, PROJECT_ROOT),
        "artifact_sha256": _sha256(contract_path),
        "validator_path": "scripts/validate_l_2_falsification_execution_contract_v2.py",
        "validator_sha256": _sha256(Path(__file__)),
        "supersedes_gate_id": "l_2_falsification_execution_contract_v1",
    }
    return [] if all(row.get(key) == value for key, value in expected.items()) else ["manifest_hash_or_path_mismatch"]


def _sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _result(path: Path, blockers: list[str]) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "contract_path": relative_to_root(path, PROJECT_ROOT)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    args = parser.parse_args()
    result = validate_contract(args.contract)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
