import json
import unittest
from pathlib import Path
from scripts.validate_l_3_b714_preflight_report_v2 import validate
ROOT=Path(__file__).resolve().parents[1]
def report(): return json.loads((ROOT/'tests/fixtures/l3_b714_preflight_v1/report_v2.json').read_text())
class Tests(unittest.TestCase):
 def test_approved_fixture_only(self): self.assertEqual('pass',validate(report())['status'])
 def test_rehashed_alternate_rejected(self):
  x=report();x['synthetic_date_metadata']['symbols']['VTI'][-1]='2007-03-08';x['provenance']['fixture_metadata_sha256']=__import__('hashlib').sha256(json.dumps(x['synthetic_date_metadata'],sort_keys=True,separators=(',',':')).encode()).hexdigest();self.assertEqual('blocked',validate(x)['status'])
if __name__=='__main__':unittest.main()
