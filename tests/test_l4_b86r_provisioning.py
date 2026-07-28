from __future__ import annotations
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from jsonschema import Draft202012Validator
from lib.l4_b86r_provisioning_scanner_v2 import ScanError,U8,scan_dataset
import scripts.run_l_4_breadth_b86r_provisioning_v2 as runner
import scripts.validate_l_4_breadth_b86r_provisioning_report_v2 as report_validator
from scripts.validate_l_4_breadth_b86r_provisioning_gate_v2 import validate as validate_gate

def source():
 symbols=[]
 for symbol in U8:
  records=[{"session_date":"2015-12-30","availability_timestamp":"2015-12-30T16:00:00-05:00","raw_close":"1.00","cash_distribution":None,"split":1,"total_return_close":"1.00","trading_currency":"USD","provider_revision":"download_timestamp_container","is_backfilled":False},{"session_date":"2015-12-31","availability_timestamp":"2015-12-31T16:00:00-05:00","raw_close":"2.00","cash_distribution":0,"split":None,"total_return_close":"2.00","trading_currency":"USD","provider_revision":"download_timestamp_container","is_backfilled":False}]
  symbols.append({"schema_version":"lily_yahoo_daily_normalized_v1","provider":"Yahoo Finance chart API","symbol":symbol,"legal_inception":"2000-01-01","coverage":{"start":"2015-12-30","end":"2015-12-31"},"records":records,"limitations":[]})
 return json.dumps({"schema_version":"lily_l1_daily_dataset_v1","acquired_at":"synthetic","cutoff_inclusive":"2015-12-31","symbols":symbols},separators=(",",":")).encode("ascii")
def accepted(head="a"*40):
 return json.dumps({"schema_version":"lily_l4_b86r_provisioning_activation_v2","gate_id":runner.GATE_ID,"gate_sha256":runner.identities()["phase_a_gate"]["sha256"],"accepted_gate_head_sha":head,"hermetic_ci_head_sha":head,"hermetic_ci_run_id":1,"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.6R one-shot owner authorization","scope":"one_repo_relative_falsification_container_provisioning_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}},separators=(",",":")).encode("ascii")
def check(accepted_head,checkpoint,gate_hash):return accepted_head=="a"*40 and checkpoint=="b"*40 and gate_hash==runner.identities()["phase_a_gate"]["sha256"]

class B86RTests(unittest.TestCase):
 def test_gate_and_draft_schemas(self):
  self.assertEqual("pass",validate_gate()["status"])
  for name in ("l_4_breadth_b86r_provisioning_activation_v2.schema.json","l_4_breadth_b86r_provisioning_report_v2.schema.json","l_4_breadth_b86r_falsification_manifest_v2.schema.json","l_4_breadth_b86r_u8_session_dates_v2.schema.json"):
   schema=json.loads((runner.ROOT/"schemas"/name).read_text("ascii")); Draft202012Validator.check_schema(schema)
 def test_scanner_opaque_and_drift(self):
  raw=source();self.assertEqual(0,scan_dataset(raw,expected_sha256=hashlib.sha256(raw).hexdigest())["opaque_unsafe_lexeme_decode_count"])
  for bad in (raw.replace(b'"VTI"',b'"BAD"',1),raw.replace(b'2015-12-31',b'2016-01-01',1),raw.replace(b'"raw_close":"1.00"',b'"raw_close":{}',1),raw+b"x"):
   with self.assertRaises(ScanError):scan_dataset(bad,expected_sha256=hashlib.sha256(bad).hexdigest())
 def test_activated_synthetic_success_and_second_invocation_preserves_first(self):
  raw=source(); old_runner,old_validator=runner.EXPECTED_SHA256,report_validator.EXPECTED_SHA256; runner.EXPECTED_SHA256=report_validator.EXPECTED_SHA256=hashlib.sha256(raw).hexdigest()
  try:
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);dataset=root/"input.json";report=root/"report.json";marker=root/"marker";manifest=root/"manifest.json";payload=root/"payload.json";dataset.write_bytes(raw)
    one=runner.run_one_shot(dataset,report_path=report,marker_path=marker,manifest_path=manifest,payload_path=payload,activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=check)
    self.assertEqual("structural_provisioned",one["outcome"]);self.assertEqual("pass",report_validator.validate(one,provenance_check=lambda *_:True)["status"]);before=(report.read_bytes(),marker.read_bytes())
    two=runner.run_one_shot(dataset,report_path=report,marker_path=marker,manifest_path=manifest,payload_path=payload,activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=check);self.assertEqual({"outcome":"refused_already_consumed"},two);self.assertEqual(before,(report.read_bytes(),marker.read_bytes()))
  finally:runner.EXPECTED_SHA256,report_validator.EXPECTED_SHA256=old_runner,old_validator
 def test_forged_activation_and_blocked_output(self):
  forged=json.loads(accepted());forged["inspector_decision"]="REJECTED";self.assertIsNone(runner.activation(json.dumps(forged).encode(),activation_head="b"*40,accepted_gate_check=check))
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);out=runner.run_one_shot(root/"missing",report_path=root/"report",marker_path=root/"marker",manifest_path=root/"manifest",payload_path=root/"payload",activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=check)
   self.assertEqual("provisioning_blocked",out["outcome"]);self.assertEqual("pass",report_validator.validate(out,provenance_check=lambda *_:True)["status"])
   changed=copy.deepcopy(out);changed["dataset_artifact"]["read_count"]=2;self.assertEqual("blocked",report_validator.validate(changed,provenance_check=lambda *_:True)["status"])
 def test_cli_is_inert_and_has_no_environment_dependency(self):
  self.assertEqual(2,runner.main([]));self.assertEqual(2,runner.main(["--wrong"]));self.assertNotIn("LILY_DATA_ROOT",(runner.ROOT/"scripts"/"run_l_4_breadth_b86r_provisioning_v2.py").read_text("ascii"))
if __name__=="__main__":unittest.main()
