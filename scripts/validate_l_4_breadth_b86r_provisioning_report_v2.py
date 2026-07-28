"""Closed-world semantic validator for B8.6R reports; it never opens the dataset."""
from __future__ import annotations
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b86r_provisioning_scanner_v2 import MAX_BYTES,U8
from scripts.run_l_4_breadth_b86r_provisioning_v2 import ACTIVATION_RELATIVE,DATASET_REFERENCE,EXPECTED_SHA256,GATE_ID,activation,identities,summary
from scripts.validate_l_4_breadth_b86r_provisioning_gate_v2 import validate as validate_gate
from scripts.validate_l_4_breadth_b86r_falsification_manifest_v2 import validate as validate_manifest
from scripts.validate_l_4_breadth_b86r_u8_session_dates_v2 import validate as validate_payload
HEX=re.compile(r"^[0-9a-f]{64}$");COMMIT=re.compile(r"^[0-9a-f]{40}$")
BASE={"schema_version","order_id","hypothesis_id","mode","outcome","evidence_tier","edge_claim","real_provisioning_consumed","dataset_reference","expected_dataset_sha256","dataset_artifact","contract_artifacts","activation_provenance","access_counters","validation_seal","producing_git_commit"}; AK={"attempted_read_count","read_count","observed_byte_count","complete_read","complete_raw_sha256","bounded_prefix_sha256","hash_count","scan_count","opaque_unsafe_lexeme_decode_count"}
def untouched(a):return a=={"attempted_read_count":0,"read_count":0,"observed_byte_count":None,"complete_read":False,"complete_raw_sha256":None,"bounded_prefix_sha256":None,"hash_count":0,"scan_count":0,"opaque_unsafe_lexeme_decode_count":0}
def failed(a):return isinstance(a,dict) and set(a)==AK and a["attempted_read_count"]==1 and a["read_count"]==0 and a["observed_byte_count"] is None and a["hash_count"]==a["scan_count"]==a["opaque_unsafe_lexeme_decode_count"]==0
def over(a):return isinstance(a,dict) and set(a)==AK and a["attempted_read_count"]==a["read_count"]==a["hash_count"]==1 and a["observed_byte_count"]==MAX_BYTES+1 and a["complete_read"] is False and a["complete_raw_sha256"] is None and isinstance(a["bounded_prefix_sha256"],str) and HEX.fullmatch(a["bounded_prefix_sha256"]) and a["scan_count"]==a["opaque_unsafe_lexeme_decode_count"]==0
def complete(a,scan=0):return isinstance(a,dict) and set(a)==AK and a["attempted_read_count"]==a["read_count"]==a["hash_count"]==1 and isinstance(a["observed_byte_count"],int) and 0<a["observed_byte_count"]<=MAX_BYTES and a["complete_read"] is True and isinstance(a["complete_raw_sha256"],str) and HEX.fullmatch(a["complete_raw_sha256"]) and a["bounded_prefix_sha256"]==a["complete_raw_sha256"] and a["scan_count"]==scan and a["opaque_unsafe_lexeme_decode_count"]==0
def provenance(p,producing):
 if not isinstance(p,dict) or set(p)!={"path","raw_sha256","content","activation_checkpoint_head"} or p.get("path")!=ACTIVATION_RELATIVE.as_posix() or p.get("activation_checkpoint_head")!=producing or not COMMIT.fullmatch(producing) or not isinstance(p.get("raw_sha256"),str) or not HEX.fullmatch(p["raw_sha256"]):return False
 shown=subprocess.run(["git","show",f"{producing}:{p['path']}"],cwd=ROOT,capture_output=True)
 return not shown.returncode and hashlib.sha256(shown.stdout).hexdigest()==p["raw_sha256"] and not subprocess.run(["git","merge-base","--is-ancestor",producing,"HEAD"],cwd=ROOT,capture_output=True).returncode and activation(shown.stdout,activation_head=producing) is not None and json.loads(shown.stdout.decode("ascii"))==p["content"]
def validate(report,*,provenance_check=None):
 if not isinstance(report,dict):return {"status":"blocked","blockers":["type"]}
 outcome=report.get("outcome");allowed=BASE|({"manifest","payload","structural_summary_sha256"} if outcome=="structural_provisioned" else {"blocker"} if outcome=="provisioning_blocked" else set());b=[]
 ident={"schema_version":"lily_l4_b86r_provisioning_report_v2","order_id":"B8.6R","hypothesis_id":"L-4","evidence_tier":"E0","edge_claim":"none","dataset_reference":DATASET_REFERENCE,"expected_dataset_sha256":EXPECTED_SHA256}
 if set(report)!=allowed or report.get("mode") not in ("synthetic_fixture","real_one_shot") or outcome not in ("structural_provisioned","provisioning_blocked") or any(report.get(k)!=v for k,v in ident.items()):b.append("shape")
 if report.get("contract_artifacts")!=identities() or report.get("access_counters")!={"return_value_decode_count":0,"opaque_unsafe_lexeme_decode_count":0,"validation_access_count":0} or report.get("validation_seal")!={"status":"sealed_not_accessed","accessed":False} or validate_gate().get("status")!="pass":b.append("contract")
 row=report.get("dataset_artifact")
 if outcome=="structural_provisioned":
  if not complete(row,1) or validate_manifest(report.get("manifest")).get("status")!="pass" or validate_payload(report.get("payload")).get("status")!="pass" or report["manifest"].get("dataset_sha256")!=row.get("complete_raw_sha256") or report["payload"].get("dataset_sha256")!=row.get("complete_raw_sha256") or report.get("structural_summary_sha256")!=summary(report["manifest"],report["payload"]):b.append("pass")
 else:
  blocker=report.get("blocker");valid={"dataset_missing":failed(row),"dataset_read_error":failed(row),"dataset_input_over_limit":over(row)}
  if report.get("mode")!="real_one_shot" or valid.get(blocker) is not True:b.append("blocked")
 if report.get("mode")=="synthetic_fixture":
  if report.get("real_provisioning_consumed") is not False or report.get("activation_provenance") is not None or report.get("producing_git_commit")!="synthetic_fixture":b.append("synthetic")
 elif report.get("real_provisioning_consumed") is not True or not (provenance_check or provenance)(report.get("activation_provenance"),report.get("producing_git_commit","")):b.append("provenance")
 return {"status":"pass" if not b else "blocked","blockers":sorted(set(b))}
if __name__=="__main__":print(json.dumps({"status":"blocked","blockers":["report_path_required"]}));raise SystemExit(1)
