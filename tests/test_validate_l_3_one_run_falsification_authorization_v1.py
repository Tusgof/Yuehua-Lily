from __future__ import annotations
import copy, tempfile, unittest
from pathlib import Path
from lib.io import load_json, write_json
from scripts.validate_l_3_one_run_falsification_authorization_v1 import GATE, validate_authorization
class AuthorizationTests(unittest.TestCase):
 def test_passes(self): self.assertEqual('pass',validate_authorization()['status'])
 def test_rejects_authorization_drift_and_unknown_fields(self):
  payload=load_json(GATE)
  cases=[(lambda p:p['authorizations'].update(validation_access_authorized=True),'authorization_drift'),(lambda p:p['source_binding']['l1'].update(sha256='0'*64),'source_binding_declaration_mismatch:l1'),(lambda p:p.update(extra=True),'unknown_top_level_field:extra')]
  for mutate,blocker in cases:
   with self.subTest(blocker=blocker):
    candidate=copy.deepcopy(payload);mutate(candidate)
    with tempfile.TemporaryDirectory() as d:
     path=Path(d)/'gate.json';write_json(path,candidate);self.assertIn(blocker,validate_authorization(path)['blockers'])
if __name__=='__main__': unittest.main()
