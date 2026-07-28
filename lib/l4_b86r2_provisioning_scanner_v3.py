"""Bounded opaque scan for B8.6R2; numeric lexemes never become Python values."""
from __future__ import annotations
import hashlib,json,re
from dataclasses import dataclass
from datetime import date
DATASET_SCHEMA="lily_l1_daily_dataset_v1";NORMALIZED_SCHEMA="lily_yahoo_daily_normalized_v1";U8=("VTI","VGK","EWJ","VWO","IEF","TIP","GLD","DBC");CUTOFF="2015-12-31";MAX_BYTES=32*1024*1024
TOP_KEYS=("schema_version","acquired_at","cutoff_inclusive","symbols");SYMBOL_KEYS=("schema_version","provider","symbol","legal_inception","coverage","records","limitations");RECORD_KEYS=("session_date","availability_timestamp","raw_close","cash_distribution","split","total_return_close","trading_currency","provider_revision","is_backfilled");UNSAFE_KEYS=("raw_close","cash_distribution","split","total_return_close")
NUMBER=re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
class ScanError(ValueError):pass
@dataclass(frozen=True)
class Opaque: raw:bytes;kind:str
class Parser:
 def __init__(self,raw):self.raw,self.i=raw,0
 def ws(self):
  while self.i<len(self.raw) and self.raw[self.i] in b" \t\r\n":self.i+=1
 def value(self):
  self.ws()
  if self.i>=len(self.raw):raise ScanError("structural_syntax")
  c=self.raw[self.i]
  if c==123:return self.obj()
  if c==91:return self.arr()
  if c==34:return self.string()
  for raw,kind in ((b"true","bool"),(b"false","bool"),(b"null","null")):
   if self.raw.startswith(raw,self.i):self.i+=len(raw);return Opaque(raw,kind)
  if c in b"-0123456789":return self.number()
  raise ScanError("structural_syntax")
 def string(self):
  start=self.i;self.i+=1;escaped=False
  while self.i<len(self.raw):
   c=self.raw[self.i]
   if escaped:escaped=False
   elif c==92:escaped=True
   elif c==34:self.i+=1;return Opaque(self.raw[start:self.i],"string")
   elif c<32:raise ScanError("structural_syntax")
   self.i+=1
  raise ScanError("unterminated_string")
 def number(self):
  start=self.i
  while self.i<len(self.raw) and self.raw[self.i] in b"-+0123456789.eE":self.i+=1
  raw=self.raw[start:self.i]
  if NUMBER.fullmatch(raw) is None:raise ScanError("invalid_numeric_lexeme")
  return Opaque(raw,"number")
 def obj(self):
  out={};self.i+=1;self.ws()
  if self.i<len(self.raw) and self.raw[self.i]==125:self.i+=1;return out
  while True:
   self.ws()
   if self.i>=len(self.raw) or self.raw[self.i]!=34:raise ScanError("structural_syntax")
   key=text(self.string());self.ws()
   if self.i>=len(self.raw) or self.raw[self.i]!=58 or key in out:raise ScanError("unknown_or_duplicate_field")
   self.i+=1;out[key]=self.value();self.ws()
   if self.i<len(self.raw) and self.raw[self.i]==125:self.i+=1;return out
   if self.i>=len(self.raw) or self.raw[self.i]!=44:raise ScanError("structural_syntax")
   self.i+=1
 def arr(self):
  out=[];self.i+=1;self.ws()
  if self.i<len(self.raw) and self.raw[self.i]==93:self.i+=1;return out
  while True:
   out.append(self.value());self.ws()
   if self.i<len(self.raw) and self.raw[self.i]==93:self.i+=1;return out
   if self.i>=len(self.raw) or self.raw[self.i]!=44:raise ScanError("structural_syntax")
   self.i+=1
def text(value):
 if not isinstance(value,Opaque) or value.kind!="string":raise ScanError("schema_mismatch")
 try:out=json.loads(value.raw.decode("ascii"))
 except (UnicodeDecodeError,ValueError) as exc:raise ScanError("schema_mismatch") from exc
 if not isinstance(out,str):raise ScanError("schema_mismatch")
 return out
def exact(value,keys):
 if not isinstance(value,dict) or set(value)!=set(keys):raise ScanError("unknown_or_duplicate_field")
def calendar(value):
 value=text(value)
 try:
  if date.fromisoformat(value).isoformat()!=value:raise ValueError
 except ValueError as exc:raise ScanError("invalid_calendar_session") from exc
 if value>CUTOFF:raise ScanError("post_cutoff_session")
 return value
def opaque(value):
 if not isinstance(value,Opaque) or value.kind not in ("string","number","null"):raise ScanError("unsafe_value_not_opaque_scalar")
def boolean(value):
 if not isinstance(value,Opaque) or value.kind!="bool":raise ScanError("record_schema_mismatch")
def scan_dataset(raw,*,expected_sha256):
 if not isinstance(raw,bytes) or not raw or len(raw)>MAX_BYTES:raise ScanError("bounded_raw_bytes_required")
 digest=hashlib.sha256(raw).hexdigest()
 if digest!=expected_sha256:raise ScanError("dataset_hash_mismatch")
 p=Parser(raw);payload=p.value();p.ws()
 if p.i!=len(raw):raise ScanError("trailing_bytes")
 exact(payload,TOP_KEYS)
 if text(payload["schema_version"])!=DATASET_SCHEMA or text(payload["cutoff_inclusive"])!=CUTOFF:raise ScanError("dataset_schema_mismatch")
 text(payload["acquired_at"]);symbols=payload["symbols"]
 if not isinstance(symbols,list) or len(symbols)!=len(U8):raise ScanError("symbol_order_mismatch")
 sessions={};coverage={};total=0
 for expected,item in zip(U8,symbols,strict=True):
  exact(item,SYMBOL_KEYS)
  if text(item["schema_version"])!=NORMALIZED_SCHEMA or text(item["symbol"])!=expected:raise ScanError("symbol_schema_mismatch")
  text(item["provider"]);text(item["legal_inception"])
  if not isinstance(item["limitations"],list) or any(not isinstance(x,Opaque) or x.kind!="string" for x in item["limitations"]):raise ScanError("limitations_schema_mismatch")
  exact(item["coverage"],("start","end"));start,end=calendar(item["coverage"]["start"]),calendar(item["coverage"]["end"]);rows=item["records"]
  if not isinstance(rows,list) or not rows:raise ScanError("missing_or_ambiguous_u8_member")
  dates=[]
  for row in rows:
   exact(row,RECORD_KEYS);dates.append(calendar(row["session_date"]));text(row["availability_timestamp"]);text(row["trading_currency"]);text(row["provider_revision"]);boolean(row["is_backfilled"])
   for name in UNSAFE_KEYS:opaque(row[name])
  if dates!=sorted(set(dates)) or dates[0]!=start or dates[-1]!=end:raise ScanError("duplicate_symbol_session")
  sessions[expected]=dates;coverage[expected]={"start":start,"end":end,"row_count":len(dates)};total+=len(dates)
 return {"dataset_sha256":digest,"dataset_byte_count":len(raw),"u8_members_in_order":list(U8),"session_dates_by_symbol":sessions,"coverage_by_symbol":coverage,"session_count":total,"max_session_date":max(x[-1] for x in sessions.values()),"opaque_unsafe_lexeme_decode_count":0,"return_value_decode_count":0,"validation_access_count":0}
