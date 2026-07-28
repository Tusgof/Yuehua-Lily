from __future__ import annotations
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from lib.draft202012_subset import ValidationError,validate as schema_validate
from lib.l4_b86r2_provisioning_scanner_v3 import MAX_BYTES
from scripts.run_l_4_breadth_b86r2_provisioning_v3 import DATASET_REFERENCE,EXPECTED_SHA256,MANIFEST_RELATIVE,PAYLOAD_RELATIVE,canonical,identities
from scripts.validate_l_4_breadth_b86r2_falsification_manifest_v3 import validate as manifest_validate
from scripts.validate_l_4_breadth_b86r2_u8_session_dates_v3 import validate as payload_validate
SCHEMA=ROOT/"schemas/l_4_breadth_b86r2_provisioning_report_v3.schema.json";HEX=re.compile(r"^[0-9a-f]{64}$")
AK={"attempted_read_count","read_count","observed_byte_count","complete_read","complete_raw_sha256","bounded_prefix_sha256","hash_count","scan_count","opaque_unsafe_lexeme_decode_count"}
def row_ok(a,scan):return isinstance(a,dict) and set(a)==AK and a["attempted_read_count"]==a["read_count"]==a["hash_count"]==1 and isinstance(a["observed_byte_count"],int) and 0<a["observed_byte_count"]<=MAX_BYTES and a["complete_read"] and HEX.fullmatch(str(a["complete_raw_sha256"])) and a["bounded_prefix_sha256"]==a["complete_raw_sha256"] and a["scan_count"]==scan and a["opaque_unsafe_lexeme_decode_count"]==0
def blocked_row(a,blocker):
 if not isinstance(a,dict) or set(a)!=AK:return False
 if blocker in ("dataset_missing","dataset_read_error"):return a["attempted_read_count"]==1 and a["read_count"]==0 and a["observed_byte_count"] is None and a["hash_count"]==a["scan_count"]==a["opaque_unsafe_lexeme_decode_count"]==0
 if blocker=="dataset_input_over_limit":return a["attempted_read_count"]==a["read_count"]==a["hash_count"]==1 and a["observed_byte_count"]==MAX_BYTES+1 and not a["complete_read"] and a["complete_raw_sha256"] is None and HEX.fullmatch(str(a["bounded_prefix_sha256"])) and a["scan_count"]==0
 return row_ok(a,1)
def validate(report,*,output_paths=None):
 b=[]
 try:schema_validate(json.loads(SCHEMA.read_text("ascii")),report)
 except (OSError,ValueError,ValidationError):b.append("schema")
 if not isinstance(report,dict):return {"status":"blocked","blockers":["type"]}
 if report.get("contract_artifacts")!=identities() or report.get("dataset_reference")!=DATASET_REFERENCE or report.get("expected_dataset_sha256")!=EXPECTED_SHA256 or report.get("access_counters")!={"return_value_decode_count":0,"opaque_unsafe_lexeme_decode_count":0,"validation_access_count":0} or report.get("validation_seal")!={"status":"sealed_not_accessed","accessed":False}:b.append("contract")
 outcome=report.get("outcome");row=report.get("dataset_artifact")
 if outcome=="provisioning_blocked":
  if not blocked_row(row,report.get("blocker")):b.append("blocked")
 elif outcome=="structural_provisioned":
  m,p=report.get("manifest"),report.get("payload");ids=report.get("output_artifacts",{})
  if not row_ok(row,1) or manifest_validate(m).get("status")!="pass" or payload_validate(p).get("status")!="pass" or not isinstance(ids,dict) or set(ids)!={"manifest","payload"}:b.append("success")
  else:
   paths=output_paths or (ROOT/MANIFEST_RELATIVE,ROOT/PAYLOAD_RELATIVE)
   for name,value,path in zip(("manifest","payload"),(m,p),paths,strict=True):
    raw=canonical(value);identity=ids[name]
    if identity!={"path":path.as_posix(),"raw_sha256":hashlib.sha256(raw).hexdigest(),"byte_count":len(raw)}:b.append("identity");continue
    if report.get("mode")=="real_one_shot":
     try:disk=Path(path).read_bytes()
     except OSError:b.append("identity");continue
     if disk!=raw:b.append("identity")
  if isinstance(m,dict) and isinstance(p,dict) and (m.get("dataset_sha256")!=row.get("complete_raw_sha256") or p.get("dataset_sha256")!=row.get("complete_raw_sha256")):b.append("binding")
 else:b.append("outcome")
 return {"status":"pass" if not b else "blocked","blockers":sorted(set(b))}
