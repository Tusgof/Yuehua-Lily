from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from lib.io import write_jsonl


def write_search_log(path: Path, records: Iterable[Mapping[str, Any]]) -> int:
    return write_jsonl(path, (dict(record) for record in records))


def append_search_log(path: Path, records: Iterable[Mapping[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count
