"""Future one-shot B8.6 provisioning runner; Phase A never invokes it."""
from __future__ import annotations

import hashlib, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.environment import require_configured_path
from lib.l4_b86_provisioning_scanner_v1 import MAX_BYTES, ScanError, scan_dataset
from lib.provenance import git_commit

GATE_ID = "l_4_breadth_b86_provisioning_gate_v1"
DATASET_RELATIVE = Path("data/normalized/l1_yahoo_daily_v1.json")
DATASET_REFERENCE = "${LILY_DATA_ROOT}/data/normalized/l1_yahoo_daily_v1.json"
EXPECTED_SHA256 = "6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd"
ACTIVATION_RELATIVE = Path("experiments/activation_records/l_4_breadth_b86_provisioning_activation_v1.json")
REPORT_RELATIVE = Path("reports/experiments/l_4_breadth_b86_provisioning_report_v1.json")
MARKER_RELATIVE = Path("reports/experiments/l_4_breadth_b86_provisioning_attempt_v1.json")
MANIFEST_RELATIVE = Path("experiments/provisioned/l_4_breadth_b86_falsification_manifest_v1.json")
PAYLOAD_RELATIVE = Path("experiments/provisioned/l_4_breadth_b86_u8_session_dates_v1.json")


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii"))


def _claim(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try: fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError: return False
    os.write(fd, b'{"schema_version":"lily_l4_b86_attempt_v1","state":"consumed"}'); os.close(fd); return True


def _activation() -> bool:
    try: value = json.loads((ROOT / ACTIVATION_RELATIVE).read_text(encoding="ascii"))
    except (OSError, ValueError): return False
    return value == {"schema_version":"lily_l4_b86_provisioning_activation_v1","gate_id":GATE_ID,"inspector_decision":"ACCEPTED","scope":"one_falsification_container_provisioning_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}}


def provision(root: Path, *, report_path: Path, marker_path: Path) -> dict:
    if not _claim(marker_path): return {"outcome":"refused_already_consumed"}
    base = {"schema_version":"lily_l4_b86_provisioning_report_v1","order_id":"B8.6","hypothesis_id":"L-4","evidence_tier":"E0","edge_claim":"none","real_provisioning_consumed":True,"dataset_reference":DATASET_REFERENCE,"expected_dataset_sha256":EXPECTED_SHA256,"access_counters":{"dataset_read_count":0,"numeric_lexeme_decode_count":0,"validation_access_count":0},"validation_seal":{"status":"sealed_not_accessed","accessed":False},"producing_git_commit":git_commit(ROOT)}
    try: raw = (root / DATASET_RELATIVE).read_bytes()
    except OSError: base.update({"outcome":"provisioning_blocked","blocker":"dataset_unavailable"}); _write(report_path, base); return base
    base["access_counters"]["dataset_read_count"] = 1
    try: scanned = scan_dataset(raw, expected_sha256=EXPECTED_SHA256)
    except ScanError as exc: base.update({"outcome":"provisioning_blocked","blocker":str(exc)}); _write(report_path, base); return base
    _write(ROOT / MANIFEST_RELATIVE, {"schema_version":"lily_l4_b86_falsification_manifest_v1","dataset_reference":DATASET_REFERENCE,"dataset_sha256":scanned["dataset_sha256"],"coverage_by_symbol":scanned["coverage_by_symbol"],"validation_seal":base["validation_seal"]})
    _write(ROOT / PAYLOAD_RELATIVE, {"schema_version":"lily_l4_b86_u8_session_dates_v1","u8_members_in_order":scanned["u8_members_in_order"],"session_dates_by_symbol":scanned["session_dates_by_symbol"]})
    base.update({"outcome":"structural_provisioned","structural_summary":scanned,"access_counters":{"dataset_read_count":1,"numeric_lexeme_decode_count":0,"validation_access_count":0}}); _write(report_path, base); return base


def main(argv: list[str]) -> int:
    if argv != ["--execute-one-shot"] or not _activation(): return 2
    try: root = require_configured_path("LILY_DATA_ROOT")
    except (OSError, ValueError):
        if _claim(ROOT / MARKER_RELATIVE): _write(ROOT / REPORT_RELATIVE, {"schema_version":"lily_l4_b86_provisioning_report_v1","outcome":"provisioning_blocked","blocker":"data_root_unavailable"})
        return 1
    return 0 if provision(root, report_path=ROOT / REPORT_RELATIVE, marker_path=ROOT / MARKER_RELATIVE).get("outcome") == "structural_provisioned" else 1


if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
