from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from scripts.validate_l_4_breadth_b85r3_phase_a_activation_order_v4 import GATE, validate
class B85R3GateTests(unittest.TestCase):
 def test_gate_passes(self): self.assertEqual("pass",validate()["status"])
 def test_capacity_or_activation_tamper_blocks(self):
  for mutate in (lambda p:p["future_phase_b_contract"].__setitem__("max_payload_bytes",1),lambda p:p["future_phase_b_contract"].__setitem__("repo_relative_activation_record_path","other.json"),lambda p:p["phase_a_authorizations"].__setitem__("environment",True)):
   payload=json.loads(GATE.read_text(encoding="utf-8")); mutate(payload)
   with tempfile.TemporaryDirectory() as temporary:
    path=Path(temporary)/"gate.json"; path.write_text(json.dumps(payload),encoding="utf-8"); self.assertEqual("blocked",validate(path)["status"])
if __name__=="__main__": unittest.main()
