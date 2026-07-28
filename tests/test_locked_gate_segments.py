from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.validate_locked_gates as gates


class LockedGateSegmentsTests(unittest.TestCase):
 def test_current_two_segment_chain_passes(self): self.assertEqual("pass",gates.validate_locked_gates()["status"])
 def test_invalid_segment_registry_fails_closed(self):
  with tempfile.TemporaryDirectory() as temporary:
   registry=Path(temporary)/"segments.json";registry.write_text("{}",encoding="utf-8")
   with patch.object(gates,"SEGMENT_REGISTRY",registry): self.assertEqual("blocked",gates.validate_locked_gates()["status"])

if __name__ == "__main__": unittest.main()
