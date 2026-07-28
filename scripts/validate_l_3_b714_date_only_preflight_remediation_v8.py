"""Validate the exact v5/v6 checkout compatibility exception."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.provenance import file_sha256

GATE = ROOT / "experiments/l_3_b714_date_only_preflight_remediation_v8.json"
ADDENDUM = ROOT / "experiments/l_3_b714r5_v8_checkout_compatibility_addendum_v1.json"
ATTRIBUTES = ROOT / ".gitattributes"
V5_V6 = (
    "experiments/l_3_b714_date_only_preflight_remediation_v5.json",
    "scripts/validate_l_3_b714_date_only_preflight_remediation_v5.py",
    "lib/l3_b714_date_only_scanner_v5.py",
    "scripts/run_l_3_b714_date_only_preflight_v5.py",
    "schemas/l_3_b714_date_only_preflight_report_v5.schema.json",
    "schemas/l_3_b714_date_only_schedule_attestation_v5.schema.json",
    "scripts/validate_l_3_b714_date_only_preflight_report_v5.py",
    "tests/fixtures/l3_b714_v5/*.json",
    "experiments/l_3_b714_date_only_preflight_remediation_v6.json",
    "scripts/validate_l_3_b714_date_only_preflight_remediation_v6.py",
    "lib/l3_b714_date_only_scanner_v6.py",
    "scripts/run_l_3_b714_date_only_preflight_v6.py",
    "schemas/l_3_b714_date_only_preflight_report_v6.schema.json",
    "schemas/l_3_b714_date_only_schedule_attestation_v6.schema.json",
    "scripts/validate_l_3_b714_date_only_preflight_report_v6.py",
    "tests/fixtures/l3_b714_v6/*.json",
)


def validate() -> dict[str, object]:
    try:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        addendum = json.loads(ADDENDUM.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    lines = set(ATTRIBUTES.read_text(encoding="utf-8").splitlines())
    blocked: list[str] = []
    if any(f"{path} text eol=crlf" not in lines for path in V5_V6):
        blocked.append("legacy_checkout_attributes")
    if any(f"{path} text eol=lf" not in lines for path in ("experiments/l_3_b714_date_only_preflight_remediation_v7.json", "scripts/validate_l_3_b714_date_only_preflight_remediation_v7.py")):
        blocked.append("v7_lf_attributes")
    if gate.get("source_binding", {}).get("v7_gate_sha256") != file_sha256(ROOT / "experiments/l_3_b714_date_only_preflight_remediation_v7.json"):
        blocked.append("v7_identity")
    if addendum.get("rejected_checkpoint", {}).get("ci_run_id") != 30348523127 or addendum.get("access") != {"data": False, "container": False, "provider": False, "research_log": False}:
        blocked.append("addendum_identity")
    return {"status": "pass" if not blocked else "blocked", "blockers": blocked}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
