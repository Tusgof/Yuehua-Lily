from __future__ import annotations

import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class HermeticContractTests(unittest.TestCase):
    def test_committed_smoke_fixture_requires_no_external_state(self) -> None:
        path = PROJECT_ROOT / "tests" / "fixtures" / "hermetic" / "smoke.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("lily_hermetic_fixture_v1", payload["schema_version"])
        self.assertFalse(payload["uses_external_state"])

    def test_machine_specific_config_is_not_tracked(self) -> None:
        ignore_text = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("config/machine.json", ignore_text.splitlines())
        self.assertFalse((PROJECT_ROOT / "config" / "machine.json").exists())


if __name__ == "__main__":
    unittest.main()
