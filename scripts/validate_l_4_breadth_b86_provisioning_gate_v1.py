"""Validate B8.6's E0 provisioning gate and its disclosed pre-gate incident."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from lib.io import load_json
GATE=ROOT/"experiments/l_4_breadth_b86_provisioning_gate_v1.json"
INCIDENT=ROOT/"experiments/l_4_breadth_b86_inspector_pre_gate_hash_incident_v1.json"
EXPECTED_HASH="6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd"
U8=["VTI","VGK","EWJ","VWO","IEF","TIP","GLD","DBC"]
def sha(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def validate()->dict:
 try: gate=load_json(GATE); incident=load_json(INCIDENT)
 except (OSError,ValueError) as exc:return {"status":"blocked","blockers":[type(exc).__name__]}
 required={"schema_version":"lily_l4_b86_provisioning_gate_v1","order_id":"B8.6","phase":"A","gate_id":"l_4_breadth_b86_provisioning_gate_v1","hypothesis_id":"L-4","status":"locked_E0_no_data_provisioning_machinery_only","evidence_ceiling":"E0","edge_claim":"none","validation_seal":{"status":"sealed_not_accessed","accessed":False}}
 blocked=[]
 if not all(gate.get(k)==v for k,v in required.items()):blocked.append("gate_identity")
 data=gate.get("dataset",{})
 if data!={"repo_relative_path":"data/normalized/l1_yahoo_daily_v1.json","storage_reference":"${LILY_DATA_ROOT}/data/normalized/l1_yahoo_daily_v1.json","expected_sha256":EXPECTED_HASH,"schema_version":"lily_l1_daily_dataset_v1","cutoff_inclusive":"2015-12-31","u8_members_in_order":U8}:blocked.append("dataset_contract")
 sources=gate.get("source_binding",{})
 for name in ("active_l4_v4","yahoo_daily","b85r5_gate","b85r5_consumed_result","pre_gate_hash_incident"):
  value=sources.get(name,{})
  try:
   if sha(ROOT/value["path"])!=value["sha256"]:blocked.append("source_binding")
  except (KeyError,OSError):blocked.append("source_binding")
 if incident!={"schema_version":"lily_l4_b86_inspector_pre_gate_hash_incident_v1","event_date":"2026-07-29","event_type":"out_of_gate_hash_only_byte_read","actor":"Lily Inspector","dataset_reference":"${LILY_DATA_ROOT}/data/normalized/l1_yahoo_daily_v1.json","observed_sha256":EXPECTED_HASH,"json_or_value_decode_count":0,"return_value_decode_count":0,"validation_access_count":0,"experimental_evidence":False,"does_not_satisfy_future_one_shot_read":True}:blocked.append("incident")
 if gate.get("authorizations")!={"container":False,"environment":False,"market":False,"return":False,"value":False,"validation":False,"execution":False,"research_decision":False} or gate.get("access_counters")!={"real_container_read":0,"real_container_hash":0,"numeric_lexeme_decode":0,"validation_access":0}:blocked.append("seals")
 return {"status":"pass" if not blocked else "blocked","blockers":sorted(set(blocked))}
if __name__=="__main__":
 r=validate();print(json.dumps(r));raise SystemExit(r["status"]!="pass")
