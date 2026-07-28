"""E0-only v4 byte lexeme helpers; no filesystem or real-container API exists."""
from __future__ import annotations
import re
NUMBER=re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
def valid_utf8_bytes(raw:bytes)->bool:
 i=0
 while i<len(raw):
  x=raw[i];n=1 if x<128 else 2 if 194<=x<=223 else 3 if 224<=x<=239 else 4 if 240<=x<=244 else 0
  if not n or i+n>len(raw) or any(raw[i+j]&192!=128 for j in range(1,n)):return False
  i+=n
 return True
def skip_timestamp_lexeme(raw:bytes)->bool:
 return len(raw)>=2 and raw[:1]==b'"' and raw[-1:]==b'"' and b'\\' not in raw and valid_utf8_bytes(raw[1:-1])
def skip_return_number_lexeme(raw:bytes)->bool:
 return bool(NUMBER.fullmatch(raw))
