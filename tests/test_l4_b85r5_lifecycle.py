from __future__ import annotations
import copy,hashlib,json,shutil,tempfile,unittest
from datetime import date,timedelta
from pathlib import Path
from lib.l4_b85r5_structural_scanner_v6 import MAX_BYTES,PAYLOAD_SCHEMA,U8,ScanError,scan_payload
from scripts.run_l_4_breadth_b85r5_phase_b_preflight_v6 import GATE_ID,MANIFEST_RELATIVE,PAYLOAD_RELATIVE,activation,artifact,blocked,identities,main,run_one_shot,structural
from scripts.validate_l_4_breadth_b85r5_phase_a_activation_order_v6 import validate as validate_gate
from scripts.validate_l_4_breadth_b85r5_structural_preflight_report_v6 import MANIFEST,PAYLOAD,validate

def accepted(head="a"*40):
 return json.dumps({"schema_version":"lily_l4_b85r5_phase_b_activation_v6","gate_id":GATE_ID,"gate_sha256":identities()["phase_a_gate"]["sha256"],"accepted_gate_head_sha":head,"hermetic_ci_run_id":1,"hermetic_ci_head_sha":head,"inspector_decision":"ACCEPTED","owner_authorization_reference":"B8.5R5 Phase B owner authorization","scope":"one_structural_u8_preflight_only","validation_seal":{"status":"sealed_not_accessed","accessed":False}},separators=(",",":")).encode("ascii")
def accept_check(accepted_head,checkpoint,gate_hash):return accepted_head=="a"*40 and checkpoint=="b"*40 and gate_hash==identities()["phase_a_gate"]["sha256"]
def maximum():
 days=[(date(2000,1,1)+timedelta(days=i)).isoformat() for i in range(4096)]
 return json.dumps({"schema_version":PAYLOAD_SCHEMA,"symbol_sessions":[{"symbol":s,"session_dates":days} for s in U8]},separators=(",",":")).encode("ascii")
