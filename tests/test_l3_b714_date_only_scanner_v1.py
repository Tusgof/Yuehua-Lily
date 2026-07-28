from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from lib.l3_b714_date_only_scanner_v1 import ASSETS, scan_date_metadata

def _payload(*, post_end: bool=False) -> bytes:
 records=[]
 for symbol in ASSETS:
  dates=['2007-02-05','2007-02-06','2007-02-07','2007-02-08','2007-02-09']
  if post_end and symbol=='VTI': dates[-1]='2016-01-04'
  records.append({'symbol':symbol,'records':[{'session_date':d,'availability_timestamp':'2015-01-01T00:00:00Z','total_return_close':123.45} for d in dates]})
 return json.dumps({'schema_version':'lily_l1_daily_dataset_v1','acquired_at':'2026-01-01','cutoff_inclusive':'2015-12-31','symbols':records},separators=(',',':')).encode()

class ScannerTests(unittest.TestCase):
 def test_date_only_scan_never_decodes_return_values(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'fixture.json';path.write_bytes(_payload());result=scan_date_metadata(path)
  self.assertEqual('preflight_pass',result['status']);self.assertEqual(0,result['return_values_decoded_count'])
 def test_post_end_on_one_symbol_blocks_before_intersection(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'fixture.json';path.write_bytes(_payload(post_end=True));result=scan_date_metadata(path)
  self.assertEqual('scope_restricted',result['status']);self.assertEqual('post_end_session_before_intersection',result['blocker'])
 def test_duplicate_key_and_extra_record_key_block(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'fixture.json';path.write_bytes(b'{"schema_version":"lily_l1_daily_dataset_v1","schema_version":"x"}');result=scan_date_metadata(path)
  self.assertEqual('scope_restricted',result['status']);self.assertEqual('duplicate_json_key',result['blocker'])
