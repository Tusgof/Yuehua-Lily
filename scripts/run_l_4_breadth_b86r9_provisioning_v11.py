"""Runtime loaded only by the commit-sourced B8.6R9 bootstrap."""
from __future__ import annotations

import sys
from pathlib import Path


def run_one_shot(*, root: Path, commit: str, dependency_identities: dict, activation: dict) -> dict:
    # These imports are intentionally after the stdlib-only bootstrap has
    # compared every runtime byte with the producing commit.
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from lib.l4_b86r9_contract_v11 import (
        ACTIVATION, DATASET, EXPECTED_DATASET_SHA256, MANIFEST, MARKER,
        MAX_BYTES, PAYLOAD, REPORT, REPORT_SCHEMA, SEAL, U8, artifact,
        atomic_write_all, canonical, claim_once, sha256,
    )
    from lib.l4_b86r2_provisioning_scanner_v3 import ScanError, scan_dataset

    if not claim_once(root / MARKER):
        return {"outcome": "refused_already_consumed", "dataset_read_count": 0}
    row = artifact(); row["attempted_read_count"] = 1
    try:
        with (root / DATASET).open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
    except FileNotFoundError:
        raw, blocker = None, "dataset_missing"
    except OSError:
        raw, blocker = None, "dataset_read_error"
    else:
        blocker = None; row.update({"read_count": 1, "observed_byte_count": len(raw), "hash_count": 1, "bounded_prefix_sha256": sha256(raw)})
        if len(raw) > MAX_BYTES:
            blocker = "dataset_input_over_limit"
        else:
            row.update({"complete_read": True, "complete_raw_sha256": row["bounded_prefix_sha256"], "scan_count": 1})
    report = {"schema_version": REPORT_SCHEMA, "order_id": "B8.6R9", "hypothesis_id": "L-4", "mode": "real_one_shot", "evidence_tier": "E0", "edge_claim": "none", "real_provisioning_consumed": True, "dataset_reference": DATASET, "expected_dataset_sha256": EXPECTED_DATASET_SHA256, "dataset_artifact": row, "contract_artifacts": dependency_identities, "activation_provenance": activation, "access_counters": {"return_value_decode_count": 0, "validation_access_count": 0}, "validation_seal": SEAL, "producing_git_commit": commit}
    if blocker:
        report.update({"outcome": "provisioning_blocked", "blocker": blocker})
    else:
        try:
            scanned = scan_dataset(raw, expected_sha256=EXPECTED_DATASET_SHA256)
        except ScanError as error:
            report.update({"outcome": "provisioning_blocked", "blocker": str(error)})
        else:
            manifest = {"schema_version": "lily_l4_b86r9_falsification_manifest_v11", "dataset_reference": DATASET, "dataset_sha256": scanned["dataset_sha256"], "dataset_byte_count": scanned["dataset_byte_count"], "u8_members_in_order": list(U8), "coverage_by_symbol": scanned["coverage_by_symbol"], "session_count": scanned["session_count"], "max_session_date": scanned["max_session_date"], "validation_seal": SEAL}
            payload = {"schema_version": "lily_l4_b86r9_u8_session_dates_v11", "dataset_sha256": scanned["dataset_sha256"], "u8_members_in_order": list(U8), "session_dates_by_symbol": scanned["session_dates_by_symbol"]}
            manifest_raw, payload_raw = canonical(manifest), canonical(payload)
            atomic_write_all(((root / MANIFEST, manifest_raw), (root / PAYLOAD, payload_raw)))
            report.update({"outcome": "structural_provisioned", "manifest": manifest, "payload": payload, "output_artifacts": {"manifest": {"path": MANIFEST, "raw_sha256": sha256(manifest_raw), "byte_count": len(manifest_raw)}, "payload": {"path": PAYLOAD, "raw_sha256": sha256(payload_raw), "byte_count": len(payload_raw)}}, "structural_summary_sha256": sha256(canonical({"manifest": manifest, "payload": payload}))})
    atomic_write_all(((root / REPORT, canonical(report)),))
    return report


if __name__ == "__main__":
    # A mutable worktree file is never an accepted production entry point.
    raise SystemExit(2)
