from __future__ import annotations
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from lib.draft202012_subset import ValidationError,validate as draft_validate
from lib.l4_b86r2_provisioning_scanner_v3 import ScanError,U8,scan_dataset
import scripts.run_l_4_breadth_b86r2_provisioning_v3 as runner
import scripts.validate_l_4_breadth_b86r2_provisioning_report_v3 as report_validator
from scripts.validate_l_4_breadth_b86r2_falsification_manifest_v3 import validate as manifest_validate
from scripts.validate_l_4_breadth_b86r2_u8_session_dates_v3 import validate as payload_validate
def source():
 symbols=[]
 for s in U8:
  rows=[]
  for day,value in (("2015-12-30","1.0"),("2015-12-31","2e+1")):
   rows.append({"session_date":day,"availability_timestamp":day+"T16:00:00-05:00","raw_close":value,"cash_distribution":None,"split":1,"total_return_close":"2.0","trading_currency":"USD","provider_revision":"v1","is_backfilled":False})
  symbols.append({"schema_version":"lily_yahoo_daily_normalized_v1","provider":"Yahoo","symbol":s,"legal_inception":"2000-01-01","coverage":{"start":"2015-12-30","end":"2015-12-31"},"records":rows,"limitations":["synthetic"]})
 return json.dumps({"schema_version":"lily_l1_daily_dataset_v1","acquired_at":"synthetic","cutoff_inclusive":"2015-12-31","symbols":symbols},separators=(",",":")).encode()
def accepted():
 h=runner.identities()["phase_a_gate"]["sha256"]
 return json.dumps({"schema_version":"lily_l4_b86r2_provisioning_activation_v3","gate_id":runner.GATE_ID,"gate_sha256":h,"accepted_gate_head_sha":"a"*40,"hermetic_ci_head_sha":"a"*40,"hermetic_ci_run_id":1,"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.6R2 one-shot owner authorization","scope":"one_repo_relative_falsification_container_provisioning_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}},separators=(",",":")).encode()
def check(a,c,h):return a=="a"*40 and c=="b"*40 and h==runner.identities()["phase_a_gate"]["sha256"]
class Tests(unittest.TestCase):
 def test_draft_schemas_are_executed_and_reject_extra(self):
  for n in ("l_4_breadth_b86r2_provisioning_activation_v3.schema.json","l_4_breadth_b86r2_provisioning_report_v3.schema.json","l_4_breadth_b86r2_falsification_manifest_v3.schema.json","l_4_breadth_b86r2_u8_session_dates_v3.schema.json"):
   s=json.loads((runner.ROOT/"schemas"/n).read_text());self.assertEqual(s["$schema"],"https://json-schema.org/draft/2020-12/schema")
  activation=json.loads(accepted());schema=json.loads((runner.ROOT/"schemas/l_4_breadth_b86r2_provisioning_activation_v3.schema.json").read_text());draft_validate(schema,activation);activation["extra"]=1
  with self.assertRaises(ValidationError):draft_validate(schema,activation)
 def test_scanner_number_grammar_and_drift(self):
  raw=source();self.assertEqual(0,scan_dataset(raw,expected_sha256=hashlib.sha256(raw).hexdigest())["return_value_decode_count"])
  for changed in (raw.replace(b'"raw_close":"1.0"',b'"raw_close":01',1),raw.replace(b'"limitations":["synthetic"]',b'"limitations":[{}]',1),raw.replace(b'"coverage":{"start"',b'"coverage":{"extra":1,"start"',1),raw+b"x"):
   with self.assertRaises(ScanError):scan_dataset(changed,expected_sha256=hashlib.sha256(changed).hexdigest())
 def test_every_structural_blocker_validates(self):
  raw=source()
  for changed in (raw.replace(b'"raw_close":"1.0"',b'"raw_close":{}',1),raw.replace(b'"VTI"',b'"BAD"',1),raw.replace(b'2015-12-31',b'2016-01-01',1),raw+b"x"):
   r=runner.structural(changed);self.assertEqual("provisioning_blocked",r["outcome"]);self.assertEqual("pass",report_validator.validate(r)["status"],r)
 def test_real_identity_and_closed_world_outputs(self):
  raw=source();old=runner.EXPECTED_SHA256;oldv=report_validator.EXPECTED_SHA256;runner.EXPECTED_SHA256=report_validator.EXPECTED_SHA256=hashlib.sha256(raw).hexdigest()
  try:
   with tempfile.TemporaryDirectory() as d:
    root=Path(d);data=root/"in";data.write_bytes(raw);rp=root/"report";mp=root/"manifest";pp=root/"payload";r=runner.run_one_shot(data,report_path=rp,marker_path=root/"marker",manifest_path=mp,payload_path=pp,activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=check)
    self.assertEqual("pass",report_validator.validate(r,output_paths=(mp,pp))["status"])
    m=copy.deepcopy(r["manifest"]);m["coverage_by_symbol"]["VTI"]["unexpected"]=1;self.assertEqual("blocked",manifest_validate(m)["status"])
    p=copy.deepcopy(r["payload"]);p["session_dates_by_symbol"]["BAD"]=[];self.assertEqual("blocked",payload_validate(p)["status"])
    mp.write_bytes(b"{}" );self.assertEqual("blocked",report_validator.validate(r,output_paths=(mp,pp))["status"])
  finally:runner.EXPECTED_SHA256,report_validator.EXPECTED_SHA256=old,oldv
if __name__=="__main__":unittest.main()
