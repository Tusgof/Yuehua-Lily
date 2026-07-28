"""Future B8.6R4 one-shot; only injected synthetic paths are used in tests."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b86r2_provisioning_scanner_v3 import MAX_BYTES,ScanError,scan_dataset
from lib.provenance import git_commit
from lib.l4_b86r4_output_contract_v5 import MANIFEST_SCHEMA,PAYLOAD_SCHEMA,SEAL
GATE_ID="l_4_breadth_b86r4_provisioning_gate_v5";DATASET_RELATIVE=Path("data/normalized/l1_yahoo_daily_v1.json");DATASET_REFERENCE=DATASET_RELATIVE.as_posix();EXPECTED_SHA256="6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd"
ACTIVATION_RELATIVE=Path("experiments/activation_records/l_4_breadth_b86r4_provisioning_activation_v5.json");REPORT_RELATIVE=Path("reports/experiments/l_4_breadth_b86r4_provisioning_report_v5.json");MARKER_RELATIVE=Path("reports/experiments/l_4_breadth_b86r4_provisioning_attempt_v5.json");MANIFEST_RELATIVE=Path("experiments/provisioned/l_4_breadth_b86r4_falsification_manifest_v5.json");PAYLOAD_RELATIVE=Path("experiments/provisioned/l_4_breadth_b86r4_u8_session_dates_v5.json")
MARKER_BYTES=b'{"schema_version":"lily_l4_b86r4_attempt_v5","state":"consumed"}'
CONTRACT_ARTIFACTS={"phase_a_gate":"experiments/l_4_breadth_b86r4_provisioning_gate_v5.json","phase_a_validator":"scripts/validate_l_4_breadth_b86r4_provisioning_gate_v5.py","output_contract":"lib/l4_b86r4_output_contract_v5.py","runner":"scripts/run_l_4_breadth_b86r4_provisioning_v5.py","report_schema":"schemas/l_4_breadth_b86r4_provisioning_report_v5.schema.json","report_validator":"scripts/validate_l_4_breadth_b86r4_provisioning_report_v5.py","activation_schema":"schemas/l_4_breadth_b86r4_provisioning_activation_v5.schema.json","manifest_schema":"schemas/l_4_breadth_b86r4_falsification_manifest_v5.schema.json","payload_schema":"schemas/l_4_breadth_b86r4_u8_session_dates_v5.schema.json","output_validator":"scripts/validate_l_4_breadth_b86r4_falsification_outputs_v5.py"}
def canonical(value):return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("ascii")
def limited(path):
 with path.open("rb") as h:return h.read(MAX_BYTES+1)
def identities():
 out={}
 for name,path in CONTRACT_ARTIFACTS.items():
  raw=limited(ROOT/path)
  if len(raw)>MAX_BYTES:raise ScanError("contract_artifact_over_limit")
  out[name]={"path":path,"sha256":hashlib.sha256(raw).hexdigest()}
 return out
def blob(commit,path):
 p=subprocess.run(["git","show",f"{commit}:{path}"],cwd=ROOT,capture_output=True,check=False);return p.stdout if p.returncode==0 else None
def accepted_gate(accepted,checkpoint,gate_sha):
 raw=blob(accepted,CONTRACT_ARTIFACTS["phase_a_gate"]);p=subprocess.run(["git","merge-base","--is-ancestor",accepted,checkpoint],cwd=ROOT,capture_output=True,check=False)
 return p.returncode==0 and raw is not None and hashlib.sha256(raw).hexdigest()==gate_sha
def activation(raw,*,activation_head,accepted_gate_check=None):
 try:value=json.loads(raw.decode("ascii"));gate_sha=identities()["phase_a_gate"]["sha256"]
 except (UnicodeDecodeError,ValueError,ScanError):return None
 expected={"schema_version":"lily_l4_b86r4_provisioning_activation_v5","gate_id":GATE_ID,"gate_sha256":gate_sha,"hermetic_ci_head_sha":value.get("accepted_gate_head_sha"),"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.6R4 one-shot owner authorization","scope":"one_repo_relative_falsification_container_provisioning_only","validation_seal":SEAL}
 accepted=value.get("accepted_gate_head_sha")
 if raw!=canonical(value) or not isinstance(value,dict) or set(value)!=set(expected)|{"accepted_gate_head_sha","hermetic_ci_run_id"} or any(value.get(k)!=v for k,v in expected.items()) or not isinstance(accepted,str) or len(accepted)!=40 or any(c not in "0123456789abcdef" for c in accepted) or not isinstance(value.get("hermetic_ci_run_id"),int) or value["hermetic_ci_run_id"]<1:return None
 if not (accepted_gate_check or accepted_gate)(accepted,activation_head,gate_sha):return None
 return {"path":ACTIVATION_RELATIVE.as_posix(),"raw_sha256":hashlib.sha256(raw).hexdigest(),"content":value,"activation_checkpoint_head":activation_head}
def artifact():return {"attempted_read_count":0,"read_count":0,"observed_byte_count":None,"complete_read":False,"complete_raw_sha256":None,"bounded_prefix_sha256":None,"hash_count":0,"scan_count":0,"opaque_unsafe_lexeme_decode_count":0}
def read(path,row):
 row["attempted_read_count"]=1
 try:raw=limited(path)
 except FileNotFoundError:return None,"dataset_missing"
 except OSError:return None,"dataset_read_error"
 row.update({"read_count":1,"observed_byte_count":len(raw),"hash_count":1,"bounded_prefix_sha256":hashlib.sha256(raw).hexdigest()})
 if len(raw)>MAX_BYTES:return None,"dataset_input_over_limit"
 row["complete_read"]=True;row["complete_raw_sha256"]=row["bounded_prefix_sha256"];return raw,None
def write_raw(path,raw):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+".tmp");fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 try:
  pos=0
  while pos<len(raw):pos+=os.write(fd,raw[pos:])
  os.fsync(fd)
 finally:os.close(fd)
 os.replace(tmp,path)
def claim(path):
 path.parent.mkdir(parents=True,exist_ok=True)
 try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 except FileExistsError:return False
 try:os.write(fd,MARKER_BYTES);os.fsync(fd)
 finally:os.close(fd)
 return True
def base(mode,row,provenance):return {"schema_version":"lily_l4_b86r4_provisioning_report_v5","order_id":"B8.6R4","hypothesis_id":"L-4","mode":mode,"evidence_tier":"E0","edge_claim":"none","real_provisioning_consumed":mode=="real_one_shot","dataset_reference":DATASET_REFERENCE,"expected_dataset_sha256":EXPECTED_SHA256,"dataset_artifact":row,"contract_artifacts":identities(),"activation_provenance":provenance,"access_counters":{"return_value_decode_count":0,"opaque_unsafe_lexeme_decode_count":0,"validation_access_count":0},"validation_seal":SEAL,"producing_git_commit":"synthetic_fixture" if mode=="synthetic_fixture" else git_commit(ROOT)}
def outputs(scanned):
 return ({"schema_version":MANIFEST_SCHEMA,"dataset_reference":DATASET_REFERENCE,"dataset_sha256":scanned["dataset_sha256"],"dataset_byte_count":scanned["dataset_byte_count"],"u8_members_in_order":scanned["u8_members_in_order"],"coverage_by_symbol":scanned["coverage_by_symbol"],"session_count":scanned["session_count"],"max_session_date":scanned["max_session_date"],"validation_seal":SEAL},{"schema_version":PAYLOAD_SCHEMA,"dataset_sha256":scanned["dataset_sha256"],"u8_members_in_order":scanned["u8_members_in_order"],"session_dates_by_symbol":scanned["session_dates_by_symbol"]})
def identity(path,raw):return {"path":Path(path).as_posix(),"raw_sha256":hashlib.sha256(raw).hexdigest(),"byte_count":len(raw)}
def structural(raw,*,mode="synthetic_fixture",row=None,provenance=None,output_paths=None):
 row=row or {**artifact(),"attempted_read_count":1,"read_count":1,"observed_byte_count":len(raw),"complete_read":len(raw)<=MAX_BYTES,"complete_raw_sha256":hashlib.sha256(raw).hexdigest() if len(raw)<=MAX_BYTES else None,"bounded_prefix_sha256":hashlib.sha256(raw).hexdigest(),"hash_count":1};r=base(mode,row,provenance);row["scan_count"]=1
 try:s=scan_dataset(raw,expected_sha256=EXPECTED_SHA256 if mode=="real_one_shot" else hashlib.sha256(raw).hexdigest())
 except ScanError as e:r.update({"outcome":"provisioning_blocked","blocker":str(e)});return r
 m,p=outputs(s);mr,pr=canonical(m),canonical(p);mp,pp=output_paths or (ROOT/MANIFEST_RELATIVE,ROOT/PAYLOAD_RELATIVE);r.update({"outcome":"structural_provisioned","manifest":m,"payload":p,"output_artifacts":{"manifest":identity(mp,mr),"payload":identity(pp,pr)},"structural_summary_sha256":hashlib.sha256(canonical({"manifest":m,"payload":p})).hexdigest()});return r
def run_one_shot(dataset_path,*,report_path,marker_path,manifest_path,payload_path,activation_raw,activation_head,accepted_gate_check):
 p=activation(activation_raw,activation_head=activation_head,accepted_gate_check=accepted_gate_check)
 if p is None:return {"outcome":"refused_activation"}
 if not claim(marker_path):return {"outcome":"refused_already_consumed"}
 row=artifact();raw,error=read(dataset_path,row);r=base("real_one_shot",row,p) if error else structural(raw,mode="real_one_shot",row=row,provenance=p,output_paths=(manifest_path,payload_path))
 if error:r.update({"outcome":"provisioning_blocked","blocker":error})
 if r["outcome"]=="structural_provisioned":write_raw(manifest_path,canonical(r["manifest"]));write_raw(payload_path,canonical(r["payload"]))
 write_raw(report_path,canonical(r));return r
def main(argv):return 2 if argv!=["--execute-one-shot"] else 1
if __name__=="__main__":raise SystemExit(main(sys.argv[1:]))
