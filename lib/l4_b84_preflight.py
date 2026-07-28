"""Synthetic-only structural preflight primitives for the future L-4 falsification container."""
from __future__ import annotations

from datetime import date
import hashlib
import json
from typing import Any

U8 = ("VTI", "VGK", "EWJ", "VWO", "IEF", "TIP", "GLD", "DBC")
CUTOFF = date(2015, 12, 31)


def canonical_fixture_sha256(payload: Any) -> str | None:
    """Commit fixture controls without recursively hashing its gate provenance."""
    if not isinstance(payload, dict):
        return None
    controls = dict(payload)
    controls.pop("provenance", None)
    return hashlib.sha256(json.dumps(controls, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def structural_preflight(symbol_sessions: Any) -> list[str]:
    """Validate only synthetic date metadata; this function never opens a container or decodes returns."""
    if not isinstance(symbol_sessions, dict) or set(symbol_sessions) != set(U8):
        return ["membership_ambiguity"]
    blockers: list[str] = []
    for symbol in U8:
        sessions = symbol_sessions[symbol]
        if not isinstance(sessions, list) or not sessions:
            blockers.append(f"schema_or_path_ambiguity:{symbol}")
            continue
        for value in sessions:
            if not isinstance(value, str):
                blockers.append(f"timestamp_type_ambiguity:{symbol}")
                continue
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                blockers.append(f"timestamp_schema_ambiguity:{symbol}")
                continue
            if parsed > CUTOFF:
                blockers.append(f"post_falsification_session:{symbol}")
    return sorted(set(blockers))
