from __future__ import annotations
import copy,json,unittest
from scripts.run_l_4_breadth_b85r5_phase_b_preflight_v6 import activation
from scripts.validate_l_4_breadth_b85r5_phase_b_activation_v6 import ACCEPTED,PATH,validate
class ActivationCheckpointTests(unittest.TestCase):
 def test_content_and_accepted_gate_proof_pass(self):self.assertEqual("pass",validate()["status"])
 def test_required_content_tampering_blocks(self):
  record=json.loads(PATH.read_text(encoding="ascii"));record["hermetic_ci_head_sha"]="0"*40
  self.assertIsNone(activation(json.dumps(record).encode("ascii"),activation_head=ACCEPTED))
if __name__=="__main__":unittest.main()
