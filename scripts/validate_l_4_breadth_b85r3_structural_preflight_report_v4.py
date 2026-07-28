"""Closed-world report validator for B8.5R3/v4."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.l4_b85r3_structural_scanner_v4 import CUTOFF, MAX_BYTES, U8
from lib.provenance import git_commit
from scripts.run_l_4_breadth_b85r3_phase_b_preflight_v4 import ATTEMPT_MARKER_RELATIVE, CONTAINER_IDENTITY, MANIFEST_REFERENCE, MARKER_BYTES, PAYLOAD_REFERENCE, contract_identities, preflight_from_raw

FIXTURE_ROOT = ROOT / "tests/fixtures/l4_b85r3"
MANIFEST = FIXTURE_ROOT / "structural_manifest_v4.json"; PAYLOAD = FIXTURE_ROOT / "u8_symbol_session_dates_v4.json"
ARTIFACT_KEYS = {"attempted_read_count","read_count","observed_byte_count","complete_read","complete_raw_sha256","bounded_prefix_sha256","hash_count","scan_count","minimal_ascii_decode_count"}
BASE = {"schema_version","order_id","hypothesis_id","mode","outcome","evidence_tier","edge_claim","real_preflight_consumed","storage_references","container_identity","artifacts","contract_artifacts","access_counters","validation_seal","attempt","producing_git_commit"}


def _artifact(value: object, *, real: bool, passed: bool) -> bool:
    if not isinstance(value, dict) or set(value) != ARTIFACT_KEYS: return False
    attempted, read, size, complete, full, prefix, hashes, scans, decoded = (value[key] for key in ("attempted_read_count","read_count","observed_byte_count","complete_read","complete_raw_sha256","bounded_prefix_sha256","hash_count","scan_count","minimal_ascii_decode_count"))
    if not all(isinstance(item, int) and item >= 0 for item in (attempted, read, hashes, scans, decoded)) or not isinstance(complete, bool): return False
    if attempted == 0:
        if passed:
            return read == 0 and hashes == scans == 1 and decoded > 0 and isinstance(size, int) and complete and full == prefix and isinstance(prefix, str)
        return read == hashes == scans == decoded == 0 and size is None and not complete and full is None and prefix is None
    if attempted != 1 or read > 1: return False
    if read == 0: return size is None and not complete and full is None and prefix is None and hashes == scans == decoded == 0
    if not isinstance(size, int) or hashes != 1 or not isinstance(prefix, str) or len(prefix) != 64: return False
    if complete != (size <= MAX_BYTES) or (complete and full != prefix) or (not complete and full is not None): return False
    if passed: return ((read == 1 and attempted == 1) if real else (read == 0 and attempted == 0)) and scans == 1 and decoded > 0 and complete
    return scans in (0, 1) and decoded >= 0


def _payload(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {"complete_raw_sha256","observed_byte_count","u8_members_in_order","session_count","session_counts_by_symbol","session_dates_by_symbol","max_session_date","minimal_ascii_decode_count"}: return False
    dates = value.get("session_dates_by_symbol"); counts = value.get("session_counts_by_symbol")
    if value.get("u8_members_in_order") != list(U8) or not isinstance(dates, dict) or not isinstance(counts, dict) or set(dates) != set(U8) or set(counts) != set(U8): return False
    try:
        if any(not isinstance(dates[symbol], list) or dates[symbol] != sorted(set(dates[symbol])) or not dates[symbol] or any(date.fromisoformat(item).isoformat() != item or item > CUTOFF for item in dates[symbol]) or counts[symbol] != len(dates[symbol]) for symbol in U8): return False
    except (TypeError, ValueError): return False
    return value.get("session_count") == sum(counts.values()) and value.get("minimal_ascii_decode_count") == value["session_count"] + len(U8) + 1


def _gate_manifest_current() -> bool:
    try:
        with (ROOT / "experiments/locked_gates.jsonl").open("rb") as handle: raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES: return False
        row = next(json.loads(line) for line in raw.decode("utf-8").splitlines() if 'l_4_breadth_b85r3_phase_a_activation_order_v4' in line)
        identities = contract_identities()
    except (OSError, UnicodeDecodeError, ValueError, StopIteration, json.JSONDecodeError): return False
    return row.get("artifact_path") == identities["phase_a_gate"]["path"] and row.get("artifact_sha256") == identities["phase_a_gate"]["sha256"] and row.get("validator_path") == identities["phase_a_validator"]["path"] and row.get("validator_sha256") == identities["phase_a_validator"]["sha256"]


def validate(report: object, *, marker_path: Path | None = None) -> dict[str, object]:
    blockers: list[str] = []
    if not isinstance(report, dict): return {"status":"blocked","blockers":["report_type"]}
    mode, outcome = report.get("mode"), report.get("outcome"); allowed = BASE | ({"manifest","payload"} if outcome == "structural_pass" else {"blocker"} if outcome == "preflight_blocked" else set())
    identity = {"schema_version":"lily_l4_b85r3_structural_preflight_report_v4","order_id":"B8.5R3","hypothesis_id":"L-4","evidence_tier":"E0","edge_claim":"none","container_identity":CONTAINER_IDENTITY}
    if set(report) != allowed or mode not in ("synthetic_fixture","real_one_shot") or outcome not in ("structural_pass","preflight_blocked") or any(report.get(key) != value for key, value in identity.items()): blockers.append("shape_or_identity")
    real = mode == "real_one_shot"; passed = outcome == "structural_pass"
    if report.get("storage_references") != {"manifest":MANIFEST_REFERENCE,"payload":PAYLOAD_REFERENCE} or report.get("contract_artifacts") != contract_identities() or report.get("access_counters") != {"return_value_decode_count":0,"validation_access_count":0} or report.get("validation_seal") != {"status":"sealed_not_accessed","accessed":False}: blockers.append("contract")
    if not _gate_manifest_current(): blockers.append("gate_manifest")
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {"manifest","payload"} or not _artifact(artifacts.get("manifest"), real=real, passed=passed) or not _artifact(artifacts.get("payload"), real=real, passed=passed): blockers.append("artifact_counters")
    if real:
        if report.get("real_preflight_consumed") is not True or report.get("producing_git_commit") != git_commit(ROOT) or report.get("attempt") != {"state":"consumed","repo_relative_marker_path":ATTEMPT_MARKER_RELATIVE.as_posix(),"marker_raw_sha256":hashlib.sha256(MARKER_BYTES).hexdigest()}: blockers.append("real_state")
        try:
            with (marker_path or ROOT / ATTEMPT_MARKER_RELATIVE).open("rb") as handle: marker_raw = handle.read(MAX_BYTES + 1)
            if marker_raw != MARKER_BYTES: blockers.append("marker")
        except OSError: blockers.append("marker")
    elif report.get("real_preflight_consumed") is not False: blockers.append("synthetic_state")
    if passed:
        manifest, payload = report.get("manifest"), report.get("payload")
        if not isinstance(manifest, dict) or set(manifest) != {"complete_raw_sha256","observed_byte_count","metadata_sha256","minimal_ascii_decode_count"} or not _payload(payload) or manifest.get("metadata_sha256") != payload.get("complete_raw_sha256"): blockers.append("pass_content")
    else:
        blocker = report.get("blocker", "")
        if not isinstance(blocker, str) or not blocker: blockers.append("blocked_content")
        elif blocker == "manifest_input_over_limit":
            expected = {"manifest":(1,1,MAX_BYTES+1,False,0,0),"payload":(0,0,None,False,0,0)}
            for name, state in expected.items():
                item=artifacts[name]
                if tuple(item[key] for key in ("attempted_read_count","read_count","observed_byte_count","complete_read","scan_count","minimal_ascii_decode_count")) != state: blockers.append("over_limit_counters")
        elif blocker.startswith("manifest_") and artifacts["payload"]["attempted_read_count"] != 0: blockers.append("manifest_blocker_counters")
        elif blocker.startswith("payload_") and (artifacts["manifest"]["read_count"] != 1 or artifacts["manifest"]["complete_read"] is not True or artifacts["manifest"]["scan_count"] != 0): blockers.append("payload_blocker_counters")
        elif blocker.startswith("structural_") and (artifacts["manifest"]["read_count"] != 1 or artifacts["payload"]["read_count"] != 1 or artifacts["manifest"]["complete_read"] is not True or artifacts["payload"]["complete_read"] is not True or artifacts["manifest"]["scan_count"] != 1 or artifacts["payload"]["scan_count"] not in (0,1)): blockers.append("structural_blocker_counters")
        elif blocker.startswith("data_root_") and any(artifacts[name]["attempted_read_count"] != 0 for name in ("manifest","payload")): blockers.append("data_root_counters")
    return {"status":"pass" if not blockers else "blocked","blockers":sorted(set(blockers))}


if __name__ == "__main__":
    result = validate(preflight_from_raw(MANIFEST.read_bytes(), PAYLOAD.read_bytes()))
    print(json.dumps(result)); raise SystemExit(result["status"] != "pass")
