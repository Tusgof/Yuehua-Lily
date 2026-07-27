from __future__ import annotations
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from scripts.validate_l_3_corrected_rerun_report import ACTIVATION,validate_report
class CorrectedRerunReportTests(unittest.TestCase):
 def _report(self):
  return {'schema_version':'lily_l3_corrected_rerun_falsification_report_v1','order_id':'B7.6','hypothesis_id':'L-3','rerun_id':'L-3-B7.5-CORRECTED-RERUN-ONE','evidence_tier':'E1','edge_claim':'none','producing_git_commit':'0'*40,'activation_sha256':hashlib.sha256(ACTIVATION.read_bytes()).hexdigest(),'container_sha256':None,'schedule_attestation_sha256':None,'validation_seal':{'start':'2016-01-04','end':'2026-06-30','status':'sealed_not_accessed','validation_access_authorized':False},'report_mode':'preflight_failure','decision':'scope_restricted','market_returns_read':False,'pre_return_schedule_attestation':None,'observation_counts':None,'primary_statistics':None,'realized_confirmation':None,'side_effects':None,'regimes':{'claims':[],'rule':'no regime pooling'},'mechanism_autopsy':None,'claim_limits':['E1 only']}
 def test_scope_fixture_passes_and_unknown_field_fails(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'report.json'; path.write_text(json.dumps(self._report()),encoding='utf-8')
   self.assertEqual('pass',validate_report(path)['status'])
   p=self._report();p['forged']=True;path.write_text(json.dumps(p),encoding='utf-8')
   self.assertIn('unknown_field:forged',validate_report(path)['blockers'])
if __name__=='__main__':unittest.main()
