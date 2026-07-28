"""Validate the sole B7.14R5 CRLF/LF predecessor exception."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.provenance import file_sha256
ADD = ROOT / "experiments/l_3_b714r5_v7_cross_platform_addendum_v1.json"
EXPECTED = (
    {
        "gate_id": "l_3_b714_date_only_preflight_remediation_v5",
        "commit": "d2a15b717d29f55ce9ee55847fb3db3787da94e2",
        "artifact_path": "experiments/l_3_b714_date_only_preflight_remediation_v5.json",
        "validator_path": "scripts/validate_l_3_b714_date_only_preflight_remediation_v5.py",
        "manifest_artifact_sha256": "a0aa4049e19e3bc2997deab4f0a4dc000650932fc213bdb0624f7ab143207130",
        "manifest_validator_sha256": "fbc4e5dbe18f26f7be65095b3bfd82c5d683fca69d99f50c2b8d0b428e8b989d",
        "authored_windows_artifact_sha256": "59f193fe78169d46dcf5f7e06f2f04eeb3adee7ce4ea8a9c38255a15e014a398",
        "authored_windows_validator_sha256": "d21967a1f4be6b862f562df2a5553e2754714b8a7f67d10d7a5d0f24df645314",
        "committed_lf_artifact_sha256": "a0aa4049e19e3bc2997deab4f0a4dc000650932fc213bdb0624f7ab143207130",
        "committed_lf_validator_sha256": "fbc4e5dbe18f26f7be65095b3bfd82c5d683fca69d99f50c2b8d0b428e8b989d",
    },
    {
        "gate_id": "l_3_b714_date_only_preflight_remediation_v6",
        "commit": "53bbf429bd9cb321827036464040957db86caad7",
        "artifact_path": "experiments/l_3_b714_date_only_preflight_remediation_v6.json",
        "validator_path": "scripts/validate_l_3_b714_date_only_preflight_remediation_v6.py",
        "manifest_artifact_sha256": "565d7bcaa726f566b8d81e1197e41d024238286ba2783f93f341e7e019727925",
        "manifest_validator_sha256": "09b2ca768b1cb7a27a48401e91319f3c68f328cba2fd82ac764886d91d7cf793",
        "authored_windows_artifact_sha256": "f2bb881f95dadae0b92aced5b749144a406c9c38c14d9ebba603e8f220addfd4",
        "authored_windows_validator_sha256": "b59038e397bb20dc5b1f1d88a1eb5f2745b15fb7470a13671772c25812d3aa2e",
        "committed_lf_artifact_sha256": "565d7bcaa726f566b8d81e1197e41d024238286ba2783f93f341e7e019727925",
        "committed_lf_validator_sha256": "09b2ca768b1cb7a27a48401e91319f3c68f328cba2fd82ac764886d91d7cf793",
    },
)
ACCESS = {"data": False, "container": False, "provider": False, "research_log": False}
FAILED_CI = {
    "commit": "d3555846fa647d699bcfed84b9b3526f1c6d35cf",
    "run_id": 30347332981,
    "url": "https://github.com/Tusgof/Yuehua-Lily/actions/runs/30347332981",
}


def _shown_bytes(commit: str, path: str) -> bytes | None:
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def validate() -> dict[str, object]:
    try:
        obj = json.loads(ADD.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    required = {"schema_version", "status", "affected_gates", "failed_ci", "access", "remediation"}
    blockers: list[str] = []
    # The shared provenance helper is deliberately used so this new validator
    # is covered by the post-B0 script-infrastructure audit.
    if not file_sha256(ADD):
        blockers.append("addendum_unreadable")
    if set(obj) != required or obj.get("schema_version") != "lily_l3_b714r5_v7_cross_platform_addendum_v1" or obj.get("status") != "rejected_predecessor_hash_encoding" or obj.get("access") != ACCESS or obj.get("failed_ci") != FAILED_CI or obj.get("remediation") != "v7 binds only audited committed LF blob identities for rejected v5/v6; no other hash mismatch is tolerated.":
        blockers.append("addendum_identity")
    if obj.get("affected_gates") != list(EXPECTED):
        blockers.append("affected_gates_identity")
    for expected in EXPECTED:
        commit = expected["commit"]
        manifest = subprocess.run(["git", "show", f"{commit}:experiments/locked_gates.jsonl"], cwd=ROOT, capture_output=True, text=True, check=False)
        try:
            row = next(json.loads(line) for line in manifest.stdout.splitlines() if json.loads(line).get("gate_id") == expected["gate_id"])
        except (StopIteration, json.JSONDecodeError):
            blockers.append(f"manifest_row:{expected['gate_id']}")
            continue
        if any(row.get(key) != expected[key] for key in ("gate_id", "artifact_path", "validator_path", "manifest_artifact_sha256", "manifest_validator_sha256")):
            # Manifest uses the two non-prefixed field names.
            if row.get("artifact_sha256") != expected["manifest_artifact_sha256"] or row.get("validator_sha256") != expected["manifest_validator_sha256"]:
                blockers.append(f"manifest_hashes:{expected['gate_id']}")
        artifact = _shown_bytes(commit, expected["artifact_path"])
        validator = _shown_bytes(commit, expected["validator_path"])
        if artifact is None or hashlib.sha256(artifact).hexdigest() != expected["committed_lf_artifact_sha256"]:
            blockers.append(f"artifact_blob:{expected['gate_id']}")
        if validator is None or hashlib.sha256(validator).hexdigest() != expected["committed_lf_validator_sha256"]:
            blockers.append(f"validator_blob:{expected['gate_id']}")
        if artifact is None or hashlib.sha256(artifact.replace(b"\n", b"\r\n")).hexdigest() != expected["authored_windows_artifact_sha256"]:
            blockers.append(f"authored_windows_artifact:{expected['gate_id']}")
        if validator is None or hashlib.sha256(validator.replace(b"\n", b"\r\n")).hexdigest() != expected["authored_windows_validator_sha256"]:
            blockers.append(f"authored_windows_validator:{expected['gate_id']}")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
