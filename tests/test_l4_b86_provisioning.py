from __future__ import annotations
import hashlib,json,unittest
from lib.l4_b86_provisioning_scanner_v1 import ScanError,U8,scan_dataset
from scripts.run_l_4_breadth_b86_provisioning_v1 import main
from scripts.validate_l_4_breadth_b86_provisioning_gate_v1 import validate

def payload():
 rows=[]
 for symbol in U8:
  records=[{"session_date":"2015-12-30","availability_timestamp":"2015-12-30T16:00:00-05:00","raw_close":1.0,"cash_distribution":0.0,"split":None,"total_return_close":1.0,"trading_currency":"USD","provider_revision":"download_timestamp_container","is_backfilled":False},{"session_date":"2015-12-31","availability_timestamp":"2015-12-31T16:00:00-05:00","raw_close":2.0,"cash_distribution":0.0,"split":None,"total_return_close":2.0,"trading_currency":"USD","provider_revision":"download_timestamp_container","is_backfilled":False}]
  rows.append({"schema_version":"lily_yahoo_daily_normalized_v1","provider":"Yahoo Finance chart API","symbol":symbol,"legal_inception":"2000-01-01","coverage":{"start":"2015-12-30","end":"2015-12-31"},"records":records,"limitations":[]})
 return json.dumps({"schema_version":"lily_l1_daily_dataset_v1","acquired_at":"synthetic","cutoff_inclusive":"2015-12-31","symbols":rows},separators=(",",":")).encode("ascii")
class B86Tests(unittest.TestCase):
 def test_gate_and_synthetic_structure_pass(self):
  self.assertEqual("pass",validate()["status"]);raw=payload();out=scan_dataset(raw,expected_sha256=hashlib.sha256(raw).hexdigest());self.assertEqual(list(U8),out["u8_members_in_order"]);self.assertEqual(0,out["numeric_lexeme_decode_count"])
 def test_hash_order_and_cutoff_drift_block(self):
  raw=payload()
  with self.assertRaises(ScanError):scan_dataset(raw,expected_sha256="0"*64)
  for changed in (raw.replace(b'"VTI"',b'"BAD"',1),raw.replace(b'2015-12-31',b'2016-01-01',1)):
   with self.assertRaises(ScanError):scan_dataset(changed,expected_sha256=hashlib.sha256(changed).hexdigest())
 def test_runner_is_inert_without_exact_flag_or_activation(self):
  self.assertEqual(2,main([]));self.assertEqual(2,main(["--wrong"]))
if __name__=="__main__":unittest.main()
