"""Hermetic tests for the B8.8R5AR-X incident contract."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import validate_l_4_breadth_b88r5arx_incident_v1 as incident


ROOT = Path(__file__).resolve().parents[1]


def _copy_fixture_root() -> Path:
    temporary = Path(tempfile.mkdtemp())
    for relative in (
        incident.MARKER,
        incident.ACTIVATION,
        incident.DEFAULT_REPORT,
        "schemas/l_4_breadth_b88r5arx_incident_v1.schema.json",
    ):
        source = ROOT / relative
        target = temporary / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return temporary


class B88R5ARXIncidentTests(unittest.TestCase):
    def test_committed_incident_report_passes(self) -> None:
        result = incident.validate()
        self.assertEqual("pass", result["status"], result)
        self.assertEqual(0, result["validation_access_count"])
        self.assertEqual(0, result["container_return_access"]["lower_bound"])
        self.assertEqual(1, result["container_return_access"]["upper_bound"])

    def test_marker_binding_is_exact(self) -> None:
        temporary = _copy_fixture_root()
        try:
            marker = temporary / incident.MARKER
            marker.write_text(marker.read_text(encoding="ascii").replace("lily_l4_b88r5_marker_v6", "forged"), encoding="ascii")
            result = incident.validate(temporary / incident.DEFAULT_REPORT, project_root=temporary)
        finally:
            shutil.rmtree(temporary)
        self.assertEqual("blocked", result["status"])
        self.assertIn("marker_sha256_mismatch", result["blockers"])

    def test_false_unknown_bound_claim_is_rejected(self) -> None:
        temporary = _copy_fixture_root()
        try:
            report = temporary / incident.DEFAULT_REPORT
            value = json.loads(report.read_text(encoding="ascii"))
            value["access_bounds"]["container_return_access"]["upper_bound"] = 0
            report.write_text(json.dumps(value), encoding="ascii")
            result = incident.validate(report, project_root=temporary)
        finally:
            shutil.rmtree(temporary)
        self.assertEqual("blocked", result["status"])
        self.assertTrue(result["blockers"][0].startswith("report_or_schema_invalid"))

    def test_absent_scientific_output_is_required(self) -> None:
        temporary = _copy_fixture_root()
        try:
            output = temporary / "reports/experiments/l_4_breadth_b88r5_scientific_report_v6.json"
            output.write_text("{}", encoding="ascii")
            result = incident.validate(temporary / incident.DEFAULT_REPORT, project_root=temporary)
        finally:
            shutil.rmtree(temporary)
        self.assertEqual("blocked", result["status"])
        self.assertIn(
            "unexpected_artifact_present:reports/experiments/l_4_breadth_b88r5_scientific_report_v6.json",
            result["blockers"],
        )

    def test_container_and_structural_paths_are_never_touched(self) -> None:
        forbidden = (
            "data/normalized/l1_yahoo_daily_v1.json",
            "experiments/provisioned/l_4_breadth_b86r13_falsification_manifest_v15.json",
            "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json",
        )
        original_read_bytes = Path.read_bytes
        original_exists = Path.exists

        def guarded_read_bytes(path: Path) -> bytes:
            if any(item in path.as_posix() for item in forbidden):
                raise AssertionError(f"forbidden path read: {path}")
            return original_read_bytes(path)

        def guarded_exists(path: Path) -> bool:
            if any(item in path.as_posix() for item in forbidden):
                raise AssertionError(f"forbidden path stat: {path}")
            return original_exists(path)

        with patch.object(Path, "read_bytes", guarded_read_bytes), patch.object(Path, "exists", guarded_exists):
            result = incident.validate()
        self.assertEqual("pass", result["status"], result)


if __name__ == "__main__":
    unittest.main()
