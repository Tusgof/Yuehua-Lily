from __future__ import annotations

import unittest

from lib.environment import require_configured_path


class DataRootStateAuditTests(unittest.TestCase):
    def test_configured_data_root_is_a_directory(self) -> None:
        root = require_configured_path("LILY_DATA_ROOT")
        self.assertTrue(root.is_dir(), "LILY_DATA_ROOT must resolve to a readable directory")


if __name__ == "__main__":
    unittest.main()
