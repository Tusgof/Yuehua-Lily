"""Closed-world report validation for B8.6R11/v13."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.l4_b86r11_contract_v13 import ACTIVATION, ACTIVATION_CONTENT_KEYS, ACTIVATION_PROVENANCE_KEYS, BLOCKERS, COMMON_REPORT_KEYS, MANIFEST, OUTPUT_ID_KEYS, PAYLOAD, REPORT_SCHEMA, SEAL, canonical, h40, h64, outputs_ok, row_ok, sha256
from scripts.run_l_4_breadth_b86r11_committed_bootstrap_v13 import DEPENDENCIES, GATE, GATE_ID
def blob(commit, path):
    result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, capture_output=True, check=False)
    return result.stdout if result.returncode == 0 else None
def artifacts_ok(report):
    commit, artifacts = report.get("producing_git_commit"), report.get("contract_artifacts")
    if not h40(commit) or not isinstance(artifacts, dict) or set(artifacts) != set(DEPENDENCIES): return False
    return all((raw := blob(commit, path)) is not None and artifacts[path] == {"path":path,"sha256":sha256(raw)} for path in DEPENDENCIES)
def activation_ok(report):
    provenance, commit = report.get("activation_provenance"), report.get("producing_git_commit")
    if not isinstance(provenance, dict) or set(provenance) != ACTIVATION_PROVENANCE_KEYS or provenance.get("path") != ACTIVATION or provenance.get("activation_checkpoint_head") != commit or not h64(provenance.get("raw_sha256")) or not h64(provenance.get("accepted_gate_blob_sha256")): return False
    raw, gate = blob(commit, ACTIVATION), blob(commit, GATE)
    if raw is None or gate is None or not isinstance(provenance.get("content"), dict) or raw != canonical(provenance["content"]) or sha256(raw) != provenance["raw_sha256"] or sha256(gate) != provenance["accepted_gate_blob_sha256"]: return False
    value, accepted = provenance["content"], provenance["content"].get("accepted_gate_head_sha")
    if set(value) != ACTIVATION_CONTENT_KEYS or value.get("schema_version") != "lily_l4_b86r11_provisioning_activation_v13" or value.get("gate_id") != GATE_ID or value.get("gate_sha256") != sha256(gate) or not h40(accepted) or value.get("hermetic_ci_head_sha") != accepted or not isinstance(value.get("hermetic_ci_run_id"), int) or isinstance(value.get("hermetic_ci_run_id"), bool) or value["hermetic_ci_run_id"] <= 0 or value.get("inspector_decision") != "ACCEPTED" or value.get("owner_authorization_reference") != "B8.6R11 one-shot owner authorization" or value.get("scope") != "one_repo_relative_falsification_container_provisioning_only" or value.get("validation_seal") != SEAL: return False
    return subprocess.run(["git", "merge-base", "--is-ancestor", accepted, commit], cwd=ROOT, capture_output=True, check=False).returncode == 0 and blob(accepted, GATE) == gate
def outputs_identity_ok(report, root=ROOT):
    manifest, payload, identities = report.get("manifest"), report.get("payload"), report.get("output_artifacts")
    if not outputs_ok(manifest, payload) or not isinstance(identities, dict) or set(identities) != {"manifest", "payload"} or report["dataset_artifact"].get("complete_raw_sha256") != manifest["dataset_sha256"] or report["dataset_artifact"].get("observed_byte_count") != manifest["dataset_byte_count"] or report.get("structural_summary_sha256") != sha256(canonical({"manifest":manifest,"payload":payload})): return False
    for name, path, value in (("manifest", MANIFEST, manifest), ("payload", PAYLOAD, payload)):
        raw = canonical(value)
        try: disk = (Path(root) / path).read_bytes()
        except OSError: return False
        if not isinstance(identities[name], dict) or set(identities[name]) != OUTPUT_ID_KEYS or identities[name] != {"path":path,"raw_sha256":sha256(raw),"byte_count":len(raw)} or disk != raw: return False
    return True
def validate(report, *, root=ROOT):
    blockers = []
    common = isinstance(report, dict) and set(report) >= COMMON_REPORT_KEYS
    if not common or report.get("schema_version") != REPORT_SCHEMA or report.get("order_id") != "B8.6R11" or report.get("hypothesis_id") != "L-4" or report.get("evidence_tier") != "E0" or report.get("edge_claim") != "none" or report.get("dataset_reference") != "data/normalized/l1_yahoo_daily_v1.json" or report.get("expected_dataset_sha256") != "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd" or report.get("access_counters") != {"return_value_decode_count":0,"validation_access_count":0} or report.get("validation_seal") != SEAL: blockers.append("contract")
    mode, outcome = report.get("mode"), report.get("outcome")
    expected_keys = (COMMON_REPORT_KEYS | {"blocker"}) if outcome == "provisioning_blocked" else (COMMON_REPORT_KEYS | {"manifest", "payload", "output_artifacts", "structural_summary_sha256"}) if mode == "real_one_shot" and outcome == "structural_provisioned" else set()
    if not expected_keys or not isinstance(report, dict) or set(report) != expected_keys: blockers.append("closed_world")
    if mode == "synthetic_fixture":
        if outcome != "provisioning_blocked" or report.get("real_provisioning_consumed") is not False or report.get("activation_provenance") is not None or report.get("producing_git_commit") != "synthetic_fixture" or report.get("contract_artifacts") != {}: blockers.append("synthetic")
    elif mode == "real_one_shot":
        if report.get("real_provisioning_consumed") is not True or not artifacts_ok(report) or not activation_ok(report): blockers.append("provenance")
    else: blockers.append("mode")
    if outcome == "provisioning_blocked":
        if report.get("blocker") not in BLOCKERS or not row_ok(report.get("dataset_artifact"), report.get("blocker")): blockers.append("blocked")
    elif outcome == "structural_provisioned":
        if mode != "real_one_shot" or not row_ok(report.get("dataset_artifact")) or not outputs_identity_ok(report, root): blockers.append("outputs")
    else: blockers.append("outcome")
    return {"status":"pass" if not blockers else "blocked", "blockers":sorted(set(blockers))}
if __name__ == "__main__":
    try: report = json.loads(Path(sys.argv[1]).read_text("ascii"))
    except (IndexError, OSError, ValueError): raise SystemExit(2)
    result = validate(report); print(json.dumps(result)); raise SystemExit(result["status"] != "pass")
