"""Versioned v6 scanner with the immutable v5 byte grammar."""
from __future__ import annotations

import hashlib
from lib.l4_b85r4_structural_scanner_v5 import CUTOFF, MAX_BYTES, MAX_SESSION_DATES_PER_SYMBOL, ScanError, U8, canonical_payload_capacity_bytes
from lib.l4_b85r4_structural_scanner_v5 import scan_manifest as _scan_manifest, scan_payload as _scan_payload

MANIFEST_SCHEMA = "lily_l4_b85r5_structural_manifest_v6"
PAYLOAD_SCHEMA = "lily_l4_b85r5_u8_symbol_session_dates_v6"


def scan_manifest(raw: bytes, *, expected_identity: str, expected_payload_path: str) -> dict:
    translated = raw.replace(MANIFEST_SCHEMA.encode("ascii"), b"lily_l4_b85r4_structural_manifest_v5", 1)
    result = _scan_manifest(translated, expected_identity=expected_identity, expected_payload_path=expected_payload_path)
    result.update({"complete_raw_sha256": hashlib.sha256(raw).hexdigest(), "observed_byte_count": len(raw)})
    return result


def scan_payload(raw: bytes) -> dict:
    translated = raw.replace(PAYLOAD_SCHEMA.encode("ascii"), b"lily_l4_b85r4_u8_symbol_session_dates_v5", 1)
    result = _scan_payload(translated)
    result.update({"complete_raw_sha256": hashlib.sha256(raw).hexdigest(), "observed_byte_count": len(raw)})
    return result
