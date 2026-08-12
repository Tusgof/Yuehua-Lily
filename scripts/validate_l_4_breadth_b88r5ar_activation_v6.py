"""Validate the B8.8R5AR clean replacement activation checkpoint only."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.draft202012_subset import ValidationError, validate as draft_validate
from lib.l4_b88r5_lifecycle_v6 import (
    ACTIVATION,
    GATE,
    activation_ok,
    blob,
    build_activation,
    canonical,
    clean_checkout,
)


SCHEMA = "schemas/l_4_breadth_b88r5_activation_v6.schema.json"
ACCEPTED_GATE_HEAD_SHA = "fc727d78fc38a70e7bef7c85fb22d3e8fe2c7006"
HERMETIC_CI_RUN_ID = 30806980165
EXPECTED_ACTIVATION_SHA256 = "6f092c187b8236ba52ecc9d3dfde78192a70f05ef635c4c9b5d67b97a9604913"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _static_blockers(raw: bytes, schema: dict[str, Any], gate_raw: bytes) -> list[str]:
    blockers: list[str] = []
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ["activation_not_canonical_ascii_json"]
    try:
        draft_validate(schema, value)
    except ValidationError:
        blockers.append("schema_mismatch")
    try:
        expected = canonical(
            build_activation(
                gate_raw=gate_raw,
                accepted_gate_head_sha=ACCEPTED_GATE_HEAD_SHA,
                hermetic_ci_run_id=HERMETIC_CI_RUN_ID,
            )
        )
    except (UnicodeDecodeError, ValueError, TypeError):
        return blockers + ["gate_identity_unreadable"]
    if raw.endswith(b"\n") or raw != canonical(value):
        blockers.append("noncanonical_activation_bytes")
    if raw != expected:
        blockers.append("gate_derived_activation_mismatch")
    if _sha(raw) != EXPECTED_ACTIVATION_SHA256:
        blockers.append("activation_sha256_mismatch")
    return sorted(set(blockers))


def validate(root: Path = ROOT, producing_commit: str | None = None) -> dict[str, object]:
    root = Path(root).resolve()
    blockers: list[str] = []
    if producing_commit is None:
        try:
            producing_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            producing_commit = ""

    try:
        raw = (root / ACTIVATION).read_bytes()
        schema = json.loads((root / SCHEMA).read_text(encoding="ascii"))
        gate_raw = (root / GATE).read_bytes()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {
            "status": "blocked",
            "blockers": ["activation_schema_or_gate_unreadable"],
            "real_accessed": False,
        }

    blockers.extend(_static_blockers(raw, schema, gate_raw))
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        value = {}
    if value.get("accepted_gate_head_sha") != ACCEPTED_GATE_HEAD_SHA:
        blockers.append("accepted_gate_identity_mismatch")
    if (
        value.get("hermetic_ci_head_sha") != ACCEPTED_GATE_HEAD_SHA
        or value.get("hermetic_ci_run_id") != HERMETIC_CI_RUN_ID
    ):
        blockers.append("hermetic_ci_identity_mismatch")
    if not clean_checkout(root):
        blockers.append("dirty_checkout")
    committed = blob(root, producing_commit, ACTIVATION) if producing_commit else None
    if committed != raw:
        blockers.append("activation_blob_mismatch")
    if activation_ok(root, producing_commit) is None:
        blockers.append("accepted_gate_ancestry_or_dependency_mismatch")

    preflight: dict[str, object] = {
        "ready": False,
        "outcome": "not_run",
        "real_accessed": False,
    }
    try:
        from scripts import run_l_4_breadth_b88r5_committed_bootstrap_v6 as bootstrap

        # This is deliberately the preflight only.  The production bootstrap
        # runner and scientific runner are never invoked by this validator.
        preflight = bootstrap.preflight(root, producing_commit)
        if preflight.get("ready") is not True:
            blockers.append(f"bootstrap_preflight:{preflight.get('outcome', 'unknown')}")
        if preflight.get("real_accessed") is not False:
            blockers.append("preflight_real_access")
    except (ImportError, OSError, subprocess.CalledProcessError):
        blockers.append("bootstrap_preflight_unavailable")

    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "activation_sha256": _sha(raw),
        "producing_git_commit": producing_commit,
        "preflight_outcome": preflight.get("outcome"),
        "real_accessed": False,
    }


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass" else 1)
