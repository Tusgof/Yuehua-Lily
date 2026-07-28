from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.l4_b86r2_provisioning_scanner_v3 import CUTOFF, MAX_BYTES, U8
from lib.l4_b86r3_contract_v4 import OVER_BLOCKER, READ_BLOCKERS, SCAN_BLOCKERS

GATE = ROOT / "experiments/l_4_breadth_b86r3_provisioning_gate_v4.json"
AUTHORIZATIONS = {
    "data",
    "container",
    "path_inspection",
    "environment",
    "market",
    "return",
    "value",
    "validation",
    "execution",
    "provider",
    "network",
    "credentials",
    "broker",
    "paid",
    "paper_trade",
    "real_money",
}
ACCESS_COUNTS = {
    "real_container_read",
    "environment_read",
    "market_or_return_value_decode",
    "execution",
    "validation_access",
}
IMPLEMENTATION = {
    "blocker_contract",
    "runner",
    "report_schema",
    "activation_schema",
    "report_validator",
    "gate_validator",
}
SOURCE_BINDING = {"science_v4", "consumed_b85r5_result", "rejected_v3"}


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(gate_path=GATE):
    try:
        gate = json.loads(Path(gate_path).read_text("ascii"))
    except (OSError, ValueError) as error:
        return {"status": "blocked", "blockers": [type(error).__name__]}
    blockers = []
    required = {
        "schema_version": "lily_l4_b86r3_provisioning_gate_v4",
        "order_id": "B8.6R3",
        "phase": "A",
        "gate_id": "l_4_breadth_b86r3_provisioning_gate_v4",
        "supersedes_gate_id": "l_4_breadth_b86r2_provisioning_gate_v3",
        "hypothesis_id": "L-4",
        "status": "locked_E0_v4_remediation_awaiting_inspector_acceptance_and_activation",
        "evidence_ceiling": "E0",
        "edge_claim": "none",
        "execution_flag": "--execute-one-shot",
        "report_path": "reports/experiments/l_4_breadth_b86r3_provisioning_report_v4.json",
        "marker_path": "reports/experiments/l_4_breadth_b86r3_provisioning_attempt_v4.json",
        "validation_seal": {"status": "sealed_not_accessed", "accessed": False},
    }
    required_keys = set(required) | {
        "dataset",
        "source_binding",
        "implementation",
        "blocker_matrix",
        "future_activation_lifecycle",
        "phase_a_authorizations",
        "phase_a_access_counts",
    }
    if set(gate) != required_keys or any(gate.get(key) != value for key, value in required.items()):
        blockers.append("identity")
    dataset = gate.get("dataset")
    expected_dataset = {
        "repo_relative_path": "data/normalized/l1_yahoo_daily_v1.json",
        "expected_sha256": "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd",
        "schema_version": "lily_l1_daily_dataset_v1",
        "cutoff_inclusive": CUTOFF,
        "u8_members_in_order": list(U8),
        "max_bounded_read_bytes": MAX_BYTES + 1,
    }
    if dataset != expected_dataset:
        blockers.append("dataset")
    sources = gate.get("source_binding")
    if not isinstance(sources, dict) or set(sources) != SOURCE_BINDING:
        blockers.append("source_binding")
    else:
        for source in sources.values():
            try:
                if set(source) != {"path", "sha256"} or _sha(ROOT / source["path"]) != source["sha256"]:
                    blockers.append("source_binding")
            except (KeyError, OSError):
                blockers.append("source_binding")
    implementation = gate.get("implementation")
    if not isinstance(implementation, dict) or set(implementation) != IMPLEMENTATION:
        blockers.append("implementation")
    else:
        for item in implementation.values():
            try:
                if set(item) != {"path", "sha256"} or _sha(ROOT / item["path"]) != item["sha256"]:
                    blockers.append("implementation")
            except (KeyError, OSError):
                blockers.append("implementation")
    expected_matrix = {
        "read_unavailable": sorted(READ_BLOCKERS),
        "bounded_read_over_limit": OVER_BLOCKER,
        "opaque_structural_scan": sorted(SCAN_BLOCKERS),
        "all_blockers_are_reportable": True,
        "fabricated_blocker_rejected": True,
    }
    if gate.get("blocker_matrix") != expected_matrix:
        blockers.append("blocker_matrix")
    expected_lifecycle = {
        "activation_path": "experiments/activation_records/l_4_breadth_b86r3_provisioning_activation_v4.json",
        "activation_is_new_tracked_checkpoint": True,
        "requires_inspector_accepted_gate": True,
        "requires_exact_sha_hermetic_ci": True,
        "accepted_gate_head_must_be_ancestor_of_activation_head": True,
        "accepted_gate_blob_must_match_gate_sha256": True,
        "activation_json_must_be_canonical_bytes": True,
        "marker_claim_before_dataset_read": True,
        "marker_is_atomic_one_shot": True,
        "first_report_is_immutable": True,
        "execution_requires_exact_flag": "--execute-one-shot",
    }
    if gate.get("future_activation_lifecycle") != expected_lifecycle:
        blockers.append("lifecycle")
    authorizations = gate.get("phase_a_authorizations")
    if not isinstance(authorizations, dict) or set(authorizations) != AUTHORIZATIONS or any(authorizations.values()):
        blockers.append("authorizations")
    counts = gate.get("phase_a_access_counts")
    if not isinstance(counts, dict) or set(counts) != ACCESS_COUNTS or any(counts.values()):
        blockers.append("access_counts")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
