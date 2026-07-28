from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from scripts.validate_l_4_breadth_b85r5_phase_b_result_v1 import PATH,validate
class PhaseBResultTests(unittest.TestCase):
 def test_consumed_blocked_result_passes(self):self.assertEqual("pass",validate()["status"])
 def test_result_tampering_blocks(self):
  value=json.loads(PATH.read_text(encoding="ascii"));value["command_exit_code"]=0
  with tempfile.TemporaryDirectory() as temporary:
   path=Path(temporary)/"result.json";path.write_text(json.dumps(value),encoding="ascii");self.assertEqual("blocked",validate(path)["status"])
if __name__=="__main__":unittest.main()
