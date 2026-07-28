"""Single-source B8.6R3 report blocker matrix."""
from __future__ import annotations

READ_BLOCKERS = frozenset(("dataset_missing", "dataset_read_error"))
OVER_BLOCKER = "dataset_input_over_limit"
SCAN_BLOCKERS = frozenset(
    (
        "bounded_raw_bytes_required",
        "dataset_hash_mismatch",
        "structural_syntax",
        "unterminated_string",
        "invalid_numeric_lexeme",
        "unknown_or_duplicate_field",
        "trailing_bytes",
        "dataset_schema_mismatch",
        "symbol_order_mismatch",
        "symbol_schema_mismatch",
        "limitations_schema_mismatch",
        "invalid_calendar_session",
        "post_cutoff_session",
        "missing_or_ambiguous_u8_member",
        "record_schema_mismatch",
        "unsafe_value_not_opaque_scalar",
        "duplicate_symbol_session",
        "schema_mismatch",
    )
)
REACHABLE_BLOCKERS = READ_BLOCKERS | {OVER_BLOCKER} | SCAN_BLOCKERS


def category(blocker):
    if blocker in READ_BLOCKERS:
        return "unread"
    if blocker == OVER_BLOCKER:
        return "over"
    if blocker in SCAN_BLOCKERS:
        return "scanned"
    return None
