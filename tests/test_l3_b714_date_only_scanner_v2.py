from __future__ import annotations
import ast,json,tempfile,unittest
from datetime import date,timedelta
from pathlib import Path
import lib.l3_b714_date_only_scanner_v2 as scanner
from lib.l3_b714_date_only_scanner_v2 import ASSETS,scan_date_only
def payload(n=25):
 dates=['2007-02-%02d'%x for x in (5,6,7,8,9,12,13,14,15,16,19,20,21,22,23,26,27,28)]+['2007-03-%02d'%x for x in (1,2,5,6,7,8,9)]
 dates=dates[:n]; return {'schema_version':'lily_l1_daily_dataset_v1','acquired_at':'x','cutoff_inclusive':'2015-12-31','symbols':[{'symbol':s,'records':[{'session_date':d,'availability_timestamp':'x','total_return_close':-1.2e3} for d in dates]} for s in ASSETS]}
class Tests(unittest.TestCase):
 def scan(self,x):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'x.json';p.write_bytes(x if isinstance(x,bytes) else json.dumps(x,separators=(',',':')).encode());return scan_date_only(p)
 def test_skip_path_has_no_semantic_converter(self):
  tree=ast.parse((Path(__file__).parents[1]/'lib/l3_b714_date_only_scanner_v2.py').read_text()); skips=[x for x in ast.walk(tree) if isinstance(x,ast.FunctionDef) and x.name in {'skip_value','skip_return_value'}]; names={x.id for skip in skips for x in ast.walk(skip) if isinstance(x,ast.Name)};self.assertFalse(names & {'float','int','Decimal','loads','load','decode'})
 def test_pass_and_return_counter(self):
  r=self.scan(payload());self.assertEqual(r['outcome'],'preflight_pass');self.assertEqual(r['counters']['forbidden_semantic_decode_count'],0)
 def test_duplicate_and_post_end(self):
  self.assertEqual(self.scan(b'{"schema_version":"x","schema_version":"x"}')['blocker'],'duplicate_json_key');x=payload();x['symbols'][0]['records'][-1]['session_date']='2016-01-04';self.assertEqual(self.scan(x)['blocker'],'post_end_session_before_intersection')
 def test_invalid_number_and_escape(self):
  raw=json.dumps(payload(),separators=(',',':')).replace('-1200.0','01').encode();self.assertEqual(self.scan(raw)['outcome'],'scope_restricted');self.assertEqual(self.scan(b'{"schema_version":"\\q"}')['outcome'],'scope_restricted')
 def test_return_lexeme_rejects_non_numbers_without_decoding(self):
  for value in ('"1"','true','null','{}','[]','01','NaN'):
   with self.subTest(value=value):
    raw=json.dumps(payload(),separators=(',',':')).replace('-1200.0',value).encode();self.assertEqual('invalid_total_return_close_lexeme',self.scan(raw)['blocker'])
 def test_empty_and_incomplete_t20_schedule_reject(self):
  self.assertEqual('empty_schedule',self.scan(payload(20))['blocker'])
 def test_weekly_ceiling_accepts_465_and_rejects_466(self):
  original=scanner.END
  try:
   scanner.END='2020-12-31'
   start=date(2007,2,5); common=[(start+timedelta(days=7*n)).isoformat() for n in range(485)]
   accepted=scanner._schedule({asset:common for asset in ASSETS});self.assertEqual(465,len(accepted['selected_decision_dates']))
   scanner.END='2021-01-07';too_many=common+[(start+timedelta(days=7*485)).isoformat()]
   with self.assertRaisesRegex(scanner.ScanError,'weekly_pair_ceiling_exceeded'): scanner._schedule({asset:too_many for asset in ASSETS})
  finally: scanner.END=original
