"""Recompute a v4 report from its exact hash-bound normalized container."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from lib.l4_b88r3_scientific_engine_v4 import SEAL, derive
from lib.l4_b88r3_lifecycle_v4 import ACTIVATION, GATE, blob, canonical as lifecycle_canonical, dependencies_ok, h40, h64
from scripts.validate_l_4_breadth_b88r3_phase_a_execution_contract_v4 import validate as validate_gate

FIELDS={"schema_version","order_id","hypothesis_id","mode","evidence_tier","edge_claim","provenance","validation_seal","access_counts","container_sha256","derived","outcome"}
PROVENANCE_FIELDS={"producing_commit","accepted_gate_head_sha","hermetic_ci_head_sha","hermetic_ci_run_id","gate_path","gate_sha256","activation_path","activation_sha256","marker_path","marker_sha256","container_path","container_sha256","structural_manifest_path","structural_manifest_sha256","u8_sessions_sha256","cutoff_inclusive","runtime_dependency_identities"}

def canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("ascii")


def _provenance_ok(provenance: dict, raw: bytes) -> bool:
    """Require exact activation, gate, dependency, session and Git ancestry."""
    try:
        gate_raw = (ROOT / GATE).read_bytes(); gate = json.loads(gate_raw.decode("ascii"))
        activation_raw = (ROOT / ACTIVATION).read_bytes(); activation = json.loads(activation_raw.decode("ascii"))
        manifest_raw = (ROOT / provenance["structural_manifest_path"]).read_bytes()
        sessions_raw = (ROOT / "experiments/provisioned/l_4_breadth_b86r13_u8_session_dates_v15.json").read_bytes()
        manifest = json.loads(manifest_raw.decode("ascii")); sessions = json.loads(sessions_raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, ValueError, KeyError):
        return False
    commit = provenance["producing_commit"]
    expected_ids = {path:item["sha256"] for path,item in gate.get("execution_binding",{}).items()}
    return (
        validate_gate().get("status") == "pass"
        and provenance["gate_sha256"] == hashlib.sha256(gate_raw).hexdigest()
        and provenance["activation_path"] == ACTIVATION
        and provenance["activation_sha256"] == hashlib.sha256(lifecycle_canonical(activation)).hexdigest()
        and provenance["container_path"] == activation.get("container_path")
        and provenance["container_sha256"] == hashlib.sha256(raw).hexdigest() == activation.get("container_sha256")
        and provenance["structural_manifest_sha256"] == hashlib.sha256(manifest_raw).hexdigest() == activation.get("structural_manifest_sha256")
        and provenance["u8_sessions_sha256"] == activation.get("u8_sessions_sha256") == hashlib.sha256(canonical([item for item in sessions.get("session_dates_by_symbol",{}).get("VTI",[]) if all(item in values for values in sessions.get("session_dates_by_symbol",{}).values())])).hexdigest()
        and manifest.get("dataset_reference") == provenance["container_path"]
        and manifest.get("dataset_sha256") == provenance["container_sha256"]
        and provenance["runtime_dependency_identities"] == expected_ids
        and blob(ROOT, commit, GATE) == gate_raw
        and dependencies_ok(ROOT, commit, gate)
    )
def validate_value(report: dict, container: dict, raw: bytes) -> dict:
    blockers=[]
    if set(report)!=FIELDS: blockers.append("closed_world")
    if {key:report.get(key) for key in ("schema_version","order_id","hypothesis_id","mode","evidence_tier","edge_claim","validation_seal")} != {"schema_version":"lily_l4_b88r3_scientific_report_v4","order_id":"B8.8R3","hypothesis_id":"L-4","mode":"future_falsification_only","evidence_tier":"E1","edge_claim":"none","validation_seal":SEAL}: blockers.append("identity")
    counts=report.get("access_counts",{})
    if not all(counts.get(key)==0 for key in ("validation_access_count","provider_network_credentials_broker_paid_paper_real_money_count")) or not all(counts.get(key,0)>0 for key in ("activation_count","production_execution_count","production_report_count","ledger_count","real_container_read_hash_scan_count","market_return_signal_position_covariance_regime_cost_pnl_count")): blockers.append("access_counts")
    provenance=report.get("provenance",{})
    if not isinstance(provenance,dict) or set(provenance)!=PROVENANCE_FIELDS or provenance.get("cutoff_inclusive")!="2015-12-31" or not h40(provenance.get("producing_commit")) or not h40(provenance.get("accepted_gate_head_sha")) or provenance.get("hermetic_ci_head_sha") != provenance.get("accepted_gate_head_sha") or not isinstance(provenance.get("hermetic_ci_run_id"),int) or provenance["hermetic_ci_run_id"] < 1 or provenance.get("gate_path") != GATE or not h64(provenance.get("gate_sha256")) or not all(h64(value) for key,value in provenance.items() if key.endswith("_sha256")) or not isinstance(provenance.get("runtime_dependency_identities"),dict) or not provenance["runtime_dependency_identities"] or not all(isinstance(path,str) and h64(digest) for path,digest in provenance.get("runtime_dependency_identities",{}).items()): blockers.append("provenance")
    digest=hashlib.sha256(raw).hexdigest()
    if digest != report.get("container_sha256") or digest != provenance.get("container_sha256"): blockers.append("container_hash")
    if not isinstance(provenance, dict) or not _provenance_ok(provenance, raw): blockers.append("provenance_binding")
    derived=derive(container,config={"u8_sessions":container.get("sessions")})
    if derived is None or report.get("derived") != derived: blockers.append("derived")
    elif report.get("outcome") != derived["outcome"]: blockers.append("outcome")
    return {"status":"pass" if not blockers else "blocked","blockers":sorted(set(blockers))}

def validate(report_path: Path, container_path: Path | None = None) -> dict:
    try:
        report=json.loads(Path(report_path).read_text("ascii")); path=Path(container_path or ROOT / report.get("provenance",{}).get("container_path","")); raw=path.read_bytes(); container=json.loads(raw.decode("utf-8"))
    except Exception: return {"status":"blocked","blockers":["unreadable_or_container"]}
    return validate_value(report,container,raw)
if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("report",type=Path); parser.add_argument("--container",type=Path); args=parser.parse_args()
    result=validate(args.report,args.container); print(json.dumps(result,sort_keys=True)); raise SystemExit(result["status"]!="pass")
