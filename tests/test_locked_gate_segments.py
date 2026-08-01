from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.validate_locked_gates as gates


class LockedGateSegmentsTests(unittest.TestCase):
 def test_current_two_segment_chain_passes(self): self.assertEqual("pass",gates.validate_locked_gates()["status"])
 def test_b88r4_manifest_hash_recovery_is_exact(self):
  baseline=subprocess.check_output(["git","show","8f3b432232d30a7ae4c23857693e7c2cb036a8e8:experiments/locked_gates_v2.jsonl"],cwd=gates.PROJECT_ROOT,text=True).splitlines()
  current=[line for line in (gates.PROJECT_ROOT/"experiments/locked_gates_v2.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
  self.assertTrue(gates._is_exact_b88r4_manifest_hash_recovery(current,baseline))
  current[-1]=current[-1].replace("8242f8d", "9242f8d", 1)
  self.assertFalse(gates._is_exact_b88r4_manifest_hash_recovery(current,baseline))
 def test_invalid_segment_registry_fails_closed(self):
  with tempfile.TemporaryDirectory() as temporary:
   registry=Path(temporary)/"segments.json";registry.write_text("{}",encoding="utf-8")
   with patch.object(gates,"SEGMENT_REGISTRY",registry): self.assertEqual("blocked",gates.validate_locked_gates()["status"])

if __name__ == "__main__": unittest.main()
