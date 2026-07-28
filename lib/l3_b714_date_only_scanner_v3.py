"""B7.14 v3 byte scanner: only allowed structural/date strings become text."""
from __future__ import annotations
import hashlib,json,re
from datetime import date
from pathlib import Path
from typing import Any,Callable
from scripts.validate_l_3_corrected_rerun_pre_return_schedule_v1 import canonical_schedule_sha256
ASSETS=("VTI","VGK","EWJ","VWO","IEF","TIP","GLD","DBC"); START="2007-02-05"; END="2015-12-31"; SCHEMA="lily_l1_daily_dataset_v1"
NUMBER=re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
class ScanError(ValueError):pass
def _utf8(raw:bytes)->bool:
 try:raw.decode("utf-8")
 except UnicodeDecodeError:return False
 return True
class P:
 def __init__(self,raw:bytes,c:dict[str,int]):self.raw,self.pos,self.c=raw,0,c
 def ws(self)->None:
  while self.pos<len(self.raw) and self.raw[self.pos] in b" \t\r\n":self.pos+=1
 def expect(self,x:bytes)->None:
  self.ws()
  if not self.raw.startswith(x,self.pos):raise ScanError("malformed_json")
  self.pos+=len(x)
 def bounds(self)->tuple[int,int]:
  self.ws()
  if self.pos>=len(self.raw) or self.raw[self.pos]!=34:raise ScanError("expected_json_string")
  self.pos+=1; begin=self.pos; segment=begin
  while self.pos<len(self.raw):
   x=self.raw[self.pos]
   if x==34:
    if not _utf8(self.raw[segment:self.pos]):raise ScanError("invalid_utf8_string")
    end=self.pos;self.pos+=1;return begin,end
   if x<32:raise ScanError("invalid_json_string")
   if x==92:
    if not _utf8(self.raw[segment:self.pos]):raise ScanError("invalid_utf8_string")
    self.pos+=1
    if self.pos>=len(self.raw):raise ScanError("malformed_json")
    e=self.raw[self.pos]
    if e not in b'"\\/bfnrtu':raise ScanError("invalid_json_escape")
    if e==117:
     if self.pos+4>=len(self.raw) or any(chr(v) not in "0123456789abcdefABCDEF" for v in self.raw[self.pos+1:self.pos+5]):raise ScanError("invalid_json_escape")
     self.pos+=5
    else:self.pos+=1
    segment=self.pos
   else:self.pos+=1
  raise ScanError("malformed_json")
 def decoded(self)->str:
  a,b=self.bounds();raw=self.raw[a:b]
  if b"\\" in raw:raise ScanError("escaped_allowed_string")
  if not _utf8(raw):raise ScanError("invalid_utf8_string")
  self.c["allowed_metadata_string_decode_count"]+=1
  return raw.decode("utf-8")
 def timestamp(self)->None:
  self.bounds();self.c["skipped_timestamp_string_lexeme_count"]+=1
 def return_number(self)->None:
  self.ws();a=self.pos
  while self.pos<len(self.raw) and self.raw[self.pos] not in b" \t\r\n,]}":self.pos+=1
  if not NUMBER.fullmatch(self.raw[a:self.pos]):raise ScanError("invalid_total_return_close_lexeme")
  self.c["skipped_return_number_lexeme_count"]+=1
 def obj(self,h:dict[str,Callable[[],Any]])->dict[str,Any]:
  self.expect(b"{");out={};self.ws()
  if self.pos<len(self.raw) and self.raw[self.pos]==125:self.pos+=1;return out
  while True:
   key=self.decoded()
   if key in out:raise ScanError("duplicate_json_key")
   self.expect(b":")
   if key not in h:raise ScanError("unknown_structural_key")
   out[key]=h[key]();self.ws()
   if self.pos<len(self.raw) and self.raw[self.pos]==125:self.pos+=1;return out
   self.expect(b",")
def _shape(x:dict[str,Any],keys:set[str],why:str)->None:
 if set(x)!=keys:raise ScanError(why)
