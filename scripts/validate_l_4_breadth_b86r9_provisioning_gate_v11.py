"""Validate the static B8.6R9/v11 bootstrap gate without data access."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "experiments/l_4_breadth_b86r9_provisioning_gate_v11.json"


def validate() -> dict:
    try:
        value = json.loads(GATE.read_text("ascii"))
        paths = value["execution_dependencies"]
        expected = {path: {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()} for path in paths if path != GATE.relative_to(ROOT).as_posix()}
        ok = (set(value) == {"schema_version", "order_id", "phase", "gate_id", "supersedes_gate_id", "hypothesis_id", "evidence_ceiling", "edge_claim", "source_binding", "execution_dependencies", "entry_command", "activation_path", "dataset_path", "marker_path", "report_path", "validation_seal", "authorizations", "access_counts", "residual_risk"} and value["schema_version"] == "lily_l4_b86r9_provisioning_gate_v11" and value["order_id"] == "B8.6R9" and value["phase"] == "A" and value["gate_id"] == "l_4_breadth_b86r9_provisioning_gate_v11" and value["supersedes_gate_id"] == "l_4_breadth_b86r8_provisioning_gate_v10" and value["hypothesis_id"] == "L-4" and value["evidence_ceiling"] == "E0" and value["edge_claim"] == "none" and value["source_binding"] == expected and value["activation_path"] == "experiments/activation_records/l_4_breadth_b86r9_provisioning_activation_v11.json" and value["dataset_path"] == "data/normalized/l1_yahoo_daily_v1.json" and value["marker_path"] == "reports/experiments/l_4_breadth_b86r9_provisioning_attempt_v11.json" and value["report_path"] == "reports/experiments/l_4_breadth_b86r9_provisioning_report_v11.json" and value["validation_seal"] == {"status": "sealed_not_accessed", "accessed": False} and all(flag is False for flag in value["authorizations"].values()) and value["access_counts"] == {"dataset": 0, "return_value": 0, "validation": 0})
    except (OSError, ValueError, KeyError, TypeError):
        ok = False
    return {"status": "pass" if ok else "blocked"}


if __name__ == "__main__":
    result = validate(); print(json.dumps(result)); raise SystemExit(result["status"] != "pass")
