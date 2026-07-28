from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.draft202012_subset import ValidationError, validate as draft_validate
from lib.l4_b86r2_provisioning_scanner_v3 import MAX_BYTES
from lib.l4_b86r3_contract_v4 import REACHABLE_BLOCKERS, category
from scripts.run_l_4_breadth_b86r3_provisioning_v4 import (
    ACTIVATION_RELATIVE,
    CONTRACT_ARTIFACTS,
    DATASET_REFERENCE,
    EXPECTED_SHA256,
    MANIFEST_RELATIVE,
    PAYLOAD_RELATIVE,
    accepted_gate,
    canonical,
    identities,
)

SCHEMA = ROOT / "schemas/l_4_breadth_b86r3_provisioning_report_v4.schema.json"
ACTIVATION_SCHEMA = ROOT / "schemas/l_4_breadth_b86r3_provisioning_activation_v4.schema.json"
HEX = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
ARTIFACT_KEYS = {
    "attempted_read_count",
    "read_count",
    "observed_byte_count",
    "complete_read",
    "complete_raw_sha256",
    "bounded_prefix_sha256",
    "hash_count",
    "scan_count",
    "opaque_unsafe_lexeme_decode_count",
}


def row_ok(row, blocker):
    if not isinstance(row, dict) or set(row) != ARTIFACT_KEYS:
        return False
    kind = category(blocker)
    if kind == "unread":
        return (
            row["attempted_read_count"] == 1
            and row["read_count"] == row["hash_count"] == row["scan_count"] == 0
            and row["observed_byte_count"] is None
            and row["complete_read"] is False
            and row["complete_raw_sha256"] is None
            and row["bounded_prefix_sha256"] is None
            and row["opaque_unsafe_lexeme_decode_count"] == 0
        )
    if kind == "over":
        return (
            row["attempted_read_count"] == row["read_count"] == row["hash_count"] == 1
            and row["observed_byte_count"] == MAX_BYTES + 1
            and row["complete_read"] is False
            and row["complete_raw_sha256"] is None
            and bool(HEX.fullmatch(str(row["bounded_prefix_sha256"])))
            and row["scan_count"] == row["opaque_unsafe_lexeme_decode_count"] == 0
        )
    return (
        row["attempted_read_count"] == row["read_count"] == row["hash_count"] == row["scan_count"] == 1
        and isinstance(row["observed_byte_count"], int)
        and 0 < row["observed_byte_count"] <= MAX_BYTES
        and row["complete_read"] is True
        and bool(HEX.fullmatch(str(row["complete_raw_sha256"])))
        and row["bounded_prefix_sha256"] == row["complete_raw_sha256"]
        and row["opaque_unsafe_lexeme_decode_count"] == 0
    )


def _provenance_ok(provenance, commit, accepted_gate_check=accepted_gate):
    if not isinstance(provenance, dict) or set(provenance) != {
        "path", "raw_sha256", "content", "activation_checkpoint_head"
    }:
        return False
    if provenance["path"] != ACTIVATION_RELATIVE.as_posix() or not COMMIT.fullmatch(str(commit)):
        return False
    raw = canonical(provenance["content"])
    if hashlib.sha256(raw).hexdigest() != provenance["raw_sha256"]:
        return False
    try:
        draft_validate(json.loads(ACTIVATION_SCHEMA.read_text("ascii")), provenance["content"])
    except (OSError, ValueError, ValidationError):
        return False
    content = provenance["content"]
    if content["accepted_gate_head_sha"] != content["hermetic_ci_head_sha"]:
        return False
    if provenance["activation_checkpoint_head"] != commit:
        return False
    return accepted_gate_check(content["accepted_gate_head_sha"], commit, content["gate_sha256"])


def _persisted_output_ok(path, raw):
    try:
        return path.read_bytes() == raw
    except OSError:
        return False


