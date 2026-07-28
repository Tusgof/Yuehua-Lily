"""Fail-closed validator for the B8.5R2 Phase-A structural-contract remediation."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.l4_b85r2_structural_scanner_v3 import read_bounded

GATE = ROOT / "experiments/l_4_breadth_b85r2_phase_a_activation_order_v3.json"
IMPLEMENTATION_PATHS = {
    "scanner": "lib/l4_b85r2_structural_scanner_v3.py",
    "runner": "scripts/run_l_4_breadth_b85r2_phase_b_preflight_v3.py",
    "report_schema": "schemas/l_4_breadth_b85r2_structural_preflight_report_v3.schema.json",
    "report_validator": "scripts/validate_l_4_breadth_b85r2_structural_preflight_report_v3.py",
    "synthetic_manifest": "tests/fixtures/l4_b85r2/structural_manifest_v3.json",
    "synthetic_payload": "tests/fixtures/l4_b85r2/u8_symbol_session_dates_v3.json",
}
AUTHORIZATIONS = {"data", "container", "path_inspection", "environment", "market", "return", "value", "signal", "position", "covariance", "regime", "cost", "pnl", "execution", "report_decision", "ledger", "validation", "provider", "network", "credentials", "broker", "paid", "paper_trade", "real_money"}
PREDECESSORS = {
    "rejected_v1": {"gate_id": "l_4_breadth_b85_phase_a_activation_order_v1", "artifact_path": "experiments/l_4_breadth_b85_phase_a_activation_order_v1.json", "artifact_sha256": "d8887c5851a06605895ac287676d7912bedca4869bae73ccabf57317936ba962", "validator_path": "scripts/validate_l_4_breadth_b85_phase_a_activation_order_v1.py", "validator_sha256": "6e6e3b65c82b02ffdc51727ef52124667ec3235f80d1aba5f8e2538f5d72d1bd"},
    "rejected_v2": {"gate_id": "l_4_breadth_b85_phase_a_activation_order_v2", "artifact_path": "experiments/l_4_breadth_b85_phase_a_activation_order_v2.json", "artifact_sha256": "d8e03f932f0aea861a6611d578ea19903b9b722872bc2866cb21573c2fea3f89", "validator_path": "scripts/validate_l_4_breadth_b85_phase_a_activation_order_v2.py", "validator_sha256": "7e9c2fafcbaab0ac627f83a66e2c2d7e8bf28dc8aef9f2bf172d265ac40c9b74"},
}


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(read_bounded(path)).hexdigest()
    except OSError:
        return None


def _manifest_identity(gate_id: str) -> dict[str, str] | None:
    try:
        rows = [json.loads(line) for line in read_bounded(ROOT / "experiments/locked_gates.jsonl").decode("utf-8").splitlines() if line]
        row = next(row for row in rows if row.get("gate_id") == gate_id)
    except (OSError, ValueError, StopIteration, json.JSONDecodeError):
        return None
    return {key: row.get(key) for key in ("gate_id", "artifact_path", "artifact_sha256", "validator_path", "validator_sha256")}


def validate(path: Path = GATE) -> dict[str, object]:
    try:
        gate = json.loads(read_bounded(path).decode("ascii"))
    except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    blockers: list[str] = []
    identity = {"schema_version": "lily_l4_b85r2_phase_a_activation_order_v3", "order_id": "B8.5R2", "phase": "A", "gate_id": "l_4_breadth_b85r2_phase_a_activation_order_v3", "supersedes_gate_id": "l_4_breadth_b85_phase_a_activation_order_v2", "activation_for_gate_id": "l_4_breadth_b84r2_activation_contract_v3", "hypothesis_id": "L-4", "status": "published_E0_phase_a_remediation_awaiting_inspector_acceptance", "evidence_ceiling": "E0", "edge_claim": "none"}
    if not isinstance(gate, dict) or any(gate.get(key) != value for key, value in identity.items()):
        blockers.append("identity")
    for name, expected in PREDECESSORS.items():
        if gate.get("source_binding", {}).get(name) != expected or _sha(ROOT / expected["artifact_path"]) != expected["artifact_sha256"] or _sha(ROOT / expected["validator_path"]) != expected["validator_sha256"] or _manifest_identity(expected["gate_id"]) != expected:
            blockers.append("predecessor_binding:" + name)
    for name, relative in IMPLEMENTATION_PATHS.items():
        row = gate.get("implementation", {}).get(name, {})
        if row.get("path") != relative or row.get("sha256") != _sha(ROOT / relative):
            blockers.append("implementation:" + name)
    contract = gate.get("future_phase_b_contract", {})
    expected_contract = {"status": "not_executed", "preconditions": ["inspector_acceptance_recorded", "exact_sha_hermetic_ci_success"], "one_shot_real_preflight_maximum": 1, "storage_root_variable": "LILY_DATA_ROOT", "manifest_storage_reference": "${LILY_DATA_ROOT}/sealed/l4_b85r2/l4_b85r2_structural_manifest_v3.json", "payload_storage_reference": "${LILY_DATA_ROOT}/sealed/l4_b85r2/l4_b85r2_u8_symbol_session_dates_v3.json", "container_identity": "lily-l4-falsification-pre2016-v3", "repo_relative_report_path": "reports/experiments/l_4_breadth_b85r2_phase_b_preflight_report_v3.json", "repo_relative_attempt_marker_path": "reports/experiments/l_4_breadth_b85r2_phase_b_preflight_attempt_v3.json"}
    if any(contract.get(key) != value for key, value in expected_contract.items()) or any(term not in contract.get("resolution_rule", "") for term in ("no alternate root", "no fallback", "no glob", "no directory listing")) or any(term not in contract.get("consumption_rule", "") for term in ("Atomically", "before environment", "Missing root", "second attempt")) or any(term not in contract.get("scanner_rule", "") for term in ("MAX_BYTES + 1", "invalid calendar", "every individual post-cutoff", "return or value")):
        blockers.append("future_phase_b_contract")
    authorizations = gate.get("phase_a_authorizations")
    if not isinstance(authorizations, dict) or set(authorizations) != AUTHORIZATIONS or any(value is not False for value in authorizations.values()):
        blockers.append("phase_a_authorizations")
    counts = gate.get("phase_a_access_counts")
    if not isinstance(counts, dict) or any(value != 0 for value in counts.values()):
        blockers.append("phase_a_access_counts")
    if gate.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}:
        blockers.append("validation_seal")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
