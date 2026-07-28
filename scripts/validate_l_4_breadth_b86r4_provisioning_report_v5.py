from __future__ import annotations
import hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.draft202012_subset import ValidationError,validate as draft
from lib.l4_b86r2_provisioning_scanner_v3 import MAX_BYTES
from lib.l4_b86r3_contract_v4 import REACHABLE_BLOCKERS,category
from lib.l4_b86r4_output_contract_v5 import validate_outputs
from scripts.run_l_4_breadth_b86r4_provisioning_v5 import ACTIVATION_RELATIVE,DATASET_REFERENCE,EXPECTED_SHA256,MANIFEST_RELATIVE,PAYLOAD_RELATIVE,accepted_gate,canonical,identities
SCHEMA=ROOT/"schemas/l_4_breadth_b86r4_provisioning_report_v5.schema.json";ACTIVATION_SCHEMA=ROOT/"schemas/l_4_breadth_b86r4_provisioning_activation_v5.schema.json";HEX=re.compile(r"^[0-9a-f]{64}$");COMMIT=re.compile(r"^[0-9a-f]{40}$");AK={"attempted_read_count","read_count","observed_byte_count","complete_read","complete_raw_sha256","bounded_prefix_sha256","hash_count","scan_count","opaque_unsafe_lexeme_decode_count"}
def row_ok(a,blocker):
 if not isinstance(a,dict) or set(a)!=AK:return False
 if category(blocker)=="unread":return a["attempted_read_count"]==1 and a["read_count"]==a["hash_count"]==a["scan_count"]==0 and a["observed_byte_count"] is None and not a["complete_read"] and a["complete_raw_sha256"] is a["bounded_prefix_sha256"] is None and a["opaque_unsafe_lexeme_decode_count"]==0
 if category(blocker)=="over":return a["attempted_read_count"]==a["read_count"]==a["hash_count"]==1 and a["observed_byte_count"]==MAX_BYTES+1 and not a["complete_read"] and a["complete_raw_sha256"] is None and bool(HEX.fullmatch(str(a["bounded_prefix_sha256"]))) and a["scan_count"]==a["opaque_unsafe_lexeme_decode_count"]==0
 return a["attempted_read_count"]==a["read_count"]==a["hash_count"]==a["scan_count"]==1 and isinstance(a["observed_byte_count"],int) and 0<a["observed_byte_count"]<=MAX_BYTES and a["complete_read"] and bool(HEX.fullmatch(str(a["complete_raw_sha256"]))) and a["bounded_prefix_sha256"]==a["complete_raw_sha256"] and a["opaque_unsafe_lexeme_decode_count"]==0
def git_blob(commit,path):
 p=subprocess.run(["git","show",f"{commit}:{path}"],cwd=ROOT,capture_output=True,check=False);return p.stdout if p.returncode==0 else None
def provenance_ok(p,commit,*,blob_loader=git_blob,accepted_gate_check=accepted_gate):
 if not isinstance(p,dict) or set(p)!={"path","raw_sha256","content","activation_checkpoint_head"} or p.get("path")!=ACTIVATION_RELATIVE.as_posix() or not COMMIT.fullmatch(str(commit)) or p.get("activation_checkpoint_head")!=commit:return False
 raw=blob_loader(commit,p["path"])
 if raw is None or raw!=canonical(p["content"]) or hashlib.sha256(raw).hexdigest()!=p.get("raw_sha256"):return False
 try:draft(json.loads(ACTIVATION_SCHEMA.read_text("ascii")),p["content"])
 except (OSError,ValueError,ValidationError):return False
 c=p["content"]
 return c["accepted_gate_head_sha"]==c["hermetic_ci_head_sha"] and accepted_gate_check(c["accepted_gate_head_sha"],commit,c["gate_sha256"])
def validate(r,*,output_paths=None,blob_loader=git_blob,accepted_gate_check=accepted_gate):
 b=[]
 try:draft(json.loads(SCHEMA.read_text("ascii")),r)
 except (OSError,ValueError,ValidationError):b.append("schema")
 if not isinstance(r,dict):return {"status":"blocked","blockers":["type"]}
 if r.get("contract_artifacts")!=identities() or r.get("dataset_reference")!=DATASET_REFERENCE or r.get("expected_dataset_sha256")!=EXPECTED_SHA256 or r.get("access_counters")!={"return_value_decode_count":0,"opaque_unsafe_lexeme_decode_count":0,"validation_access_count":0} or r.get("validation_seal")!={"status":"sealed_not_accessed","accessed":False}:b.append("contract")
 if r.get("mode")=="synthetic_fixture":
  if r.get("real_provisioning_consumed") or r.get("activation_provenance") is not None or r.get("producing_git_commit")!="synthetic_fixture":b.append("mode")
 elif r.get("mode")=="real_one_shot":
  if not r.get("real_provisioning_consumed") or not provenance_ok(r.get("activation_provenance"),r.get("producing_git_commit"),blob_loader=blob_loader,accepted_gate_check=accepted_gate_check):b.append("provenance")
 else:b.append("mode")
 if r.get("outcome")=="provisioning_blocked":
  if r.get("blocker") not in REACHABLE_BLOCKERS or not row_ok(r.get("dataset_artifact"),r.get("blocker")):b.append("blocked")
 elif r.get("outcome")=="structural_provisioned":
  m,p,ids=r.get("manifest"),r.get("payload"),r.get("output_artifacts")
  if not row_ok(r.get("dataset_artifact"),"dataset_hash_mismatch") or not validate_outputs(m,p) or not isinstance(ids,dict) or set(ids)!={"manifest","payload"} or r.get("structural_summary_sha256")!=hashlib.sha256(canonical({"manifest":m,"payload":p})).hexdigest():b.append("success")
  else:
   row=r["dataset_artifact"]
   if m["dataset_sha256"]!=row["complete_raw_sha256"] or m["dataset_byte_count"]!=row["observed_byte_count"]:b.append("binding")
   for name,value,path in zip(("manifest","payload"),(m,p),output_paths or (ROOT/MANIFEST_RELATIVE,ROOT/PAYLOAD_RELATIVE),strict=True):
    raw=canonical(value);want={"path":Path(path).as_posix(),"raw_sha256":hashlib.sha256(raw).hexdigest(),"byte_count":len(raw)}
    if ids.get(name)!=want:b.append("identity")
    elif r.get("mode")=="real_one_shot":
     try: ok=Path(path).read_bytes()==raw
     except OSError:ok=False
     if not ok:b.append("identity")
 else:b.append("outcome")
 return {"status":"pass" if not b else "blocked","blockers":sorted(set(b))}
