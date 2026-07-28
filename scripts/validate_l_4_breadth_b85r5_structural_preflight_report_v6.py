"""Closed-world v6 report validator, including blocked one-shot outcomes."""
from __future__ import annotations
import hashlib,json,re,subprocess,sys
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.l4_b85r5_structural_scanner_v6 import CUTOFF,MAX_BYTES,U8
from scripts.run_l_4_breadth_b85r5_phase_b_preflight_v6 import ACTIVATION_RECORD_RELATIVE,CONTAINER_IDENTITY,GATE_ID,MANIFEST_REFERENCE,PAYLOAD_REFERENCE,activation,identities,structural,structural_summary_sha256
from scripts.validate_l_4_breadth_b85r5_phase_a_activation_order_v6 import validate as validate_gate
FIX=ROOT/"tests/fixtures/l4_b85r5";MANIFEST=FIX/"structural_manifest_v6.json";PAYLOAD=FIX/"u8_symbol_session_dates_v6.json"
HEX=re.compile(r"^[0-9a-f]{64}$");COMMIT=re.compile(r"^[0-9a-f]{40}$")
BASE={"schema_version","order_id","hypothesis_id","mode","outcome","evidence_tier","edge_claim","real_preflight_consumed","storage_references","container_identity","artifacts","contract_artifacts","activation_provenance","access_counters","validation_seal","producing_git_commit"}
AK={"attempted_read_count","read_count","observed_byte_count","complete_read","complete_raw_sha256","bounded_prefix_sha256","hash_count","scan_count","minimal_ascii_decode_count"}
SCAN={"bounded_raw_bytes_required","input_over_limit","bom_escape_or_encoding_ambiguity","structural_syntax","ambiguous_string","unterminated_string","unknown_or_duplicate_field","trailing_bytes","invalid_calendar_session","post_cutoff_session","manifest_schema_mismatch","container_identity_mismatch","payload_path_mismatch","manifest_hash_shape","record_bound_exceeded","session_dates_not_strictly_ordered","duplicate_symbol_session","missing_or_ambiguous_u8_member","payload_schema_mismatch"}

def untouched(a:object)->bool:return a=={"attempted_read_count":0,"read_count":0,"observed_byte_count":None,"complete_read":False,"complete_raw_sha256":None,"bounded_prefix_sha256":None,"hash_count":0,"scan_count":0,"minimal_ascii_decode_count":0}
def failed(a:object)->bool:return isinstance(a,dict) and set(a)==AK and a=={"attempted_read_count":1,"read_count":0,"observed_byte_count":None,"complete_read":False,"complete_raw_sha256":None,"bounded_prefix_sha256":None,"hash_count":0,"scan_count":0,"minimal_ascii_decode_count":0}
def complete(a:object,*,scan:int=0,decode:int=0,attempted:int=1)->bool:
 if not isinstance(a,dict) or set(a)!=AK:return False
 return a["attempted_read_count"]==a["read_count"]==attempted and a["hash_count"]==1 and isinstance(a["observed_byte_count"],int) and 0<a["observed_byte_count"]<=MAX_BYTES and a["complete_read"] is True and isinstance(a["complete_raw_sha256"],str) and HEX.fullmatch(a["complete_raw_sha256"]) and a["bounded_prefix_sha256"]==a["complete_raw_sha256"] and a["scan_count"]==scan and a["minimal_ascii_decode_count"]==decode
def over(a:object)->bool:
 return isinstance(a,dict) and set(a)==AK and a["attempted_read_count"]==a["read_count"]==a["hash_count"]==1 and a["observed_byte_count"]==MAX_BYTES+1 and a["complete_read"] is False and a["complete_raw_sha256"] is None and isinstance(a["bounded_prefix_sha256"],str) and HEX.fullmatch(a["bounded_prefix_sha256"]) and a["scan_count"]==a["minimal_ascii_decode_count"]==0
def payload(p:object)->bool:
 if not isinstance(p,dict) or set(p)!={"complete_raw_sha256","observed_byte_count","u8_members_in_order","session_count","session_counts_by_symbol","session_dates_by_symbol","max_session_date","minimal_ascii_decode_count"}:return False
 d=p.get("session_dates_by_symbol");c=p.get("session_counts_by_symbol")
 try:
  if not isinstance(p.get("complete_raw_sha256"),str) or not HEX.fullmatch(p["complete_raw_sha256"]) or not isinstance(p.get("observed_byte_count"),int) or p["u8_members_in_order"]!=list(U8) or not isinstance(d,dict) or not isinstance(c,dict) or set(d)!=set(U8) or set(c)!=set(U8) or any(not isinstance(d[s],list) or not d[s] or d[s]!=sorted(set(d[s])) or not isinstance(c[s],int) or c[s]!=len(d[s]) or any(date.fromisoformat(x).isoformat()!=x or x>CUTOFF for x in d[s]) for s in U8):return False
 except (TypeError,ValueError):return False
 flat=[x for s in U8 for x in d[s]];return p.get("session_count")==len(flat) and p.get("max_session_date")==max(flat) and p.get("minimal_ascii_decode_count")==len(flat)+len(U8)+1
