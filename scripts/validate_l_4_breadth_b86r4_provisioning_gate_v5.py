from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b86r2_provisioning_scanner_v3 import CUTOFF,MAX_BYTES,U8
from lib.l4_b86r3_contract_v4 import OVER_BLOCKER,READ_BLOCKERS,SCAN_BLOCKERS
GATE=ROOT/"experiments/l_4_breadth_b86r4_provisioning_gate_v5.json"
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def validate(path=GATE):
 try:g=json.loads(Path(path).read_text("ascii"))
 except (OSError,ValueError) as e:return {"status":"blocked","blockers":[type(e).__name__]}
 required={"schema_version":"lily_l4_b86r4_provisioning_gate_v5","order_id":"B8.6R4","phase":"A","gate_id":"l_4_breadth_b86r4_provisioning_gate_v5","supersedes_gate_id":"l_4_breadth_b86r3_provisioning_gate_v4","hypothesis_id":"L-4","status":"locked_E0_v5_remediation_awaiting_inspector_acceptance_and_activation","evidence_ceiling":"E0","edge_claim":"none","dataset":{"repo_relative_path":"data/normalized/l1_yahoo_daily_v1.json","expected_sha256":"6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd","schema_version":"lily_l1_daily_dataset_v1","cutoff_inclusive":CUTOFF,"u8_members_in_order":list(U8),"max_bounded_read_bytes":MAX_BYTES+1},"execution_flag":"--execute-one-shot","report_path":"reports/experiments/l_4_breadth_b86r4_provisioning_report_v5.json","marker_path":"reports/experiments/l_4_breadth_b86r4_provisioning_attempt_v5.json","validation_seal":{"status":"sealed_not_accessed","accessed":False}}
 b=[]
 if any(g.get(k)!=v for k,v in required.items()):b.append("identity")
 for group,names in (("source_binding",{"rejected_v4","science_v4","consumed_b85r5_result"}),("implementation",{"output_contract","runner","report_schema","activation_schema","manifest_schema","payload_schema","output_validator","report_validator","gate_validator"})):
  values=g.get(group)
  if not isinstance(values,dict) or set(values)!=names:b.append(group);continue
  for item in values.values():
   try:
    if set(item)!={"path","sha256"} or sha(ROOT/item["path"])!=item["sha256"]:b.append(group)
   except (KeyError,OSError):b.append(group)
 matrix={"read_unavailable":sorted(READ_BLOCKERS),"bounded_read_over_limit":OVER_BLOCKER,"opaque_structural_scan":sorted(SCAN_BLOCKERS),"all_blockers_are_reportable":True,"fabricated_blocker_rejected":True}
 if g.get("blocker_matrix")!=matrix:b.append("blocker_matrix")
 lifecycle={"activation_path":"experiments/activation_records/l_4_breadth_b86r4_provisioning_activation_v5.json","activation_is_new_tracked_checkpoint":True,"requires_inspector_accepted_gate":True,"requires_exact_sha_hermetic_ci":True,"accepted_gate_head_must_be_ancestor_of_activation_head":True,"accepted_gate_blob_must_match_gate_sha256":True,"activation_blob_must_exist_at_producing_commit":True,"activation_json_must_be_canonical_bytes":True,"marker_claim_before_dataset_read":True,"marker_is_atomic_one_shot":True,"first_report_is_immutable":True,"execution_requires_exact_flag":"--execute-one-shot"}
 if g.get("future_activation_lifecycle")!=lifecycle:b.append("lifecycle")
 auth=g.get("phase_a_authorizations",{});counts=g.get("phase_a_access_counts",{})
 if not auth or any(auth.values()):b.append("authorizations")
 if set(counts)!={"real_container_read","environment_read","market_or_return_value_decode","execution","validation_access"} or any(counts.values()):b.append("access_counts")
 return {"status":"pass" if not b else "blocked","blockers":sorted(set(b))}
if __name__=="__main__":
 r=validate();print(json.dumps(r));raise SystemExit(r["status"]!="pass")
