"""Strict v5 report validator with non-circular activation checkpoint provenance."""
from __future__ import annotations
import hashlib,json,re,subprocess,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b85r4_structural_scanner_v5 import CUTOFF,MAX_BYTES,U8
from scripts.run_l_4_breadth_b85r4_phase_b_preflight_v5 import ACTIVATION_RECORD_RELATIVE,CONTAINER_IDENTITY,GATE_ID,MANIFEST_REFERENCE,PAYLOAD_REFERENCE,structural_summary_sha256,synthetic,identities
from scripts.validate_l_4_breadth_b85r4_phase_a_activation_order_v5 import validate as validate_gate
FIX=ROOT/"tests/fixtures/l4_b85r4"; MANIFEST=FIX/"structural_manifest_v5.json"; PAYLOAD=FIX/"u8_symbol_session_dates_v5.json"
HEX=re.compile(r"^[0-9a-f]{64}$"); COMMIT=re.compile(r"^[0-9a-f]{40}$")
BASE={"schema_version","order_id","hypothesis_id","mode","outcome","evidence_tier","edge_claim","real_preflight_consumed","storage_references","container_identity","artifacts","contract_artifacts","activation_provenance","access_counters","validation_seal","producing_git_commit"}
AK={"attempted_read_count","read_count","observed_byte_count","complete_read","complete_raw_sha256","bounded_prefix_sha256","hash_count","scan_count","minimal_ascii_decode_count"}
def valid_artifact(a:object,summary:dict,synthetic_mode:bool)->bool:
 if not isinstance(a,dict) or set(a)!=AK:return False
 if not all(isinstance(a[k],int) and a[k]>=0 for k in ("attempted_read_count","read_count","observed_byte_count","hash_count","scan_count","minimal_ascii_decode_count")) or not isinstance(a["complete_read"],bool):return False
 if not isinstance(a["bounded_prefix_sha256"],str) or not HEX.fullmatch(a["bounded_prefix_sha256"]):return False
 if a["complete_read"] and (not isinstance(a["complete_raw_sha256"],str) or not HEX.fullmatch(a["complete_raw_sha256"]) or a["complete_raw_sha256"]!=a["bounded_prefix_sha256"]):return False
 if not a["complete_read"] and a["complete_raw_sha256"] is not None:return False
 return a["complete_read"] and a["complete_raw_sha256"]==summary["complete_raw_sha256"] and a["observed_byte_count"]==summary["observed_byte_count"] and a["scan_count"]==1 and a["minimal_ascii_decode_count"]==summary["minimal_ascii_decode_count"] and (a["attempted_read_count"],a["read_count"])==((0,0) if synthetic_mode else (1,1))
def valid_payload(p:object)->bool:
 if not isinstance(p,dict) or set(p)!={"complete_raw_sha256","observed_byte_count","u8_members_in_order","session_count","session_counts_by_symbol","session_dates_by_symbol","max_session_date","minimal_ascii_decode_count"}:return False
 if not isinstance(p.get("complete_raw_sha256"),str) or not HEX.fullmatch(p["complete_raw_sha256"]) or not isinstance(p.get("observed_byte_count"),int) or p["observed_byte_count"]<1 or p["u8_members_in_order"]!=list(U8) or not isinstance(p.get("session_count"),int) or not isinstance(p.get("minimal_ascii_decode_count"),int) or not isinstance(p.get("max_session_date"),str):return False
 dates=p.get("session_dates_by_symbol"); counts=p.get("session_counts_by_symbol")
 try:
  if not isinstance(dates,dict) or not isinstance(counts,dict) or set(dates)!=set(U8) or set(counts)!=set(U8) or any(not isinstance(dates[s],list) or dates[s]!=sorted(set(dates[s])) or not dates[s] or not isinstance(counts[s],int) or counts[s]!=len(dates[s]) or any(date.fromisoformat(x).isoformat()!=x or x>CUTOFF for x in dates[s]) for s in U8):return False
 except (TypeError,ValueError):return False
 flat=[x for s in U8 for x in dates[s]]
 return p["session_count"]==len(flat) and p["max_session_date"]==max(flat) and p["minimal_ascii_decode_count"]==len(flat)+len(U8)+1
def blob_at(commit:str,path:str)->bytes|None:
 p=subprocess.run(["git","show",f"{commit}:{path}"],cwd=ROOT,capture_output=True)
 return p.stdout if p.returncode==0 else None