def provenance(p:object,producing:str)->bool:
 if not isinstance(p,dict) or set(p)!={"path","raw_sha256","content","activation_checkpoint_head"} or p.get("path")!=ACTIVATION_RECORD_RELATIVE.as_posix() or p.get("activation_checkpoint_head")!=producing or not COMMIT.fullmatch(producing) or not isinstance(p.get("raw_sha256"),str) or not HEX.fullmatch(p["raw_sha256"]):return False
 show=subprocess.run(["git","show",f"{producing}:{p['path']}"],cwd=ROOT,capture_output=True)
 if show.returncode or hashlib.sha256(show.stdout).hexdigest()!=p["raw_sha256"] or subprocess.run(["git","merge-base","--is-ancestor",producing,"HEAD"],cwd=ROOT,capture_output=True).returncode:return False
 return activation(show.stdout,activation_head=producing) is not None and json.loads(show.stdout.decode("ascii"))==p["content"]
def blocked_artifacts(blocker:object,rows:object)->bool:
 if not isinstance(blocker,str) or not isinstance(rows,dict) or set(rows)!={"manifest","payload"}:return False
 m,p=rows["manifest"],rows["payload"]
 if blocker=="data_root_unavailable":return untouched(m) and untouched(p)
 if blocker in ("manifest_missing","manifest_read_error"):return failed(m) and untouched(p)
 if blocker=="manifest_input_over_limit":return over(m) and untouched(p)
 if blocker in ("payload_missing","payload_read_error"):return complete(m) and failed(p)
 if blocker=="payload_input_over_limit":return complete(m) and over(p)
 if blocker.startswith("structural_manifest_") and blocker.removeprefix("structural_manifest_") in SCAN:return complete(m,scan=1,decode=0) and complete(p)
 if blocker.startswith("structural_payload_") and blocker.removeprefix("structural_payload_") in SCAN:return complete(m,scan=1,decode=1) and complete(p,scan=1,decode=0)
 if blocker=="manifest_payload_hash_mismatch":return complete(m,scan=1,decode=1) and complete(p,scan=1,decode=16+len(U8)+1)
 return False
def validate(report:object,*,provenance_check=None)->dict:
 b=[]
 if not isinstance(report,dict):return {"status":"blocked","blockers":["type"]}
 outcome=report.get("outcome");allowed=BASE|({"manifest","payload","structural_summary_sha256"} if outcome=="structural_pass" else {"blocker"} if outcome=="preflight_blocked" else set())
 ident={"schema_version":"lily_l4_b85r5_structural_preflight_report_v6","order_id":"B8.5R5","hypothesis_id":"L-4","evidence_tier":"E0","edge_claim":"none","container_identity":CONTAINER_IDENTITY}
 if set(report)!=allowed or report.get("mode") not in ("synthetic_fixture","real_one_shot") or outcome not in ("structural_pass","preflight_blocked") or any(report.get(k)!=v for k,v in ident.items()):b.append("shape")
 if report.get("storage_references")!={"manifest":MANIFEST_REFERENCE,"payload":PAYLOAD_REFERENCE} or report.get("contract_artifacts")!=identities() or report.get("access_counters")!={"return_value_decode_count":0,"validation_access_count":0} or report.get("validation_seal")!={"status":"sealed_not_accessed","accessed":False} or validate_gate().get("status")!="pass":b.append("contract")
 if outcome=="structural_pass":
  m,p=report.get("manifest"),report.get("payload");a=report.get("artifacts",{})
  reads=0 if report.get("mode")=="synthetic_fixture" else 1
  if not isinstance(m,dict) or set(m)!={"complete_raw_sha256","observed_byte_count","metadata_sha256","minimal_ascii_decode_count"} or not isinstance(m.get("complete_raw_sha256"),str) or not HEX.fullmatch(m["complete_raw_sha256"]) or not isinstance(m.get("metadata_sha256"),str) or not HEX.fullmatch(m["metadata_sha256"]) or m.get("minimal_ascii_decode_count")!=1 or not payload(p) or m["metadata_sha256"]!=p["complete_raw_sha256"] or report.get("structural_summary_sha256")!=structural_summary_sha256(m,p) or not complete(a.get("manifest"),scan=1,decode=1,attempted=reads) or not complete(a.get("payload"),scan=1,decode=p["minimal_ascii_decode_count"],attempted=reads):b.append("pass")
 else:
  if report.get("mode")!="real_one_shot" or not blocked_artifacts(report.get("blocker"),report.get("artifacts")):b.append("blocked")
 if report.get("mode")=="synthetic_fixture":
  if report.get("real_preflight_consumed") is not False or report.get("activation_provenance") is not None or report.get("producing_git_commit")!="synthetic_fixture":b.append("synthetic")
 else:
  if report.get("real_preflight_consumed") is not True or not (provenance_check or provenance)(report.get("activation_provenance"),report.get("producing_git_commit", "")):b.append("provenance")
 return {"status":"pass" if not b else "blocked","blockers":sorted(set(b))}
if __name__=="__main__":
 r=validate(structural(MANIFEST.read_bytes(),PAYLOAD.read_bytes()));print(json.dumps(r));raise SystemExit(r["status"]!="pass")
