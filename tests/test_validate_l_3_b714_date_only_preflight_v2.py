from __future__ import annotations
import json,unittest
from scripts.validate_l_3_b714_pre_checkpoint_filesystem_metadata_incident_v1 import validate as incident
from scripts.validate_l_3_b714_date_only_preflight_activation_v2 import validate as gate
class Tests(unittest.TestCase):
 def test_incident_and_gate(self):self.assertEqual(incident()['status'],'pass');self.assertEqual(gate()['status'],'pass')