def real_valid(report):return validate(report,provenance_check=lambda p,c:True)["status"]
class V6Tests(unittest.TestCase):
 def setUp(self):self.report=structural(MANIFEST.read_bytes(),PAYLOAD.read_bytes())
 def test_gate_fixture_summary_and_capacity(self):
  self.assertEqual("pass",validate_gate()["status"]);self.assertEqual("pass",validate(self.report)["status"])
  raw=maximum();self.assertEqual(MAX_BYTES,len(raw));self.assertEqual(32768,scan_payload(raw)["session_count"])
  with self.assertRaises(ScanError):scan_payload(raw+b"x")
 def test_summary_rejects_valid_date_drift(self):
  report=copy.deepcopy(self.report);report["payload"]["session_dates_by_symbol"]["VTI"][0]="2015-12-29";self.assertEqual("blocked",validate(report)["status"])
 def test_every_blocked_category_validates(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/"root";out=Path(tmp)/"out";marker=Path(tmp)/"marker";(root/MANIFEST_RELATIVE).parent.mkdir(parents=True)
   cases=[]
   cases.append(blocked({"manifest":artifact(),"payload":artifact()},"data_root_unavailable",{"x":1}))
   cases.append(run_one_shot(root,report_path=out,attempt_marker_path=marker,activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=accept_check))
   root_error=Path(tmp)/"manifest_error";(root_error/MANIFEST_RELATIVE).mkdir(parents=True)
   cases.append(run_one_shot(root_error,report_path=Path(tmp)/"me.json",attempt_marker_path=Path(tmp)/"me.marker",activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=accept_check))
   root2=Path(tmp)/"over";(root2/MANIFEST_RELATIVE).parent.mkdir(parents=True);(root2/MANIFEST_RELATIVE).write_bytes(b"x"*(MAX_BYTES+1))
   cases.append(run_one_shot(root2,report_path=Path(tmp)/"over.json",attempt_marker_path=Path(tmp)/"over.marker",activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=accept_check))
   root3=Path(tmp)/"payload_missing";(root3/MANIFEST_RELATIVE).parent.mkdir(parents=True);shutil.copyfile(MANIFEST,root3/MANIFEST_RELATIVE)
   cases.append(run_one_shot(root3,report_path=Path(tmp)/"pm.json",attempt_marker_path=Path(tmp)/"pm.marker",activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=accept_check))
   root_payload_error=Path(tmp)/"payload_error";(root_payload_error/MANIFEST_RELATIVE).parent.mkdir(parents=True);shutil.copyfile(MANIFEST,root_payload_error/MANIFEST_RELATIVE);(root_payload_error/PAYLOAD_RELATIVE).mkdir()
   cases.append(run_one_shot(root_payload_error,report_path=Path(tmp)/"pe.json",attempt_marker_path=Path(tmp)/"pe.marker",activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=accept_check))
   root_payload_over=Path(tmp)/"payload_over";(root_payload_over/MANIFEST_RELATIVE).parent.mkdir(parents=True);shutil.copyfile(MANIFEST,root_payload_over/MANIFEST_RELATIVE);(root_payload_over/PAYLOAD_RELATIVE).write_bytes(b"x"*(MAX_BYTES+1))
   cases.append(run_one_shot(root_payload_over,report_path=Path(tmp)/"po.json",attempt_marker_path=Path(tmp)/"po.marker",activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=accept_check))
   root4=Path(tmp)/"struct_manifest";(root4/MANIFEST_RELATIVE).parent.mkdir(parents=True);(root4/MANIFEST_RELATIVE).write_bytes(b"{}");shutil.copyfile(PAYLOAD,root4/PAYLOAD_RELATIVE)
   cases.append(run_one_shot(root4,report_path=Path(tmp)/"sm.json",attempt_marker_path=Path(tmp)/"sm.marker",activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=accept_check))
   root5=Path(tmp)/"struct_payload";(root5/MANIFEST_RELATIVE).parent.mkdir(parents=True);shutil.copyfile(MANIFEST,root5/MANIFEST_RELATIVE);(root5/PAYLOAD_RELATIVE).write_bytes(b"{}")
   cases.append(run_one_shot(root5,report_path=Path(tmp)/"sp.json",attempt_marker_path=Path(tmp)/"sp.marker",activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=accept_check))
   root6=Path(tmp)/"mismatch";(root6/MANIFEST_RELATIVE).parent.mkdir(parents=True);raw=MANIFEST.read_bytes().replace(PAYLOAD.read_bytes() and json.loads(MANIFEST.read_text())["metadata_sha256"].encode(),b"0"*64);(root6/MANIFEST_RELATIVE).write_bytes(raw);shutil.copyfile(PAYLOAD,root6/PAYLOAD_RELATIVE)
   cases.append(run_one_shot(root6,report_path=Path(tmp)/"mm.json",attempt_marker_path=Path(tmp)/"mm.marker",activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=accept_check))
   for report in cases:self.assertEqual("pass",real_valid(report),report)
 def test_blocked_tampering_rejects(self):
  report=blocked({"manifest":artifact(),"payload":artifact()},"data_root_unavailable",{"x":1})
  for change in (lambda r:r.__setitem__("blocker",1),lambda r:r.__setitem__("blocker","unknown"),lambda r:r["artifacts"]["manifest"].__setitem__("read_count",1),lambda r:r["artifacts"].__setitem__("extra",{})):
   row=copy.deepcopy(report);change(row);self.assertEqual("blocked",real_valid(row))
 def test_activation_provenance_checks_and_cli_inert(self):
  self.assertIsNotNone(activation(accepted(),activation_head="b"*40,accepted_gate_check=accept_check))
  for raw,check in ((accepted("c"*40),accept_check),(accepted(),lambda *_:False),(accepted("f"*40),lambda *_:False)):
   self.assertIsNone(activation(raw,activation_head="b"*40,accepted_gate_check=check))
  self.assertEqual(2,main([]));self.assertEqual(2,main(["--wrong"]))
 def test_no_overwrite(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/"root";out=Path(tmp)/"out";marker=Path(tmp)/"marker";(root/MANIFEST_RELATIVE).parent.mkdir(parents=True);shutil.copyfile(MANIFEST,root/MANIFEST_RELATIVE);shutil.copyfile(PAYLOAD,root/PAYLOAD_RELATIVE)
   one=run_one_shot(root,report_path=out,attempt_marker_path=marker,activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=accept_check);h=(hashlib.sha256(out.read_bytes()).hexdigest(),hashlib.sha256(marker.read_bytes()).hexdigest());two=run_one_shot(root,report_path=out,attempt_marker_path=marker,activation_raw=accepted(),activation_head="b"*40,accepted_gate_check=accept_check)
   self.assertEqual("structural_pass",one["outcome"]);self.assertEqual("refused_already_consumed",two["outcome"]);self.assertEqual(h,(hashlib.sha256(out.read_bytes()).hexdigest(),hashlib.sha256(marker.read_bytes()).hexdigest()))
if __name__=="__main__":unittest.main()