def validate(report, *, output_paths=None, accepted_gate_check=None):
    blockers = []
    try:
        draft_validate(json.loads(SCHEMA.read_text("ascii")), report)
    except (OSError, ValueError, ValidationError):
        blockers.append("schema")
    if not isinstance(report, dict):
        return {"status": "blocked", "blockers": ["type"]}
    if (
        report.get("contract_artifacts") != identities()
        or report.get("dataset_reference") != DATASET_REFERENCE
        or report.get("expected_dataset_sha256") != EXPECTED_SHA256
        or report.get("access_counters")
        != {
            "return_value_decode_count": 0,
            "opaque_unsafe_lexeme_decode_count": 0,
            "validation_access_count": 0,
        }
        or report.get("validation_seal") != {"status": "sealed_not_accessed", "accessed": False}
    ):
        blockers.append("contract")
    mode = report.get("mode")
    if mode == "synthetic_fixture":
        if (
            report.get("real_provisioning_consumed") is not False
            or report.get("activation_provenance") is not None
            or report.get("producing_git_commit") != "synthetic_fixture"
        ):
            blockers.append("mode")
    elif mode == "real_one_shot":
        check = lambda provenance, commit: _provenance_ok(
            provenance, commit, accepted_gate_check or accepted_gate
        )
        if (
            report.get("real_provisioning_consumed") is not True
            or not COMMIT.fullmatch(str(report.get("producing_git_commit")))
            or not check(report.get("activation_provenance"), report.get("producing_git_commit"))
        ):
            blockers.append("provenance")
    else:
        blockers.append("mode")

    outcome = report.get("outcome")
    row = report.get("dataset_artifact")
    if outcome == "provisioning_blocked":
        blocker = report.get("blocker")
        if blocker not in REACHABLE_BLOCKERS or not row_ok(row, blocker):
            blockers.append("blocked")
    elif outcome == "structural_provisioned":
        manifest = report.get("manifest")
        payload = report.get("payload")
        identities_by_output = report.get("output_artifacts")
        if not row_ok(row, "dataset_hash_mismatch"):
            blockers.append("success")
        if (
            not isinstance(manifest, dict)
            or not isinstance(payload, dict)
            or not isinstance(identities_by_output, dict)
            or set(identities_by_output) != {"manifest", "payload"}
            or report.get("structural_summary_sha256")
            != hashlib.sha256(canonical({"manifest": manifest, "payload": payload})).hexdigest()
        ):
            blockers.append("success")
        else:
            if (
                manifest.get("dataset_sha256") != row.get("complete_raw_sha256")
                or manifest.get("dataset_byte_count") != row.get("observed_byte_count")
                or payload.get("dataset_sha256") != manifest.get("dataset_sha256")
                or payload.get("u8_members_in_order") != manifest.get("u8_members_in_order")
                or set(payload.get("session_dates_by_symbol", {}))
                != set(manifest.get("coverage_by_symbol", {}))
            ):
                blockers.append("binding")
            paths = output_paths or (ROOT / MANIFEST_RELATIVE, ROOT / PAYLOAD_RELATIVE)
            for name, value, path in zip(
                ("manifest", "payload"), (manifest, payload), paths, strict=True
            ):
                raw = canonical(value)
                expected = {
                    "path": Path(path).as_posix(),
                    "raw_sha256": hashlib.sha256(raw).hexdigest(),
                    "byte_count": len(raw),
                }
                if identities_by_output.get(name) != expected:
                    blockers.append("identity")
                elif mode == "real_one_shot" and not _persisted_output_ok(Path(path), raw):
                    blockers.append("identity")
    else:
        blockers.append("outcome")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


def main(argv):
    if len(argv) != 1:
        return 2
    try:
        report = json.loads(Path(argv[0]).read_text("ascii"))
    except (OSError, ValueError):
        print(json.dumps({"status": "blocked", "blockers": ["unreadable_report"]}))
        return 1
    result = validate(report)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
