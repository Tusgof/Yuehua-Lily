# Decision Record 002 — Human-Readable Research Logs

- **Date**: 2026-07-15
- **Status**: accepted
- **Owner decision**: Every completed Lily experiment must have a plain-Thai research log that a human can understand without opening machine artifacts first.

## Decision

Lily adopts a tracked `research_log/` modeled on Higanbana's human-readable research notes. Each completed experiment or conclusion-changing diagnostic uses the six sections defined in `RESEARCH_LOG_FORMAT.md`:

1. ข้อมูลพื้นฐาน
2. ปัญหา (คำถาม) และสมมติฐาน
3. ขั้นตอนการทดลอง
4. ผลลัพธ์
5. อภิปรายผล ปัญหา และข้อจำกัด
6. สรุปผลการทดลองและแนวทางพัฒนาต่อ

Questions must be short, scoped, testable, and paired with a decision rule. A vague topic is not a research question.

Machine artifacts remain authoritative for exact values, provenance, and validation. The Thai log explains the research path and must cite those artifacts. A completed summary listed in `config/research_log_requirements.json` is incomplete without its audited log.

## Legacy Note Decision

The owner explicitly retired the old `Note/` files on 2026-07-15. Their hypothesis content had already been promoted into `experiments/hypothesis_registry.json`, the founding decision record, and locked preregistrations. The files are deleted rather than retained as active or historical project inputs.

This supersedes the `Note/` preservation decision in Decision Record 001 and the founding control documents. It does not alter any locked experiment gate.

## Higanbana Adaptation

Kept: numbered Markdown logs, Thai-first prose, quick-read summary, evidence tier, limitations, forbidden claims, next action, Git tracking, and automated readability checks.

Changed for Lily: section names follow the owner's scientific-report structure; question clarity and scope fields are mandatory; exact results remain linked to Lily JSON reports and locked-gate governance.
