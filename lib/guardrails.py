from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def append_missing_fields(
    record: Mapping[str, Any],
    required_fields: Iterable[str],
    blockers: list[str],
) -> None:
    for field in required_fields:
        if record.get(field) in (None, ""):
            blockers.append(f"missing_required_field:{field}")


def append_forbidden_true_fields(
    record: Mapping[str, Any],
    forbidden_fields: Iterable[str],
    blockers: list[str],
) -> None:
    for field in forbidden_fields:
        if record.get(field) is True:
            blockers.append(f"forbidden_guardrail_true:{field}")


def status_from_blockers(
    blockers: Iterable[str],
    *,
    passing_status: str = "pass",
    blocked_status: str = "blocked",
) -> str:
    return blocked_status if list(blockers) else passing_status
