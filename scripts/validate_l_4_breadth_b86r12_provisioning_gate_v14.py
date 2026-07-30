"""Validate the B8.6R12/v14 gate without activation or data access."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = "experiments/l_4_breadth_b86r12_provisioning_gate_v14.json"
GATE = ROOT / GATE_PATH
ACTIVATION_SCHEMA = "schemas/l_4_breadth_b86r12_provisioning_activation_v14.schema.json"
INCIDENT_COMMIT = "8093183f87a56fa4788c9e1d82d60b323bf23558"


def blob(commit, path):
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def validate():
    try:
        gate = json.loads(GATE.read_text("ascii"))
        dependencies = gate["execution_dependencies"]
        expected = {path: {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()} for path in dependencies if path != GATE_PATH}
        sources = gate["source_binding"]
        schema = json.loads((ROOT / ACTIVATION_SCHEMA).read_text("ascii"))
        incident = sources["v13_incident_state"]
        incident_raw = blob(incident["commit"], incident["path"])
        source_hashes_ok = all(hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"] for name, item in sources.items() if name != "v13_incident_state")
        incident_ok = incident["commit"] == INCIDENT_COMMIT and incident_raw is not None and hashlib.sha256(incident_raw).hexdigest() == incident["sha256"]
        schema_ok = schema["properties"]["schema_version"]["const"] == gate["activation_schema_version"]
        ok = gate["gate_id"] == "l_4_breadth_b86r12_provisioning_gate_v14" and gate["supersedes_gate_id"] == "l_4_breadth_b86r11_provisioning_gate_v13" and gate["order_id"] == "B8.6R12" and gate["evidence_ceiling"] == "E0" and gate["edge_claim"] == "none" and gate["activation_path"] == "experiments/activation_records/l_4_breadth_b86r12_provisioning_activation_v14.json" and gate["activation_schema_version"] == "lily_l4_breadth_b86r12_provisioning_activation_v14" and gate["execution_binding"] == expected and source_hashes_ok and incident_ok and schema_ok and set(sources) == {"active_l4_v4", "consumed_b85r5_result", "superseded_v13", "v13_incident_state"} and gate["validation_seal"] == {"status": "sealed_not_accessed", "accessed": False} and all(value is False for value in gate["authorizations"].values()) and gate["access_counts"] == {"dataset": 0, "return_value": 0, "validation": 0}
    except Exception:
        ok = False
    return {"status": "pass" if ok else "blocked"}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result))
    raise SystemExit(result["status"] != "pass")
