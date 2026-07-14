from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.io import load_json, relative_to_root


DEFAULT_CONFIG = PROJECT_ROOT / "config" / "research_log_requirements.json"
DEFAULT_LOG_ROOT = PROJECT_ROOT / "research_log"
FILENAME_PATTERN = re.compile(r"^(\d{3})-lily-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
THAI_CHARACTER_PATTERN = re.compile(r"[\u0E00-\u0E7F]")
QUESTION_PATTERN = re.compile(r"(?m)^- คำถามวิจัย:\s*(.+)$")
REQUIRED_HEADINGS = (
    "## 1. ข้อมูลพื้นฐาน",
    "## 2. ปัญหา (คำถาม) และสมมติฐาน",
    "## 3. ขั้นตอนการทดลอง",
    "## 4. ผลลัพธ์",
    "## 5. อภิปรายผล ปัญหา และข้อจำกัด",
    "## 6. สรุปผลการทดลองและแนวทางพัฒนาต่อ",
)
REQUIRED_LABELS = (
    "- Timestamp UTC:",
    "- โครงการ:",
    "- Hypothesis ID:",
    "- Experiment ID:",
    "- ระดับหลักฐาน:",
    "- ข้อสรุป:",
    "- Artifact หลัก:",
    "- Producing commit:",
    "### อ่านแบบเร็ว",
    "- คำถามวิจัย:",
    "- ขอบเขต:",
    "- สมมติฐาน:",
    "- เกณฑ์ตัดสิน:",
    "สิ่งที่ห้ามสรุปจากการทดลองนี้:",
    "ข้อสรุป:",
    "แนวทางพัฒนาต่อ:",
)
QUESTION_TERMS = ("หรือไม่", "เพียงใด", "เท่าใด", "อะไร", "อย่างไร")
MOJIBAKE_MARKERS = ("\ufffd", "เน€", "โ€", "เธ\x81", "เธ\x99")


def audit_research_logs(
    config_path: Path = DEFAULT_CONFIG,
    log_root: Path = DEFAULT_LOG_ROOT,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        config = load_json(config_path)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return _result(config_path, log_root, [f"config_unreadable:{exc.__class__.__name__}"], [], [])
    if config.get("schema_version") != "lily_research_log_requirements_v1":
        blockers.append("invalid_config_schema_version")
    entries = config.get("entries")
    if not isinstance(entries, list) or not entries:
        blockers.append("requirements_entries_must_be_nonempty_list")
        entries = []

    requirements: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            blockers.append(f"requirement_{index}_must_be_object")
            continue
        summary_path = entry.get("summary_path")
        log_path = entry.get("research_log_path")
        if not _safe_relative_path(summary_path):
            blockers.append(f"requirement_{index}_summary_path_invalid")
            continue
        if not _safe_relative_path(log_path) or not str(log_path).startswith("research_log/"):
            blockers.append(f"requirement_{index}_research_log_path_invalid")
            continue
        summary_exists = (project_root / str(summary_path)).is_file()
        log_exists = (project_root / str(log_path)).is_file()
        required = entry.get("required_when_summary_exists") is True and summary_exists
        if required and not log_exists:
            blockers.append(f"missing_required_research_log:{entry.get('experiment_id')}")
        requirements.append(
            {
                "experiment_id": entry.get("experiment_id"),
                "summary_path": summary_path,
                "summary_exists": summary_exists,
                "research_log_path": log_path,
                "research_log_exists": log_exists,
                "required_now": required,
            }
        )

    log_paths = sorted(log_root.glob("*.md")) if log_root.is_dir() else []
    log_rows: list[dict[str, Any]] = []
    numbers: list[int] = []
    for path in log_paths:
        match = FILENAME_PATTERN.fullmatch(path.name)
        if match is None:
            blockers.append(f"invalid_research_log_filename:{path.name}")
        else:
            numbers.append(int(match.group(1)))
        file_blockers = _audit_log_file(path)
        blockers.extend(f"{path.name}:{item}" for item in file_blockers)
        log_rows.append(
            {
                "path": relative_to_root(path, project_root),
                "status": "pass" if not file_blockers else "blocked",
                "blockers": file_blockers,
            }
        )

    expected_numbers = list(range(1, len(numbers) + 1))
    if sorted(numbers) != expected_numbers:
        blockers.append(
            "research_log_sequence_must_be_contiguous_from_001:"
            + ",".join(f"{number:03d}" for number in sorted(numbers))
        )
    return _result(config_path, log_root, blockers, requirements, log_rows)


def _audit_log_file(path: Path) -> list[str]:
    blockers: list[str] = []
    text = path.read_text(encoding="utf-8")
    if not text.startswith("# บันทึกการวิจัย "):
        blockers.append("title_must_start_with_research_log")
    positions = [text.find(heading) for heading in REQUIRED_HEADINGS]
    for heading, position in zip(REQUIRED_HEADINGS, positions, strict=True):
        if position < 0:
            blockers.append(f"missing_heading:{heading}")
    if all(position >= 0 for position in positions) and positions != sorted(positions):
        blockers.append("required_headings_out_of_order")
    for label in REQUIRED_LABELS:
        if label not in text:
            blockers.append(f"missing_required_label:{label}")
    if len(THAI_CHARACTER_PATTERN.findall(text)) < 300:
        blockers.append("insufficient_Thai_narrative")
    for marker in MOJIBAKE_MARKERS:
        if marker in text:
            blockers.append("mojibake_detected")
            break
    if re.search(r"<[^>]+>|\b(?:TODO|TBD)\b", text, flags=re.IGNORECASE):
        blockers.append("template_placeholder_or_TODO_present")

    question_match = QUESTION_PATTERN.search(text)
    if question_match is not None:
        question = question_match.group(1).strip()
        if not 20 <= len(question) <= 240:
            blockers.append("research_question_must_be_20_to_240_characters")
        if not any(term in question for term in QUESTION_TERMS):
            blockers.append("research_question_must_be_an_explicit_question")
        if "\n" in question:
            blockers.append("research_question_must_be_one_sentence")
    return blockers


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def _result(
    config_path: Path,
    log_root: Path,
    blockers: list[str],
    requirements: list[dict[str, Any]],
    logs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "config_path": relative_to_root(config_path, PROJECT_ROOT),
        "research_log_root": relative_to_root(log_root, PROJECT_ROOT),
        "requirements": requirements,
        "logs": logs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Lily's human-readable Thai research logs.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--research-log-root", type=Path, default=DEFAULT_LOG_ROOT)
    args = parser.parse_args()
    result = audit_research_logs(args.config, args.research_log_root)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
