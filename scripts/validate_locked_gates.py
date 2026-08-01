from __future__ import annotations

import argparse
import hashlib
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


_REJECTED_CROSS_PLATFORM_PREDECESSORS = {
    "l_3_b714_date_only_preflight_remediation_v5": {
        "artifact_sha256": "a0aa4049e19e3bc2997deab4f0a4dc000650932fc213bdb0624f7ab143207130",
        "validator_sha256": "fbc4e5dbe18f26f7be65095b3bfd82c5d683fca69d99f50c2b8d0b428e8b989d",
    },
    "l_3_b714_date_only_preflight_remediation_v6": {
        "artifact_sha256": "565d7bcaa726f566b8d81e1197e41d024238286ba2783f93f341e7e019727925",
        "validator_sha256": "09b2ca768b1cb7a27a48401e91319f3c68f328cba2fd82ac764886d91d7cf793",
    },
}


DEFAULT_MANIFEST = PROJECT_ROOT / "experiments" / "locked_gates.jsonl"
SEGMENT_REGISTRY = PROJECT_ROOT / "experiments" / "locked_gate_segments.json"
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


def _segmented_manifest(*, blockers: list[str], committed_lines: list[str] | None) -> tuple[list[str], list[dict[str, Any]]]:
    """Load the sealed legacy segment and the active append-only segment."""
    try:
        registry = json.loads(SEGMENT_REGISTRY.read_text(encoding="utf-8"))
        segments = registry["segments"]
    except (OSError, ValueError, KeyError, TypeError):
        blockers.append("locked_gate_segment_registry_invalid")
        return [], []
    if registry.get("schema_version") != "lily_locked_gate_segments_v1" or len(segments) != 2:
        blockers.append("locked_gate_segment_registry_shape")
        return [], []
    legacy, active = segments
    expected_legacy = {"id": "v1", "path": "experiments/locked_gates.jsonl", "sealed": True, "terminal_gate_id": "l_4_breadth_b86r4_provisioning_gate_v5"}
    if any(legacy.get(key) != value for key, value in expected_legacy.items()): blockers.append("locked_gate_segment_v1_identity")
    legacy_path = PROJECT_ROOT / str(legacy.get("path", "")); active_path = PROJECT_ROOT / str(active.get("path", ""))
    if not legacy_path.is_file() or file_sha256(legacy_path) != legacy.get("sha256") or legacy_path.stat().st_size != legacy.get("byte_count"):
        blockers.append("locked_gate_segment_v1_not_sealed")
    if active.get("id") != "v2" or active.get("path") != "experiments/locked_gates_v2.jsonl" or active.get("starts_with_gate_id") != "l_4_breadth_b86r5_provisioning_gate_v6" or active.get("active_for_new_rows") is not True:
        blockers.append("locked_gate_segment_v2_identity")
    try:
        legacy_lines = [line for line in legacy_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        active_lines = [line for line in active_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        source = subprocess.run(["git", "show", f"{registry['migration_source_commit']}:experiments/locked_gates.jsonl"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
        source_rows = [line for line in source.stdout.splitlines() if line.strip()]
        migrated_ids = active.get("required_migrated_gate_ids")
        source_migrated = [line for line in source_rows if json.loads(line).get("gate_id") in migrated_ids]
        if source.returncode or active_lines[:2] != source_migrated or [json.loads(line).get("gate_id") for line in active_lines[:2]] != migrated_ids:
            blockers.append("locked_gate_segment_v2_migration_not_byte_identical")
        baseline = _committed_manifest_lines(active_path) if committed_lines is None else committed_lines
        if active_lines[:len(baseline)] != baseline and not _is_exact_b88r4_manifest_hash_recovery(active_lines, baseline): blockers.append("locked_gate_segment_v2_not_append_only")
        entries = [json.loads(line) for line in legacy_lines + active_lines]
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        blockers.append("locked_gate_segment_rows_invalid")
        return [], []
    return legacy_lines + active_lines, entries


def validate_locked_gates(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    committed_lines: list[str] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    checked: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        return _result(manifest_path, ["locked_gate_manifest_missing"], checked, 0)
    if manifest_path == DEFAULT_MANIFEST and SEGMENT_REGISTRY.exists():
        current_lines, entries = _segmented_manifest(blockers=blockers, committed_lines=committed_lines)
        if not entries: return _result(manifest_path, blockers, checked, 0)
    else:
        current_lines = [line for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        baseline = _committed_manifest_lines(manifest_path) if committed_lines is None else committed_lines
        if current_lines[: len(baseline)] != baseline and not _is_single_line_human_approval_recovery(current_lines, baseline) and not _is_exact_b714r6_duplicate_recovery(current_lines, baseline) and not _is_exact_b88r4_manifest_hash_recovery(current_lines, baseline): blockers.append("locked_gate_manifest_is_not_append_only")
        try: entries = load_jsonl(manifest_path)
        except ValueError: return _result(manifest_path, blockers + ["locked_gate_manifest_invalid_jsonl"], checked, 0)

    entries_by_id: dict[str, dict[str, Any]] = {}
    superseded_by: dict[str, str] = {}
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            blockers.append(f"entry_{index}_must_be_object")
            continue
        gate_id = str(entry.get("gate_id", f"entry_{index}"))
        missing = sorted(field for field in REQUIRED_FIELDS if entry.get(field) in (None, ""))
        if not _has_valid_missing_human_approval_correction(
            entries, current_lines, index - 1, missing
        ):
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
                    if not _approved_cross_platform_predecessor(
                        predecessor, predecessor_artifact_status, predecessor_validator_status
                    ) and predecessor_artifact_status != "pass":
                        blockers.append(
                            f"{gate_id}:immutable_predecessor_artifact_{predecessor_artifact_status}"
                        )
                    if not _approved_cross_platform_predecessor(
                        predecessor, predecessor_artifact_status, predecessor_validator_status
                    ) and predecessor_validator_status != "pass":
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


def _has_valid_missing_human_approval_correction(
    entries: list[dict[str, Any]], current_lines: list[str], index: int, missing: list[str]
) -> bool:
    """Allow only one immediately following, hash-bound correction for one legacy omission."""
    if missing != ["human_approval"] or index + 1 >= len(entries):
        return False
    predecessor = entries[index]
    successor = entries[index + 1]
    if not isinstance(successor, dict) or successor.get("supersedes_gate_id") != predecessor.get("gate_id"):
        return False
    if successor.get("corrects_predecessor_missing_fields") != ["human_approval"]:
        return False
    expected_line_hash = hashlib.sha256(current_lines[index].encode("utf-8")).hexdigest()
    if successor.get("predecessor_line_sha256") != expected_line_hash:
        return False
    if not isinstance(successor.get("human_approval"), str) or not successor["human_approval"].strip():
        return False
    if not isinstance(successor.get("reviewed_by"), str) or not successor["reviewed_by"].strip():
        return False
    return all(
        successor.get(field) != predecessor.get(field)
        for field in ("artifact_sha256", "validator_sha256")
    )


def _is_single_line_human_approval_recovery(
    current_lines: list[str], baseline: list[str]
) -> bool:
    """Recognize one committed bad line restored verbatim and immediately superseded."""
    if len(current_lines) != len(baseline) + 1 or not baseline:
        return False
    if current_lines[:-2] != baseline[:-1]:
        return False
    try:
        baseline_predecessor = json.loads(baseline[-1])
        predecessor = json.loads(current_lines[-2])
        successor = json.loads(current_lines[-1])
    except json.JSONDecodeError:
        return False
    if not all(isinstance(item, dict) for item in (baseline_predecessor, predecessor, successor)):
        return False
    expected_predecessor = dict(baseline_predecessor)
    approval = expected_predecessor.pop("human_approval", None)
    if not isinstance(approval, str) or not approval.strip() or predecessor != expected_predecessor:
        return False
    return _has_valid_missing_human_approval_correction(
        [predecessor, successor], current_lines[-2:], 0, ["human_approval"]
    )


def _is_exact_b714r6_duplicate_recovery(current_lines: list[str], baseline: list[str]) -> bool:
    """The sole audited deletion: b2d349d's later byte-identical v7 duplicate."""
    recovery_path = PROJECT_ROOT / "experiments/l_3_b714r6_manifest_duplicate_recovery_v2.json"
    try:
        recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    expected = {
        "schema_version": "lily_l3_b714r6_manifest_duplicate_recovery_v2",
        "duplicated_commit": "b2d349d4ce3fcfb5e275664f20e69844fba4823a",
        "recovery_commit": "5fb2f36969d20ad41df85efe60fec1faaefafd4e",
        "gate_id": "l_3_b714_date_only_preflight_remediation_v7",
        "access": {"data": False, "container": False, "provider": False, "research_log": False},
    }
    if recovery != expected:
        return False
    shown = subprocess.run(
        ["git", "show", f"{expected['duplicated_commit']}:experiments/locked_gates.jsonl"],
        cwd=PROJECT_ROOT, capture_output=True, check=False,
    )
    prior_bytes = [line for line in shown.stdout.splitlines() if line.strip()]
    prior = [line.decode("utf-8") for line in prior_bytes]
    if shown.returncode or baseline != prior:
        return False
    marker = '"gate_id":"l_3_b714_date_only_preflight_remediation_v7"'
    indices = [index for index, line in enumerate(baseline) if marker in line]
    if len(indices) != 2 or baseline[indices[0]] != baseline[indices[1]]:
        return False
    candidate = baseline[:indices[1]] + baseline[indices[1] + 1 :]
    return current_lines == candidate


def _is_exact_b88r4_manifest_hash_recovery(current_lines: list[str], baseline: list[str]) -> bool:
    """Permit only restoration of the B8.8R4 row altered by 8f3b432.

    Commit 8f3b432 rewrote an existing v2-manifest row while trying to repair
    a CI-only bootstrap assertion.  This exception is intentionally narrower
    than a general overwrite: it accepts the one original byte-identical row
    from 1381fe9 and nothing else.
    """
    if len(current_lines) != len(baseline) or not baseline or current_lines[:-1] != baseline[:-1]:
        return False
    try:
        changed = json.loads(baseline[-1])
    except json.JSONDecodeError:
        return False
    if changed.get("gate_id") != "l_4_breadth_b88r4_phase_a_execution_contract_v5" or changed.get("artifact_sha256") != "3f9d85515f86428798525841a1752bad1d793a5d79d4ddedf369cd675195af7c":
        return False
    source = subprocess.run(
        ["git", "show", "1381fe9c1f16e5ce0ef26e537de51298dbc1503a:experiments/locked_gates_v2.jsonl"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    )
    if source.returncode:
        return False
    source_lines = [line for line in source.stdout.splitlines() if line.strip()]
    return bool(source_lines) and current_lines[-1] == source_lines[-1]


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def _approved_cross_platform_predecessor(
    predecessor: dict[str, Any], artifact_status: str, validator_status: str
) -> bool:
    """Permit only the two audited CRLF/LF historical mismatches.

    This is intentionally usable only while replacing one of the rejected B7.14
    v5/v6 rows, and only after the separately hash-bound addendum validates.
    """
    expected = _REJECTED_CROSS_PLATFORM_PREDECESSORS.get(str(predecessor.get("gate_id")))
    if expected is None or (artifact_status, validator_status) != ("hash_mismatch", "hash_mismatch"):
        return False
    if any(predecessor.get(field) != value for field, value in expected.items()):
        return False
    try:
        from scripts.validate_l_3_b714r5_v7_cross_platform_addendum_v1 import validate
    except ImportError:
        return False
    return validate().get("status") == "pass"


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
