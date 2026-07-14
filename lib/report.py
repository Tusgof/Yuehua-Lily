from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from lib.io import write_json
from lib.provenance import provenance_metadata


def render_markdown_report(title: str, sections: Iterable[tuple[str, str]]) -> str:
    lines = [f"# {title}", ""]
    for heading, body in sections:
        lines.extend([f"## {heading}", "", body.rstrip(), ""])
    return "\n".join(lines)


def write_report_pair(
    payload: dict[str, Any],
    json_path: Path,
    markdown_path: Path,
    markdown: str,
    *,
    project_root: Path,
) -> dict[str, Any]:
    stored = {**payload}
    stored.setdefault("provenance", provenance_metadata(project_root))
    write_json(json_path, stored)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown.rstrip() + "\n", encoding="utf-8", newline="\n")
    return stored
