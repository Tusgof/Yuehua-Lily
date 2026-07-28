"""Fail-closed validator for append-only B7.14R5/v7 E0 gate."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.provenance import file_sha256
from scripts.validate_l_3_b714r5_v7_cross_platform_addendum_v1 import validate as validate_addendum

GATE = ROOT / "experiments/l_3_b714_date_only_preflight_remediation_v7.json"
MANIFEST = ROOT / "experiments/locked_gates.jsonl"
AUTH = {"real_container_access": False, "container_hashing": False, "date_inspection": False, "return_parsing": False, "execution": False, "research_decision": False, "ledger_write": False, "validation": False, "provider": False, "credentials": False, "broker": False, "paid": False, "paper_trade": False, "real_money": False}
ARTIFACT_PATHS = {
    "scanner": "lib/l3_b714_date_only_scanner_v7.py",
    "runner": "scripts/run_l_3_b714_date_only_preflight_v7.py",
    "report_schema": "schemas/l_3_b714_date_only_preflight_report_v7.schema.json",
    "attestation_schema": "schemas/l_3_b714_date_only_schedule_attestation_v7.schema.json",
    "report_validator": "scripts/validate_l_3_b714_date_only_preflight_report_v7.py",
    "gate_validator": "scripts/validate_l_3_b714_date_only_preflight_remediation_v7.py",
    "cross_platform_addendum": "experiments/l_3_b714r5_v7_cross_platform_addendum_v1.json",
    "cross_platform_addendum_validator": "scripts/validate_l_3_b714r5_v7_cross_platform_addendum_v1.py",
    "metadata_fixture": "tests/fixtures/l3_b714_v7/metadata.json",
    "report_fixture": "tests/fixtures/l3_b714_v7/report.json",
    "attestation_fixture": "tests/fixtures/l3_b714_v7/attestation.json",
}
SOURCES = {
    "b713_v3": ("experiments/l_3_b714_activation_contract_v3.json", "29808a30a0451a4f2d39eeca73dd053a87edf7caab4b05231e3cad5471e38032"),
    "b75": ("experiments/l_3_corrected_rerun_pre_return_schedule_v1.json", "1202f477bf6d890dfb0b926b3bff9c775215762209627cb53e9c55b5c18957eb"),
    "v3_report": ("reports/experiments/l_3_b714_date_only_preflight_report_v3.json", "71727c6ee76f2af5c862da1fdc59c9a717005065c3abc0d61830dc08dd1c41dc"),
    "v3_addendum": ("experiments/l_3_b714_v3_timestamp_decode_violation_addendum_v1.json", "c3ae1a58a6f00da691ef4edccf54dffb98c1415dd4613b0ac9f709286923a6fa"),
}
PREDECESSORS = {
    "v5": ("l_3_b714_date_only_preflight_remediation_v5", "d2a15b717d29f55ce9ee55847fb3db3787da94e2", "experiments/l_3_b714_date_only_preflight_remediation_v5.json", "a0aa4049e19e3bc2997deab4f0a4dc000650932fc213bdb0624f7ab143207130"),
    "v6": ("l_3_b714_date_only_preflight_remediation_v6", "53bbf429bd9cb321827036464040957db86caad7", "experiments/l_3_b714_date_only_preflight_remediation_v6.json", "565d7bcaa726f566b8d81e1197e41d024238286ba2783f93f341e7e019727925"),
}


def validate() -> dict[str, object]:
    try:
        gate = json.loads(GATE.read_text(encoding="utf-8")); rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line]
    except (OSError, json.JSONDecodeError) as exc: return {"status": "blocked", "blockers": [type(exc).__name__]}
    blockers: list[str] = []
    required = {"schema_version", "order_id", "gate_id", "supersedes_gate_id", "hypothesis_id", "status", "evidence_ceiling", "edge_claim", "source_binding", "authorizations", "validation_seal", "artifact_identities"}
    identity = {"schema_version": "lily_l3_b714_date_only_preflight_remediation_v7", "order_id": "B7.14R5", "gate_id": "l_3_b714_date_only_preflight_remediation_v7", "supersedes_gate_id": "l_3_b714_date_only_preflight_remediation_v6", "hypothesis_id": "L-3", "status": "locked_E0_rejected_v6_remediation", "evidence_ceiling": "E0", "edge_claim": "none", "validation_seal": {"status": "sealed_not_accessed", "accessed": False}}
    if set(gate) != required or any(gate.get(k) != v for k, v in identity.items()): blockers.append("identity_or_unknown_field")
    if gate.get("authorizations") != AUTH: blockers.append("authorizations")
    artifacts = gate.get("artifact_identities")
    if not isinstance(artifacts, dict) or set(artifacts) != set(ARTIFACT_PATHS): blockers.append("artifact_shape")
    else:
        for name, item in artifacts.items():
            if not isinstance(item, dict) or set(item) != {"path", "sha256"} or item.get("path") != ARTIFACT_PATHS[name] or file_sha256(ROOT / ARTIFACT_PATHS[name]) != item.get("sha256"): blockers.append(f"artifact:{name}")
    source = gate.get("source_binding")
    expected_source_keys = {"v5", "v6", "b713_v3", "b75", "cross_platform_addendum", "v3_checkpoint", "v3_report", "v3_addendum", "historical_container_sha256", "b73_ledger", "missing_agent_trailer"}
    if validate_addendum().get("status") != "pass": blockers.append("cross_platform_addendum")
    if not isinstance(source, dict) or set(source) != expected_source_keys: blockers.append("source_shape")
    else:
        if source.get("v3_checkpoint") != "99e33857064e6eec76baba21ea64d9aaecea578f" or source.get("historical_container_sha256") != "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd":
            blockers.append("historical_provenance")
        for name, (path, digest) in SOURCES.items():
            item = source.get(name)
            if not isinstance(item, dict) or item.get("path") != path or item.get("sha256") != digest or file_sha256(ROOT / path) != digest: blockers.append(f"source:{name}")
        for name, (gate_id, commit, path, digest) in PREDECESSORS.items():
            item = source.get(name)
            shown = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
            if not isinstance(item, dict) or item != {"gate_id": gate_id, "commit": commit, "path": path, "committed_lf_sha256": digest} or shown.returncode or hashlib.sha256(shown.stdout).hexdigest() != digest:
                blockers.append(f"source:{name}")
        addendum = source.get("cross_platform_addendum")
        if not isinstance(addendum, dict) or addendum != artifacts.get("cross_platform_addendum"):
            blockers.append("source:cross_platform_addendum")
        ledger = source.get("b73_ledger")
        raw = (ROOT / ledger.get("path", "")).read_bytes() if isinstance(ledger, dict) and (ROOT / ledger.get("path", "")).is_file() else b""
        first = raw.split(b"\n", 1)[0]
        try: row = json.loads(first)
        except json.JSONDecodeError: row = {}
        expected_ledger = {"path": "reports/experiments/l_3_falsification_execution_ledger.jsonl", "first_row_sha256": "594b8cbbdf7c27769191ab9495275803478481121372cd3bfc6f7e6d3a8a556a", "event": "real_return_decision_run", "run_id": "B7.3-L3-ONE", "producing_git_commit": "3e3cfc773b8e327dca63bfdd8f2a1b103376173d"}
        if ledger != expected_ledger or hashlib.sha256(first).hexdigest() != expected_ledger["first_row_sha256"] or {k: row.get(k) for k in ("event", "run_id", "producing_git_commit")} != {k: expected_ledger[k] for k in ("event", "run_id", "producing_git_commit")}: blockers.append("b73_ledger_identity")
        trailer = source.get("missing_agent_trailer")
        message = subprocess.run(["git", "show", "-s", "--format=%B", trailer.get("commit", "")], cwd=ROOT, capture_output=True, text=True, check=False)
        if not isinstance(trailer, dict) or trailer != {"commit": "512120f35461ecb99e607d20aa2937a056434339", "required_trailer": "Agent: Codex (GPT-5.6 Terra, high)", "defect": "commit_message_missing_agent_trailer"} or message.returncode or trailer["required_trailer"] in message.stdout: blockers.append("missing_agent_trailer_defect")
    row = next((item for item in rows if item.get("gate_id") == identity["gate_id"]), None)
    if not isinstance(row, dict) or row.get("artifact_sha256") != file_sha256(GATE) or row.get("validator_sha256") != file_sha256(Path(__file__)) or row.get("human_approval") is None or row.get("reviewed_by") is None: blockers.append("v7_manifest_identity")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate(); print(json.dumps(result, sort_keys=True)); raise SystemExit(result["status"] != "pass")
