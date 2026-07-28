from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
import scripts.run_l_4_breadth_b86r5_provisioning_v6 as runner
class Tests(unittest.TestCase):
 def test_main_dispatches_and_invalid_activation_has_no_marker_or_data_read(self):
  self.assertEqual(2,runner.main([]))
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/runner.ACTIVATION_RELATIVE).parent.mkdir(parents=True);(root/runner.ACTIVATION_RELATIVE).write_bytes(b"{}")
   result=runner.run_phase_b(root=root,head="b"*40,blob_loader=lambda *_:b"{}",gate_check=lambda *_:True)
   self.assertEqual({"outcome":"refused_activation","dataset_read_count":0},result);self.assertFalse((root/runner.MARKER_RELATIVE).exists())
 def test_marker_precedes_missing_data_and_repeat_preserves_first(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);gate=root/runner.GATE_RELATIVE;gate.parent.mkdir(parents=True);gate.write_text("{}",encoding="ascii");sha=runner.gate_sha(root);head="b"*40
   raw=runner.canonical({"schema_version":"lily_l4_b86r5_provisioning_activation_v6","gate_id":"l_4_breadth_b86r5_provisioning_gate_v6","gate_sha256":sha,"accepted_gate_head_sha":"a"*40,"hermetic_ci_head_sha":"a"*40,"hermetic_ci_run_id":1,"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.6R5 one-shot owner authorization","scope":"one_repo_relative_falsification_container_provisioning_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}});p=root/runner.ACTIVATION_RELATIVE;p.parent.mkdir(parents=True);p.write_bytes(raw)
   check=lambda a,c,s:a=="a"*40 and c==head and s==sha
   first=runner.run_phase_b(root=root,head=head,blob_loader=lambda *_:raw,gate_check=check);self.assertEqual("dataset_missing",first["blocker"]);saved=(root/runner.REPORT_RELATIVE).read_bytes();second=runner.run_phase_b(root=root,head=head,blob_loader=lambda *_:raw,gate_check=check);self.assertEqual("refused_already_consumed",second["outcome"]);self.assertEqual(saved,(root/runner.REPORT_RELATIVE).read_bytes())
if __name__=="__main__":unittest.main()
