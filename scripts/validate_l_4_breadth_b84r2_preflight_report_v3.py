"""Closed-world validator for B8.4 synthetic-only preflight reports."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.l4_b84_preflight import U8, canonical_fixture_sha256, structural_preflight

V4 = "experiments/l_4_breadth_preregistration_v4.json"
B84_GATE = "experiments/l_4_breadth_b84r2_activation_contract_v3.json"
B84_VALIDATOR = "scripts/validate_l_4_breadth_b84r2_activation_contract_v3.py"
FIXTURE = "tests/fixtures/l4_b84/synthetic_preflight_report_v3.json"
TOP = {"schema_version", "order_id", "hypothesis_id", "report_mode", "evidence_tier", "edge_claim", "decision", "provenance", "v4_controls_sha256", "canonical_sections", "universes", "weekly_schedule", "paired_weeks", "symbol_sessions", "validation_seal", "authorizations", "producing_checkout"}
AUTH = {"data", "container", "market", "return", "signal", "position", "covariance", "regime", "cost", "pnl", "execution", "report_decision", "ledger", "validation", "provider", "network", "credentials", "broker", "paid", "paper_trade", "real_money"}
IMPLEMENTATION = {"runner", "report_validator", "report_schema", "shared_preflight_library"}


def sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    except OSError:
        return None


def manifest_identity(gate_id: str) -> dict[str, Any] | None:
    try:
        for line in (ROOT / "experiments/locked_gates.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("gate_id") == gate_id:
                return {key: row.get(key) for key in ("gate_id", "artifact_path", "artifact_sha256", "validator_path", "validator_sha256")}
    except (OSError, json.JSONDecodeError):
        pass
    return None


def v4_controls_sha256() -> str | None:
    try:
        gate = json.loads((ROOT / V4).read_text(encoding="utf-8"))
        controls = {key: gate[key] for key in ("universes", "static_capacity", "mandatory_metrics", "statistics", "macro_sleeves", "component_risk", "robustness_and_side_effects", "regime_matrix", "decision_contract", "timing_and_seal", "authorizations")}
        return hashlib.sha256(json.dumps(controls, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    except (OSError, KeyError, json.JSONDecodeError):
        return None


def canonical_sections() -> dict[str, str] | None:
    try:
        gate = json.loads((ROOT / V4).read_text(encoding="utf-8"))
        return {name: hashlib.sha256(json.dumps(gate[key], sort_keys=True, separators=(",", ":")).encode()).hexdigest() for name, key in {"mandatory_metrics": "mandatory_metrics", "statistics": "statistics", "regime_matrix": "regime_matrix", "robustness_and_side_effects": "robustness_and_side_effects", "timing_and_seal": "timing_and_seal", "universes": "universes", "static_capacity": "static_capacity", "decision_contract": "decision_contract"}.items()}
    except (OSError, KeyError, json.JSONDecodeError):
        return None


def expected_b84_implementation() -> dict[str, Any] | None:
    try:
        gate = json.loads((ROOT / B84_GATE).read_text(encoding="utf-8"))
        implementation = gate["implementation"]
        return {name: implementation[name] for name in IMPLEMENTATION}
    except (OSError, KeyError, json.JSONDecodeError):
        return None


def expected_fixture_sha256() -> str | None:
    try:
        gate = json.loads((ROOT / B84_GATE).read_text(encoding="utf-8"))
        return gate["implementation"]["synthetic_fixture"]["canonical_payload_sha256"]
    except (OSError, KeyError, json.JSONDecodeError):
        return None


def schema_matches(value: Any, schema: dict[str, Any]) -> bool:
    """Hermetic Draft-2020-12 subset used by this closed B8.4 report schema."""
    if "const" in schema and value != schema["const"]:
        return False
    if "anyOf" in schema and not any(schema_matches(value, option) for option in schema["anyOf"]):
        return False
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            return False
        properties = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", [])):
            return False
        if schema.get("additionalProperties") is False and any(key not in properties for key in value):
            return False
        return all(schema_matches(value[key], properties[key]) for key in value if key in properties)
    if kind == "array":
        return isinstance(value, list)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool) and value >= schema.get("minimum", value) and value <= schema.get("maximum", value)
    if kind == "string":
        return isinstance(value, str) and ("pattern" not in schema or re.fullmatch(schema["pattern"], value) is not None)
    return kind is None


def current_head() -> str | None:
    run = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False)
    return run.stdout.strip() if run.returncode == 0 else None


def materialize_fixture(payload: Any) -> dict[str, Any] | None:
    """Replace the committed template sentinel with this checkout's actual HEAD in memory."""
    if not isinstance(payload, dict) or payload.get("producing_checkout") != {"mode": "committed_synthetic_fixture", "validating_checkout_commit": "runtime_head_required"}:
        return None
    materialized = json.loads(json.dumps(payload))
    materialized["producing_checkout"]["validating_checkout_commit"] = current_head()
    return materialized


