from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_new_script_lib_usage import audit_new_script_lib_usage


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class NewScriptLibUsageAuditTests(unittest.TestCase):
    def test_current_registry_passes(self) -> None:
        result = audit_new_script_lib_usage()
        self.assertEqual("pass", result["status"], result["blockers"])
        self.assertEqual(45, result["registered_script_count"])
        self.assertEqual(2, result["grandfathered_script_count"])

    def test_unregistered_script_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            config_dir = root / "config"
            scripts.mkdir()
            config_dir.mkdir()
            (scripts / "new.py").write_text("from lib.io import load_json\n", encoding="utf-8")
            config = config_dir / "new_code_scripts.json"
            config.write_text(json.dumps(_config()), encoding="utf-8")
            result = audit_new_script_lib_usage(config, project_root=root)
        self.assertIn("unregistered_new_script:scripts/new.py", result["blockers"])

    def test_registered_script_without_lib_or_with_copied_helper_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / "scripts"
            config_dir = root / "config"
            scripts.mkdir()
            config_dir.mkdir()
            (scripts / "bad.py").write_text(
                "import json\n\ndef load_json(path):\n    return json.loads(path.read_text())\n",
                encoding="utf-8",
            )
            config = config_dir / "new_code_scripts.json"
            config.write_text(json.dumps(_config(scripts=["scripts/bad.py"])), encoding="utf-8")
            result = audit_new_script_lib_usage(config, project_root=root)
        self.assertIn("blocked_no_lib_import:scripts/bad.py", result["blockers"])
        self.assertIn("copied_shared_helper:scripts/bad.py:load_json", result["blockers"])


def _config(*, scripts: list[str] | None = None) -> dict[str, object]:
    return {
        "schema_version": "lily_new_code_scripts_v1",
        "enforcement_start_order": "B0.2",
        "grandfathered_scripts": [],
        "scripts": scripts or [],
    }


if __name__ == "__main__":
    unittest.main()