def _schedule(s:dict[str,list[str]])->dict[str,Any]:
 common=sorted(set.intersection(*(set(s[a]) for a in ASSETS)))
 if not common:raise ScanError("empty_common_intersection")
 weekly=[]
 for x in common:
  if START<=x<=END:
   if weekly and date.fromisoformat(weekly[-1]).isocalendar()[:2]==date.fromisoformat(x).isocalendar()[:2]:weekly[-1]=x
   else:weekly.append(x)
 index={x:i for i,x in enumerate(common)}; selected=[x for x in weekly if index[x]+20<len(common) and common[index[x]+20]<=END]
 if not selected:raise ScanError("empty_schedule")
 if len(selected)>465:raise ScanError("weekly_pair_ceiling_exceeded")
 execution=[common[index[x]+1] for x in selected]; t20=[common[index[x]+20] for x in selected]
 evidence={"per_symbol_sessions":s,"common_sessions":common,"selected_decision_dates":selected,"execution_dates":execution,"t_plus_20_dates":t20}
 return {**evidence,"canonical_schedule_sha256":canonical_schedule_sha256(selected),"date_evidence_sha256":hashlib.sha256(json.dumps(evidence,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()}
def scan_date_only(path:Path,expected_container_sha256:str)->dict[str,Any]:
 c={"raw_byte_read_attempt_count":1,"raw_byte_read_count":0,"raw_byte_hash_count":0,"allowed_metadata_string_decode_count":0,"session_date_values_decoded_count":0,"date_metadata_inspection_count":0,"skipped_timestamp_string_lexeme_count":0,"skipped_return_number_lexeme_count":0,"forbidden_semantic_decode_count":0,"research_decision_count":0,"ledger_row_count":0}
 try:raw=path.read_bytes();c["raw_byte_read_count"]=1;c["raw_byte_hash_count"]=1
 except OSError as e:return {"outcome":"scope_restricted","blocker":type(e).__name__,"container_sha256":None,"counters":c}
 digest=hashlib.sha256(raw).hexdigest()
 if digest!=expected_container_sha256:return {"outcome":"scope_restricted","blocker":"container_sha256_mismatch","container_sha256":digest,"counters":c}
 p=P(raw,c)
 try:
  def record()->str:
   def session()->str:
    value=p.decoded();c["session_date_values_decoded_count"]+=1;c["date_metadata_inspection_count"]+=1;return value
   x=p.obj({"session_date":session,"availability_timestamp":p.timestamp,"total_return_close":p.return_number});_shape(x,{"session_date","availability_timestamp","total_return_close"},"record_shape");return x["session_date"]
  def symbol()->tuple[str,list[str]]:
   def records()->list[str]:
    p.expect(b"[");out=[];p.ws()
    if p.pos<len(raw) and raw[p.pos]==93:p.pos+=1;return out
    while True:
     out.append(record());p.ws()
     if p.pos<len(raw) and raw[p.pos]==93:p.pos+=1;return out
     p.expect(b",")
   x=p.obj({"symbol":p.decoded,"records":records});_shape(x,{"symbol","records"},"symbol_shape");return x["symbol"],x["records"]
  def symbols()->list[tuple[str,list[str]]]:
   p.expect(b"[");out=[];p.ws()
   if p.pos<len(raw) and raw[p.pos]==93:p.pos+=1;return out
   while True:
    out.append(symbol());p.ws()
    if p.pos<len(raw) and raw[p.pos]==93:p.pos+=1;return out
    p.expect(b",")
  root=p.obj({"schema_version":p.decoded,"acquired_at":p.timestamp,"cutoff_inclusive":p.decoded,"symbols":symbols});_shape(root,{"schema_version","acquired_at","cutoff_inclusive","symbols"},"root_shape");p.ws()
  if p.pos!=len(raw):raise ScanError("malformed_json")
  if root["schema_version"]!=SCHEMA or root["cutoff_inclusive"]!=END:raise ScanError("schema_or_cutoff_mismatch")
  if [x[0] for x in root["symbols"]]!=list(ASSETS):raise ScanError("symbol_identity_or_order_mismatch")
  sessions=dict(root["symbols"])
  for values in sessions.values():
   if not values or values!=sorted(values) or len(values)!=len(set(values)):raise ScanError("nonmonotonic_or_duplicate_session_date")
   for x in values:
    try:d=date.fromisoformat(x)
    except ValueError as e:raise ScanError("invalid_session_date") from e
    if d.isoformat()!=x or d.weekday()>4:raise ScanError("invalid_or_weekend_session_date")
    if x>END:raise ScanError("post_end_session_before_intersection")
  return {"outcome":"preflight_pass","container_sha256":digest,"attestation":_schedule(sessions),"counters":c}
 except (ScanError,ValueError) as e:return {"outcome":"scope_restricted","blocker":str(e),"container_sha256":digest,"counters":c}
