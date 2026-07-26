"""Fail-closed, data-free validator for the locked L-3 B7.1 preflight gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GATE = PROJECT_ROOT / "experiments/l_3_falsification_activation_preflight_v1.json"
MANIFEST = PROJECT_ROOT / "experiments/locked_gates.jsonl"
L3_V2_GATE = PROJECT_ROOT / "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json"
L3_V2_VALIDATOR = PROJECT_ROOT / "scripts/validate_l_3_inverse_volatility_sizing_preregistration_v2.py"
L3_V1_GATE = PROJECT_ROOT / "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json"
L3_V1_VALIDATOR = PROJECT_ROOT / "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py"
L1_GATE = PROJECT_ROOT / "experiments/l_1_baseline_preregistration.json"
L1_VALIDATOR = PROJECT_ROOT / "scripts/validate_l_1_baseline_preregistration.py"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_jsonl, relative_to_root
from scripts.validate_l_1_baseline_preregistration import validate_preregistration
from scripts.validate_l_3_inverse_volatility_sizing_preregistration_v2 import validate_gate as validate_l3_v2


L3_V2_ARTIFACT_HASH = "83a68792614ee0def3ddb96349d6d95c7f0aeb0ac8b1c984c1e3d29ed74e709e"
L3_V2_VALIDATOR_HASH = "1556108bb69f7621ebedcaeb046e53d12b5b7eea473fe36454f02c56399b9ea6"
L3_V1_ARTIFACT_HASH = "0e0aaf281c75a450bbdf1015c1f400fc7ce8a398952ea25ddbb0ba2f4557c2b0"
L3_V1_VALIDATOR_HASH = "948dd2737e0f04f6f9c256ad91bb2cb348bbe48eb58db3d77150b6ef4abd55be"
L1_ARTIFACT_HASH = "91527c2f4ec00134767df86849f36b9876b00eb44cd56dc01650d33bf938fe29"
L1_VALIDATOR_HASH = "c568f5db8236e253e63056ed2797ead9259397d293c478e7f0abf53bfda70232"

L3_V2_MANIFEST = {
    "gate_id": "l_3_inverse_volatility_sizing_v2",
    "artifact_path": "experiments/l_3_inverse_volatility_sizing_preregistration_v2.json",
    "artifact_sha256": L3_V2_ARTIFACT_HASH,
    "validator_path": "scripts/validate_l_3_inverse_volatility_sizing_preregistration_v2.py",
    "validator_sha256": L3_V2_VALIDATOR_HASH,
    "supersedes_gate_id": "l_3_inverse_volatility_sizing_v1",
}
L3_V1_MANIFEST = {
    "gate_id": "l_3_inverse_volatility_sizing_v1",
    "artifact_path": "experiments/l_3_inverse_volatility_sizing_preregistration_v1.json",
    "artifact_sha256": L3_V1_ARTIFACT_HASH,
    "validator_path": "scripts/validate_l_3_inverse_volatility_sizing_preregistration.py",
    "validator_sha256": L3_V1_VALIDATOR_HASH,
}
L1_MANIFEST = {
    "gate_id": "l_1_baseline_v1",
    "artifact_path": "experiments/l_1_baseline_preregistration.json",
    "artifact_sha256": L1_ARTIFACT_HASH,
    "validator_path": "scripts/validate_l_1_baseline_preregistration.py",
    "validator_sha256": L1_VALIDATOR_HASH,
}
REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version", "order_id", "checkpoint", "gate_id", "hypothesis_id", "status", "evidence_ceiling",
    "edge_claim", "owner_authorization", "source_binding", "locked_research_facts", "authorizations",
    "validation_seal", "future_preflight_sequence", "hard_stops",
}


def validate_gate(
    gate_path: Path = GATE,
    *,
    project_root: Path = PROJECT_ROOT,
    manifest_path: Path = MANIFEST,
    l3_v2_gate_path: Path = L3_V2_GATE,
    l3_v2_validator_path: Path = L3_V2_VALIDATOR,
    l3_v1_gate_path: Path = L3_V1_GATE,
    l3_v1_validator_path: Path = L3_V1_VALIDATOR,
    l1_gate_path: Path = L1_GATE,
    l1_validator_path: Path = L1_VALIDATOR,
) -> dict[str, Any]:
    blockers: list[str] = []
    gate = _read_json(gate_path, "gate", blockers)
    if gate is None:
        return _result(gate_path, blockers, project_root)
    _require_exact_keys(gate, REQUIRED_TOP_LEVEL_FIELDS, "top_level", blockers)
    _validate_fixed_contract(gate, blockers)
    _validate_source_bindings(
        gate, manifest_path, l3_v2_gate_path, l3_v2_validator_path, l3_v1_gate_path,
        l3_v1_validator_path, l1_gate_path, l1_validator_path, blockers,
    )
    _validate_active_gates(l3_v2_gate_path, l1_gate_path, blockers)
    return _result(gate_path, blockers, project_root)


def _validate_fixed_contract(gate: dict[str, Any], blockers: list[str]) -> None:
    expected = {
        "schema_version": "lily_l3_falsification_activation_preflight_v1",
        "order_id": "B7.1",
        "checkpoint": "activation_preflight_gate_only",
        "gate_id": "l_3_falsification_activation_preflight_v1",
        "hypothesis_id": "L-3",
        "status": "locked_activation_preflight_execution_not_authorized",
        "evidence_ceiling": "E0",
        "edge_claim": "none",
        "owner_authorization": "Owner authorized B7.1 activation/preflight gate design, hash lock, validation, publication, and CI check only; no data, container, return, validation, execution, report decision, provider, credential, or acquisition action is authorized.",
        "validation_seal": {"start": "2016-01-04", "end": "2026-06-30", "opened": False, "pooled_with_falsification": False},
    }
    _require_values(gate, expected, "governance_mismatch", blockers)
    _validate_research_facts(gate.get("locked_research_facts"), blockers)
    _validate_authorizations(gate.get("authorizations"), blockers)
    _validate_preflight_sequence(gate.get("future_preflight_sequence"), blockers)
    required_stops = {
        "No dataset or container inspection, market date, price, return, signal, position, covariance, regime, turnover, cost, or PnL read or computation occurs in B7.1.",
        "No validation access, falsification/validation pooling, broker/provider/network data call, credential or environment-variable read, paid action, paper trade, or real-money action.",
        "No market-data loader, executable backtest runner, report decision, E1/E2 promotion, edge claim, deployment claim, threshold weakening, or locked-history edit.",
        "Provider calls, credentials, and data acquisition are never fallback behavior; a mixed validation container hard-stops rather than being filtered in memory.",
    }
    if set(gate.get("hard_stops", [])) != required_stops:
        blockers.append("hard_stops_incomplete_or_open")


def _validate_research_facts(facts: Any, blockers: list[str]) -> None:
    expected = {
        "research_universe_tickers_in_order": ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"],
        "candidate_raw_score": "q[i,t] / max(annualized_volatility[i,t], 0.05)",
        "comparator_raw_score": "q[i,t]",
        "inherited_signal": "L1 60_day_directional_count_raw only",
        "decision_index_and_timing": "weekly decision index after the official close of the last NYSE session of each week; next actual NYSE close execution only",
        "inherited_constraints_and_cost_accounting": "L1 90% gross normalization, 10% minimum cash, 25% absolute asset cap, 60-session EWMA PSD-clipped covariance, target-volatility scale-down-only, and locked L1 cost accounting",
        "missing_sessions_policy": "Inherited L1 missing-data policy is mandatory: no price forward fill; any required missing input makes the affected paired date non-evaluable and scope_restricted rather than silently dropped.",
        "falsification_window": {"start": "2007-02-05", "end": "2015-12-31", "validation_pooling": "forbidden"},
        "observation_unit": "one weekly paired portfolio observation; never multiply by assets, days, 20-session confirmation rows, sleeves, or trades",
        "mintrl_falsify_weekly_paired_observations": 49,
        "optimistic_weekly_capacity_ceiling": 465,
        "optimistic_regime_eligible_weekly_capacity_ceiling": 366,
        "regime_inference": "Every regime claim separately needs its actual recomputed requirement and cannot pool regimes.",
        "falsification_boundary": "Only a separately authorized funded B7.1 execution may falsify after mechanism autopsy when the one-sided upper confidence bound is below 0.05, or when a funded and evaluable primary result breaches a locked side-effect limit. Non-evaluable requirements remain scope_restricted.",
    }
    _require_exact_keys(facts, set(expected), "locked_research_facts", blockers)
    if isinstance(facts, dict):
        _require_values(facts, expected, "research_fact_mismatch", blockers)


def _validate_authorizations(value: Any, blockers: list[str]) -> None:
    expected = {
        "data_access_authorized": False,
        "container_inspection_authorized": False,
        "return_parsing_authorized": False,
        "execution_authorized": False,
        "report_decision_authorized": False,
        "validation_access_authorized": False,
    }
    _require_exact_keys(value, set(expected), "authorizations", blockers)
    if isinstance(value, dict):
        _require_values(value, expected, "authorization_mismatch", blockers)


def _validate_preflight_sequence(value: Any, blockers: list[str]) -> None:
    expected = [
        "Validate this locked B7.1 gate, the active L-3 v2 gate, immutable v1 research semantics, locked L1 baseline, and their exact manifest-row identities and SHA-256 hashes before any path resolution.",
        "Only under a later separately owner-authorized one-run execution order, resolve a repo-relative container path or a configured LILY_DATA_ROOT reference; do not read environment variables, credentials, providers, or acquire data as fallback behavior.",
        "Inspect only container metadata, schema, and the declared date-column definition before accessing any return field.",
        "Before parsing any return row, prove the container maximum date is no later than 2015-12-31 and its exact eight-ETF identity and order are VTI, VGK, EWJ, VWO, IEF, TIP, GLD, DBC.",
        "Hard-stop a container that may contain validation dates; never filter a mixed falsification-plus-validation container in memory.",
        "Reject missing or extra assets, unbound lineage or hashes, schema drift, missing-session-policy absence, non-finite identifiers, any validation date, or any failed hard stop before return parsing.",
        "Only a later one-run execution order, after Inspector acceptance and successful exact-SHA CI for this gate, may grant new explicit authorization; this B7.1 gate does not grant it.",
    ]
    if value != expected:
        blockers.append("future_preflight_sequence_mismatch")


def _validate_source_bindings(
    gate: dict[str, Any], manifest_path: Path, l3_v2_gate_path: Path, l3_v2_validator_path: Path,
    l3_v1_gate_path: Path, l3_v1_validator_path: Path, l1_gate_path: Path, l1_validator_path: Path,
    blockers: list[str],
) -> None:
    binding = gate.get("source_binding")
    expected_keys = {
        "active_l3_v2_artifact", "active_l3_v2_validator", "active_l3_v2_manifest_row",
        "immutable_l3_v1_research_semantics", "l1_baseline_preregistration", "validation_seal_boundary",
        "whole_manifest_hash_binding", "self_or_circular_hash_binding",
    }
    _require_exact_keys(binding, expected_keys, "source_binding", blockers)
    if not isinstance(binding, dict):
        return
    expected = {
        "active_l3_v2_artifact": {"path": L3_V2_MANIFEST["artifact_path"], "sha256": L3_V2_ARTIFACT_HASH},
        "active_l3_v2_validator": {"path": L3_V2_MANIFEST["validator_path"], "sha256": L3_V2_VALIDATOR_HASH},
        "active_l3_v2_manifest_row": L3_V2_MANIFEST,
        "immutable_l3_v1_research_semantics": {
            "path": L3_V1_MANIFEST["artifact_path"], "sha256": L3_V1_ARTIFACT_HASH,
            "manifest_row": L3_V1_MANIFEST, "through_active_v2_only": True,
        },
        "l1_baseline_preregistration": {
            "path": L1_MANIFEST["artifact_path"], "sha256": L1_ARTIFACT_HASH, "manifest_row": L1_MANIFEST,
        },
        "validation_seal_boundary": {
            "source_gate_id": "l_3_inverse_volatility_sizing_v2", "start": "2016-01-04", "end": "2026-06-30",
            "opened": False, "pooled_with_falsification": False,
        },
        "whole_manifest_hash_binding": False,
        "self_or_circular_hash_binding": False,
    }
    _require_values(binding, expected, "source_binding_mismatch", blockers)
    for label, path, digest in (
        ("active_l3_v2_artifact", l3_v2_gate_path, L3_V2_ARTIFACT_HASH),
        ("active_l3_v2_validator", l3_v2_validator_path, L3_V2_VALIDATOR_HASH),
        ("immutable_l3_v1_artifact", l3_v1_gate_path, L3_V1_ARTIFACT_HASH),
        ("immutable_l3_v1_validator", l3_v1_validator_path, L3_V1_VALIDATOR_HASH),
        ("l1_baseline_artifact", l1_gate_path, L1_ARTIFACT_HASH),
        ("l1_baseline_validator", l1_validator_path, L1_VALIDATOR_HASH),
    ):
        if _sha256(path) != digest:
            blockers.append(f"{label}_hash_mismatch")
    rows = _read_jsonl(manifest_path, blockers)
    if rows is None:
        return
    for label, identity in (("active_l3_v2", L3_V2_MANIFEST), ("immutable_l3_v1", L3_V1_MANIFEST), ("l1_baseline", L1_MANIFEST)):
        matching = [row for row in rows if row.get("gate_id") == identity["gate_id"]]
        if len(matching) != 1 or any(matching[0].get(key) != value for key, value in identity.items()):
            blockers.append(f"{label}_manifest_identity_mismatch")


def _validate_active_gates(l3_v2_gate_path: Path, l1_gate_path: Path, blockers: list[str]) -> None:
    if l3_v2_gate_path == L3_V2_GATE:
        result = validate_l3_v2()
        if result["status"] != "pass":
            blockers.append("active_l3_v2_validator_failed")
    if l1_gate_path == L1_GATE:
        result = validate_preregistration()
        if result["status"] != "pass":
            blockers.append("locked_l1_validator_failed")


def _read_json(path: Path, label: str, blockers: list[str]) -> dict[str, Any] | None:
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


def _read_jsonl(path: Path, blockers: list[str]) -> list[dict[str, Any]] | None:
    try:
        rows = load_jsonl(path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        blockers.append("manifest_unreadable")
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
    except OSError:
        return None


def _result(path: Path, blockers: list[str], project_root: Path) -> dict[str, Any]:
    return {"status": "pass" if not blockers else "blocked", "blockers": blockers, "gate_path": relative_to_root(path, project_root)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the locked L-3 B7.1 activation/preflight gate.")
    parser.add_argument("--gate", type=Path, default=GATE)
    args = parser.parse_args()
    result = validate_gate(args.gate)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
