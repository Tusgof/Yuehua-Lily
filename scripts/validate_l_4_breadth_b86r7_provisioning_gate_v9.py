"""Hash and semantic validator for the B8.6R7/v9 E0 gate."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib.l4_b86r7_contract_v9 import DATASET, EXPECTED_DATASET_SHA256, GATE_ID, SEAL

PATH = ROOT / "experiments/l_4_breadth_b86r7_provisioning_gate_v9.json"
KEYS = {
    "schema_version", "order_id", "phase", "gate_id", "supersedes_gate_id", "hypothesis_id",
    "evidence_ceiling", "edge_claim", "source_binding", "activation_path", "dataset_path",
    "expected_dataset_sha256", "marker_path", "report_path", "manifest_path", "payload_path",
    "execution_flag", "lifecycle", "blocker_matrix", "validation_seal", "authorizations", "access_counts",
}


def validate():
    try:
        value = json.loads(PATH.read_text("ascii")); sources = value["source_binding"]
        ok = (
            set(value) == KEYS and value["schema_version"] == "lily_l4_b86r7_provisioning_gate_v9"
            and value["order_id"] == "B8.6R7" and value["phase"] == "A" and value["gate_id"] == GATE_ID
            and value["supersedes_gate_id"] == "l_4_breadth_b86r6_provisioning_gate_v8"
            and value["hypothesis_id"] == "L-4" and value["evidence_ceiling"] == "E0" and value["edge_claim"] == "none"
            and value["dataset_path"] == DATASET and value["expected_dataset_sha256"] == EXPECTED_DATASET_SHA256
            and value["execution_flag"] == "--execute-one-shot" and value["validation_seal"] == SEAL
            and isinstance(sources, dict) and len(sources) >= 11
            and all(set(item) == {"path", "sha256"} and isinstance(item["path"], str)
                    and len(item["sha256"]) == 64 and hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
                    for item in sources.values())
            and value["lifecycle"] == {"accepted_gate_required": True, "activation_checkpoint_required": True, "marker_before_dataset_access": True, "one_shot": True, "repeat_preserves_first_artifacts": True}
            and not any(value["authorizations"].values())
            and value["access_counts"] == {"dataset": 0, "return_value": 0, "validation": 0}
        )
    except Exception:
        ok = False
    return {"status": "pass" if ok else "blocked"}


if __name__ == "__main__":
    result = validate(); print(json.dumps(result)); raise SystemExit(result["status"] != "pass")
