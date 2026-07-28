"""Future B8.6R one-shot; the Phase-A gate never invokes this module."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from pathlib import Path
from typing import Callable
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b86r_provisioning_scanner_v2 import MAX_BYTES,ScanError,scan_dataset
from lib.provenance import git_commit

GATE_ID="l_4_breadth_b86r_provisioning_gate_v2"; DATASET_RELATIVE=Path("data/normalized/l1_yahoo_daily_v1.json"); DATASET_REFERENCE=DATASET_RELATIVE.as_posix(); EXPECTED_SHA256="6608c0ef88f4b7edaef7523738d7a172215aa4f97c8c403adeba884d6582a4dd"
ACTIVATION_RELATIVE=Path("experiments/activation_records/l_4_breadth_b86r_provisioning_activation_v2.json"); REPORT_RELATIVE=Path("reports/experiments/l_4_breadth_b86r_provisioning_report_v2.json"); MARKER_RELATIVE=Path("reports/experiments/l_4_breadth_b86r_provisioning_attempt_v2.json"); MANIFEST_RELATIVE=Path("experiments/provisioned/l_4_breadth_b86r_falsification_manifest_v2.json"); PAYLOAD_RELATIVE=Path("experiments/provisioned/l_4_breadth_b86r_u8_session_dates_v2.json")
MARKER_BYTES=b'{"schema_version":"lily_l4_b86r_attempt_v2","state":"consumed"}'
CONTRACT_ARTIFACTS={"phase_a_gate":"experiments/l_4_breadth_b86r_provisioning_gate_v2.json","phase_a_validator":"scripts/validate_l_4_breadth_b86r_provisioning_gate_v2.py","scanner":"lib/l4_b86r_provisioning_scanner_v2.py","runner":"scripts/run_l_4_breadth_b86r_provisioning_v2.py","report_schema":"schemas/l_4_breadth_b86r_provisioning_report_v2.schema.json","report_validator":"scripts/validate_l_4_breadth_b86r_provisioning_report_v2.py","activation_schema":"schemas/l_4_breadth_b86r_provisioning_activation_v2.schema.json","manifest_schema":"schemas/l_4_breadth_b86r_falsification_manifest_v2.schema.json","manifest_validator":"scripts/validate_l_4_breadth_b86r_falsification_manifest_v2.py","payload_schema":"schemas/l_4_breadth_b86r_u8_session_dates_v2.schema.json","payload_validator":"scripts/validate_l_4_breadth_b86r_u8_session_dates_v2.py"}
def limited(path:Path)->bytes:
 with path.open("rb") as h:return h.read(MAX_BYTES+1)
def identities()->dict:
 out={}
 for name,relative in CONTRACT_ARTIFACTS.items():
  raw=limited(ROOT/relative)
  if len(raw)>MAX_BYTES:raise ScanError("contract_artifact_over_limit")
  out[name]={"path":relative,"sha256":hashlib.sha256(raw).hexdigest()}
 return out
def _git_blob(commit:str,path:str)->bytes|None:
 result=subprocess.run(["git","show",f"{commit}:{path}"],cwd=ROOT,capture_output=True)
 return result.stdout if result.returncode==0 else None
def _accepted_gate(accepted:str,checkpoint:str,gate_sha:str)->bool:
 if subprocess.run(["git","merge-base","--is-ancestor",accepted,checkpoint],cwd=ROOT,capture_output=True).returncode:return False
 raw=_git_blob(accepted,CONTRACT_ARTIFACTS["phase_a_gate"])
 return raw is not None and hashlib.sha256(raw).hexdigest()==gate_sha
def activation(raw:bytes,*,activation_head:str,accepted_gate_check:Callable[[str,str,str],bool]|None=None)->dict|None:
 try: record=json.loads(raw.decode("ascii")); gate_sha=identities()["phase_a_gate"]["sha256"]
 except (UnicodeDecodeError,ValueError,ScanError):return None
 expected={"schema_version":"lily_l4_b86r_provisioning_activation_v2","gate_id":GATE_ID,"gate_sha256":gate_sha,"hermetic_ci_head_sha":record.get("accepted_gate_head_sha"),"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.6R one-shot owner authorization","scope":"one_repo_relative_falsification_container_provisioning_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}}
 accepted=record.get("accepted_gate_head_sha")
 if not isinstance(record,dict) or set(record)!=set(expected)|{"accepted_gate_head_sha","hermetic_ci_run_id"} or any(record.get(k)!=v for k,v in expected.items()) or not isinstance(accepted,str) or len(accepted)!=40 or any(c not in "0123456789abcdef" for c in accepted) or not isinstance(record.get("hermetic_ci_run_id"),int) or record["hermetic_ci_run_id"]<=0:return None
 if not (accepted_gate_check or _accepted_gate)(accepted,activation_head,gate_sha):return None
 return {"path":ACTIVATION_RELATIVE.as_posix(),"raw_sha256":hashlib.sha256(raw).hexdigest(),"content":record,"activation_checkpoint_head":activation_head}
def tracked_activation()->dict|None:
 path=ROOT/ACTIVATION_RELATIVE
 try:raw=limited(path)
 except OSError:return None
 if len(raw)>MAX_BYTES:return None
 current=git_commit(ROOT);tracked=subprocess.run(["git","ls-files","--error-unmatch",ACTIVATION_RELATIVE.as_posix()],cwd=ROOT,capture_output=True).returncode==0
 if not tracked or _git_blob("HEAD",ACTIVATION_RELATIVE.as_posix())!=raw:return None
 return activation(raw,activation_head=current)
def artifact()->dict:return {"attempted_read_count":0,"read_count":0,"observed_byte_count":None,"complete_read":False,"complete_raw_sha256":None,"bounded_prefix_sha256":None,"hash_count":0,"scan_count":0,"opaque_unsafe_lexeme_decode_count":0}
def read(path:Path,row:dict)->tuple[bytes|None,str|None]:
 row["attempted_read_count"]=1
 try:raw=limited(path)
 except FileNotFoundError:return None,"missing"
 except OSError:return None,"read_error"
 row.update({"read_count":1,"observed_byte_count":len(raw),"hash_count":1,"bounded_prefix_sha256":hashlib.sha256(raw).hexdigest()})
 if len(raw)>MAX_BYTES:return None,"input_over_limit"
 row["complete_read"]=True;row["complete_raw_sha256"]=row["bounded_prefix_sha256"]
 return raw,None
def write_all(fd:int,raw:bytes)->None:
 offset=0
 while offset<len(raw):offset+=os.write(fd,raw[offset:])
def durable(path:Path,value:dict)->None:
 path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+".tmp");fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 try:write_all(fd,json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("ascii"));os.fsync(fd)
 finally:os.close(fd)
 os.replace(temp,path)
def claim(path:Path)->bool:
 path.parent.mkdir(parents=True,exist_ok=True)
 try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 except FileExistsError:return False
 try:write_all(fd,MARKER_BYTES);os.fsync(fd)
 finally:os.close(fd)
 return True
def base(*,mode:str,consumed:bool,row:dict,provenance:dict|None)->dict:
 return {"schema_version":"lily_l4_b86r_provisioning_report_v2","order_id":"B8.6R","hypothesis_id":"L-4","mode":mode,"evidence_tier":"E0","edge_claim":"none","real_provisioning_consumed":consumed,"dataset_reference":DATASET_REFERENCE,"expected_dataset_sha256":EXPECTED_SHA256,"dataset_artifact":row,"contract_artifacts":identities(),"activation_provenance":provenance,"access_counters":{"return_value_decode_count":0,"opaque_unsafe_lexeme_decode_count":0,"validation_access_count":0},"validation_seal":{"status":"sealed_not_accessed","accessed":False},"producing_git_commit":"synthetic_fixture" if mode=="synthetic_fixture" else git_commit(ROOT)}
def outputs(scanned:dict)->tuple[dict,dict]:
 manifest={"schema_version":"lily_l4_b86r_falsification_manifest_v2","dataset_reference":DATASET_REFERENCE,"dataset_sha256":scanned["dataset_sha256"],"dataset_byte_count":scanned["dataset_byte_count"],"u8_members_in_order":scanned["u8_members_in_order"],"coverage_by_symbol":scanned["coverage_by_symbol"],"session_count":scanned["session_count"],"max_session_date":scanned["max_session_date"],"validation_seal":{"status":"sealed_not_accessed","accessed":False}}
 payload={"schema_version":"lily_l4_b86r_u8_session_dates_v2","dataset_sha256":scanned["dataset_sha256"],"u8_members_in_order":scanned["u8_members_in_order"],"session_dates_by_symbol":scanned["session_dates_by_symbol"]}
 return manifest,payload
def summary(manifest:dict,payload:dict)->str:return hashlib.sha256(json.dumps({"manifest":manifest,"payload":payload},sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("ascii")).hexdigest()
def structural(raw:bytes,*,mode="synthetic_fixture",row:dict|None=None,provenance:dict|None=None)->dict:
 row=row or {"attempted_read_count":1,"read_count":1,"observed_byte_count":len(raw),"complete_read":len(raw)<=MAX_BYTES,"complete_raw_sha256":hashlib.sha256(raw).hexdigest() if len(raw)<=MAX_BYTES else None,"bounded_prefix_sha256":hashlib.sha256(raw).hexdigest(),"hash_count":1,"scan_count":0,"opaque_unsafe_lexeme_decode_count":0}
 report=base(mode=mode,consumed=mode=="real_one_shot",row=row,provenance=provenance)
 try:scanned=scan_dataset(raw,expected_sha256=EXPECTED_SHA256 if mode=="real_one_shot" else hashlib.sha256(raw).hexdigest());row["scan_count"]=1
 except ScanError as exc:report.update({"outcome":"provisioning_blocked","blocker":str(exc)});return report
 manifest,payload=outputs(scanned);report.update({"outcome":"structural_provisioned","manifest":manifest,"payload":payload,"structural_summary_sha256":summary(manifest,payload)});return report
def run_one_shot(dataset_path:Path,*,report_path:Path,marker_path:Path,manifest_path:Path,payload_path:Path,activation_raw:bytes,activation_head:str,accepted_gate_check:Callable[[str,str,str],bool])->dict:
 provenance=activation(activation_raw,activation_head=activation_head,accepted_gate_check=accepted_gate_check)
 if provenance is None:return {"outcome":"refused_activation"}
 if not claim(marker_path):return {"outcome":"refused_already_consumed"}
 row=artifact();raw,error=read(dataset_path,row)
 if error: report=base(mode="real_one_shot",consumed=True,row=row,provenance=provenance);report.update({"outcome":"provisioning_blocked","blocker":"dataset_"+error})
 else: report=structural(raw or b"",mode="real_one_shot",row=row,provenance=provenance)
 if report["outcome"]=="structural_provisioned":durable(manifest_path,report["manifest"]);durable(payload_path,report["payload"])
 durable(report_path,report);return report
def run_phase_b()->dict:
 provenance=tracked_activation()
 if provenance is None:return {"outcome":"refused_activation"}
 if not claim(ROOT/MARKER_RELATIVE):return {"outcome":"refused_already_consumed"}
 row=artifact();raw,error=read(ROOT/DATASET_RELATIVE,row)
 if error:report=base(mode="real_one_shot",consumed=True,row=row,provenance=provenance);report.update({"outcome":"provisioning_blocked","blocker":"dataset_"+error})
 else:report=structural(raw or b"",mode="real_one_shot",row=row,provenance=provenance)
 if report["outcome"]=="structural_provisioned":durable(ROOT/MANIFEST_RELATIVE,report["manifest"]);durable(ROOT/PAYLOAD_RELATIVE,report["payload"])
 durable(ROOT/REPORT_RELATIVE,report);return report
def main(argv:list[str])->int:
 if argv!=["--execute-one-shot"]:return 2
 return 0 if run_phase_b().get("outcome")=="structural_provisioned" else 1
if __name__=="__main__":raise SystemExit(main(sys.argv[1:]))
