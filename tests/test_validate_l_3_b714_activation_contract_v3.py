from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import validate_l_3_b714_activation_contract_v3 as validator


class B713V3GateTests(unittest.TestCase):
    def test_committed_manifest_integrity_gate_passes(self) -> None:
        result = validator.validate()
        self.assertEqual("pass", result["status"], result["blockers"])

    def test_authorization_or_source_identity_drift_blocks(self) -> None:
        payload = json.loads(validator.GATE.read_text(encoding="utf-8"))
        payload["authorizations"]["execution"] = True
        payload["source_binding"]["b7_13_v2"]["manifest_identity"]["gate_id"] = "forged"
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "gate.json"
            candidate.write_text(json.dumps(payload), encoding="utf-8")
            with patch.object(validator, "GATE", candidate):
                result = validator.validate()
        self.assertEqual("blocked", result["status"])
        self.assertIn("authorizations", result["blockers"])
        self.assertIn("manifest_identity:b7_13_v2", result["blockers"])


if __name__ == "__main__":
    unittest.main()
