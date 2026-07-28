"""Fail-closed B7.14R7/v9 gate validator; predecessor proof uses committed blobs only."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.provenance import file_sha256

GATE = ROOT / "experiments/l_3_b714_date_only_preflight_remediation_v9.json"
MANIFEST = ROOT / "experiments/locked_gates.jsonl"
AUTH = {"real_container_access": False, "container_hashing": False, "date_inspection": False, "return_parsing": False, "execution": False, "research_decision": False, "ledger_write": False, "validation": False, "provider": False, "credentials": False, "broker": False, "paid": False, "paper_trade": False, "real_money": False}
ARTIFACT_PATHS = {"scanner": "lib/l3_b714_date_only_scanner_v9.py", "runner": "scripts/run_l_3_b714_date_only_preflight_v9.py", "report_schema": "schemas/l_3_b714_date_only_preflight_report_v9.schema.json", "attestation_schema": "schemas/l_3_b714_date_only_schedule_attestation_v9.schema.json", "report_validator": "scripts/validate_l_3_b714_date_only_preflight_report_v9.py", "gate_validator": "scripts/validate_l_3_b714_date_only_preflight_remediation_v9.py", "metadata_fixture": "tests/fixtures/l3_b714_v9/metadata.json", "report_fixture": "tests/fixtures/l3_b714_v9/report.json", "attestation_fixture": "tests/fixtures/l3_b714_v9/attestation.json", "recovery_addendum": "experiments/l_3_b714r6_manifest_duplicate_recovery_v2.json", "recovery_validator": "scripts/validate_l_3_b714r6_manifest_duplicate_recovery_v2.py"}
PREDECESSORS = {
    "v5": ("d2a15b717d29f55ce9ee55847fb3db3787da94e2", "experiments/l_3_b714_date_only_preflight_remediation_v5.json", "a0aa4049e19e3bc2997deab4f0a4dc000650932fc213bdb0624f7ab143207130"),
    "v6": ("53bbf429bd9cb321827036464040957db86caad7", "experiments/l_3_b714_date_only_preflight_remediation_v6.json", "565d7bcaa726f566b8d81e1197e41d024238286ba2783f93f341e7e019727925"),
    "v7": ("f458c32249e398428c421477f373f96840f92a1f", "experiments/l_3_b714_date_only_preflight_remediation_v7.json", "576b4ddd85cce521a1eb56a2633374ec4254434f925d77992cd662fb4a29553e"),
    "v8": ("b2d349d4ce3fcfb5e275664f20e69844fba4823a", "experiments/l_3_b714_date_only_preflight_remediation_v8.json", "892d6ef7b2a0e795800e4c6814fd214a763f0b18b79e39c1377ff7baec849c36"),
}
SOURCES = {
    "b713_v3": ("5d52119e81862c4ed2007be6e87d596d4be4d46e", "experiments/l_3_b714_activation_contract_v3.json", "29808a30a0451a4f2d39eeca73dd053a87edf7caab4b05231e3cad5471e38032"),
    "b75": ("6a515c3adb019b7c2199e0a4a5e09a687bd92868", "experiments/l_3_corrected_rerun_pre_return_schedule_v1.json", "1202f477bf6d890dfb0b926b3bff9c775215762209627cb53e9c55b5c18957eb"),
    "v3_report": ("512120f35461ecb99e607d20aa2937a056434339", "reports/experiments/l_3_b714_date_only_preflight_report_v3.json", "71727c6ee76f2af5c862da1fdc59c9a717005065c3abc0d61830dc08dd1c41dc"),
    "v3_addendum": ("512120f35461ecb99e607d20aa2937a056434339", "experiments/l_3_b714_v3_timestamp_decode_violation_addendum_v1.json", "c3ae1a58a6f00da691ef4edccf54dffb98c1415dd4613b0ac9f709286923a6fa"),
    "v7_addendum": ("f458c32249e398428c421477f373f96840f92a1f", "experiments/l_3_b714r5_v7_cross_platform_addendum_v1.json", "0d828d9b677dd89080d2988d2c8e068cf15e0f735225e3ccc3b0bac7c0d140a6"),
    "v8_addendum": ("b2d349d4ce3fcfb5e275664f20e69844fba4823a", "experiments/l_3_b714r5_v8_checkout_compatibility_addendum_v1.json", "c3a6b06c612b745c3980f37ff90ca9c103c5825326385fc81112a9ab4cf5e97e"),
    "recovery_v1": ("1e2fee053edaa31d5d886f911f6e08055d0fb9b2", "experiments/l_3_b714r6_manifest_duplicate_recovery_v1.json", "b8694d631f6306dca433ec741948bbb2ed2aabd93fbb83f201b27d88bfb38f26"),
}


def _blob(commit: str, path: str) -> bytes | None:
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None


def validate() -> dict[str, object]:
    try:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line]
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked", "blockers": [type(exc).__name__]}
    blockers: list[str] = []
    identity = {"schema_version": "lily_l3_b714_date_only_preflight_remediation_v9", "order_id": "B7.14R7", "gate_id": "l_3_b714_date_only_preflight_remediation_v9", "supersedes_gate_id": "l_3_b714_date_only_preflight_remediation_v8", "hypothesis_id": "L-3", "status": "locked_E0_rejected_v8_remediation", "evidence_ceiling": "E0", "edge_claim": "none", "validation_seal": {"status": "sealed_not_accessed", "accessed": False}}
    required = set(identity) | {"authorizations", "source_binding", "artifact_identities"}
    if set(gate) != required or any(gate.get(key) != value for key, value in identity.items()): blockers.append("identity_or_unknown_field")
    if gate.get("authorizations") != AUTH: blockers.append("authorizations")
    artifacts = gate.get("artifact_identities")
    if not isinstance(artifacts, dict) or set(artifacts) != set(ARTIFACT_PATHS): blockers.append("artifact_shape")
    else:
        for name, path in ARTIFACT_PATHS.items():
            if artifacts.get(name) != {"path": path, "sha256": file_sha256(ROOT / path)}: blockers.append(f"artifact:{name}")
    source = gate.get("source_binding")
    expected_keys = set(PREDECESSORS) | set(SOURCES) | {"historical_container_sha256", "b73_ledger", "missing_agent_trailer"}
    if not isinstance(source, dict) or set(source) != expected_keys: blockers.append("source_shape")
    else:
        for name, (commit, path, digest) in PREDECESSORS.items():
            blob = _blob(commit, path)
            expected = {"commit": commit, "path": path, "committed_blob_sha256": digest}
            if source.get(name) != expected or blob is None or hashlib.sha256(blob).hexdigest() != digest: blockers.append(f"predecessor:{name}")
        for name, (commit, path, digest) in SOURCES.items():
            blob = _blob(commit, path)
            expected = {"commit": commit, "path": path, "committed_blob_sha256": digest}
            if source.get(name) != expected or blob is None or hashlib.sha256(blob).hexdigest() != digest: blockers.append(f"source:{name}")
        ledger = source.get("b73_ledger")
        ledger_blob = _blob("512120f35461ecb99e607d20aa2937a056434339", "reports/experiments/l_3_falsification_execution_ledger.jsonl")
        first = ledger_blob.split(b"\n", 1)[0] if ledger_blob else b""
        try: row = json.loads(first)
        except json.JSONDecodeError: row = {}
        expected_ledger = {"commit": "512120f35461ecb99e607d20aa2937a056434339", "path": "reports/experiments/l_3_falsification_execution_ledger.jsonl", "first_row_sha256": "594b8cbbdf7c27769191ab9495275803478481121372cd3bfc6f7e6d3a8a556a", "event": "real_return_decision_run", "run_id": "B7.3-L3-ONE", "producing_git_commit": "3e3cfc773b8e327dca63bfdd8f2a1b103376173d"}
        if ledger != expected_ledger or hashlib.sha256(first).hexdigest() != expected_ledger["first_row_sha256"] or {key: row.get(key) for key in ("event", "run_id", "producing_git_commit")} != {key: expected_ledger[key] for key in ("event", "run_id", "producing_git_commit")}: blockers.append("b73_ledger")
        trailer = source.get("missing_agent_trailer")
        message = subprocess.run(["git", "show", "-s", "--format=%B", "512120f35461ecb99e607d20aa2937a056434339"], cwd=ROOT, text=True, capture_output=True, check=False)
        expected_trailer = {"commit": "512120f35461ecb99e607d20aa2937a056434339", "required_trailer": "Agent: Codex (GPT-5.6 Terra, high)", "defect": "commit_message_missing_agent_trailer"}
        if trailer != expected_trailer or message.returncode or expected_trailer["required_trailer"] in message.stdout: blockers.append("missing_agent_trailer")
        if source.get("historical_container_sha256") != "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd": blockers.append("historical_container")
    matches = [row for row in rows if row.get("gate_id") == identity["gate_id"]]
    if len(matches) != 1 or matches[0].get("artifact_sha256") != file_sha256(GATE) or matches[0].get("validator_sha256") != file_sha256(Path(__file__)) or not matches[0].get("human_approval") or not matches[0].get("reviewed_by"):
        blockers.append("manifest_identity")
    return {"status": "pass" if not blockers else "blocked", "blockers": sorted(set(blockers))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(result["status"] != "pass")
