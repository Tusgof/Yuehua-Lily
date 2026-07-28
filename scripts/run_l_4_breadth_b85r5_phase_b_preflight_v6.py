"""Future v6 preflight; Phase-A only defines this inert contract."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from pathlib import Path
from typing import Any,Callable
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.environment import require_configured_path
from lib.l4_b85r5_structural_scanner_v6 import MAX_BYTES,ScanError,scan_manifest,scan_payload
from lib.provenance import git_commit
MANIFEST_RELATIVE=Path("sealed/l4_b85r5/l4_b85r5_structural_manifest_v6.json"); PAYLOAD_RELATIVE=Path("sealed/l4_b85r5/l4_b85r5_u8_symbol_session_dates_v6.json")
MANIFEST_REFERENCE="${LILY_DATA_ROOT}/sealed/l4_b85r5/l4_b85r5_structural_manifest_v6.json"; PAYLOAD_REFERENCE="${LILY_DATA_ROOT}/sealed/l4_b85r5/l4_b85r5_u8_symbol_session_dates_v6.json"
CONTAINER_IDENTITY="lily-l4-falsification-pre2016-v6"; GATE_ID="l_4_breadth_b85r5_phase_a_activation_order_v6"
ACTIVATION_RECORD_RELATIVE=Path("experiments/activation_records/l_4_breadth_b85r5_phase_b_activation_v6.json"); REPORT_RELATIVE=Path("reports/experiments/l_4_breadth_b85r5_phase_b_preflight_report_v6.json"); MARKER_RELATIVE=Path("reports/experiments/l_4_breadth_b85r5_phase_b_preflight_attempt_v6.json")
MARKER_BYTES=b'{"schema_version":"lily_l4_b85r5_attempt_v6","state":"consumed"}'
CONTRACT_ARTIFACTS={"phase_a_gate":"experiments/l_4_breadth_b85r5_phase_a_activation_order_v6.json","phase_a_validator":"scripts/validate_l_4_breadth_b85r5_phase_a_activation_order_v6.py","scanner":"lib/l4_b85r5_structural_scanner_v6.py","runner":"scripts/run_l_4_breadth_b85r5_phase_b_preflight_v6.py","report_schema":"schemas/l_4_breadth_b85r5_structural_preflight_report_v6.schema.json","report_validator":"scripts/validate_l_4_breadth_b85r5_structural_preflight_report_v6.py","activation_schema":"schemas/l_4_breadth_b85r5_phase_b_activation_v6.schema.json"}

def limited(path:Path)->bytes:
 with path.open("rb") as h:return h.read(MAX_BYTES+1)
def identities()->dict:
 out={}
 for name,path in CONTRACT_ARTIFACTS.items():
  raw=limited(ROOT/path)
  if len(raw)>MAX_BYTES:raise ScanError("contract_artifact_over_limit")
  out[name]={"path":path,"sha256":hashlib.sha256(raw).hexdigest()}
 return out
def _git_blob(commit:str,path:str)->bytes|None:
 p=subprocess.run(["git","show",f"{commit}:{path}"],cwd=ROOT,capture_output=True)
 return p.stdout if p.returncode==0 else None
def _accepted_gate(accepted:str,checkpoint:str,gate_sha:str)->bool:
 if subprocess.run(["git","merge-base","--is-ancestor",accepted,checkpoint],cwd=ROOT,capture_output=True).returncode:return False
 raw=_git_blob(accepted,CONTRACT_ARTIFACTS["phase_a_gate"])
 return raw is not None and hashlib.sha256(raw).hexdigest()==gate_sha
def activation(raw:bytes,*,activation_head:str,accepted_gate_check:Callable[[str,str,str],bool]|None=None)->dict|None:
 try:record=json.loads(raw.decode("ascii")); gate_sha=identities()["phase_a_gate"]["sha256"]
 except (ValueError,UnicodeDecodeError,ScanError):return None
 if not isinstance(record,dict):return None
 expected={"schema_version":"lily_l4_b85r5_phase_b_activation_v6","gate_id":GATE_ID,"gate_sha256":gate_sha,"hermetic_ci_head_sha":record.get("accepted_gate_head_sha"),"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.5R5 Phase B owner authorization","scope":"one_structural_u8_preflight_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}}
 accepted=record.get("accepted_gate_head_sha")
 if set(record)!=set(expected)|{"accepted_gate_head_sha","hermetic_ci_run_id"} or not all(record.get(k)==v for k,v in expected.items()) or not isinstance(accepted,str) or len(accepted)!=40 or any(c not in "0123456789abcdef" for c in accepted) or not isinstance(record.get("hermetic_ci_run_id"),int) or record["hermetic_ci_run_id"]<=0:return None
 if not (accepted_gate_check or _accepted_gate)(accepted,activation_head,gate_sha):return None
 return {"path":ACTIVATION_RECORD_RELATIVE.as_posix(),"raw_sha256":hashlib.sha256(raw).hexdigest(),"content":record,"activation_checkpoint_head":activation_head}
def tracked_activation()->dict|None:
 path=ROOT/ACTIVATION_RECORD_RELATIVE
 try:raw=limited(path)
 except OSError:return None
 if len(raw)>MAX_BYTES:return None
 current=git_commit(ROOT); tracked=subprocess.run(["git","ls-files","--error-unmatch",ACTIVATION_RECORD_RELATIVE.as_posix()],cwd=ROOT,capture_output=True).returncode==0
 if not tracked or _git_blob("HEAD",ACTIVATION_RECORD_RELATIVE.as_posix())!=raw:return None
 return activation(raw,activation_head=current)
def artifact()->dict:
 return {"attempted_read_count":0,"read_count":0,"observed_byte_count":None,"complete_read":False,"complete_raw_sha256":None,"bounded_prefix_sha256":None,"hash_count":0,"scan_count":0,"minimal_ascii_decode_count":0}
def from_raw(raw:bytes,*,attempted:int=0)->dict:
 complete=len(raw)<=MAX_BYTES; digest=hashlib.sha256(raw).hexdigest()
 return {"attempted_read_count":attempted,"read_count":attempted,"observed_byte_count":len(raw),"complete_read":complete,"complete_raw_sha256":digest if complete else None,"bounded_prefix_sha256":digest,"hash_count":1,"scan_count":0,"minimal_ascii_decode_count":0}
def read(path:Path,row:dict)->tuple[bytes|None,str|None]:
 row["attempted_read_count"]=1
 try:raw=limited(path)
 except FileNotFoundError:return None,"missing"
 except OSError:return None,"read_error"
 row.update({"read_count":1,"observed_byte_count":len(raw),"hash_count":1,"bounded_prefix_sha256":hashlib.sha256(raw).hexdigest()})
 if len(raw)>MAX_BYTES:return None,"input_over_limit"
 row["complete_read"]=True;row["complete_raw_sha256"]=row["bounded_prefix_sha256"]
 return raw,None
def base(*,mode:str,consumed:bool,rows:dict,provenance:dict|None)->dict:
 return {"schema_version":"lily_l4_b85r5_structural_preflight_report_v6","order_id":"B8.5R5","hypothesis_id":"L-4","mode":mode,"evidence_tier":"E0","edge_claim":"none","real_preflight_consumed":consumed,"storage_references":{"manifest":MANIFEST_REFERENCE,"payload":PAYLOAD_REFERENCE},"container_identity":CONTAINER_IDENTITY,"artifacts":rows,"contract_artifacts":identities(),"activation_provenance":provenance,"access_counters":{"return_value_decode_count":0,"validation_access_count":0},"validation_seal":{"status":"sealed_not_accessed","accessed":False},"producing_git_commit":"synthetic_fixture" if mode=="synthetic_fixture" else git_commit(ROOT)}
def structural_summary_sha256(manifest:dict,payload:dict)->str:return hashlib.sha256(json.dumps({"manifest":manifest,"payload":payload},ensure_ascii=True,sort_keys=True,separators=(",",":")).encode("ascii")).hexdigest()
def structural(manifest_raw:bytes,payload_raw:bytes,*,mode:str="synthetic_fixture",rows:dict|None=None,provenance:dict|None=None)->dict:
 rows=rows or {"manifest":from_raw(manifest_raw),"payload":from_raw(payload_raw)}; report=base(mode=mode,consumed=mode=="real_one_shot",rows=rows,provenance=provenance)
 try:
  rows["manifest"]["scan_count"]=1; manifest=scan_manifest(manifest_raw,expected_identity=CONTAINER_IDENTITY,expected_payload_path=PAYLOAD_RELATIVE.as_posix()); rows["manifest"]["minimal_ascii_decode_count"]=manifest["minimal_ascii_decode_count"]
 except ScanError as exc:report.update({"outcome":"preflight_blocked","blocker":"structural_manifest_"+str(exc)});return report
 try:
  rows["payload"]["scan_count"]=1; payload=scan_payload(payload_raw); rows["payload"]["minimal_ascii_decode_count"]=payload["minimal_ascii_decode_count"]
 except ScanError as exc:report.update({"outcome":"preflight_blocked","blocker":"structural_payload_"+str(exc)});return report
 if manifest["metadata_sha256"]!=payload["complete_raw_sha256"]:report.update({"outcome":"preflight_blocked","blocker":"manifest_payload_hash_mismatch"});return report
 report.update({"outcome":"structural_pass","manifest":manifest,"payload":payload,"structural_summary_sha256":structural_summary_sha256(manifest,payload)});return report
def write_all(fd:int,raw:bytes)->None:
 n=0
 while n<len(raw):n+=os.write(fd,raw[n:])
def durable(path:Path,report:dict)->None:
 path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+".tmp");fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 try:write_all(fd,json.dumps(report,ensure_ascii=True,separators=(",",":")).encode("ascii"));os.fsync(fd)
 finally:os.close(fd)
 os.replace(temp,path)
def claim(path:Path)->bool:
 path.parent.mkdir(parents=True,exist_ok=True)
 try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 except FileExistsError:return False
 try:write_all(fd,MARKER_BYTES);os.fsync(fd)
 finally:os.close(fd)
 return True
def blocked(rows:dict,blocker:str,provenance:dict)->dict:
 r=base(mode="real_one_shot",consumed=True,rows=rows,provenance=provenance);r.update({"outcome":"preflight_blocked","blocker":blocker});return r
def after_claim(root:Path,report_path:Path,provenance:dict)->dict:
 rows={"manifest":artifact(),"payload":artifact()};m,err=read(root/MANIFEST_RELATIVE,rows["manifest"])
 if err:r=blocked(rows,"manifest_"+err,provenance)
 else:
  p,err=read(root/PAYLOAD_RELATIVE,rows["payload"])
  r=blocked(rows,"payload_"+err,provenance) if err else structural(m or b"",p or b"",mode="real_one_shot",rows=rows,provenance=provenance)
 durable(report_path,r);return r
def run_one_shot(root:Path,*,report_path:Path,attempt_marker_path:Path,activation_raw:bytes,activation_head:str,accepted_gate_check:Callable[[str,str,str],bool])->dict:
 p=activation(activation_raw,activation_head=activation_head,accepted_gate_check=accepted_gate_check)
 if p is None:return {"outcome":"refused_activation"}
 if not claim(attempt_marker_path):return {"outcome":"refused_already_consumed"}
 return after_claim(root,report_path,p)
def run_phase_b()->dict:
 p=tracked_activation()
 if p is None:return {"outcome":"refused_activation"}
 if not claim(ROOT/MARKER_RELATIVE):return {"outcome":"refused_already_consumed"}
 rows={"manifest":artifact(),"payload":artifact()}
 try:root=require_configured_path("LILY_DATA_ROOT")
 except (OSError,ValueError):r=blocked(rows,"data_root_unavailable",p);durable(ROOT/REPORT_RELATIVE,r);return r
 return after_claim(root,ROOT/REPORT_RELATIVE,p)
def main(argv:list[str])->int:
 if argv!=["--execute-one-shot"]:return 2
 return 0 if run_phase_b().get("outcome")=="structural_pass" else 1
if __name__=="__main__":raise SystemExit(main(sys.argv[1:]))
