"""Fail-closed validator for the B8.5 Phase A metadata-only activation/order lock."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.provenance import file_sha256

GATE = ROOT / "experiments/l_4_breadth_b85_phase_a_activation_order_v1.json"

AUTH = {"data", "container", "path_inspection", "market", "return", "value", "signal", "position", "covariance", "regime", "cost", "pnl", "execution", "report_decision", "ledger", "validation", "provider", "network", "credentials", "broker", "paid", "paper_trade", "real_money", "environment"}
COUNTS = {"real_container_discovery", "real_container_read", "real_container_hash", "real_container_scan", "real_path_inspection", "environment_read", "market_or_return_value_decode", "research_computation", "execution", "report_decision", "ledger_write", "validation_access", "provider_network_credentials_broker_paid_paper_real_money_access"}
U8 = ["VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC"]


def canonical_sha(path: Path) -> str | None:
    try:
        file_sha256(path)
        return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    except OSError:
        return None


def manifest_identity(gate_id: str, root: Path) -> dict[str, str] | None:
    try:
        rows = [json.loads(line) for line in (root / "experiments/locked_gates.jsonl").read_text(encoding="utf-8").splitlines() if line]
        row = next(row for row in rows if row.get("gate_id") == gate_id)
        return {key: row.get(key) for key in ("gate_id", "artifact_path", "artifact_sha256", "validator_path", "validator_sha256")}
    except (OSError, StopIteration, json.JSONDecodeError):
        return None


def validate(path: Path = GATE, *, project_root: Path = ROOT) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    blockers: list[str] = []
    identity = {"schema_version": "lily_l4_b85_phase_a_activation_order_v1", "order_id": "B8.5", "phase": "A", "gate_id": "l_4_breadth_b85_phase_a_activation_order_v1", "activation_for_gate_id": "l_4_breadth_b84r2_activation_contract_v3", "hypothesis_id": "L-4", "status": "published_E0_phase_a_awaiting_inspector_acceptance", "evidence_ceiling": "E0", "edge_claim": "none"}
    if set(payload) != set(identity) | {"source_binding", "phase_b_contract", "phase_a_authorizations", "phase_a_access_counts", "validation_seal"} or any(payload.get(key) != value for key, value in identity.items()):
        blockers.append("identity_or_top_shape")
    sources = payload.get("source_binding", {})
    source_specs = {
        "accepted_b84r2_gate": ("l_4_breadth_b84r2_activation_contract_v3", "experiments/l_4_breadth_b84r2_activation_contract_v3.json", "4fe9c465111a4200730b8cbc5bd64f7971c53b826b5c3a5cddee30389131a76a", "scripts/validate_l_4_breadth_b84r2_activation_contract_v3.py", "ac74067c13b1a7d72f374c6e0f08fabb37f04325690285cbf4535234d02578a3"),
        "accepted_v4_science": ("l_4_breadth_v4", "experiments/l_4_breadth_preregistration_v4.json", "648b480aed523074e8c99646b313c70b074ca6bde95c2a30fb88a128d150ffcb", "scripts/validate_l_4_breadth_preregistration_v4.py", "78bd4553ca0145d78f2408b0a325fe630897cc717495c6a60766fd72b9a42a42"),
    }
    for key, (gate_id, artifact, artifact_hash, validator, validator_hash) in source_specs.items():
        expected = {"gate_id": gate_id, "artifact_path": artifact, "artifact_sha256": artifact_hash, "validator_path": validator, "validator_sha256": validator_hash, "manifest_identity": {"gate_id": gate_id, "artifact_path": artifact, "artifact_sha256": artifact_hash, "validator_path": validator, "validator_sha256": validator_hash}}
        if sources.get(key) != expected or canonical_sha(project_root / artifact) != artifact_hash or canonical_sha(project_root / validator) != validator_hash or manifest_identity(gate_id, project_root) != expected["manifest_identity"]:
            blockers.append(f"source_binding:{key}")
    implementation = {"runner_path": "scripts/run_l_4_breadth_b84r2_preflight_v3.py", "runner_sha256": "78167352d69b5bed70b44005b665d39480aaa854d6c84f2613cfce61fa9f93d8", "report_validator_path": "scripts/validate_l_4_breadth_b84r2_preflight_report_v3.py", "report_validator_sha256": "684476401fd05c9f492137eb98d3c05703852cbf58f389c26ac38bafea086dae", "report_schema_path": "schemas/l_4_breadth_b84r2_preflight_report_v3.schema.json", "report_schema_sha256": "947911d0409cd09606cb5201663409be635705b63a4954181e26285d1619b992", "synthetic_fixture_path": "tests/fixtures/l4_b84/synthetic_preflight_report_v3.json", "synthetic_fixture_sha256": "23c1ede2b8735f0d8b73bcd221a6d12a0b22d2c7489de3443e910916104473bb"}
    if sources.get("b84r2_preflight_implementation") != implementation or any(canonical_sha(project_root / implementation[f"{name}_path"]) != implementation[f"{name}_sha256"] for name in ("runner", "report_validator", "report_schema", "synthetic_fixture")):
        blockers.append("source_binding:b84r2_preflight_implementation")
    if sources.get("sealed_validation_boundary") != {"falsification_end": "2015-12-31", "validation_start": "2016-01-04", "validation_opened": False, "edge_claim": "none"}:
        blockers.append("sealed_validation_boundary")
    contract = payload.get("phase_b_contract", {})
    structural = contract.get("structural_metadata_only", {}) if isinstance(contract, dict) else {}
    expected_contract = {"status": "not_executed", "owner_preapproval": "Phase B is owner-preapproved only after Inspector acceptance of this Phase A artifact and exact-SHA Hermetic CI success.", "required_preconditions": ["inspector_acceptance_recorded", "exact_sha_hermetic_ci_success"], "real_preflight_limit": {"maximum": 1, "used": 0}, "exact_environment": {"container_id_environment_variable": "LILY_L4_B85_CONTAINER_ID", "required_container_identity": "lily-l4-falsification-pre2016-v1", "environment_read_forbidden_in_phase_a": True}, "hard_stops": ["Phase B may inspect only the declared U8 symbol/session-date structural metadata after its preconditions pass.", "Reject before any return, price, value, signal, position, covariance, regime, cost, PnL, execution, report decision, ledger, or validation access.", "Provider, network, credentials, broker, paid, paper-trade, and real-money access are forbidden.", "No second real preflight is permitted for any result, error, or ambiguity."]}
    expected_structural = {"container_relative_manifest_path": "lily/l4/b85/structural_manifest_v1.json", "container_relative_payload_path": "lily/l4/b85/u8_symbol_session_dates_v1.json", "manifest_required_keys": ["schema_version", "container_identity", "metadata_path", "metadata_sha256"], "manifest_schema_version": "lily_l4_b85_structural_manifest_v1", "payload_schema_version": "lily_l4_b85_u8_symbol_session_dates_v1", "payload_allowed_fields": ["schema_version", "symbol_sessions"], "symbol_session_allowed_fields": ["symbol", "session_date"], "required_u8_members_in_order": U8, "session_date_format": "YYYY-MM-DD", "latest_permitted_session_date": "2015-12-31", "required_check_order": ["container_identity", "manifest_schema", "manifest_path", "manifest_hash", "payload_schema", "exact_u8_membership", "each_symbol_session_date_at_or_before_cutoff", "stop_before_return_or_value_decoding"], "rejection_conditions": ["missing_u8_member", "duplicate_or_ambiguous_u8_member", "schema_mismatch", "path_mismatch", "hash_mismatch", "post_cutoff_session", "non_structural_field", "return_or_value_decode_attempt"]}
    if set(contract) != set(expected_contract) | {"structural_metadata_only"} or any(contract.get(key) != value for key, value in expected_contract.items()) or structural != expected_structural:
        blockers.append("phase_b_contract")
    authorizations = payload.get("phase_a_authorizations")
    if not isinstance(authorizations, dict) or set(authorizations) != AUTH or any(value is not False for value in authorizations.values()):
        blockers.append("phase_a_authorizations")
    counts = payload.get("phase_a_access_counts")
    if not isinstance(counts, dict) or set(counts) != COUNTS or any(value != 0 for value in counts.values()):
        blockers.append("phase_a_access_counts")
    if payload.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}:
        blockers.append("validation_seal")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result))
    raise SystemExit(result["status"] != "pass")
