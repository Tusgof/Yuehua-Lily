"""Static v15 gate validation only; it never opens an activation or dataset."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = "experiments/l_4_breadth_b86r13_provisioning_gate_v15.json"
DEPS = (GATE_PATH, "scripts/run_l_4_breadth_b86r13_committed_bootstrap_v15.py", "scripts/run_l_4_breadth_b86r13_provisioning_v15.py", "lib/l4_b86r13_contract_v15.py", "lib/l4_b86r2_provisioning_scanner_v3.py", "lib/draft202012_subset.py", "scripts/validate_l_4_breadth_b86r13_provisioning_gate_v15.py", "scripts/validate_l_4_breadth_b86r13_provisioning_report_v15.py", "scripts/validate_l_4_breadth_b86r13_provisioning_activation_v15.py", "schemas/l_4_breadth_b86r13_provisioning_activation_v15.schema.json", "schemas/l_4_breadth_b86r13_provisioning_report_v15.schema.json", "schemas/l_4_breadth_b86r13_falsification_manifest_v15.schema.json", "schemas/l_4_breadth_b86r13_u8_session_dates_v15.schema.json")


def digest(path): return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def validate():
    try:
        gate = json.loads((ROOT / GATE_PATH).read_text("ascii"))
        activation_schema = json.loads((ROOT / "schemas/l_4_breadth_b86r13_provisioning_activation_v15.schema.json").read_text("ascii"))
        expected = {path: {"path": path, "sha256": digest(path)} for path in DEPS if path != GATE_PATH}
        v14 = "experiments/l_4_breadth_b86r12_provisioning_gate_v14.json"
        ok = set(gate) == {"schema_version", "order_id", "gate_id", "supersedes_gate_id", "hypothesis_id", "evidence_ceiling", "edge_claim", "activation_schema_version", "required_owner_authorization_reference", "source_binding", "execution_binding", "execution_dependencies", "activation_path", "marker_path", "report_path", "manifest_path", "payload_path", "validation_seal", "authorizations"} and gate["schema_version"] == "lily_l4_b86r13_provisioning_gate_v15" and gate["order_id"] == "B8.6R13" and gate["gate_id"] == "l_4_breadth_b86r13_provisioning_gate_v15" and gate["supersedes_gate_id"] == "l_4_breadth_b86r12_provisioning_gate_v14" and gate["hypothesis_id"] == "L-4" and gate["evidence_ceiling"] == "E0" and gate["edge_claim"] == "none" and gate["activation_schema_version"] == activation_schema["properties"]["schema_version"]["const"] and gate["required_owner_authorization_reference"] == activation_schema["properties"]["owner_authorization_reference"]["const"] == "B8.6R13 one-shot owner authorization" and gate["execution_dependencies"] == list(DEPS) and gate["execution_binding"] == expected and gate["source_binding"]["superseded_v14"] == {"path": v14, "sha256": digest(v14)} and gate["validation_seal"] == {"status": "sealed_not_accessed", "accessed": False} and isinstance(gate["authorizations"], dict) and gate["authorizations"] and all(value is False for value in gate["authorizations"].values())
    except (KeyError, OSError, UnicodeDecodeError, ValueError, TypeError):
        ok = False
    return {"status": "pass" if ok else "blocked"}


if __name__ == "__main__":
    result = validate(); print(json.dumps(result)); raise SystemExit(result["status"] != "pass")
