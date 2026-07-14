from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.environment import interpreter_metadata
from lib.io import load_json, relative_to_root


DEFAULT_CONFIG = PROJECT_ROOT / "config" / "new_code_scripts.json"
FORBIDDEN_HELPER_DEFINITIONS = {
    "interpreter_metadata",
    "load_json",
    "load_jsonl",
    "render_markdown_report",
    "write_json",
    "write_jsonl",
    "write_report_pair",
    "write_search_log",
}


def _script_facts(path: Path) -> tuple[bool, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports_lib = False
    copied_helpers: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports_lib = imports_lib or any(
                alias.name == "lib" or alias.name.startswith("lib.") for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            imports_lib = imports_lib or node.module == "lib" or (node.module or "").startswith("lib.")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in FORBIDDEN_HELPER_DEFINITIONS:
            copied_helpers.append(node.name)
    return imports_lib, sorted(set(copied_helpers))


def audit_new_script_lib_usage(
    config_path: Path = DEFAULT_CONFIG,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    config = load_json(config_path)
    registered = set(config.get("scripts", []))
    grandfathered = set(config.get("grandfathered_scripts", []))
    tracked_scripts = {
        path.relative_to(project_root).as_posix()
        for path in (project_root / "scripts").glob("*.py")
        if path.is_file()
    }
    blockers: list[str] = []
    rows: list[dict[str, Any]] = []

    for relative in sorted(tracked_scripts - registered - grandfathered):
        blockers.append(f"unregistered_new_script:{relative}")
    for relative in sorted((registered | grandfathered) - tracked_scripts):
        blockers.append(f"registered_script_missing:{relative}")

    for relative in sorted(registered):
        path = project_root / relative
        if not path.is_file():
            continue
        try:
            imports_lib, copied_helpers = _script_facts(path)
        except SyntaxError as exc:
            blockers.append(f"script_syntax_error:{relative}:{exc.lineno}")
            continue
        if not imports_lib:
            blockers.append(f"blocked_no_lib_import:{relative}")
        if copied_helpers:
            blockers.append(f"copied_shared_helper:{relative}:{','.join(copied_helpers)}")
        rows.append(
            {
                "script_path": relative_to_root(path, project_root),
                "imports_lib": imports_lib,
                "copied_helpers": copied_helpers,
            }
        )

    return {
        "audit_id": "new_script_lib_usage",
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "registered_script_count": len(registered),
        "grandfathered_script_count": len(grandfathered),
        "rows": rows,
        "interpreter": interpreter_metadata(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit that post-B0.1 scripts use shared lib infrastructure.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    result = audit_new_script_lib_usage(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
