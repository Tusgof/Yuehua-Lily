from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from lib.environment import PROJECT_ROOT, interpreter_metadata


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def git_commit(project_root: Path = PROJECT_ROOT) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and len(value) == 40 else "unavailable"


def provenance_metadata(project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    return {
        "git_commit": git_commit(project_root),
        "interpreter": interpreter_metadata(),
    }
