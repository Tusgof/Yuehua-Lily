from __future__ import annotations
import copy,json,tempfile,unittest
from pathlib import Path
import scripts.run_l_4_breadth_b86r4_provisioning_v5 as runner
from scripts.validate_l_4_breadth_b86r4_provisioning_gate_v5 import validate as gate_validate
from scripts.validate_l_4_breadth_b86r4_provisioning_report_v5 import validate
from tests.test_l4_b86r2_provisioning import source
def accepted():
 return runner.canonical({"schema_version":"lily_l4_b86r4_provisioning_activation_v5","gate_id":runner.GATE_ID,"gate_sha256":runner.identities()["phase_a_gate"]["sha256"],"accepted_gate_head_sha":"a"*40,"hermetic_ci_head_sha":"a"*40,"hermetic_ci_run_id":1,"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.6R4 one-shot owner authorization","scope":"one_repo_relative_falsification_container_provisioning_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}})
def accepted_gate_check(accepted_head,checkpoint_head,gate_sha):return accepted_head=="a"*40 and len(checkpoint_head)==40 and gate_sha==runner.identities()["phase_a_gate"]["sha256"]
class Tests(unittest.TestCase):
 def test_gate(self):self.assertEqual("pass",gate_validate()["status"])
 def test_coherent_cross_binding_forgery_is_rejected(self):
  report=runner.structural(source());self.assertEqual("pass",validate(report)["status"])
  forged=copy.deepcopy(report);m,p=forged["manifest"],forged["payload"];m["coverage_by_symbol"]["VTI"]["row_count"]=9;m["session_count"]+=7
  forged["structural_summary_sha256"]=__import__("hashlib").sha256(runner.canonical({"manifest":m,"payload":p})).hexdigest()
  for name,value,path in (("manifest",m,runner.ROOT/runner.MANIFEST_RELATIVE),("payload",p,runner.ROOT/runner.PAYLOAD_RELATIVE)):forged["output_artifacts"][name]=runner.identity(path,runner.canonical(value))
  self.assertEqual("blocked",validate(forged)["status"])
 def test_production_requires_tracked_activation_blob(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);data=root/"input";data.write_bytes(source());raw=accepted();report=runner.run_one_shot(data,report_path=root/"report",marker_path=root/"marker",manifest_path=root/"manifest",payload_path=root/"payload",activation_raw=raw,activation_head=runner.git_commit(runner.ROOT),accepted_gate_check=accepted_gate_check)
   self.assertEqual("dataset_hash_mismatch",report["blocker"]);self.assertEqual("blocked",validate(report)["status"])
   self.assertEqual("pass",validate(report,blob_loader=lambda *_:raw,accepted_gate_check=accepted_gate_check)["status"])
   for loader,mutation in ((lambda *_:None,None),(lambda *_:b"{}",None),(lambda *_:b'{ }',None),(lambda *_:raw,lambda x:x["activation_provenance"]["content"].__setitem__("hermetic_ci_run_id",2)),(lambda *_:raw,lambda x:x.__setitem__("producing_git_commit","0"*40))):
    changed=copy.deepcopy(report)
    if mutation:mutation(changed)
    self.assertEqual("blocked",validate(changed,blob_loader=loader,accepted_gate_check=accepted_gate_check)["status"])
 def test_nested_output_drift_and_extra_fields_are_rejected(self):
  report=runner.structural(source())
  for mutation in (lambda x:x["payload"]["session_dates_by_symbol"]["VTI"].append("2015-12-31"),lambda x:x["manifest"]["coverage_by_symbol"]["VTI"].__setitem__("extra",1),lambda x:x["payload"].__setitem__("extra",1)):
   changed=copy.deepcopy(report);mutation(changed);self.assertEqual("blocked",validate(changed)["status"])
if __name__=="__main__":unittest.main()
