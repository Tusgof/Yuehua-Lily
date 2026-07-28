from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from lib.l4_b85r2_structural_scanner_v3 import MAX_BYTES, ScanError, scan_manifest, scan_payload
from scripts.run_l_4_breadth_b85r2_phase_b_preflight_v3 import CONTAINER_IDENTITY, MANIFEST_RELATIVE, PAYLOAD_RELATIVE, preflight_from_raw, run_one_shot
from scripts.validate_l_4_breadth_b85r2_structural_preflight_report_v3 import MANIFEST, PAYLOAD, validate


class B85R2StructuralPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = MANIFEST.read_bytes()
        self.payload = PAYLOAD.read_bytes()

    def test_committed_synthetic_multiple_session_envelope_passes(self) -> None:
        report = preflight_from_raw(self.manifest, self.payload)
        self.assertEqual("structural_pass", report["outcome"])
        self.assertFalse(report["real_preflight_consumed"])
        self.assertEqual(24, report["payload"]["session_count"])
        self.assertEqual("pass", validate(report)["status"])

    def test_scanner_rejects_all_adversarial_session_forms_before_pass(self) -> None:
        cases = (
            self.payload + b"x",
            b"\xef\xbb\xbf" + self.payload,
            self.payload.replace(b'"symbol":"VTI"', b'"return":"VTI"', 1),
            self.payload.replace(b'"2015-12-29"', b'"2016-01-01"', 1),
            self.payload.replace(b'"2015-12-30"', b'"2016-01-01"', 1),
            self.payload.replace(b'"2015-12-31"', b'"2016-01-01"', 1),
            self.payload.replace(b'"2015-12-30"', b'"2015-12-31"', 1),
            self.payload.replace(b'"2015-12-29"', b'"2015-02-29"', 1),
            self.payload.replace(b'"symbol":"VGK"', b'"symbol":"VTI"', 1),
            self.payload.replace(b'"session_dates"', b'"values"', 1),
            self.payload + b" " * (MAX_BYTES + 1),
        )
        for raw in cases:
            with self.subTest(raw=raw[:32]):
                with self.assertRaises(ScanError):
                    scan_payload(raw)

    def test_manifest_hash_path_and_unknown_field_fail_closed(self) -> None:
        with self.assertRaises(ScanError):
            scan_manifest(self.manifest.replace(b"sealed/l4_b85r2", b"other/l4_b85r2"), expected_identity=CONTAINER_IDENTITY, expected_payload_path=PAYLOAD_RELATIVE.as_posix())
        forged = self.manifest.replace(hashlib.sha256(self.payload).hexdigest().encode("ascii"), b"0" * 64)
        self.assertEqual("preflight_blocked", preflight_from_raw(forged, self.payload)["outcome"])

    def test_injected_one_shot_helper_accepts_genuine_real_pass_and_rejects_second_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data-root"
            manifest_path, payload_path = root / MANIFEST_RELATIVE, root / PAYLOAD_RELATIVE
            manifest_path.parent.mkdir(parents=True)
            shutil.copyfile(MANIFEST, manifest_path)
            shutil.copyfile(PAYLOAD, payload_path)
            report_path, marker_path = Path(temporary) / "report.json", Path(temporary) / "attempt.json"
            first = run_one_shot(root, report_path=report_path, attempt_marker_path=marker_path)
            self.assertTrue(first["real_preflight_consumed"])
            self.assertEqual("pass", validate(first, attempt_marker_path=marker_path)["status"])
            second = run_one_shot(root, report_path=report_path, attempt_marker_path=marker_path)
            self.assertEqual("attempt_already_consumed", second["blocker"])
            self.assertEqual("blocked", validate(second, attempt_marker_path=marker_path)["status"])

    def test_missing_temp_root_consumes_and_persists_fail_closed_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_path, marker_path = Path(temporary) / "report.json", Path(temporary) / "attempt.json"
            report = run_one_shot(Path(temporary) / "missing-root", report_path=report_path, attempt_marker_path=marker_path)
            self.assertTrue(report["real_preflight_consumed"])
            self.assertEqual("preflight_blocked", report["outcome"])
            self.assertTrue(report_path.exists() and marker_path.exists())
            self.assertEqual("pass", validate(report, attempt_marker_path=marker_path)["status"])

    def test_report_validator_rejects_forged_real_state_and_invalid_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "data-root"
            manifest_path, payload_path = root / MANIFEST_RELATIVE, root / PAYLOAD_RELATIVE
            manifest_path.parent.mkdir(parents=True)
            shutil.copyfile(MANIFEST, manifest_path)
            shutil.copyfile(PAYLOAD, payload_path)
            marker_path = Path(temporary) / "attempt.json"
            report = run_one_shot(root, report_path=Path(temporary) / "report.json", attempt_marker_path=marker_path)
            forged = deepcopy(report)
            forged["payload"]["session_dates_by_symbol"]["VTI"][0] = "2015-02-29"
            self.assertEqual("blocked", validate(forged, attempt_marker_path=marker_path)["status"])
            forged = deepcopy(report)
            forged["real_preflight_consumed"] = False
            self.assertEqual("blocked", validate(forged, attempt_marker_path=marker_path)["status"])

    def test_phase_a_tests_never_call_production_environment_resolution(self) -> None:
        with patch("scripts.run_l_4_breadth_b85r2_phase_b_preflight_v3.require_configured_path", side_effect=AssertionError("no real config")):
            report = preflight_from_raw(self.manifest, self.payload)
        self.assertEqual("synthetic_fixture", report["mode"])


if __name__ == "__main__":
    unittest.main()
