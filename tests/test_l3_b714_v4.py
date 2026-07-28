from __future__ import annotations
import unittest
from lib.l3_b714_date_only_scanner_v4 import skip_return_number_lexeme,skip_timestamp_lexeme
from scripts.validate_l_3_b714_v3_timestamp_decode_violation_addendum_v1 import validate as addendum
from scripts.validate_l_3_b714_date_only_preflight_remediation_v4 import validate as gate
from scripts.validate_l_3_b714_date_only_preflight_report_v4 import validate_static
class Tests(unittest.TestCase):
 def test_addendum_and_e0_gate(self):self.assertEqual('pass',addendum()['status']);self.assertEqual('pass',gate()['status'])
 def test_byte_only_skips(self):self.assertTrue(skip_timestamp_lexeme('ไทย'.encode().join((b'"',b'"'))));self.assertTrue(skip_return_number_lexeme(b'-1.2e3'));self.assertFalse(skip_return_number_lexeme(b'"1"'))
 def test_static_transitive_guard(self):self.assertEqual('pass',validate_static()['status'])