def provenance(p:object,producing:str)->bool:
 if not isinstance(p,dict) or set(p)!={"path","raw_sha256","content","activation_checkpoint_head"} or p.get("path")!=ACTIVATION_RECORD_RELATIVE.as_posix() or not COMMIT.fullmatch(producing) or p.get("activation_checkpoint_head")!=producing or not isinstance(p.get("raw_sha256"),str) or not HEX.fullmatch(p["raw_sha256"]):return False
 raw=blob_at(producing,p["path"])
 if raw is None or hashlib.sha256(raw).hexdigest()!=p["raw_sha256"] or subprocess.run(["git","merge-base","--is-ancestor",producing,"HEAD"],cwd=ROOT,capture_output=True).returncode!=0:return False
 try: content=json.loads(raw.decode("ascii")); gate_sha=identities()["phase_a_gate"]["sha256"]
 except (UnicodeDecodeError,ValueError):return False
 if not isinstance(content,dict):return False
 expected={"schema_version":"lily_l4_b85r4_phase_b_activation_v5","gate_id":GATE_ID,"gate_sha256":gate_sha,"hermetic_ci_head_sha":content.get("accepted_gate_head_sha"),"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.5R4 Phase B owner authorization","scope":"one_structural_u8_preflight_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}}
 return content==p["content"] and set(content)==set(expected)|{"accepted_gate_head_sha","hermetic_ci_run_id"} and all(content.get(k)==v for k,v in expected.items()) and COMMIT.fullmatch(content["accepted_gate_head_sha"]) is not None and isinstance(content["hermetic_ci_run_id"],int) and content["hermetic_ci_run_id"]>0
def validate(report:object,*,provenance_check=None)->dict:
 b=[]
 if not isinstance(report,dict):return {"status":"blocked","blockers":["type"]}
 out=report.get("outcome"); allowed=BASE|({"manifest","payload","structural_summary_sha256"} if out=="structural_pass" else {"blocker"} if out=="preflight_blocked" else set())
 ident={"schema_version":"lily_l4_b85r4_structural_preflight_report_v5","order_id":"B8.5R4","hypothesis_id":"L-4","evidence_tier":"E0","edge_claim":"none","container_identity":CONTAINER_IDENTITY}
 if set(report)!=allowed or report.get("mode") not in ("synthetic_fixture","real_one_shot") or out not in ("structural_pass","preflight_blocked") or any(report.get(k)!=v for k,v in ident.items()):b.append("shape")
 if report.get("storage_references")!={"manifest":MANIFEST_REFERENCE,"payload":PAYLOAD_REFERENCE} or report.get("contract_artifacts")!=identities() or report.get("access_counters")!={"return_value_decode_count":0,"validation_access_count":0} or report.get("validation_seal")!={"status":"sealed_not_accessed","accessed":False} or validate_gate().get("status")!="pass":b.append("contract")
 if out=="structural_pass":
  m,p=report.get("manifest"),report.get("payload")
  if not isinstance(m,dict) or set(m)!={"complete_raw_sha256","observed_byte_count","metadata_sha256","minimal_ascii_decode_count"} or not isinstance(m.get("complete_raw_sha256"),str) or not HEX.fullmatch(m["complete_raw_sha256"]) or not isinstance(m.get("observed_byte_count"),int) or m["observed_byte_count"]<1 or not isinstance(m.get("metadata_sha256"),str) or not HEX.fullmatch(m["metadata_sha256"]) or m.get("minimal_ascii_decode_count")!=1 or not valid_payload(p) or m["metadata_sha256"]!=p["complete_raw_sha256"] or report.get("structural_summary_sha256")!=structural_summary_sha256(m,p) or not valid_artifact(report["artifacts"].get("manifest"),m,report["mode"]=="synthetic_fixture") or not valid_artifact(report["artifacts"].get("payload"),p,report["mode"]=="synthetic_fixture"):b.append("pass_binding")
 if report["mode"]=="synthetic_fixture":
  if report.get("real_preflight_consumed") is not False or report.get("activation_provenance") is not None or report.get("producing_git_commit")!="synthetic_fixture":b.append("synthetic")
 else:
  check=provenance_check or provenance
  if report.get("real_preflight_consumed") is not True or not check(report.get("activation_provenance"),report.get("producing_git_commit","")):b.append("provenance")
 return {"status":"pass" if not b else "blocked","blockers":sorted(set(b))}
if __name__=="__main__":
 r=validate(synthetic(MANIFEST.read_bytes(),PAYLOAD.read_bytes()));print(json.dumps(r));raise SystemExit(r["status"]!="pass")