def validate(payload: Any, *, committed_fixture: bool = False) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"status": "blocked", "blockers": ["not_object"]}
    blockers: list[str] = []
    try:
        schema = json.loads((ROOT / "schemas/l_4_breadth_b84r2_preflight_report_v3.schema.json").read_text(encoding="utf-8"))
        if not schema_matches(payload, schema):
            raise ValueError("schema")
    except (OSError, json.JSONDecodeError, ValueError):
        blockers.append("json_schema")
    if set(payload) != TOP:
        blockers.append("closed_world_top_shape")
    identity = {"schema_version": "lily_l4_b84r2_preflight_report_v3", "order_id": "B8.4R2", "hypothesis_id": "L-4", "report_mode": "synthetic_preflight_only", "evidence_tier": "E0", "edge_claim": "none", "decision": "not_run"}
    if any(payload.get(key) != value for key, value in identity.items()):
        blockers.append("e0_identity_or_claim")
    provenance = payload.get("provenance", {})
    expected_provenance = {"v4_path": V4, "v4_sha256": sha(ROOT / V4), "v4_validator_path": "scripts/validate_l_4_breadth_preregistration_v4.py", "v4_validator_sha256": sha(ROOT / "scripts/validate_l_4_breadth_preregistration_v4.py"), "v4_manifest_identity": manifest_identity("l_4_breadth_v4"), "b84_gate_path": B84_GATE, "b84_gate_sha256": sha(ROOT / B84_GATE), "b84_gate_validator_path": B84_VALIDATOR, "b84_gate_validator_sha256": sha(ROOT / B84_VALIDATOR), "b84_manifest_identity": manifest_identity("l_4_breadth_b84r2_activation_contract_v3"), "b84_implementation": expected_b84_implementation()}
    if provenance != expected_provenance:
        blockers.append("source_provenance")
    checkout = payload.get("producing_checkout")
    if checkout != {"mode": "committed_synthetic_fixture", "validating_checkout_commit": current_head()} or not committed_fixture:
        blockers.append("producing_checkout")
    if payload.get("v4_controls_sha256") != v4_controls_sha256():
        blockers.append("exact_v4_controls")
    if payload.get("canonical_sections") != canonical_sections():
        blockers.append("canonical_section_hashes")
    try:
        gate = json.loads((ROOT / V4).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        gate = {}
    if payload.get("universes") != {"U1": ["VTI"], "U4": ["VTI", "IEF", "GLD", "DBC"], "U8": list(U8)}:
        blockers.append("universe_contract")
    if payload.get("weekly_schedule") != "synthetic U8-common weekly schedule only; no return decoding or validation dates" or type(payload.get("paired_weeks")) is not int or not 0 <= payload.get("paired_weeks", -1) <= gate.get("static_capacity", {}).get("maximum_weekly_slots_before_warmup_missingness_or_evaluable_pair_reductions", -1):
        blockers.append("schedule_or_capacity")
    blockers.extend(structural_preflight(payload.get("symbol_sessions")))
    if payload.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False} or not isinstance(payload.get("authorizations"), dict) or set(payload["authorizations"]) != AUTH or any(value is not False for value in payload["authorizations"].values()):
        blockers.append("seal_or_authorization")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        report = args.report.resolve(strict=True)
        fixture = (ROOT / FIXTURE).resolve()
        fixture_payload = json.loads(report.read_text(encoding="utf-8"))
        materialized = materialize_fixture(fixture_payload)
        result = validate(materialized if materialized is not None else fixture_payload, committed_fixture=report == fixture and materialized is not None and canonical_fixture_sha256(fixture_payload) == expected_fixture_sha256())
    except Exception as exc:
        result = {"status": "blocked", "blockers": [type(exc).__name__]}
    print(json.dumps(result))
    raise SystemExit(result["status"] != "pass")
