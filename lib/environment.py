from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MACHINE_CONFIG_PATH = PROJECT_ROOT / "config" / "machine.json"
CONFIGURED_PATH_NAMES = (
    "LILY_DATA_ROOT",
    "LILY_WIKI_ROOT",
    "LILY_IBKR_PYTHON",
    "LILY_WEBULL_PYTHON",
)


def machine_config(path: Path | None = None) -> dict[str, Any]:
    selected = path or MACHINE_CONFIG_PATH
    if not selected.exists():
        return {}
    payload = json.loads(selected.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("machine config must be a JSON object")
    variables = payload.get("environment_variables", {})
    if not isinstance(variables, dict):
        raise ValueError("machine config environment_variables must be a JSON object")
    return variables


def configured_path(name: str, *, config_path: Path | None = None) -> Path | None:
    if name not in CONFIGURED_PATH_NAMES:
        raise ValueError(f"unsupported configured path: {name}")
    raw = os.environ.get(name)
    if raw in (None, ""):
        raw = machine_config(config_path).get(name)
    if raw in (None, ""):
        return None
    return Path(os.path.expandvars(os.path.expanduser(str(raw)))).resolve()


def require_configured_path(name: str, *, config_path: Path | None = None) -> Path:
    resolved = configured_path(name, config_path=config_path)
    if resolved is None:
        raise ValueError(f"{name} is not configured")
    return resolved


def resolve_configured_path(value: str | Path, *, config_path: Path | None = None) -> Path:
    text = str(value)
    for name in CONFIGURED_PATH_NAMES:
        marker = "${" + name + "}"
        if text == marker:
            return require_configured_path(name, config_path=config_path)
        prefix = marker + "/"
        if text.startswith(prefix):
            root = require_configured_path(name, config_path=config_path)
            return root.joinpath(*Path(text[len(prefix) :]).parts)
    return Path(text)


def interpreter_metadata() -> dict[str, str]:
    return {
        "python_executable": Path(sys.executable).name,
        "python_implementation": sys.implementation.name,
        "python_version": platform.python_version(),
        "platform": platform.system().lower(),
    }


def environment_availability(*, config_path: Path | None = None) -> dict[str, bool]:
    return {name: configured_path(name, config_path=config_path) is not None for name in CONFIGURED_PATH_NAMES}
