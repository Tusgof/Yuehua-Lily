from __future__ import annotations

import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from lib.l4_b85_structural_scanner_v1 import ScanError, scan_manifest, scan_payload
from scripts.run_l_4_breadth_b85_phase_b_preflight_v1 import CONTAINER_IDENTITY, PAYLOAD_RELATIVE, preflight_from_raw, run_phase_b
from scripts.validate_l_4_breadth_b85_structural_preflight_report_v1 import MANIFEST, PAYLOAD, validate


class B85StructuralPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest, self.payload = MANIFEST.read_bytes(), PAYLOAD.read_bytes()

    def test_committed_synthetic_envelope_passes(self) -> None:
        report = preflight_from_raw(self.manifest, self.payload, mode="synthetic_fixture")
        self.assertEqual("structural_pass", report["outcome"])
        self.assertEqual("pass", validate(report, committed_synthetic=True)["status"])

    def test_scanner_rejects_ambiguity_unknowns_and_post_cutoff_before_decode(self) -> None:
        cases = (
            self.payload + b"x",
            b"\xef\xbb\xbf" + self.payload,
            self.payload.replace(b'"symbol":"VTI"', b'"return":"VTI"', 1),
            self.payload.replace(b'"session_date":"2015-12-31"', b'"session_date":"2016-01-01"', 1),
            self.payload.replace(b'"symbol":"VGK"', b'"symbol":"VTI"', 1),
            self.payload.replace(b'{"symbol":"VTI","session_date":"2015-12-31"}', b'{"symbol":"VTI","session_date":"2015-12-31","price":"1"}', 1),
        )
        for raw in cases:
            with self.subTest(raw=raw[:32]):
                with self.assertRaises(ScanError): scan_payload(raw)

    def test_manifest_hash_and_path_mismatch_fail_closed(self) -> None:
        with self.assertRaises(ScanError): scan_manifest(self.manifest.replace(b"sealed/l4_b85", b"other/l4_b85"), expected_identity=CONTAINER_IDENTITY, expected_payload_path=PAYLOAD_RELATIVE.as_posix())
        forged = self.manifest.replace(hashlib.sha256(self.payload).hexdigest().encode(), b"0" * 64)
        report = preflight_from_raw(forged, self.payload, mode="synthetic_fixture")
        self.assertEqual("preflight_blocked", report["outcome"])

    def test_real_runner_is_not_called_by_synthetic_tests(self) -> None:
        with patch("scripts.run_l_4_breadth_b85_phase_b_preflight_v1.require_configured_path", side_effect=AssertionError("no environment")):
            report = preflight_from_raw(self.manifest, self.payload, mode="synthetic_fixture")
        self.assertFalse(report["access_counters"]["real_preflight_consumed"])

    def test_real_runner_consumes_once_only_when_future_order_calls_it(self) -> None:
        with patch("scripts.run_l_4_breadth_b85_phase_b_preflight_v1.require_configured_path", side_effect=AssertionError("future-only")):
            with self.assertRaises(AssertionError): run_phase_b()


if __name__ == "__main__":
    unittest.main()
