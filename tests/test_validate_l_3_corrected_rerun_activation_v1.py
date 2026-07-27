from __future__ import annotations
import copy,tempfile,unittest
from pathlib import Path
from lib.io import load_json,write_json
from scripts.validate_l_3_corrected_rerun_activation_v1 import GATE,validate_activation
from scripts.run_l_3_corrected_rerun import _attestation
from scripts.validate_l_3_corrected_rerun_pre_return_schedule_v1 import validate_pre_return_schedule_attestation
class CorrectedRerunActivationTests(unittest.TestCase):
 def test_gate_passes(self):self.assertEqual('pass',validate_activation()['status'])
 def test_rejects_auth_source_and_unknown_drift(self):
  payload=load_json(GATE)
  cases=[(lambda x:x['authorizations'].update(validation_access_authorized=True),'authorization_drift'),(lambda x:x['source_binding']['b7_5_gate'].update(sha256='0'*64),'source_binding_mismatch:b7_5_gate'),(lambda x:x['execution_implementation'].update(runner_sha256='0'*64),'implementation_declaration_drift'),(lambda x:x.update(extra=True),'unknown_top_level_field:extra')]
  for change,blocker in cases:
   candidate=copy.deepcopy(payload);change(candidate)
   with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'gate.json';write_json(p,candidate);self.assertIn(blocker,validate_activation(p)['blockers'])
 def test_synthetic_date_only_attestation_never_selects_prestart(self):
  sessions=['2007-02-02','2007-02-05']+[f'2007-03-{n:02d}' for n in range(1,29)]
  identity={'path':'synthetic.json','sha256':'1'*64,'assets':['VTI','VGK','EWJ','VWO','IEF','TIP','GLD','DBC'],'schema':'lily_l1_daily_dataset_v1','date_column':'session_date'}
  att=_attestation(identity,sessions)
  self.assertTrue(all(value>='2007-02-05' for value in att['selected_decision_dates']))
if __name__=='__main__':unittest.main()
