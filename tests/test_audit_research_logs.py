from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_research_logs import audit_research_logs


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ResearchLogAuditTests(unittest.TestCase):
    def test_current_research_logs_pass(self) -> None:
        result = audit_research_logs()
        self.assertEqual("pass", result["status"], result["blockers"])
        self.assertEqual(2, len(result["logs"]))

    def test_existing_summary_requires_configured_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reports").mkdir()
            (root / "reports" / "summary.json").write_text("{}", encoding="utf-8")
            config = root / "requirements.json"
            config.write_text(
                json.dumps(
                    {
                        "schema_version": "lily_research_log_requirements_v1",
                        "entries": [
                            {
                                "experiment_id": "L-X",
                                "summary_path": "reports/summary.json",
                                "research_log_path": "research_log/001-lily-example.md",
                                "required_when_summary_exists": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = audit_research_logs(config, root / "research_log", project_root=root)
        self.assertIn("missing_required_research_log:L-X", result["blockers"])

    def test_vague_question_and_mojibake_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "research_log"
            logs.mkdir()
            log = logs / "001-lily-example.md"
            text = (PROJECT_ROOT / "research_log" / "001-lily-l0-sizing-feasibility.md").read_text(
                encoding="utf-8"
            )
            text = text.replace(
                "ภายใต้ทุน USD 1,000–2,000 และข้อจำกัดที่ล็อกไว้ เราสามารถสร้างพอร์ต ETF ที่กระจายอย่างน้อย 8 กลุ่ม หรือพอร์ต micro futures อย่างน้อย 4 ตลาดได้จริงหรือไม่",
                "ศึกษา trend",
            ).replace("ผลคำนวณบอกว่า", "เน€ผลคำนวณบอกว่า")
            log.write_text(text, encoding="utf-8")
            config = root / "requirements.json"
            config.write_text(
                json.dumps({"schema_version": "lily_research_log_requirements_v1", "entries": []}),
                encoding="utf-8",
            )
            result = audit_research_logs(config, logs, project_root=root)
        joined = " ".join(result["blockers"])
        self.assertIn("research_question_must_be_20_to_240_characters", joined)
        self.assertIn("research_question_must_be_an_explicit_question", joined)
        self.assertIn("mojibake_detected", joined)

    def test_missing_section_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "research_log"
            logs.mkdir()
            source = (PROJECT_ROOT / "research_log" / "001-lily-l0-sizing-feasibility.md").read_text(
                encoding="utf-8"
            )
            (logs / "001-lily-example.md").write_text(
                source.replace("## 4. ผลลัพธ์", "## ผลที่ได้"),
                encoding="utf-8",
            )
            config = root / "requirements.json"
            config.write_text(
                json.dumps({"schema_version": "lily_research_log_requirements_v1", "entries": []}),
                encoding="utf-8",
            )
            result = audit_research_logs(config, logs, project_root=root)
        self.assertTrue(any("missing_heading:## 4. ผลลัพธ์" in item for item in result["blockers"]))


if __name__ == "__main__":
    unittest.main()
