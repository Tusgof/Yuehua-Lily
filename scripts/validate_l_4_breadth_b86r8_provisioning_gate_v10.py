"""Strict semantic and hash validator for B8.6R8/v10."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.l4_b86r8_contract_v10 import DATASET, DEPENDENCY_PATHS, EXPECTED_DATASET_SHA256, GATE, GATE_ID, SEAL

PATH = ROOT / GATE
KEYS = {"schema_version", "order_id", "phase", "gate_id", "supersedes_gate_id", "hypothesis_id", "evidence_ceiling", "edge_claim", "source_binding", "execution_dependency_paths", "activation_path", "dataset_path", "expected_dataset_sha256", "marker_path", "report_path", "manifest_path", "payload_path", "execution_flag", "lifecycle", "blocker_matrix", "validation_seal", "authorizations", "access_counts"}
REQUIRED_SOURCES = {"active_l4_v4", "consumed_b85r5_result", "rejected_v9"} | (set(DEPENDENCY_PATHS) - {"gate"})

def validate():
    try:
        value = json.loads(PATH.read_text("ascii")); sources = value["source_binding"]
        ok = set(value) == KEYS and value["schema_version"] == "lily_l4_b86r8_provisioning_gate_v10" and value["order_id"] == "B8.6R8" and value["phase"] == "A" and value["gate_id"] == GATE_ID and value["supersedes_gate_id"] == "l_4_breadth_b86r7_provisioning_gate_v9" and value["hypothesis_id"] == "L-4" and value["evidence_ceiling"] == "E0" and value["edge_claim"] == "none" and value["execution_dependency_paths"] == DEPENDENCY_PATHS and value["activation_path"] == "experiments/activation_records/l_4_breadth_b86r8_provisioning_activation_v10.json" and value["dataset_path"] == DATASET and value["expected_dataset_sha256"] == EXPECTED_DATASET_SHA256 and value["marker_path"] == "reports/experiments/l_4_breadth_b86r8_provisioning_attempt_v10.json" and value["report_path"] == "reports/experiments/l_4_breadth_b86r8_provisioning_report_v10.json" and value["manifest_path"] == "experiments/provisioned/l_4_breadth_b86r8_falsification_manifest_v10.json" and value["payload_path"] == "experiments/provisioned/l_4_breadth_b86r8_u8_session_dates_v10.json" and value["execution_flag"] == "--execute-one-shot" and value["lifecycle"] == {"accepted_gate_required": True, "activation_checkpoint_required": True, "execution_provenance_before_marker": True, "marker_before_dataset_access": True, "one_shot": True, "repeat_preserves_first_artifacts": True} and value["blocker_matrix"] == "lib/l4_b86r8_contract_v10.py:BLOCKERS" and value["validation_seal"] == SEAL and value["authorizations"] == {"data": False, "activation": False, "execution": False, "validation": False, "provider": False, "network": False, "credentials": False, "broker": False, "paid": False, "paper_trade": False, "real_money": False} and value["access_counts"] == {"dataset": 0, "return_value": 0, "validation": 0} and isinstance(sources, dict) and set(sources) == REQUIRED_SOURCES and all(set(item) == {"path", "sha256"} and item["path"] == DEPENDENCY_PATHS[name] and hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"] for name, item in sources.items() if name in DEPENDENCY_PATHS) and all(set(sources[name]) == {"path", "sha256"} and hashlib.sha256((ROOT / sources[name]["path"]).read_bytes()).hexdigest() == sources[name]["sha256"] for name in {"active_l4_v4", "consumed_b85r5_result", "rejected_v9"})
    except Exception: ok = False
    return {"status": "pass" if ok else "blocked"}
if __name__ == "__main__":
    result = validate(); print(json.dumps(result)); raise SystemExit(result["status"] != "pass")
