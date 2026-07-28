"""Validate the append-only, E0-only B8.6R Phase-A gate without input access."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.io import load_json
GATE=ROOT/"experiments/l_4_breadth_b86r_provisioning_gate_v2.json"; ADDENDUM=ROOT/"experiments/l_4_breadth_b86r_inspector_pre_gate_hash_incident_addendum_v1.json"
EXPECTED="6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd";U8=["VTI","VGK","EWJ","VWO","IEF","TIP","GLD","DBC"]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bound(value):
 try:return isinstance(value,dict) and isinstance(value["path"],str) and sha(ROOT/value["path"])==value["sha256"]
 except (KeyError,OSError):return False
def validate():
 try:gate=load_json(GATE);addendum=load_json(ADDENDUM)
 except (OSError,ValueError) as exc:return {"status":"blocked","blockers":[type(exc).__name__]}
 required={"schema_version":"lily_l4_b86r_provisioning_gate_v2","order_id":"B8.6R","phase":"A","gate_id":"l_4_breadth_b86r_provisioning_gate_v2","supersedes_gate_id":"l_4_breadth_b86_provisioning_gate_v1","hypothesis_id":"L-4","status":"locked_E0_repo_relative_provisioning_machinery_awaiting_inspector_acceptance_and_activation","evidence_ceiling":"E0","edge_claim":"none","validation_seal":{"status":"sealed_not_accessed","accessed":False}}
 b=[]
 if not isinstance(gate,dict) or any(gate.get(k)!=v for k,v in required.items()):b.append("identity")
 dataset={"repo_relative_path":"data/normalized/l1_yahoo_daily_v1.json","expected_sha256":EXPECTED,"schema_version":"lily_l1_daily_dataset_v1","cutoff_inclusive":"2015-12-31","u8_members_in_order":U8}
 if gate.get("dataset")!=dataset:b.append("dataset")
 if not all(bound(v) for v in gate.get("source_binding",{}).values()) or set(gate.get("source_binding",{}))!={"active_l4_v4","yahoo_daily","b85r5_gate","b85r5_consumed_result","b86_predecessor","pre_gate_hash_addendum"}:b.append("source_binding")
 impl=gate.get("implementation",{})
 if set(impl)!={"scanner","runner","report_schema","report_validator","activation_schema","manifest_schema","manifest_validator","payload_schema","payload_validator","gate_validator"} or not all(bound(v) for v in impl.values()):b.append("implementation")
 expected_addendum={"schema_version":"lily_l4_b86r_inspector_pre_gate_hash_incident_addendum_v1","event_date":"2026-07-29","event_type":"correction_of_b86_path_reference","actor":"Lily Inspector","dataset_reference":"data/normalized/l1_yahoo_daily_v1.json","observed_sha256":EXPECTED,"json_or_value_decode_count":0,"return_value_decode_count":0,"validation_access_count":0,"experimental_evidence":False,"does_not_satisfy_future_one_shot_read":True,"correction":"The Inspector command hashed the literal repo-relative path, not ${LILY_DATA_ROOT}; this is a non-evidence addendum and does not authorize or satisfy the later gated one-shot read."}
 if addendum!=expected_addendum:b.append("addendum")
 auth={"data":False,"container":False,"path_inspection":False,"environment":False,"market":False,"return":False,"value":False,"signal":False,"position":False,"covariance":False,"regime":False,"cost":False,"pnl":False,"execution":False,"report_decision":False,"ledger":False,"validation":False,"provider":False,"network":False,"credentials":False,"broker":False,"paid":False,"paper_trade":False,"real_money":False}
 if gate.get("phase_a_authorizations")!=auth or gate.get("phase_a_access_counts")!={"real_container_read":0,"environment_read":0,"market_or_return_value_decode":0,"execution":0,"validation_access":0}:b.append("seals")
 return {"status":"pass" if not b else "blocked","blockers":sorted(set(b))}
if __name__=="__main__":r=validate();print(json.dumps(r));raise SystemExit(r["status"]!="pass")
