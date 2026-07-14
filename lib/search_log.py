from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from lib.io import write_jsonl


def write_search_log(path: Path, records: Iterable[Mapping[str, Any]]) -> int:
    return write_jsonl(path, (dict(record) for record in records))
