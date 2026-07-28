from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from scripts.validate_l_4_breadth_b85_phase_a_activation_order_v2 import GATE, validate
class B85RemediationTests(unittest.TestCase):
 def test_gate_passes(self): self.assertEqual('pass',validate()['status'])
 def test_unlocked_resolution_or_machine_drift_blocks(self):
  for mutate in (lambda p:p['future_phase_b_contract'].__setitem__('storage_root_variable','OTHER'),lambda p:p['future_phase_b_contract'].__setitem__('one_shot_real_preflight_maximum',2),lambda p:p['implementation']['scanner'].__setitem__('sha256','0'*64),lambda p:p['phase_a_authorizations'].__setitem__('environment',True)):
   p=json.loads(GATE.read_text(encoding='utf-8')); mutate(p)
   with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'gate.json'; path.write_text(json.dumps(p),encoding='utf-8'); self.assertEqual('blocked',validate(path)['status'])
if __name__=='__main__': unittest.main()
