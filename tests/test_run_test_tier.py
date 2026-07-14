from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts.run_test_tier import run_tier


class TestTierRunnerTests(unittest.TestCase):
    def test_missing_data_root_skips_loudly_with_variable_name(self) -> None:
        output = io.StringIO()
        with patch("scripts.run_test_tier.configured_path", return_value=None), redirect_stdout(output):
            passed = run_tier("state-audit", verbosity=0)
        self.assertTrue(passed)
        self.assertIn("SKIP state-audit: missing LILY_DATA_ROOT", output.getvalue())


if __name__ == "__main__":
    unittest.main()
