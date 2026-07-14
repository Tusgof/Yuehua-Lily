from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACKER = PROJECT_ROOT / "experiments" / "bootstrap_tracker.json"
VALID_STATUSES = {"not_started", "in_progress", "done", "blocked"}
SUPPORTED_PYTHON_LINE = (3, 14)
TEXT_SUFFIXES = {
    "",
    ".css",
    ".env",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_PARTS = {".git", ".venv", "Backup_", "__pycache__", "venv"}
WINDOWS_ABSOLUTE_PATH = re.compile(r"(?i)(?<![A-Za-z0-9])[A-Z]:[\\/]")
FILE_URI = re.compile("(?i)" + "file" + "://")
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
HIGH_RISK_VALUE_PATTERN = re.compile(
    r"(?i)\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b|\bAKIA[0-9A-Z]{16}\b"
)
SENSITIVE_ASSIGNMENT = re.compile(
    r'''(?im)^\s*["']?([A-Z0-9_]*(?:API_KEY|APP_KEY|SECRET|TOKEN|PASSWORD|ACCOUNT_ID)[A-Z0-9_]*)["']?\s*[:=]\s*["']?([^"'# ,\s]+)'''
)
PLACEHOLDER_VALUES = {"", "null", "none", "placeholder", "changeme", "example", "not_set"}


def validate_tracker(
    path: Path = DEFAULT_TRACKER,
    *,
    project_root: Path = PROJECT_ROOT,
    verify_runtime: bool = False,
) -> dict[str, Any]:
    blockers: list[str] = []
    checked: list[dict[str, str]] = []
    unverified: list[dict[str, str]] = []
    payload = _load_tracker(path, blockers)
    if payload is None:
        return _result("fail", path, blockers, checked, unverified)

    orders = payload.get("orders")
    if not isinstance(orders, list):
        blockers.append("orders_must_be_list")
        return _result("fail", path, blockers, checked, unverified)

    seen: set[str] = set()
    statuses: dict[str, str] = {}
    for index, order in enumerate(orders):
        if not isinstance(order, dict):
            blockers.append(f"order_{index}_must_be_object")
            continue
        order_id = order.get("id")
        if not isinstance(order_id, str) or not order_id:
            blockers.append(f"order_{index}_missing_id")
            continue
        if order_id in seen:
            blockers.append(f"duplicate_order_id:{order_id}")
        seen.add(order_id)
        status = order.get("status")
        if status not in VALID_STATUSES:
            blockers.append(f"{order_id}:invalid_status:{status}")
        else:
            statuses[order_id] = status
        required = order.get("required_artifacts")
        if not isinstance(required, list) or not required:
            blockers.append(f"{order_id}:required_artifacts_must_be_nonempty_list")
        else:
            for artifact in required:
                if not isinstance(artifact, dict):
                    blockers.append(f"{order_id}:artifact_must_be_object")
                    continue
                if not isinstance(artifact.get("path"), str) or not artifact["path"]:
                    blockers.append(f"{order_id}:artifact_missing_path")
                if not isinstance(artifact.get("must"), str) or not artifact["must"]:
                    blockers.append(f"{order_id}:artifact_missing_must")
        dependencies = order.get("depends_on")
        if not isinstance(dependencies, list) or any(not isinstance(item, str) for item in dependencies):
            blockers.append(f"{order_id}:depends_on_must_be_string_list")
        forbidden = order.get("forbidden")
        if not isinstance(forbidden, list) or not forbidden:
            blockers.append(f"{order_id}:forbidden_must_be_nonempty_list")
        evidence = order.get("evidence")
        if not isinstance(evidence, list):
            blockers.append(f"{order_id}:evidence_must_be_list")
        elif status == "done" and not evidence:
            blockers.append(f"{order_id}:done_requires_evidence")

    runtime_cache: dict[str, bool] = {}
    for order in orders:
        if not isinstance(order, dict) or not isinstance(order.get("id"), str):
            continue
        order_id = order["id"]
        dependencies = order.get("depends_on", [])
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if dependency not in seen:
                    blockers.append(f"{order_id}:unknown_dependency:{dependency}")
                elif order.get("status") == "done" and statuses.get(dependency) != "done":
                    blockers.append(f"{order_id}:done_dependency_not_done:{dependency}")
        if order.get("status") != "done":
            continue
        for artifact in order.get("required_artifacts", []):
            if not isinstance(artifact, dict):
                continue
            artifact_path = str(artifact.get("path", ""))
            must = str(artifact.get("must", ""))
            artifact_blockers, was_checked, was_unverified = _validate_done_artifact(
                order_id,
                artifact_path,
                must,
                project_root=project_root,
                verify_runtime=verify_runtime,
                runtime_cache=runtime_cache,
            )
            blockers.extend(artifact_blockers)
            entry = {"order": order_id, "path": artifact_path, "must": must}
            if was_checked:
                checked.append(entry)
            if was_unverified:
                unverified.append(entry | {"reason": "runtime_checks_disabled"})

    return _result("fail" if blockers else "pass", path, blockers, checked, unverified)


def _load_tracker(path: Path, blockers: list[str]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        blockers.append(f"tracker_missing:{path}")
        return None
    except json.JSONDecodeError as exc:
        blockers.append(f"tracker_invalid_json:{exc}")
        return None
    if not isinstance(payload, dict):
        blockers.append("tracker_must_be_object")
        return None
    if payload.get("schema_version") != "lily_bootstrap_tracker_v1":
        blockers.append(f"invalid_schema_version:{payload.get('schema_version')}")
    if not isinstance(payload.get("done_claim_rule"), str) or not payload["done_claim_rule"].strip():
        blockers.append("done_claim_rule_missing")
    return payload


def _validate_done_artifact(
    order_id: str,
    artifact_path: str,
    must: str,
    *,
    project_root: Path,
    verify_runtime: bool,
    runtime_cache: dict[str, bool],
) -> tuple[list[str], bool, bool]:
    target = (project_root / artifact_path).resolve()
    if must == "exist":
        exists = target.exists()
        return ([] if exists else [f"{order_id}:missing_artifact:{artifact_path}"], exists, False)
    if must == "pass":
        if not target.is_file():
            return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
        if target == Path(__file__).resolve():
            return [], True, False
        if not verify_runtime:
            return [], False, True
        completed = subprocess.run(
            [sys.executable, str(target)],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        return (
            [] if completed.returncode == 0 else [f"{order_id}:artifact_command_failed:{artifact_path}"],
            completed.returncode == 0,
            False,
        )
    if must in {"pass_in_hermetic_tier", "pass_hermetic_tier"}:
        if not target.exists():
            return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
        if not verify_runtime:
            return [], False, True
        passed = _run_hermetic_once(project_root, runtime_cache)
        return ([] if passed else [f"{order_id}:hermetic_tier_failed"], passed, False)
    if must == "run_hermetic_on_push":
        return _validate_ci(target, order_id, artifact_path)
    if must == "pin_supported_python":
        return _validate_python_pin(target, order_id, artifact_path)
    if must == "declare_python_and_dependencies":
        return _validate_pyproject(target, project_root, order_id, artifact_path)
    if must == "contain_placeholders_only":
        return _validate_machine_example(target, order_id, artifact_path)
    if must == "contain_environment_io_timestamp_provenance_guardrail_report_search_modules":
        return _validate_lib_skeleton(target, order_id, artifact_path)
    if must == "contain_hermetic_lib_unit_tests":
        return _validate_lib_tests(target, order_id, artifact_path)
    if must == "document_conventions_and_exist":
        return _validate_statistics_kernel(target, order_id, artifact_path)
    if must == "cite_published_anchors_and_independent_bets":
        return _validate_statistics_conventions(target, order_id, artifact_path)
    if must == "pin_lf_for_hash_bound_artifacts":
        return _validate_lf_attributes(target, order_id, artifact_path)
    if must == "contain_registry_tier_and_locked_gate_tests":
        return _validate_governance_tests(target, order_id, artifact_path)
    if must == "require_adversarial_review_for_E2":
        return _validate_evidence_policy(target, order_id, artifact_path)
    if must == "no_active_absolute_paths_or_credentials_excluding_immutable_backup_history":
        blockers = _scan_active_artifacts(project_root)
        return ([f"{order_id}:{item}" for item in blockers], not blockers, False)
    return [f"{order_id}:unsupported_done_rule:{must}"], False, False


def _run_hermetic_once(project_root: Path, cache: dict[str, bool]) -> bool:
    if "hermetic" not in cache:
        completed = subprocess.run(
            [sys.executable, "scripts/run_test_tier.py", "hermetic", "--verbosity", "0"],
            cwd=project_root,
            text=True,
            capture_output=True,
            check=False,
        )
        cache["hermetic"] = completed.returncode == 0
    return cache["hermetic"]


def _validate_ci(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = ("push:", "pull_request:", "actions/checkout@", "actions/setup-python@", "python scripts/run_test_tier.py hermetic")
    missing = [item for item in required if item not in text]
    return ([f"{order_id}:ci_missing:{item}" for item in missing], not missing, False)


def _validate_python_pin(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    value = target.read_text(encoding="utf-8").strip()
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        return [f"{order_id}:python_version_not_exact:{value}"], False, False
    if tuple(map(int, match.groups()[:2])) != SUPPORTED_PYTHON_LINE:
        return [f"{order_id}:unsupported_python_line:{value}"], False, False
    return [], True, False


def _validate_pyproject(
    target: Path,
    project_root: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = tomllib.loads(target.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return [f"{order_id}:invalid_pyproject:{exc}"], False, False
    project = payload.get("project", {})
    lily = payload.get("tool", {}).get("lily", {})
    blockers: list[str] = []
    if project.get("requires-python") != ">=3.14,<3.15":
        blockers.append(f"{order_id}:pyproject_python_range_not_pinned")
    if project.get("dependencies") != []:
        blockers.append(f"{order_id}:dependencies_must_be_explicit_list")
    pin_path = project_root / ".python-version"
    pin = pin_path.read_text(encoding="utf-8").strip() if pin_path.exists() else None
    if lily.get("python-version") != pin:
        blockers.append(f"{order_id}:pyproject_python_pin_mismatch")
    return blockers, not blockers, False


def _validate_machine_example(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{order_id}:invalid_machine_example:{exc}"], False, False
    expected = {"LILY_DATA_ROOT", "LILY_WIKI_ROOT", "LILY_IBKR_PYTHON", "LILY_WEBULL_PYTHON"}
    variables = payload.get("environment_variables")
    blockers: list[str] = []
    if not isinstance(variables, dict) or set(variables) != expected:
        blockers.append(f"{order_id}:machine_example_variable_set_mismatch")
    elif any(value is not None for value in variables.values()):
        blockers.append(f"{order_id}:machine_example_contains_non_placeholder_value")
    if set(payload) != {"schema_version", "environment_variables"}:
        blockers.append(f"{order_id}:machine_example_contains_extra_fields")
    return blockers, not blockers, False


def _validate_lib_skeleton(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    required = {
        "__init__.py",
        "environment.py",
        "guardrails.py",
        "io.py",
        "provenance.py",
        "report.py",
        "search_log.py",
        "timestamps.py",
    }
    if not target.is_dir():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    missing = sorted(name for name in required if not (target / name).is_file())
    blockers = [f"{order_id}:lib_module_missing:{name}" for name in missing]
    return blockers, not blockers, False


def _validate_lib_tests(target: Path, order_id: str, artifact_path: str) -> tuple[list[str], bool, bool]:
    required = {"test_lib_foundation.py", "test_audit_new_script_lib_usage.py"}
    if not target.is_dir():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    missing = sorted(name for name in required if not (target / name).is_file())
    blockers = [f"{order_id}:lib_test_missing:{name}" for name in missing]
    return blockers, not blockers, False


def _validate_statistics_kernel(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = (
        "raw Pearson kurtosis",
        "finite-sample Bartlett",
        "def probabilistic_sharpe_ratio",
        "def minimum_track_record_length_falsify",
        "def minimum_track_record_length_validate",
        "def deflated_sharpe_ratio",
        "def newey_west_variance_of_mean",
        "def independent_bet_equivalent_count",
    )
    missing = [item for item in required if item not in text]
    blockers = [f"{order_id}:statistics_kernel_missing:{item}" for item in missing]
    return blockers, not blockers, False


def _validate_statistics_conventions(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = (
        "Published-method anchor",
        "Offline library cross-check",
        "independent-bet",
        "Wiki-relative source",
        "SHA-256",
        "probabilistic-sharpe-ratio.md",
        "deflated-sharpe-ratio.md",
        "newey-west-validation.md",
    )
    blockers = [
        f"{order_id}:statistics_conventions_missing:{item}"
        for item in required
        if item not in text
    ]
    if len(re.findall(r"\b[0-9a-f]{64}\b", text)) < 3:
        blockers.append(f"{order_id}:statistics_conventions_require_source_hashes")
    return blockers, not blockers, False


def _validate_lf_attributes(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    lines = set(target.read_text(encoding="utf-8").splitlines())
    required = {"*.json text eol=lf", "*.jsonl text eol=lf", "*.md text eol=lf", "*.py text eol=lf"}
    missing = sorted(required - lines)
    blockers = [f"{order_id}:gitattributes_missing:{line}" for line in missing]
    return blockers, not blockers, False


def _validate_governance_tests(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_dir():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    required = {
        "test_validate_hypothesis_registry.py",
        "test_validate_evidence_tiers.py",
        "test_validate_locked_gates.py",
    }
    missing = sorted(name for name in required if not (target / name).is_file())
    blockers = [f"{order_id}:governance_test_missing:{name}" for name in missing]
    return blockers, not blockers, False


def _validate_evidence_policy(
    target: Path,
    order_id: str,
    artifact_path: str,
) -> tuple[list[str], bool, bool]:
    if not target.is_file():
        return [f"{order_id}:missing_artifact:{artifact_path}"], False, False
    text = target.read_text(encoding="utf-8")
    required = (
        "Adversarial Review Before E2",
        "reviewer_is_independent: true",
        "unresolved_critical_issues",
        "append-only",
        "supersedes_gate_id",
    )
    blockers = [f"{order_id}:evidence_policy_missing:{item}" for item in required if item not in text]
    return blockers, not blockers, False


def _scan_active_artifacts(project_root: Path) -> list[str]:
    blockers: list[str] = []
    for path in _candidate_files(project_root):
        relative = path.relative_to(project_root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if WINDOWS_ABSOLUTE_PATH.search(text) or FILE_URI.search(text):
            blockers.append(f"forbidden_absolute_path:{relative}")
        if PRIVATE_KEY.search(text) or HIGH_RISK_VALUE_PATTERN.search(text):
            blockers.append(f"credential_like_value:{relative}")
            continue
        for match in SENSITIVE_ASSIGNMENT.finditer(text):
            value = match.group(2).strip().lower()
            if value not in PLACEHOLDER_VALUES and not value.startswith("${"):
                blockers.append(f"credential_like_assignment:{relative}:{match.group(1)}")
                break
    return sorted(set(blockers))


def _candidate_files(project_root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        paths = [project_root / line for line in completed.stdout.splitlines() if line.strip()]
    else:
        paths = [path for path in project_root.rglob("*") if path.is_file()]
    result: list[Path] = []
    for path in paths:
        try:
            relative_parts = path.relative_to(project_root).parts
        except ValueError:
            continue
        if any(part in EXCLUDED_PARTS for part in relative_parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {".gitignore", ".python-version"}:
            result.append(path)
    return sorted(set(result))


def _result(
    status: str,
    path: Path,
    blockers: list[str],
    checked: list[dict[str, str]],
    unverified: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "status": status,
        "tracker_path": str(path),
        "blockers": blockers,
        "done_artifacts_checked": checked,
        "unverified": unverified,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Lily's bootstrap tracker and all done claims.")
    parser.add_argument("--tracker", type=Path, default=DEFAULT_TRACKER)
    parser.add_argument(
        "--no-runtime-checks",
        action="store_true",
        help="Validate structure and static artifacts without running artifact commands.",
    )
    args = parser.parse_args()
    result = validate_tracker(args.tracker, verify_runtime=not args.no_runtime_checks)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
