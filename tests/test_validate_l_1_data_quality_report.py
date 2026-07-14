from __future__ import annotations

import unittest

from scripts.validate_l_1_data_quality_report import EXPECTED_CONTRACT_HASH


class L1DataQualityReportValidatorTests(unittest.TestCase):
    def test_validator_is_bound_to_locked_contract(self) -> None:
        self.assertEqual("1fe4957f667bdf367d230048ac279fbdf9b4b2b109540dcdf5a54900e1c7cdb9", EXPECTED_CONTRACT_HASH)


if __name__ == "__main__":
    unittest.main()
