from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_jsonl, relative_to_root
from lib.provenance import file_sha256


DEFAULT_MANIFEST = PROJECT_ROOT / "experiments" / "locked_gates.jsonl"
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_FIELDS = {
    "gate_id",
    "gate_type",
    "artifact_path",
    "artifact_sha256",
    "validator_path",
    "validator_sha256",
    "locked_at",
    "locked_by",
    "human_approval",
}


def validate_locked_gates(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    committed_lines: list[str] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    checked: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        return _result(manifest_path, ["locked_gate_manifest_missing"], checked, 0)

    current_lines = [line for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    baseline = _committed_manifest_lines(manifest_path) if committed_lines is None else committed_lines
    if current_lines[: len(baseline)] != baseline:
        blockers.append("locked_gate_manifest_is_not_append_only")
    try:
        entries = load_jsonl(manifest_path)
    except ValueError:
        return _result(manifest_path, blockers + ["locked_gate_manifest_invalid_jsonl"], checked, 0)

    entries_by_id: dict[str, dict[str, Any]] = {}
    superseded_by: dict[str, str] = {}
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            blockers.append(f"entry_{index}_must_be_object")
            continue
        gate_id = str(entry.get("gate_id", f"entry_{index}"))
        missing = sorted(field for field in REQUIRED_FIELDS if entry.get(field) in (None, ""))
        blockers.extend(f"{gate_id}:missing_required_field:{field}" for field in missing)
        if gate_id in entries_by_id:
            blockers.append(f"duplicate_gate_id:{gate_id}")

        for path_field in ("artifact_path", "validator_path"):
            if not _safe_relative_path(entry.get(path_field)):
                blockers.append(f"{gate_id}:{path_field}_must_be_safe_relative_path")
        for hash_field in ("artifact_sha256", "validator_sha256"):
            if not HASH_PATTERN.fullmatch(str(entry.get(hash_field, ""))):
                blockers.append(f"{gate_id}:{hash_field}_must_be_sha256")

        predecessor_id = entry.get("supersedes_gate_id")
        if predecessor_id is not None:
            predecessor = entries_by_id.get(str(predecessor_id))
            if predecessor is None:
                blockers.append(f"{gate_id}:supersedes_gate_must_be_prior:{predecessor_id}")
            else:
                if str(predecessor_id) in superseded_by:
                    blockers.append(f"{gate_id}:predecessor_already_superseded:{predecessor_id}")
                if not isinstance(entry.get("reviewed_by"), str) or not entry["reviewed_by"].strip():
                    blockers.append(f"{gate_id}:supersession_requires_reviewer_identity")
                paths_changed = any(
                    entry.get(field) != predecessor.get(field)
                    for field in ("artifact_path", "validator_path")
                )
                if paths_changed:
                    predecessor_artifact_status = _hash_status(
                        predecessor.get("artifact_path"), predecessor.get("artifact_sha256")
                    )
                    predecessor_validator_status = _hash_status(
                        predecessor.get("validator_path"), predecessor.get("validator_sha256")
                    )
                    if predecessor_artifact_status != "pass":
                        blockers.append(
                            f"{gate_id}:immutable_predecessor_artifact_{predecessor_artifact_status}"
                        )
                    if predecessor_validator_status != "pass":
                        blockers.append(
                            f"{gate_id}:immutable_predecessor_validator_{predecessor_validator_status}"
                        )
                hashes_changed = any(
                    entry.get(field) != predecessor.get(field)
                    for field in ("artifact_sha256", "validator_sha256")
                )
                if not hashes_changed:
                    blockers.append(f"{gate_id}:supersession_requires_replacement_hash")
                superseded_by[str(predecessor_id)] = gate_id
        entries_by_id[gate_id] = entry

    for gate_id, entry in entries_by_id.items():
        if gate_id in superseded_by:
            checked.append({"gate_id": gate_id, "status": "superseded", "superseded_by": superseded_by[gate_id]})
            continue
        artifact_status = _hash_status(entry.get("artifact_path"), entry.get("artifact_sha256"))
        validator_status = _hash_status(entry.get("validator_path"), entry.get("validator_sha256"))
        if artifact_status != "pass":
            blockers.append(f"{gate_id}:artifact_{artifact_status}")
        if validator_status != "pass":
            blockers.append(f"{gate_id}:validator_{validator_status}")
        checked.append(
            {
                "gate_id": gate_id,
                "status": "active",
                "artifact_status": artifact_status,
                "validator_status": validator_status,
            }
        )
    return _result(manifest_path, blockers, checked, len(entries))


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def _hash_status(relative_path: Any, expected_hash: Any) -> str:
    if not _safe_relative_path(relative_path):
        return "invalid_path"
    path = PROJECT_ROOT / str(relative_path)
    if not path.is_file():
        return "missing"
    return "pass" if file_sha256(path) == expected_hash else "hash_mismatch"


def _committed_manifest_lines(manifest_path: Path) -> list[str]:
    try:
        relative = manifest_path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return []
    changed = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", relative],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    ).returncode != 0
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    ).returncode == 0
    revision = "HEAD" if changed or not tracked else "HEAD^"
    completed = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line.strip()]


def _result(
    manifest_path: Path,
    blockers: list[str],
    checked: list[dict[str, Any]],
    entry_count: int,
) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "manifest_path": relative_to_root(manifest_path, PROJECT_ROOT),
        "entry_count": entry_count,
        "checked": checked,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Lily's append-only hash-bound gate manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    result = validate_locked_gates(args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
