from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import scripts.run_l_4_breadth_b86r6_provisioning_v8 as runner
from scripts.validate_l_4_breadth_b86r6_provisioning_report_v8 import validate as validate_report
from unittest.mock import patch

class B86R6Tests(unittest.TestCase):
 def test_invalid_activation_is_zero_read_and_zero_marker(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary); path=root/runner.ACTIVATION; path.parent.mkdir(parents=True); path.write_bytes(b"{}")
   self.assertEqual({"outcome":"refused_activation","dataset_read_count":0},runner.run_one_shot(root=root,head="b"*40,blob_loader=lambda *_:b"{}",gate_check=lambda *_:True));self.assertFalse((root/runner.MARKER).exists())
 def test_missing_dataset_claims_first_and_repeat_preserves_marker(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary); gate=root/runner.GATE_PATH;gate.parent.mkdir(parents=True);gate.write_text("{}",encoding="ascii");sha=hashlib.sha256(gate.read_bytes()).hexdigest();head="b"*40
   activation={"schema_version":runner.ACTIVATION_SCHEMA,"gate_id":runner.GATE_ID,"gate_sha256":sha,"accepted_gate_head_sha":"a"*40,"hermetic_ci_head_sha":"a"*40,"hermetic_ci_run_id":1,"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.6R6 one-shot owner authorization","scope":"one_repo_relative_falsification_container_provisioning_only","validation_seal":runner.SEAL};raw=runner.canonical(activation);p=root/runner.ACTIVATION;p.parent.mkdir(parents=True);p.write_bytes(raw)
   check=lambda accepted, checkpoint, actual: accepted=="a"*40 and checkpoint==head and actual==sha
   first=runner.run_one_shot(root=root,head=head,blob_loader=lambda *_:raw,gate_check=check);self.assertEqual("dataset_missing",first["blocker"]);self.assertTrue((root/runner.MARKER).exists());self.assertEqual("refused_already_consumed",runner.run_one_shot(root=root,head=head,blob_loader=lambda *_:raw,gate_check=check)["outcome"])
 def test_cli_requires_exact_flag(self): self.assertEqual(2,runner.main([]))
 def test_synthetic_report_contract_accepts_only_coherent_output(self):
  raw=b"synthetic";digest=hashlib.sha256(raw).hexdigest();row=runner.artifact();row.update({"attempted_read_count":1,"read_count":1,"observed_byte_count":len(raw),"complete_read":True,"complete_raw_sha256":digest,"bounded_prefix_sha256":digest,"hash_count":1})
  scanned={"dataset_sha256":digest,"dataset_byte_count":len(raw),"coverage_by_symbol":{symbol:{"start":"2015-12-31","end":"2015-12-31","row_count":1} for symbol in runner.U8},"session_count":len(runner.U8),"max_session_date":"2015-12-31","session_dates_by_symbol":{symbol:["2015-12-31"] for symbol in runner.U8}}
  with patch("lib.l4_b86r6_contract_v8.scan_dataset",return_value=scanned):
   report=runner.base("synthetic_fixture",row,None)|runner.structural(raw,row)
  manifest_raw,payload_raw=runner.canonical(report["manifest"]),runner.canonical(report["payload"])
  report["output_artifacts"]={"manifest":{"path":runner.MANIFEST,"raw_sha256":hashlib.sha256(manifest_raw).hexdigest(),"byte_count":len(manifest_raw)},"payload":{"path":runner.PAYLOAD,"raw_sha256":hashlib.sha256(payload_raw).hexdigest(),"byte_count":len(payload_raw)}};report["structural_summary_sha256"]=hashlib.sha256(runner.canonical({"manifest":report["manifest"],"payload":report["payload"]})).hexdigest()
  self.assertEqual("pass",validate_report(report)["status"]);report["blocker"]="fabricated";self.assertEqual("blocked",validate_report(report)["status"])

if __name__ == "__main__": unittest.main()
